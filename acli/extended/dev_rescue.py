"""Developer Rescue Suite: diagnosis and recovery tools for difficult CLI development issues."""
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from acli.extended.security import scan_text
from acli.extended.shell import run_command
from acli.production.environment import scrub_environment

PROCESSES = {}

ERROR_RULES = [
    (re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)", re.I), "missing_python_module", "Install the missing Python package in the active environment and verify the interpreter path."),
    (re.compile(r"Cannot find module ['\"]([^'\"]+)", re.I), "missing_node_module", "Install dependencies and verify package.json plus the active Node working directory."),
    (re.compile(r"EADDRINUSE|address already in use", re.I), "port_in_use", "Inspect the occupied port, stop the old process, or choose another port."),
    (re.compile(r"permission denied|EACCES", re.I), "permission_denied", "Check file ownership, executable bits, workspace policy, and whether elevated access is actually required."),
    (re.compile(r"connection refused|ECONNREFUSED", re.I), "connection_refused", "Confirm the target service is running, the host/port is correct, and containers share the expected network."),
    (re.compile(r"timeout|timed out|ETIMEDOUT", re.I), "timeout", "Check service health, DNS, proxy/firewall rules, and increase timeout only after identifying the slow stage."),
    (re.compile(r"SSL|CERTIFICATE_VERIFY_FAILED|certificate", re.I), "tls_certificate", "Check system time, CA bundles, proxy interception, and certificate hostname/expiry."),
    (re.compile(r"SyntaxError|IndentationError|Unexpected token", re.I), "syntax_error", "Open the first referenced source location and run the language parser or formatter."),
    (re.compile(r"out of memory|ENOMEM|heap limit|Killed", re.I), "out_of_memory", "Measure memory use, reduce concurrency/input size, or raise the runtime memory limit."),
    (re.compile(r"merge conflict|<<<<<<<|CONFLICT \(", re.I), "merge_conflict", "List unmerged files, resolve each conflict marker, run tests, then stage the resolutions."),
    (re.compile(r"401|unauthorized|invalid.*token", re.I), "authentication", "Verify the credential source, expiration, scopes, endpoint, and accidental whitespace without printing the secret."),
    (re.compile(r"403|forbidden", re.I), "authorization", "Verify account/repository permissions, token scopes, organization policy, and branch protection."),
    (re.compile(r"429|rate.?limit", re.I), "rate_limit", "Use exponential backoff, inspect provider quotas, reduce concurrency, or route to a fallback model/service."),
    (re.compile(r"dependency conflict|ResolutionImpossible|ERESOLVE", re.I), "dependency_conflict", "Inspect incompatible version constraints, lockfiles, peer dependencies, and the minimal conflicting set."),
]


def _run(args, cwd=None, timeout=20):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        return {"ok": result.returncode == 0, "code": result.returncode, "output": output[-6000:]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "code": -1, "output": str(exc)}


def project_doctor(workspace: str) -> str:
    root = Path(workspace)
    report = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "cwd": str(root.resolve()),
        "disk_free_gb": round(shutil.disk_usage(root).free / 1024**3, 2),
        "tools": {},
        "project_markers": [],
        "git": _run(["git", "status", "--short", "--branch"], root),
    }
    for tool, version_args in {
        "git": ["git", "--version"], "node": ["node", "--version"], "npm": ["npm", "--version"],
        "python": [sys.executable, "--version"], "docker": ["docker", "--version"], "go": ["go", "version"],
        "rustc": ["rustc", "--version"], "java": ["java", "-version"],
    }.items():
        report["tools"][tool] = _run(version_args, root)["output"] or "not available"
    markers = ["pyproject.toml", "requirements.txt", "package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Dockerfile", "docker-compose.yml"]
    report["project_markers"] = [m for m in markers if (root / m).exists()]
    report["environment"] = environment_doctor(workspace)
    return json.dumps(report, indent=2)[:30000]


def diagnose_error(error_text: str) -> str:
    findings = []
    for pattern, category, fix in ERROR_RULES:
        match = pattern.search(error_text)
        if match:
            findings.append({"category": category, "evidence": match.group(0)[:300], "recommended_next_step": fix})
    if not findings:
        findings.append({"category": "unknown", "evidence": error_text[-500:], "recommended_next_step": "Capture the first error, full stack trace, command, runtime versions, and smallest reproduction. Run project_doctor and create_debug_bundle."})
    first_location = re.search(r"(?:File \"([^\"]+)\", line (\d+)|([^\s:]+\.(?:py|js|ts|go|rs|java)):(\d+))", error_text)
    return json.dumps({"diagnoses": findings, "first_source_location": first_location.group(0) if first_location else None}, indent=2)


