"""Example DevOrbit plugin."""
def run(payload):
    return {"ok": True, "echo": payload, "message": "Example plugin executed."}
