"""Task routing and a short-lived SQLite response cache."""
import hashlib
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path


def classify_task(text: str) -> str:
    lowered = text.lower()
    if any(x in lowered for x in ("image", "screenshot", "ocr", "diagram")): return "vision"
    if any(x in lowered for x in ("search web", "research", "latest", "sources")): return "research"
    if any(x in lowered for x in ("code", "bug", "test", "repository", "function")): return "coding"
    if any(x in lowered for x in ("plan", "architecture", "reason")): return "reasoning"
    return "chat"


def route_model(text: str, models: list) -> str:
    if not models: raise ValueError("No models are configured")
    task = classify_task(text)
    preferences = {"coding": ["glm", "qwen", "deepseek"], "reasoning": ["glm", "deepseek", "gpt-oss"], "research": ["glm", "llama"], "vision": ["vision", "vl", "gemma"], "chat": []}
    for hint in preferences[task]:
        for model in models:
            if hint in model.lower(): return model
    return models[0]


class ResponseCache:
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS cache(k TEXT PRIMARY KEY,value TEXT,created REAL)")
            connection.commit()

    def key(self, model, messages):
        return hashlib.sha256((model + json.dumps(messages, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()

    def get(self, key, max_age=86400):
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute("SELECT value,created FROM cache WHERE k=?", (key,)).fetchone()
        if not row or time.time() - row[1] >= max_age: return None
        try: return json.loads(row[0])
        except json.JSONDecodeError:
            with closing(sqlite3.connect(self.path)) as connection:
                connection.execute("DELETE FROM cache WHERE k=?", (key,)); connection.commit()
            return None

    def put(self, key, value):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("REPLACE INTO cache VALUES(?,?,?)", (key, json.dumps(value, ensure_ascii=False), time.time())); connection.commit()
