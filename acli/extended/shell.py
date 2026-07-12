"""Approved terminal runner, sandboxed to the workspace."""
import os, shlex, subprocess
from pathlib import Path
from acli.extended.security import command_risk
from acli.production.environment import scrub_environment

DENIED_PREFIXES=("rm -rf /","mkfs","format ","shutdown","reboot",":(){")

def run_command(workspace: str, command: str, timeout: int = 120) -> str:
    if any(command.strip().lower().startswith(x) for x in DENIED_PREFIXES):
        raise PermissionError("Command blocked by hard safety policy")
    Path(workspace).mkdir(parents=True,exist_ok=True)
    result=subprocess.run(command,cwd=workspace,shell=True,capture_output=True,text=True,timeout=max(1,min(timeout,900)),env=scrub_environment())
    output=(result.stdout or "")+(result.stderr or "")
    return "risk="+command_risk(command)+" exit_code="+str(result.returncode)+"\n"+output[-16000:]
