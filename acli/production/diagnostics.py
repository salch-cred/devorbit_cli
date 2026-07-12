"""Cross-language diagnostics through installed language tooling."""
import json, shutil, subprocess, sys
from pathlib import Path

def _run(command,cwd,timeout=180):
    try:
        r=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=timeout)
        return {"command":" ".join(command),"exit_code":r.returncode,"output":((r.stdout or "")+(r.stderr or ""))[-16000:]}
    except Exception as exc: return {"command":" ".join(command),"exit_code":-1,"output":str(exc)}

def language_diagnostics(workspace: str) -> str:
    root=Path(workspace); checks=[]
    if (root/"pyproject.toml").exists() or list(root.glob("*.py")):
        checks.append(_run([sys.executable,"-m","compileall","-q","."],root))
        if shutil.which("pyright"): checks.append(_run(["pyright","--outputjson"],root))
        elif shutil.which("mypy"): checks.append(_run(["mypy","."],root))
    if (root/"package.json").exists():
        if (root/"tsconfig.json").exists(): checks.append(_run(["npx","tsc","--noEmit","--pretty","false"],root))
        checks.append(_run(["npm","run","lint","--if-present"],root))
    if (root/"go.mod").exists(): checks += [_run(["go","vet","./..."],root),_run(["go","test","./..."],root)]
    if (root/"Cargo.toml").exists(): checks.append(_run(["cargo","check","--message-format=json"],root))
    if (root/"pom.xml").exists(): checks.append(_run(["mvn","-q","-DskipTests","compile"],root,300))
    return json.dumps(checks if checks else [{"message":"No supported project markers detected"}],indent=2)[:30000]
