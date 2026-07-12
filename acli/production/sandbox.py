"""Docker-first command sandbox with explicit resource and network limits."""
import json, shutil, subprocess
from pathlib import Path
from acli.production import native_sandbox

DEFAULT_IMAGE="python:3.13-slim"

def docker_available():
    if not shutil.which("docker"): return False
    return subprocess.run(["docker","info"],capture_output=True,timeout=15).returncode==0

def run_sandboxed(workspace: str, command: str, image: str = DEFAULT_IMAGE, timeout: int = 300, network: bool = False, memory_mb: int = 1024, cpus: float = 1.0) -> str:
    if not docker_available(): raise RuntimeError("Docker daemon is unavailable. Start Docker Desktop/Engine; native fallback is intentionally not automatic.")
    root=Path(workspace).resolve(); root.mkdir(parents=True,exist_ok=True)
    args=["docker","run","--rm","--init","--read-only","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=256","--memory="+str(max(128,memory_mb))+"m","--cpus="+str(max(.1,min(cpus,8))),"--network="+("bridge" if network else "none"),"--tmpfs","/tmp:rw,noexec,nosuid,size=256m","-v",str(root)+":/workspace:rw","-w","/workspace",image,"sh","-lc",command]
    result=subprocess.run(args,capture_output=True,text=True,timeout=max(1,min(timeout,1800)))
    return json.dumps({"exit_code":result.returncode,"image":image,"network":network,"memory_mb":memory_mb,"cpus":cpus,"stdout":result.stdout[-12000:],"stderr":result.stderr[-12000:]},indent=2)

def sandbox_status() -> str:
    version=subprocess.run(["docker","--version"],capture_output=True,text=True).stdout.strip() if shutil.which("docker") else "not installed"
    return json.dumps({"docker_installed":bool(shutil.which("docker")),"daemon_available":docker_available(),"version":version,"default_image":DEFAULT_IMAGE},indent=2)

def isolation_status() -> str:
    docker=docker_available()
    return json.dumps({"selected_backend":"docker" if docker else "native_restricted","docker_available":docker,"native_shell_enabled":False,"automatic_fallback":True},indent=2)

def run_isolated(workspace: str, command: str, image: str = DEFAULT_IMAGE, timeout: int = 300, network: bool = False, memory_mb: int = 1024, cpus: float = 1.0) -> str:
    if docker_available():
        return run_sandboxed(workspace,command,image,timeout,network,memory_mb,cpus)
    if network:
        raise PermissionError("Networked commands require the Docker backend; restricted native fallback never grants network explicitly")
    return native_sandbox.run_restricted(workspace,command,timeout)
