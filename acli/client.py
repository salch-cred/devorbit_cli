"""Multi-key NVIDIA client with automatic rotation on rate limits.

Supports up to 10 NVIDIA API keys. When one key hits a rate limit (429),
it is temporarily cooled down and the next available key is used automatically.
This makes the loop engine faster by distributing load across multiple keys.
"""
import json
import time
import threading
from collections import deque


class ModelAuthError(Exception):
    """Raised for fatal, non-retryable errors (all keys invalid, model not found)."""


class ModelTransientError(Exception):
    """Raised for retryable errors (rate limit, timeout, 5xx)."""


class MultiKeyNvidiaClient:
    """NVIDIA client that rotates across multiple API keys for higher throughput."""

    def __init__(self, api_keys, base_url: str = "https://integrate.api.nvidia.com/v1"):
        # Accept a single key, comma-separated string, or list of keys
        if isinstance(api_keys, str):
            api_keys = [k.strip() for k in api_keys.split(",") if k.strip()]
        if not api_keys:
            raise ModelAuthError(
                "No NVIDIA_API_KEY set. Add at least one key to .env.\n"
                "You can add multiple keys comma-separated: NVIDIA_API_KEY=key1,key2,key3"
            )

        from openai import (
            OpenAI,
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            NotFoundError,
            RateLimitError,
            InternalServerError,
        )

        self._exc = {
            "conn": APIConnectionError,
            "timeout": APITimeoutError,
            "auth": AuthenticationError,
            "notfound": NotFoundError,
            "ratelimit": RateLimitError,
            "server": InternalServerError,
        }

        self._base_url = base_url
        self._keys = list(api_keys)
        self._clients = {}
        self._key_status = {}  # key -> {"available": bool, "cooldown_until": float, "requests": int, "errors": int}
        self._lock = threading.Lock()
        self._key_index = 0

        for key in self._keys:
            self._clients[key] = OpenAI(api_key=key, base_url=base_url)
            self._key_status[key] = {
                "available": True,
                "cooldown_until": 0,
                "requests": 0,
                "errors": 0,
                "last_used": 0,
            }

        # Backward compat: expose a single _client for code that checks it
        self._client = self._clients[self._keys[0]]

    @property
    def key_count(self):
        return len(self._keys)

    def key_stats(self):
        """Return stats for all keys (for dashboard/API)."""
        stats = []
        for i, key in enumerate(self._keys):
            s = self._key_status[key]
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
            stats.append({
                "index": i + 1,
                "key": masked,
                "available": s["available"] and time.time() > s["cooldown_until"],
                "requests": s["requests"],
                "errors": s["errors"],
                "cooldown_remaining": max(0, int(s["cooldown_until"] - time.time())),
            })
        return stats

    def _get_available_key(self):
        """Get the next available key (round-robin among available keys)."""
        with self._lock:
            now = time.time()
            available = [k for k in self._keys if now > self._key_status[k]["cooldown_until"]]
            if not available:
                # All keys on cooldown — find the one with shortest cooldown
                soonest = min(self._keys, key=lambda k: self._key_status[k]["cooldown_until"])
                wait = self._key_status[soonest]["cooldown_until"] - now
                if wait > 0:
                    self._log(f"[keys] All keys on cooldown, waiting {wait:.1f}s for next available")
                    time.sleep(min(wait, 30))  # Wait at most 30s
                return soonest

            # Round-robin among available keys
            self._key_index = (self._key_index + 1) % len(available)
            return available[self._key_index % len(available)]

    def _log(self, text):
        import os
        if os.environ.get("DEVOBIT_VERBOSE_KEYS", "").lower() in ("1", "true", "yes"):
            print(text)

    def _mark_rate_limited(self, key):
        """Put a key on cooldown after rate limit."""
        with self._lock:
            self._key_status[key]["cooldown_until"] = time.time() + 60  # 60s cooldown
            self._key_status[key]["errors"] += 1
            self._log(f"[keys] Key {self._keys.index(key)+1} rate-limited, cooling down 60s")

    def _mark_success(self, key):
        """Mark a key as successfully used."""
        with self._lock:
            self._key_status[key]["requests"] += 1
            self._key_status[key]["last_used"] = time.time()
            # Reset cooldown if it was set
            self._key_status[key]["cooldown_until"] = 0

    def chat(self, model: str, messages, tools=None, temperature: float = 0.4):
        """Returns {"content": str|None, "tool_calls": [...]}.
        Rotates keys on rate limit. Raises ModelTransientError or ModelAuthError.
        """
        tried_keys = set()
        last_error = None

        for attempt in range(len(self._keys)):
            key = self._get_available_key()
            if key in tried_keys:
                # Small delay to avoid tight loop
                time.sleep(0.5)
                key = self._get_available_key()
            tried_keys.add(key)
            client = self._clients[key]

            try:
                kwargs = {"model": model, "messages": messages, "temperature": temperature}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                completion = client.chat.completions.create(**kwargs)
                message = completion.choices[0].message
                tool_calls = []
                raw_calls = getattr(message, "tool_calls", None) or []
                for tc in raw_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
                self._mark_success(key)
                return {"content": message.content, "tool_calls": tool_calls}

            except self._exc["ratelimit"] as e:
                self._mark_rate_limited(key)
                last_error = ModelTransientError(str(e))
                self._log(f"[keys] Rate limit on key {self._keys.index(key)+1}, rotating to next")
                continue  # Try next key

            except (self._exc["timeout"], self._exc["conn"], self._exc["server"]) as e:
                with self._lock:
                    self._key_status[key]["errors"] += 1
                last_error = ModelTransientError(str(e))
                continue  # Try next key

            except (self._exc["auth"], self._exc["notfound"]) as e:
                with self._lock:
                    self._key_status[key]["errors"] += 1
                    self._key_status[key]["available"] = False
                last_error = ModelAuthError(str(e))
                # If all keys are invalid, raise immediately
                if all(not self._key_status[k]["available"] for k in self._keys):
                    raise ModelAuthError(
                        f"All {len(self._keys)} API keys are invalid. Check your .env file.\n"
                        f"Last error: {e}"
                    ) from e
                continue  # Try next key

        # All keys exhausted — raise last error
        if last_error:
            raise last_error
        raise ModelTransientError("All API keys exhausted without a response")


# Backward-compatible alias
NvidiaClient = MultiKeyNvidiaClient
