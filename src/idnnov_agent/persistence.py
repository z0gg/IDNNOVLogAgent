"""Atomic OpenObserve settings and separately stored ingestion password."""
import json
import os
from pathlib import Path
from . import config

ALLOWED = {"collector_url", "organization", "company_name", "stream", "nas_name", "device_id", "ingest_user"}


def migrate(value):
    """Map pre-OpenObserve settings without assigning a customer automatically."""
    out = config.defaults(value.get("device_id", ""))
    # The old UI called these generic client/site fields. Carry them forward only
    # when the administrator had explicitly populated them; never inject a name.
    legacy_org = value.get("customer_id", "")
    legacy_nas = value.get("site_id", "")
    if legacy_org:
        out["organization"] = legacy_org
        out["company_name"] = legacy_org
    if legacy_nas:
        out["nas_name"] = legacy_nas
    for key, item in value.items():
        if key not in ALLOWED:
            continue
        # Empty legacy UI fields must not erase safe generated defaults.
        if key in {"organization", "stream", "nas_name", "device_id"} and not item:
            continue
        out[key] = item
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


def save(root, settings, password_action="preserve", password=None):
    root = Path(root)
    clean = config.validate_settings(migrate(settings))
    password_path = root / "token"  # Stable private path retained through upgrades.
    if password_action == "replace":
        password = password.strip() if isinstance(password, str) else password
        config.validate_ingest_password(password)
        if not clean["ingest_user"]:
            raise ValueError("ingestion username required")
        _atomic(password_path, password, 0o600)
    elif password_action == "delete":
        try:
            password_path.unlink()
        except FileNotFoundError:
            pass
    elif password_action != "preserve":
        raise ValueError("invalid password action")
    _atomic(root / "settings.json", json.dumps(clean, sort_keys=True, separators=(",", ":")) + "\n", 0o600)
    return clean


def load_public(root):
    root = Path(root)
    password_path = root / "token"  # Stable private path retained through upgrades.
    data = config.validate_settings(migrate(json.loads((root / "settings.json").read_text())))
    # An old Bearer token has no OpenObserve Basic username and is deliberately
    # inactive after migration. It is retained on disk until an admin replaces it.
    data["ingest_password_configured"] = bool(data["ingest_user"]) and password_path.is_file()
    return data
