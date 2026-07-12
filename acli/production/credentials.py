"""OS keychain credential storage. Secrets are never returned in chat output."""
import os
SERVICE="devorbit-cli"

def _keyring():
    try: import keyring; return keyring
    except ImportError as exc: raise RuntimeError("Install the keyring package to use OS credential storage") from exc

def set_secret(name: str, value: str) -> str:
    if not value: raise ValueError("Secret cannot be empty")
    _keyring().set_password(SERVICE,name,value)
    return "Stored '"+name+"' in the operating-system credential store."

def get_secret_value(name: str):
    env=os.environ.get(name)
    return env if env else _keyring().get_password(SERVICE,name)

def secret_status(name: str) -> str:
    value=get_secret_value(name)
    return name+": "+("configured" if value else "missing")

def delete_secret(name: str) -> str:
    try: _keyring().delete_password(SERVICE,name)
    except Exception: pass
    return "Deleted '"+name+"' from the operating-system credential store."
