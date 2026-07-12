"""Fake client used by --mock so the loop engine can be demoed with zero network calls.

Simulates: model 1 rate-limits twice then fails, model 2 times out once then succeeds --
so you can watch the fallback and retry loops operate. Also simulates a single tool call
(list_files) when tools are enabled and you ask to list files, so you can watch the agent
tool-loop work end to end offline.
"""
import itertools

from acli.client import ModelAuthError, ModelTransientError

_call_counts = {}


class MockClient:
    def __init__(self, api_key: str = "mock", base_url: str = "mock"):
        self._counter = itertools.count()

    def chat(self, model: str, messages, tools=None, temperature: float = 0.4):
        _call_counts[model] = _call_counts.get(model, 0) + 1
        attempt = _call_counts[model]

        if "70b" in model and attempt <= 2:
            raise ModelTransientError("[mock] " + model + " is rate-limited (attempt " + str(attempt) + ")")
        if "mixtral" in model and attempt == 1:
            raise ModelTransientError("[mock] " + model + " timed out (attempt " + str(attempt) + ")")
        if "unknown" in model:
            raise ModelAuthError("[mock] " + model + " not found on this account")

        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        just_got_tool_result = bool(messages) and messages[-1]["role"] == "tool"

        if tools and not just_got_tool_result and last_user and "list files" in last_user.lower():
            return {
                "content": None,
                "tool_calls": [{"id": "mock-call-1", "name": "list_files", "arguments": {"path": "."}}],
            }

        if just_got_tool_result:
            tool_text = messages[-1]["content"]
            reply = "(mock reply from " + model + ") Based on the tool result:\n" + tool_text
        else:
            reply = (
                "(mock reply from " + model + ") You said: " + last_user + ". "
                "This is a simulated response so you can verify the loop engine offline."
            )
        return {"content": reply, "tool_calls": []}
