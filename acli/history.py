"""Conversation save/load helpers."""
import json
from pathlib import Path
from typing import List, Dict


def save_history(path: str, messages: List[Dict[str, str]]) -> None:
    Path(path).write_text(json.dumps(messages, indent=2), encoding="utf-8")


def load_history(path: str) -> List[Dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("No such history file: " + path)
    return json.loads(p.read_text(encoding="utf-8"))


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
