"""Minimal MCP JSON-RPC stdio client with bounded, cross-platform reads."""
import json
import queue
import shlex
import subprocess
import threading
import time
from acli.production.environment import scrub_environment


class MCPClient:
    def __init__(self, command: str): self.command = command

    def _exchange(self, method, params=None, timeout=30):
        proc = subprocess.Popen(shlex.split(self.command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=scrub_environment())
        lines = queue.Queue()
        def reader():
            try:
                for line in proc.stdout: lines.put(line)
            finally: lines.put(None)
        thread = threading.Thread(target=reader, daemon=True); thread.start()
        requests = [
            {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"devorbit-cli","version":"2.1"}}},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":method,"params":params or {}},
        ]
        deadline = time.monotonic() + max(.05, float(timeout))
        try:
            for request in requests: proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise TimeoutError("MCP request timed out")
                try: line = lines.get(timeout=remaining)
                except queue.Empty as exc: raise TimeoutError("MCP request timed out") from exc
                if line is None:
                    error = proc.stderr.read()[-2000:] if proc.stderr else ""
                    raise RuntimeError("MCP server closed before responding" + (": " + error if error else ""))
                try: message = json.loads(line)
                except json.JSONDecodeError: continue
                if message.get("id") == 2:
                    if "error" in message: raise RuntimeError("MCP error: " + json.dumps(message["error"]))
                    return message.get("result")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=1)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    try: stream.close()
                    except Exception: pass
            thread.join(timeout=.2)

    def list_tools(self): return self._exchange("tools/list")
    def call_tool(self, name, args): return self._exchange("tools/call", {"name":name,"arguments":args})


def mcp_list_tools(command: str) -> str: return json.dumps(MCPClient(command).list_tools(), indent=2)[:20000]
def mcp_call_tool(command: str, name: str, arguments: dict) -> str: return json.dumps(MCPClient(command).call_tool(name, arguments), indent=2)[:20000]
