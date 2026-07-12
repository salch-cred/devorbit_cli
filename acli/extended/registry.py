"""Schemas and dispatch for v1 extended tools."""
from pathlib import Path
from acli.settings_store import BASE_DIR
from acli.extended import shell, checkpoints, project, documents, quality, security, mcp_client, plugins, providers, research, voice, dev_rescue
from acli.tools.policy import ensure_network_allowed
from acli.production.registry import SCHEMAS as PRODUCTION_SCHEMAS, MUTATING as PRODUCTION_MUTATING, NAMES as PRODUCTION_NAMES, describe as describe_production, dispatch as dispatch_production

MUTATING={"run_terminal","create_checkpoint","restore_checkpoint","build_project_index","quality_check","mcp_call_tool","run_plugin","record_audio","transcribe_audio","flaky_test_check","start_dev_process","stop_dev_process","reproduce_issue","create_debug_bundle","api_probe"}
MUTATING.update(PRODUCTION_MUTATING)

def _schema(name,description,properties=None,required=None):
    params={"type":"object","properties":properties or {}}
    if required: params["required"]=required
    return {"type":"function","function":{"name":name,"description":description,"parameters":params}}

SCHEMAS=[
 _schema("run_terminal","Run an approved shell command inside the workspace.",{"command":{"type":"string"},"timeout":{"type":"integer"}},["command"]),
 _schema("create_checkpoint","Snapshot workspace files before risky edits.",{"label":{"type":"string"}}),
 _schema("list_checkpoints","List saved workspace checkpoints."),
 _schema("restore_checkpoint","Restore files from a named checkpoint.",{"name":{"type":"string"}},["name"]),
 _schema("repo_map","List repository files for architecture understanding.",{"max_files":{"type":"integer"}}),
 _schema("build_project_index","Build a SQLite FTS code/document index."),
 _schema("search_project_index","Search the indexed repository.",{"query":{"type":"string"},"limit":{"type":"integer"}},["query"]),
 _schema("read_document","Extract text/OCR from PDF, DOCX, PPTX, XLSX, images, or text.",{"path":{"type":"string"},"max_chars":{"type":"integer"}},["path"]),
 _schema("security_scan","Scan the workspace for secrets and prompt-injection patterns."),
 _schema("quality_check","Run automatic tests, lint, build, or a supplied quality command.",{"preset":{"type":"string"}}),
 _schema("generate_changelog","Generate changelog lines from Git history.",{"limit":{"type":"integer"}}),
 _schema("mcp_list_tools","Connect to an MCP stdio server and list tools.",{"command":{"type":"string"}},["command"]),
 _schema("mcp_call_tool","Call a tool on an MCP stdio server.",{"command":{"type":"string"},"name":{"type":"string"},"arguments":{"type":"object"}},["command","name","arguments"]),
 _schema("list_skills","List installed local skills."),
 _schema("load_skill","Load a local skill instruction file.",{"name":{"type":"string"}},["name"]),
 _schema("list_plugins","List installed Python plugins."),
 _schema("run_plugin","Run an installed Python plugin with a JSON payload.",{"name":{"type":"string"},"payload":{"type":"object"}},["name","payload"]),
 _schema("provider_status","Show configured OpenAI-compatible providers."),
 _schema("research_web","Research a topic from several web sources and return source-labelled extracts.",{"query":{"type":"string"},"max_sources":{"type":"integer"}},["query"]),
 _schema("speak_text","Speak text with the operating system voice.",{"text":{"type":"string"}},["text"]),
 _schema("record_audio","Record microphone audio with ffmpeg.",{"seconds":{"type":"integer"},"filename":{"type":"string"}}),
 _schema("transcribe_audio","Send a workspace audio file to the selected provider transcription endpoint.",{"path":{"type":"string"},"model":{"type":"string"}},["path"]),
 _schema("project_doctor","Collect runtime, toolchain, disk, project, Git, and environment diagnostics."),
 _schema("diagnose_error","Classify a stack trace or CLI error and recommend concrete next steps.",{"error_text":{"type":"string"}},["error_text"]),
 _schema("diagnose_log_file","Diagnose the tail of a workspace log file.",{"path":{"type":"string"},"tail_chars":{"type":"integer"}},["path"]),
 _schema("environment_doctor","Compare .env.example and .env variable names without exposing values."),
 _schema("dependency_doctor","Check Python, npm, Go, or Rust dependency consistency."),
 _schema("analyze_merge_conflicts","List unmerged files and conflict-block counts."),
 _schema("flaky_test_check","Run the same test command repeatedly and report flaky outcomes.",{"command":{"type":"string"},"runs":{"type":"integer"},"timeout":{"type":"integer"}},["command"]),
 _schema("inspect_port","Check whether a local port is occupied and identify its process when possible.",{"port":{"type":"integer"}},["port"]),
 _schema("start_dev_process","Start a named background development process with persistent logs.",{"command":{"type":"string"},"name":{"type":"string"}},["command"]),
 _schema("list_dev_processes","List background processes started by this CLI session."),
 _schema("dev_process_logs","Read logs from a named background development process.",{"name":{"type":"string"},"tail_chars":{"type":"integer"}},["name"]),
 _schema("stop_dev_process","Stop a named background development process.",{"name":{"type":"string"}},["name"]),
 _schema("reproduce_issue","Run a failing command and write a structured reproduction report.",{"command":{"type":"string"},"timeout":{"type":"integer"}},["command"]),
 _schema("create_debug_bundle","Create a sanitized diagnostic ZIP without source code or environment values.",{"output":{"type":"string"}}),
 _schema("api_probe","Probe an HTTP endpoint and report status, latency, safe headers, and response preview.",{"url":{"type":"string"},"method":{"type":"string"},"timeout":{"type":"integer"}},["url"]),
 _schema("container_doctor","Inspect Docker availability, daemon state, Compose configuration, and services."),
 _schema("database_migration_doctor","Inspect Alembic, Django, Prisma, or Knex migration status."),
]
SCHEMAS.extend(PRODUCTION_SCHEMAS)
NAMES={s["function"]["name"] for s in SCHEMAS}

