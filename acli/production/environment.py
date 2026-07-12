"""Environment filtering for untrusted child processes."""
import os

SENSITIVE_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "COOKIE", "AUTH")
SAFE_EXACT = {"KEYBOARD_LAYOUT", "XAUTHORITY"}


def scrub_environment(source=None, extra=None):
    source = dict(os.environ if source is None else source)
    cleaned = {
        key: value for key, value in source.items()
        if key.upper() in SAFE_EXACT or not any(marker in key.upper() for marker in SENSITIVE_MARKERS)
    }
    cleaned["PYTHONUNBUFFERED"] = "1"
    if extra:
        cleaned.update(extra)
    return cleaned
