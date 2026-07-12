"""Atomic run-state persistence and crash recovery."""
import json, os, time
from pathlib import Path

class RunState:
    def __init__(self, workspace):
        self.path=Path(workspace)/".devorbit-run-state.json"
    def save(self,state):
        payload={**state,"updated_at":time.time(),"pid":os.getpid()}; temp=self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload,indent=2),encoding="utf-8"); temp.replace(self.path)
    def load(self):
        if not self.path.exists(): return None
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return {"corrupt":True,"path":str(self.path)}
    def clear(self): self.path.unlink(missing_ok=True)

def recovery_status(workspace):
    state=RunState(workspace).load()
    return json.dumps(state if state else {"recoverable_run":False},indent=2)
