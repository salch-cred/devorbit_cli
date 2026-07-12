"""MCP Streamable HTTP MVP with bearer-token environment lookup."""
import json, os, requests, uuid

def _headers(token_env):
    h={"Accept":"application/json, text/event-stream","Content-Type":"application/json","MCP-Protocol-Version":"2025-03-26"}
    token=os.environ.get(token_env,"") if token_env else ""
    if token: h["Authorization"]="Bearer "+token
    return h

def call(endpoint: str, method: str, params=None, token_env: str = "", timeout: int = 60):
    payload={"jsonrpc":"2.0","id":str(uuid.uuid4()),"method":method,"params":params or {}}
    response=requests.post(endpoint,headers=_headers(token_env),json=payload,timeout=timeout)
    response.raise_for_status()
    ctype=response.headers.get("content-type","")
    if "text/event-stream" in ctype:
        for line in response.text.splitlines():
            if line.startswith("data:"): return json.loads(line[5:].strip())
        raise RuntimeError("MCP SSE response contained no data event")
    return response.json()

def list_tools(endpoint,token_env=""): return json.dumps(call(endpoint,"tools/list",token_env=token_env),indent=2)[:30000]
def call_tool(endpoint,name,arguments,token_env=""): return json.dumps(call(endpoint,"tools/call",{"name":name,"arguments":arguments},token_env),indent=2)[:30000]
