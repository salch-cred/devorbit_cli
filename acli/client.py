"""Thin OpenAI-compatible client wrapper for NVIDIA NIM endpoints (non-streaming, tool-call aware)."""
import json


class ModelAuthError(Exception):
    """Raised for fatal, non-retryable errors (bad API key, model not found, etc)."""


class ModelTransientError(Exception):
    """Raised for retryable errors (rate limit, timeout, 5xx)."""


class NvidiaClient:
    def __init__(self, api_key: str, base_url: str):
        if not api_key:
            raise ModelAuthError(
                "No NVIDIA_API_KEY set. Copy .env.example to .env and add your key."
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
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, model: str, messages, tools=None, temperature: float = 0.4):
        """Returns {"content": str|None, "tool_calls": [{"id", "name", "arguments"}]}.
        Raises ModelTransientError or ModelAuthError on failure.
        """
        try:
            kwargs = {"model": model, "messages": messages, "temperature": temperature}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            completion = self._client.chat.completions.create(**kwargs)
            message = completion.choices[0].message
            tool_calls = []
            raw_calls = getattr(message, "tool_calls", None) or []
            for tc in raw_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
            return {"content": message.content, "tool_calls": tool_calls}
        except (self._exc["ratelimit"], self._exc["timeout"], self._exc["conn"], self._exc["server"]) as e:
            raise ModelTransientError(str(e)) from e
        except (self._exc["auth"], self._exc["notfound"]) as e:
            raise ModelAuthError(str(e)) from e