def describe(name,args):
    if name=="run_terminal": return "run terminal command: "+str(args.get("command"))
    if name=="restore_checkpoint": return "restore checkpoint '"+str(args.get("name"))+"'"
    if name=="run_plugin": return "run plugin '"+str(args.get("name"))+"'"
    if name=="mcp_call_tool": return "call MCP tool '"+str(args.get("name"))+"'"
    if name in PRODUCTION_NAMES: return describe_production(name,args)
    return name+"("+str(args)+")"

def dispatch(name,args,settings):
    ws=settings.workspace_dir
    if name=="run_terminal":
        if str(settings.terminal_policy).lower()=="deny": raise PermissionError("Terminal commands disabled in settings")
        if not getattr(settings,"allow_native_terminal",False):
            raise PermissionError("Unrestricted native terminal is disabled; use run_isolated or explicitly enable permissions.allow_native_terminal")
        return shell.run_command(ws,args["command"],args.get("timeout",120))
    if name=="create_checkpoint": return checkpoints.create_checkpoint(ws,args.get("label","checkpoint"))
    if name=="list_checkpoints": return checkpoints.list_checkpoints(ws)
    if name=="restore_checkpoint": return checkpoints.restore_checkpoint(ws,args["name"])
    if name=="repo_map": return project.repo_map(ws,args.get("max_files",1000))
    if name=="build_project_index": return project.build_index(ws)
    if name=="search_project_index": return project.search_index(ws,args["query"],args.get("limit",10))
    if name=="read_document": return documents.read_document(ws,args["path"],args.get("max_chars",20000))
    if name=="security_scan": return security.scan_workspace(ws)
    if name=="quality_check": return quality.quality_check(ws,args.get("preset","auto"))
    if name=="generate_changelog": return quality.generate_changelog(ws,args.get("limit",50))
    if name in ("mcp_list_tools","mcp_call_tool") and not settings.mcp_tools_enabled: raise PermissionError("MCP tools disabled in settings")
    if name=="mcp_list_tools": return mcp_client.mcp_list_tools(args["command"])
    if name=="mcp_call_tool": return mcp_client.mcp_call_tool(args["command"],args["name"],args["arguments"])
    if name=="list_skills": return plugins.list_skills(str(BASE_DIR))
    if name=="load_skill": return plugins.load_skill(str(BASE_DIR),args["name"])
    if name=="list_plugins": return plugins.list_plugins(str(BASE_DIR))
    if name=="run_plugin": return plugins.run_plugin(str(BASE_DIR),args["name"],args["payload"])
    if name=="provider_status": return providers.provider_status(str(BASE_DIR))
    if name=="research_web": return research.research_web(args["query"],settings,args.get("max_sources",5))
    if name=="speak_text": return voice.speak(args["text"])
    if name=="record_audio": return voice.record_audio(ws,args.get("seconds",5),args.get("filename","voice.wav"))
    if name=="transcribe_audio":
        base_url,api_key=providers.get_provider(str(BASE_DIR),settings.provider)
        return voice.transcribe_audio(ws,args["path"],api_key,base_url,args.get("model","whisper-1"))
    if name=="project_doctor": return dev_rescue.project_doctor(ws)
    if name=="diagnose_error": return dev_rescue.diagnose_error(args["error_text"])
    if name=="diagnose_log_file": return dev_rescue.diagnose_log_file(ws,args["path"],args.get("tail_chars",30000))
    if name=="environment_doctor": return dev_rescue.environment_doctor(ws)
    if name=="dependency_doctor": return dev_rescue.dependency_doctor(ws)
    if name=="analyze_merge_conflicts": return dev_rescue.analyze_merge_conflicts(ws)
    if name=="flaky_test_check": return dev_rescue.flaky_test_check(ws,args["command"],args.get("runs",5),args.get("timeout",300))
    if name=="inspect_port": return dev_rescue.inspect_port(args["port"])
    if name=="start_dev_process": return dev_rescue.start_dev_process(ws,args["command"],args.get("name","dev"))
    if name=="list_dev_processes": return dev_rescue.list_dev_processes()
    if name=="dev_process_logs": return dev_rescue.dev_process_logs(args["name"],args.get("tail_chars",12000))
    if name=="stop_dev_process": return dev_rescue.stop_dev_process(args["name"])
    if name=="reproduce_issue": return dev_rescue.reproduce_issue(ws,args["command"],args.get("timeout",300))
    if name=="create_debug_bundle": return dev_rescue.create_debug_bundle(ws,args.get("output","debug-bundle.zip"))
    if name=="api_probe":
        ensure_network_allowed(args["url"],settings)
        return dev_rescue.api_probe(args["url"],args.get("method","GET"),args.get("timeout",20))
    if name=="container_doctor": return dev_rescue.container_doctor(ws)
    if name=="database_migration_doctor": return dev_rescue.database_migration_doctor(ws)
    if name in PRODUCTION_NAMES: return dispatch_production(name,args,settings)
    raise ValueError("Unknown extended tool: "+name)
