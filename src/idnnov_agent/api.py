"""Small DSM-served CGI API. No independent listener."""
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from . import persistence
from . import config, connection, transaction

ETC = Path(os.environ.get("SYNOPKG_PKGVAR", "/var/packages/IDNNOVLogAgent")) / "etc"


@dataclass
class Response:
    status: int
    body: str


def is_admin(username):
    if not username or len(username) > 128 or any(c in username for c in "\r\n\0"):
        return False
    try:
        proc = subprocess.run(["/usr/bin/id", "-Gn", username], capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and "administrators" in proc.stdout.split()


def get_settings():
    return persistence.load_public(ETC)


def get_status():
    pkgvar = ETC.parent
    pid_file = pkgvar / "fluent-bit.pid"
    running = False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        running = True
    except (OSError, ValueError):
        pass
    buffer_bytes = sum(p.stat().st_size for p in (pkgvar / "buffer").glob("**/*") if p.is_file()) if (pkgvar / "buffer").exists() else 0
    settings = persistence.load_public(ETC)
    return {
        "running": running,
        "package_version": "1.1.9-1026",
        "fluent_bit_version": "5.0.9",
        "destination": settings["collector_url"],
        "organization": settings["organization"],
        "stream": settings["stream"],
        "nas_name": settings["nas_name"],
        "listener": "127.0.0.1:5514",
        "buffer_bytes": buffer_bytes,
        "buffer_limit_bytes": 134217728,
    }


def _service(action):
    script = Path(os.environ.get("SYNOPKG_PKGDEST", "/var/packages/IDNNOVLogAgent/target")) / "scripts/service-setup"
    return subprocess.run([str(script), action], timeout=15, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def save_settings(settings, password_action, password=None):
    password_path = ETC / "token"
    # A pre-OpenObserve Bearer token cannot become a Basic password merely
    # because an administrator later adds a username. Replacing is explicit.
    stored = persistence.load_public(ETC)
    existing_password = password_path.read_text() if stored["ingest_password_configured"] else None
    effective = password if password_action == "replace" else (None if password_action == "delete" else existing_password)
    clean = config.validate_settings(persistence.migrate(settings))
    pkgdest = Path(os.environ.get("SYNOPKG_PKGDEST", "/var/packages/IDNNOVLogAgent/target"))
    rendered = config.render_fluent_bit(clean, effective, str(ETC.parent / "buffer"), str(pkgdest / "etc/parsers.conf"))
    binary = pkgdest / "bin/fluent-bit"
    current = ETC / "fluent-bit.conf"

    def valid(path):
        return subprocess.run([str(binary), "--dry-run", "-c", str(path)], timeout=15, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    transaction.apply_config(current, rendered, valid, lambda: _service("stop") and _service("start"), lambda: _service("status"))
    persistence.save(ETC, clean, password_action, password)
    return {"applied": True}


def _response(status, code, data=None):
    value = {"success": status < 400, "code": code}
    if data is not None:
        value["data"] = data
    return Response(status, json.dumps(value, sort_keys=True, separators=(",", ":")))


def authenticated_user(env):
    """Resolve the DSM session user.

    DSM 7 does not pass REMOTE_USER to third-party package CGIs. The documented
    mechanism is running webman's authenticate.cgi from within the CGI: the web
    server supplies the session cookies to the child process automatically.
    """
    user = env.get("REMOTE_USER", "")
    if user:
        return user
    try:
        proc = subprocess.run(
            ["/usr/syno/synoman/webman/modules/authenticate.cgi"],
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()[:128]


def handle(env, raw):
    user = authenticated_user(env)
    if not user or not is_admin(user):
        return _response(403, "ADMIN_REQUIRED")
    if env.get("REQUEST_METHOD") != "POST":
        return _response(405, "METHOD_NOT_ALLOWED")
    if env.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
        return _response(415, "JSON_REQUIRED")
    if len(raw) > 65536:
        return _response(413, "REQUEST_TOO_LARGE")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return _response(400, "INVALID_JSON")
    if not isinstance(value, dict) or "action" not in value:
        return _response(400, "INVALID_SCHEMA")
    action = value["action"]
    if action in ("get_settings", "get_status") and set(value) != {"action"}:
        return _response(400, "INVALID_SCHEMA")
    if action == "get_settings":
        return _response(200, "SUCCESS", get_settings())
    if action == "get_status":
        return _response(200, "SUCCESS", get_status())
    if action == "save_settings":
        allowed = {"action", "settings", "password_action", "password"}
        if not set(value) <= allowed or not {"action", "settings", "password_action"} <= set(value) or not isinstance(value["settings"], dict):
            return _response(400, "INVALID_SCHEMA")
        if set(value["settings"]) != persistence.ALLOWED:
            return _response(400, "INVALID_SCHEMA")
        try:
            data = save_settings(value["settings"], value["password_action"], value.get("password"))
        except (ValueError, transaction.ApplyError, OSError, subprocess.TimeoutExpired):
            return _response(400, "APPLY_FAILED")
        return _response(200, "SUCCESS", data)
    if action == "test_connection":
        required = {"action", "collector_url", "organization", "stream", "ingest_user"}
        if set(value) != required:
            return _response(400, "INVALID_SCHEMA")
        stored = persistence.load_public(ETC)
        password = ((ETC / "token").read_text().strip()
                    if stored["ingest_password_configured"] and stored["ingest_user"] == value["ingest_user"]
                    else None)
        data = connection.test(value["collector_url"], value["organization"], value["stream"], value["ingest_user"], password)
        return _response(200, "SUCCESS", data)
    return _response(400, "UNKNOWN_ACTION")
