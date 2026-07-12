"""Production-hardening tool schemas and dispatch."""
from acli.production import sandbox, patch_engine, credentials, mcp_http, recovery, diagnostics, observability
from acli.tools.policy import ensure_network_allowed

MUTATING={"run_sandboxed","run_isolated","apply_unified_patch","mcp_http_call_tool"}

def _schema(name,description,properties=None,required=None):
    p={"type":"object","properties":properties or {}}
    if required: p["required"]=required
    return {"type":"function","function":{"name":name,"description":description,"parameters":p}}

SCHEMAS=[
 _schema("sandbox_status","Check Docker installation and daemon availability."),
 _schema("isolation_status","Show whether automatic isolation will use Docker or restricted native execution."),
 _schema("run_isolated","Run a command with automatic isolation: Docker when available, restricted no-shell native mode otherwise.",{"command":{"type":"string"},"image":{"type":"string"},"timeout":{"type":"integer"},"network":{"type":"boolean"},"memory_mb":{"type":"integer"},"cpus":{"type":"number"}},["command"]),
 _schema("run_sandboxed","Run a command in a restricted Docker container with resource/network limits.",{"command":{"type":"string"},"image":{"type":"string"},"timeout":{"type":"integer"},"network":{"type":"boolean"},"memory_mb":{"type":"integer"},"cpus":{"type":"number"}},["command"]),
 _schema("preview_unified_patch","Validate and preview a unified diff without applying it.",{"diff_text":{"type":"string"}},["diff_text"]),
 _schema("apply_unified_patch","Apply a unified diff after checkpointing; optionally run validation and rollback on failure.",{"diff_text":{"type":"string"},"run_check":{"type":"string"}},["diff_text"]),
 _schema("credential_status","Report whether a named environment/keychain credential exists without revealing it.",{"name":{"type":"string"}},["name"]),
 _schema("language_diagnostics","Run installed type-checkers, compilers, and linters based on project language."),
 _schema("mcp_http_list_tools","List tools from an MCP Streamable HTTP endpoint.",{"endpoint":{"type":"string"},"token_env":{"type":"string"}},["endpoint"]),
 _schema("mcp_http_call_tool","Call a tool through an MCP Streamable HTTP endpoint.",{"endpoint":{"type":"string"},"name":{"type":"string"},"arguments":{"type":"object"},"token_env":{"type":"string"}},["endpoint","name","arguments"]),
 _schema("recovery_status","Show persisted crash-recovery state for the workspace."),
 _schema("audit_metrics","Show counts from the local redacted audit log."),
]
NAMES={s["function"]["name"] for s in SCHEMAS}

def describe(name,args):
    if name=="run_isolated": return "run command with automatic safe isolation: "+str(args.get("command"))
    if name=="run_sandboxed": return "run command in Docker sandbox: "+str(args.get("command"))
    if name=="apply_unified_patch": return "apply a reviewed unified patch with rollback protection"
    if name=="mcp_http_call_tool": return "call MCP HTTP tool '"+str(args.get("name"))+"'"
    return name+"("+str(args)+")"

def dispatch(name,args,settings):
    ws=settings.workspace_dir
    if name=="sandbox_status": return sandbox.sandbox_status()
    if name=="isolation_status": return sandbox.isolation_status()
    if name=="run_isolated": return sandbox.run_isolated(ws,args["command"],args.get("image",sandbox.DEFAULT_IMAGE),args.get("timeout",300),args.get("network",False),args.get("memory_mb",1024),args.get("cpus",1.0))
    if name=="run_sandboxed": return sandbox.run_sandboxed(ws,args["command"],args.get("image",sandbox.DEFAULT_IMAGE),args.get("timeout",300),args.get("network",False),args.get("memory_mb",1024),args.get("cpus",1.0))
    if name=="preview_unified_patch": return patch_engine.preview_patch(ws,args["diff_text"])
    if name=="apply_unified_patch": return patch_engine.apply_patch(ws,args["diff_text"],args.get("run_check",""))
    if name=="credential_status": return credentials.secret_status(args["name"])
    if name=="language_diagnostics": return diagnostics.language_diagnostics(ws)
    if name=="mcp_http_list_tools": ensure_network_allowed(args["endpoint"],settings); return mcp_http.list_tools(args["endpoint"],args.get("token_env",""))
    if name=="mcp_http_call_tool": ensure_network_allowed(args["endpoint"],settings); return mcp_http.call_tool(args["endpoint"],args["name"],args["arguments"],args.get("token_env",""))
    if name=="recovery_status": return recovery.recovery_status(ws)
    if name=="audit_metrics": return observability.audit_metrics(ws)
    raise ValueError("Unknown production tool: "+name)
