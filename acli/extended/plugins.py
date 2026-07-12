"""Skills and isolated Python plugin discovery/execution."""
import json
import subprocess
import sys
from pathlib import Path
from acli.production.environment import scrub_environment


def list_skills(base_dir: str) -> str:
    root = Path(base_dir) / "skills"; root.mkdir(exist_ok=True)
    items = []
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in (".md", ".txt"):
            items.append(path.name)
        elif path.is_dir() and (path / "SKILL.md").exists():
            items.append(path.name)
    return "\n".join(sorted(items)) if items else "No skills installed."


def load_skill(base_dir: str, name: str) -> str:
    root = (Path(base_dir) / "skills").resolve()
    candidates = [root / name, root / name / "SKILL.md", root / (name + ".md")]
    for path in candidates:
        resolved = path.resolve()
        if resolved.exists() and resolved.is_file() and root in resolved.parents:
            return resolved.read_text(encoding="utf-8")[:20000]
    raise FileNotFoundError(name)


def list_plugins(base_dir: str) -> str:
    root = Path(base_dir) / "plugins"; root.mkdir(exist_ok=True)
    return "\n".join(sorted(path.stem for path in root.glob("*.py") if not path.name.startswith("_"))) or "No plugins installed."


_PLUGIN_RUNNER = r'''import contextlib, importlib.util, io, json, sys
path = sys.argv[1]
payload = json.loads(sys.stdin.read())
spec = importlib.util.spec_from_file_location("devorbit_external_plugin", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if not hasattr(module, "run"):
    raise AttributeError("Plugin must define run(payload)")
captured = io.StringIO()
with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
    result = module.run(payload)
print(json.dumps({"result": result, "plugin_output": captured.getvalue()}, default=str))
'''


def run_plugin(base_dir: str, name: str, payload: dict) -> str:
    root = (Path(base_dir) / "plugins").resolve()
    path = (root / (name + ".py")).resolve()
    if root not in path.parents or not path.exists() or not path.is_file():
        raise FileNotFoundError(name)
    process = subprocess.run(
        [sys.executable, "-I", "-c", _PLUGIN_RUNNER, str(path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        env=scrub_environment(),
    )
    if process.returncode != 0:
        raise RuntimeError("Plugin failed: " + process.stderr[-4000:])
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Plugin returned invalid output") from exc
    return json.dumps(data, indent=2, default=str)[:20000]
