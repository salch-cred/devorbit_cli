"""Multi-provider OpenAI-compatible client configuration."""
import json, os
from pathlib import Path
from acli.production.credentials import get_secret_value

DEFAULTS={
 'nvidia':{'base_url':'https://integrate.api.nvidia.com/v1','api_key_env':'NVIDIA_API_KEY'},
 'openai':{'base_url':'https://api.openai.com/v1','api_key_env':'OPENAI_API_KEY'},
 'openrouter':{'base_url':'https://openrouter.ai/api/v1','api_key_env':'OPENROUTER_API_KEY'},
 'groq':{'base_url':'https://api.groq.com/openai/v1','api_key_env':'GROQ_API_KEY'},
 'ollama':{'base_url':'http://127.0.0.1:11434/v1','api_key_env':'OLLAMA_API_KEY','default_key':'ollama'},
 'lmstudio':{'base_url':'http://127.0.0.1:1234/v1','api_key_env':'LMSTUDIO_API_KEY','default_key':'lm-studio'},
}

def load_providers(base_dir: str):
    path=Path(base_dir)/'providers.json'; data=dict(DEFAULTS)
    if path.exists(): data.update(json.loads(path.read_text(encoding='utf-8')))
    return data

def provider_status(base_dir: str) -> str:
    lines=[]
    for name,cfg in load_providers(base_dir).items():
        env_name=cfg.get('api_key_env','')
        try: key=get_secret_value(env_name) if env_name else ''
        except Exception: key=os.environ.get(env_name,'')
        key=key or cfg.get('default_key','')
        lines.append(name+': '+('configured' if key else 'missing key')+' -> '+cfg.get('base_url',''))
    return '\n'.join(lines)

def get_provider(base_dir: str, name: str):
    cfg=load_providers(base_dir).get(name)
    if not cfg: raise KeyError('Unknown provider: '+name)
    env_name=cfg.get('api_key_env','')
    try: key=get_secret_value(env_name) if env_name else ''
    except Exception: key=os.environ.get(env_name,'')
    key=key or cfg.get('default_key','')
    if not key: raise ValueError('Missing '+cfg.get('api_key_env','API key'))
    return cfg['base_url'],key


def get_nvidia_keys():
    """Load all NVIDIA API keys from environment (supports comma-separated and NVIDIA_API_KEYS)."""
    import os
    keys = []
    # Primary: NVIDIA_API_KEY (can be comma-separated)
    primary = os.environ.get("NVIDIA_API_KEY", "")
    if primary:
        keys.extend([k.strip() for k in primary.split(",") if k.strip()])
    # Secondary: NVIDIA_API_KEYS
    secondary = os.environ.get("NVIDIA_API_KEYS", "")
    if secondary:
        for k in secondary.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    # Also check NVIDIA_API_KEY_1 through NVIDIA_API_KEY_10
    for i in range(1, 11):
        k = os.environ.get(f"NVIDIA_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys
