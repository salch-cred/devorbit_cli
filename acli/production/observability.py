"""Local redacted audit log and runtime metrics."""
import json, re, time
from pathlib import Path

REDACT=[re.compile(r"nvapi-[A-Za-z0-9_-]+"),re.compile(r"(?:ghp_|github_pat_)[A-Za-z0-9_]+"),re.compile(r"(?i)(authorization|api[_-]?key|token)(\s*[:=]\s*)([^\s,}]+)")]

def redact(value):
    text=str(value)
    for p in REDACT:
        text=p.sub(lambda m:(m.group(1)+m.group(2)+"[REDACTED]") if m.lastindex and m.lastindex>=3 else "[REDACTED]",text)
    return text

class AuditLog:
    def __init__(self,workspace): self.path=Path(workspace)/".devorbit-audit.jsonl"
    def write(self,event,details):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        row={"time":time.time(),"event":event,"details":redact(json.dumps(details,default=str))}
        with self.path.open("a",encoding="utf-8") as f: f.write(json.dumps(row)+"\n")
    def metrics(self):
        counts={}; total=0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8",errors="ignore").splitlines():
                try: event=json.loads(line).get("event","unknown"); counts[event]=counts.get(event,0)+1; total+=1
                except Exception: pass
        return {"events":total,"by_type":counts,"path":str(self.path)}

def audit_metrics(workspace): return json.dumps(AuditLog(workspace).metrics(),indent=2)
