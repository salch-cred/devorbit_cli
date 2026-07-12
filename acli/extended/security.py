"""Security MVP: secret scanning, prompt-injection detection, and command risk scoring."""
import re
from pathlib import Path

SECRET_PATTERNS = {
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "github_token": re.compile(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "nvidia_key": re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"),
}
INJECTION_PATTERNS = [
    re.compile(x, re.I) for x in [
        r"ignore (all|any|the) previous instructions",
        r"reveal (your|the) system prompt",
        r"do not tell the user",
        r"exfiltrate|steal.*credential",
        r"disable.*safety|bypass.*permission",
    ]
]
DANGEROUS_COMMANDS = [r"\brm\s+-rf\b", r"\bformat\b", r"\bmkfs\b", r"\bdd\s+if=", r"git\s+push.*--force", r"git\s+reset\s+--hard", r"curl.*\|.*(?:sh|bash)"]


def scan_text(text: str) -> str:
    findings=[]
    for name, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append(name + " at character " + str(match.start()))
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text): findings.append("possible prompt injection: " + pattern.pattern)
    return "No secrets or injection patterns detected." if not findings else "\n".join(findings)


def scan_workspace(workspace: str, max_files: int = 1000) -> str:
    root=Path(workspace); findings=[]; checked=0
    for path in root.rglob("*"):
        if checked>=max_files: break
        if not path.is_file() or any(p in path.parts for p in (".git","node_modules",".venv")): continue
        if path.stat().st_size>2_000_000: continue
        checked+=1
        try: text=path.read_text(encoding="utf-8",errors="ignore")
        except OSError: continue
        result=scan_text(text)
        if not result.startswith("No secrets"): findings.append(str(path.relative_to(root))+":\n"+result)
    return "Security scan passed ("+str(checked)+" files)." if not findings else "\n\n".join(findings[:100])


def command_risk(command: str) -> str:
    matches=[p for p in DANGEROUS_COMMANDS if re.search(p,command,re.I)]
    return "high: "+", ".join(matches) if matches else ("medium" if any(x in command for x in ("sudo ","git push","pip install","npm install")) else "low")
