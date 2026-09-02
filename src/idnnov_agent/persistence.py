"""Atomic settings and separate token persistence."""
import json
import os
from pathlib import Path
from . import config

ALLOWED = {"collector_url", "endpoint", "customer_id", "site_id", "device_id"}

def migrate(value):
    out = config.defaults(value.get("device_id", ""))
    out.update({k: v for k, v in value.items() if k in ALLOWED})
    return out

def _atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, data.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, mode)
    os.replace(tmp, path)

def save(root, settings, token_action="preserve", token=None):
    root = Path(root)
    clean = migrate(settings)
    clean["collector_url"] = config.validate_collector(clean["collector_url"])
    clean["endpoint"] = config.validate_endpoint(clean["endpoint"])
    _atomic(root / "settings.json", json.dumps(clean, sort_keys=True, separators=(",", ":")) + "\n", 0o600)
    token_path = root / "token"
    if token_action == "replace":
        if not isinstance(token, str) or not token or len(token) > 8192 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError("invalid token")
        _atomic(token_path, token, 0o600)
    elif token_action == "delete":
        try: token_path.unlink()
        except FileNotFoundError: pass
    elif token_action != "preserve":
        raise ValueError("invalid token action")
    return clean

def load_public(root):
    root = Path(root)
    data = migrate(json.loads((root / "settings.json").read_text()))
    data["token_configured"] = (root / "token").is_file()
    return data