def diagnose_log_file(workspace: str, path: str, tail_chars: int = 30000) -> str:
    root = Path(workspace).resolve(); target = (root / path).resolve()
    if root not in target.parents or not target.exists(): raise PermissionError("Log is outside workspace or missing")
    text = target.read_text(encoding="utf-8", errors="replace")[-tail_chars:]
    return diagnose_error(text)


def environment_doctor(workspace: str) -> str:
    root = Path(workspace)
    example = root / ".env.example"; actual = root / ".env"
    def keys(path):
        if not path.exists(): return set()
        found=set()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line=line.strip()
            if line and not line.startswith("#") and "=" in line: found.add(line.split("=",1)[0].strip())
        return found
    expected, present = keys(example), keys(actual)
    return json.dumps({"env_example_exists": example.exists(), "env_exists": actual.exists(), "missing_keys": sorted(expected-present), "extra_keys": sorted(present-expected), "values_exposed": False}, indent=2)


def dependency_doctor(workspace: str) -> str:
    root = Path(workspace); checks=[]
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        checks.append(("python_dependency_consistency", _run([sys.executable, "-m", "pip", "check"], root, 60)))
    if (root / "package.json").exists():
        checks.append(("npm_dependency_tree", _run(["npm", "ls", "--depth=0"], root, 90)))
    if (root / "go.mod").exists(): checks.append(("go_modules", _run(["go", "mod", "verify"], root, 90)))
    if (root / "Cargo.toml").exists(): checks.append(("cargo_metadata", _run(["cargo", "metadata", "--no-deps", "--format-version", "1"], root, 90)))
    if not checks: return "No supported dependency manifest detected."
    return json.dumps({name: result for name, result in checks}, indent=2)[:30000]


def analyze_merge_conflicts(workspace: str) -> str:
    root=Path(workspace); unmerged=_run(["git","diff","--name-only","--diff-filter=U"],root)
    files=[x for x in unmerged["output"].splitlines() if x.strip()]; details=[]
    for rel in files:
        path=root/rel
        try:
            text=path.read_text(encoding="utf-8",errors="replace")
            blocks=len(re.findall(r"^<<<<<<< ",text,re.M))
            details.append({"file":rel,"conflict_blocks":blocks})
        except OSError: details.append({"file":rel,"conflict_blocks":None})
    return json.dumps({"unmerged_files":details,"next_steps":["Resolve every conflict block","Run tests","git add resolved files","Continue merge/rebase"]},indent=2)


def flaky_test_check(workspace: str, command: str, runs: int = 5, timeout: int = 300) -> str:
    runs=max(2,min(runs,20)); outcomes=[]
    for i in range(runs):
        started=time.time()
        result=subprocess.run(command,cwd=workspace,shell=True,capture_output=True,text=True,timeout=timeout)
        outcomes.append({"run":i+1,"passed":result.returncode==0,"seconds":round(time.time()-started,2),"tail":((result.stdout or "")+(result.stderr or ""))[-1500:]})
    passed=sum(1 for x in outcomes if x["passed"])
    return json.dumps({"runs":runs,"passed":passed,"failed":runs-passed,"flaky":0<passed<runs,"outcomes":outcomes},indent=2)[:30000]


def inspect_port(port: int) -> str:
    port=int(port)
    listening=False
    with socket.socket() as sock:
        sock.settimeout(0.5)
        listening=sock.connect_ex(("127.0.0.1",port))==0
    commands=[]
    if shutil.which("lsof"): commands=["lsof","-nP","-iTCP:"+str(port),"-sTCP:LISTEN"]
    elif os.name=="nt": commands=["netstat","-ano"]
    else: commands=["ss","-ltnp"]
    process=_run(commands,timeout=10) if commands else {"output":"No process inspector available"}
    return json.dumps({"port":port,"listening":listening,"process_info":process.get("output","")},indent=2)


def start_dev_process(workspace: str, command: str, name: str = "dev") -> str:
    lowered=command.strip().lower()
    if any(lowered.startswith(x) for x in ("rm -rf /","mkfs","format ","shutdown","reboot")):
        raise PermissionError("Background command blocked by hard safety policy")
    if name in PROCESSES and PROCESSES[name]["process"].poll() is None: raise RuntimeError("Process name already running: "+name)
    logs=Path(workspace)/".devorbit-processes"; logs.mkdir(parents=True,exist_ok=True); log_path=logs/(name+".log")
    handle=log_path.open("a",encoding="utf-8")
    proc=subprocess.Popen(command,cwd=workspace,shell=True,stdout=handle,stderr=subprocess.STDOUT,text=True,start_new_session=(os.name!="nt"),env=scrub_environment())
    PROCESSES[name]={"process":proc,"command":command,"log":str(log_path),"handle":handle,"started":time.time()}
    return json.dumps({"name":name,"pid":proc.pid,"log":str(log_path),"command":command})


def list_dev_processes() -> str:
    rows=[]
    for name,item in PROCESSES.items():
        proc=item["process"]; rows.append({"name":name,"pid":proc.pid,"running":proc.poll() is None,"exit_code":proc.poll(),"command":item["command"],"log":item["log"]})
    return json.dumps(rows,indent=2)


def dev_process_logs(name: str, tail_chars: int = 12000) -> str:
    if name not in PROCESSES: raise KeyError(name)
    path=Path(PROCESSES[name]["log"])
    return path.read_text(encoding="utf-8",errors="replace")[-tail_chars:] if path.exists() else "No logs yet."


def stop_dev_process(name: str) -> str:
    if name not in PROCESSES: raise KeyError(name)
    item=PROCESSES[name]; proc=item["process"]
    if proc.poll() is None:
        if os.name!="nt": os.killpg(proc.pid,signal.SIGTERM)
        else: proc.terminate()
        try: proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            if os.name!="nt": os.killpg(proc.pid,signal.SIGKILL)
            else: proc.kill()
    item["handle"].close()
    return "Stopped "+name+" with exit code "+str(proc.poll())

def stop_all_dev_processes() -> None:
    for name in list(PROCESSES):
        try: stop_dev_process(name)
        except Exception: pass


def reproduce_issue(workspace: str, command: str, timeout: int = 300) -> str:
    result=run_command(workspace,command,timeout)
    report={"command":command,"result":result,"doctor":json.loads(project_doctor(workspace)),"timestamp":time.time()}
    path=Path(workspace)/"issue-reproduction.json"; path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return "Created "+str(path)+"\n"+result[-12000:]


def create_debug_bundle(workspace: str, output: str = "debug-bundle.zip") -> str:
    root=Path(workspace).resolve(); target=root/Path(output).name; temp=root/".devorbit-debug-bundle"; shutil.rmtree(temp,ignore_errors=True); temp.mkdir()
    (temp/"doctor.json").write_text(project_doctor(workspace),encoding="utf-8")
    (temp/"dependencies.json").write_text(dependency_doctor(workspace),encoding="utf-8")
    (temp/"merge-conflicts.json").write_text(analyze_merge_conflicts(workspace),encoding="utf-8")
    for candidate in ("package.json","pyproject.toml","requirements.txt","go.mod","Cargo.toml","Dockerfile"):
        src=root/candidate
        if src.exists(): shutil.copy2(src,temp/candidate)
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
        for path in temp.rglob("*"):
            if path.is_file(): z.write(path,path.relative_to(temp))
    shutil.rmtree(temp,ignore_errors=True)
    return "Created sanitized debug bundle "+str(target)+" (environment variable values and source files excluded)"


def api_probe(url: str, method: str = "GET", timeout: int = 20) -> str:
    import requests
    started=time.time()
    response=requests.request(method.upper(),url,timeout=max(1,min(timeout,120)),allow_redirects=True)
    safe_headers={k:v for k,v in response.headers.items() if k.lower() not in ("set-cookie","authorization","proxy-authorization")}
    return json.dumps({"method":method.upper(),"requested_url":url,"final_url":response.url,"status":response.status_code,"seconds":round(time.time()-started,3),"headers":safe_headers,"body_preview":response.text[:4000]},indent=2)


def container_doctor(workspace: str) -> str:
    root=Path(workspace); report={"docker_version":_run(["docker","--version"],root),"docker_info":_run(["docker","info"],root,30)}
    compose=(root/"compose.yml").exists() or (root/"compose.yaml").exists() or (root/"docker-compose.yml").exists()
    if compose:
        report["compose_config"]=_run(["docker","compose","config","--quiet"],root,30)
        report["compose_ps"]=_run(["docker","compose","ps","--all"],root,30)
    return json.dumps(report,indent=2)[:30000]


def database_migration_doctor(workspace: str) -> str:
    root=Path(workspace); detected=[]; checks={}
    if (root/"alembic.ini").exists(): detected.append("alembic"); checks["alembic"]=_run([sys.executable,"-m","alembic","current"],root,30)
    if (root/"manage.py").exists(): detected.append("django"); checks["django"]=_run([sys.executable,"manage.py","showmigrations","--plan"],root,45)
    if (root/"prisma"/"schema.prisma").exists(): detected.append("prisma"); checks["prisma"]=_run(["npx","prisma","migrate","status"],root,60)
    if (root/"knexfile.js").exists() or (root/"knexfile.ts").exists(): detected.append("knex"); checks["knex"]=_run(["npx","knex","migrate:status"],root,60)
    if not detected: return "No supported migration framework detected (Alembic, Django, Prisma, Knex)."
    return json.dumps({"detected":detected,"checks":checks},indent=2)[:30000]
