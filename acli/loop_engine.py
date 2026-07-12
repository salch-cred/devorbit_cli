"""Core loops: retry, fallback, context trim, tool calls, reflection, and autosave."""
import json
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from acli.client import ModelAuthError, ModelTransientError
from acli.history import estimate_tokens, save_history, load_history
from acli.tools.registry import TOOL_SCHEMAS, MUTATING_TOOLS, describe_call, dispatch
from acli.extended.router import ResponseCache, route_model
from acli.production.observability import AuditLog
from acli.production.recovery import RunState


class LoopExhaustedError(Exception):
    pass


class LoopEngine:
    def __init__(self, client, model_chain, settings, confirm_callback=None, enable_tools=True):
        self.client = client
        self.model_chain = list(model_chain)
        self.settings = settings
        self.enable_tools = enable_tools
        self.confirm_callback = confirm_callback or (lambda desc: True)
        self.messages = [{"role": "system", "content": settings.system_prompt}]
        self.last_model_used = None
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
        self.response_cache = ResponseCache(Path(settings.history_dir) / "response-cache.sqlite")
        self.audit = AuditLog(settings.workspace_dir)
        self.run_state = RunState(settings.workspace_dir)

    def _log(self, text):
        if self.settings.verbose_agent_chat:
            print(text)

    def _trim_history(self) -> None:
        budget = self.settings.max_context_tokens
        while len(self.messages) > 3:
            total = sum(estimate_tokens(str(m.get("content") or "")) for m in self.messages)
            if total <= budget:
                break
            first_user = next((i for i in range(1, len(self.messages)) if self.messages[i].get("role") == "user"), None)
            if first_user is None:
                break
            next_user = next((i for i in range(first_user + 1, len(self.messages)) if self.messages[i].get("role") == "user"), None)
            if next_user is None:
                break
            del self.messages[first_user:next_user]

    def _run_fallback_loop(self, messages, tools, forced_model=None):
        chain = ([forced_model] + [m for m in self.model_chain if m != forced_model]) if forced_model else self.model_chain
        errors = []
        for model in chain:
            for attempt in range(1, self.settings.max_retries_per_model + 1):
                try:
                    self._log("[loop] trying model: " + model + " (attempt " + str(attempt) + ")")
                    cache_key = self.response_cache.key(model, messages)
                    cached = self.response_cache.get(cache_key) if self.settings.response_cache and not tools else None
                    if cached is not None:
                        self._log("[cache] reused response for " + model)
                        self.last_model_used = model
                        return cached
                    result = self.client.chat(
                        model,
                        messages,
                        tools=tools,
                        temperature=self.settings.temperature,
                    )
                    self.last_model_used = model
                    if self.settings.response_cache and not tools:
                        self.response_cache.put(cache_key, result)
                    return result
                except ModelTransientError as exc:
                    errors.append(model + ": " + str(exc))
                    wait = self.settings.backoff_base_seconds * attempt
                    self._log("[loop] transient error, retrying in " + str(wait) + "s -- " + str(exc))
                    time.sleep(wait)
                except ModelAuthError as exc:
                    errors.append(model + ": " + str(exc))
                    self._log("[loop] fatal error on " + model + ", skipping -- " + str(exc))
                    break
        raise LoopExhaustedError("All models in the fallback chain failed:\n" + "\n".join(errors))

    def _execute_tool_call(self, call):
        name = call["name"]
        args = call["arguments"]
        desc = describe_call(name, args)
        self.audit.write("tool_requested", {"name": name, "description": desc})
        needs_confirmation = name in MUTATING_TOOLS
        if name.startswith("browser_") and name not in ("browser_navigate", "browser_inspect", "browser_screenshot", "browser_back", "browser_close"):
            needs_confirmation = self.settings.browser_confirm_actuation
        if needs_confirmation and not self.confirm_callback(desc):
            self.audit.write("tool_denied", {"name": name})
            return "Tool call denied by user: " + desc
        try:
            result = str(dispatch(name, args, self.settings))
            self.audit.write("tool_succeeded", {"name": name, "result_chars": len(result)})
            return result
        except Exception as exc:
            self.audit.write("tool_failed", {"name": name, "error": str(exc)})
            return "Tool error: " + str(exc)

    def send(self, user_text: str, forced_model: str = None, max_tool_iterations=None) -> str:
        max_iterations = max_tool_iterations or self.settings.max_tool_iterations
        if forced_model is None and self.settings.auto_route:
            forced_model = route_model(user_text, self.model_chain)
            self._log("[router] selected " + forced_model)
        self.messages.append({"role": "user", "content": user_text})
        self.run_state.save({"recoverable_run": True, "session_id": self.session_id, "stage": "model_or_tool_loop", "user_request": user_text[:1000]})
        self._trim_history()
        tools = TOOL_SCHEMAS if self.enable_tools else None
        for _ in range(max_iterations):
            result = self._run_fallback_loop(self.messages, tools, forced_model=forced_model)
            tool_calls = result.get("tool_calls") or []
            if tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": result.get("content"),
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    self._log("[tool] " + describe_call(tc["name"], tc["arguments"]))
                    tool_result = self._execute_tool_call(tc)
                    self._log("[tool result] " + tool_result[:500])
                    self.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": tool_result})
                self._autosave()
                continue
            content = result.get("content") or ""
            self.messages.append({"role": "assistant", "content": content})
            print(content)
            self._autosave()
            if self.settings.notifications:
                print("\a", end="", flush=True)
            self.run_state.clear()
            return content
        warning = "[loop] stopped after " + str(max_iterations) + " tool iterations without a final answer."
        print(warning)
        self._autosave()
        return warning

    def reflect(self) -> str:
        if not self.messages or self.messages[-1]["role"] != "assistant":
            return "Nothing to reflect on yet -- send a message first."
        return self.send("Carefully re-check your previous answer for mistakes, missing edge cases, or unclear parts. Then give an improved, corrected final answer.")

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": self.settings.system_prompt}]
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
        self.run_state.clear()

    def set_system_prompt(self, text: str) -> None:
        self.settings.system_prompt = text
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = text
        else:
            self.messages.insert(0, {"role": "system", "content": text})

    def _autosave(self):
        if not self.settings.autosave_conversations:
            return
        history_dir = Path(self.settings.history_dir)
        history_dir.mkdir(parents=True, exist_ok=True)
        messages = self.messages
        if not self.settings.save_tool_results:
            messages = [m for m in messages if m.get("role") != "tool"]
        save_history(str(history_dir / (self.session_id + ".json")), messages)
        files = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[self.settings.max_saved_conversations:]:
            try:
                old.unlink()
            except OSError:
                pass

    def save(self, path: str) -> None:
        save_history(path, self.messages)

    def load(self, path: str) -> None:
        self.messages = load_history(path)
        self._autosave()
