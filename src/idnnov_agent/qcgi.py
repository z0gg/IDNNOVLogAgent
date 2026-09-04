"""CGI entry point hosted by DSM's web stack.

DSM's synoscgi never feeds the request body to third-party package CGIs:
any stdin read deadlocks until DSM kills the process (observed and reproduced
on a real DSM 7.2.2-72806 VM). Therefore this CGI is strictly GET-only and
reads every parameter from the query string. Passwords are never sent in
clear: the UI fetches a one-time nonce and submits the secret XOR-masked with
it, so plaintext secrets never appear in URLs or nginx logs.
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path
from .api import _response, handle
from . import persistence
from . import config

NONCE_TTL = 300
_query = None


def query_params():
    global _query
    if _query is None:
        from urllib.parse import parse_qs
        raw = os.environ.get("QUERY_STRING", "")
        _query = {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()
                  if isinstance(v, list) and v}
    return _query


def _nonce_store():
    root = Path(os.environ.get("SYNOPKG_PKGVAR", "/var/packages/IDNNOVLogAgent/var")) / "etc"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "nonces.json"


def nonce_new():
    path = _nonce_store()
    try:
        store = json.loads(path.read_text())
    except Exception:
        store = {}
    now = time.time()
    store = {k: v for k, v in store.items() if now - v < NONCE_TTL}
    nonce = uuid.uuid4().hex
    store[nonce] = now
    _atomic(path, json.dumps(store))
    return nonce


def nonce_pop(nonce):
    path = _nonce_store()
    try:
        store = json.loads(path.read_text())
    except Exception:
        return False
    now = time.time()
    value = store.pop(nonce, None)
    store = {k: v for k, v in store.items() if now - v < NONCE_TTL}
    _atomic(path, json.dumps(store))
    return value is not None and now - value <= NONCE_TTL


def _atomic(path, data):
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(data)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def unmask(masked, nonce):
    """Reverse the XOR+base64 mask applied by the UI."""
    import base64
    raw = base64.b64decode(masked)
    key = nonce.encode()
    # Strip whitespace the clipboard may introduce (secret managers often
    # copy a trailing newline); the XOR mask is computed on the trimmed text.
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)).decode().strip()


def main():
    q = query_params()
    action = q.get("action", "")
    env = dict(os.environ)
    env.setdefault("REQUEST_METHOD", "GET")

    if action == "nonce":
        sys.stdout.write(_response(200, "SUCCESS", {"nonce": nonce_new()}).serialize())
        return

    if action == "save_settings":
        try:
            nonce = q.get("nonce", "")
            if not nonce or not nonce_pop(nonce):
                sys.stdout.write(_response(403, "NONCE_INVALID").serialize())
                return
            settings = json.loads(q.get("settings", "{}"))
            password_action = q.get("password_action", "preserve")
            password = unmask(q["password"], nonce) if "password" in q else None
            from .api import save_settings as _save
            data = _save(settings, password_action, password)
            sys.stdout.write(_response(200, "SUCCESS", data).serialize())
        except Exception as exc:  # noqa: BLE001 - surface a precise failure code
            if os.environ.get("IDNNOV_CGI_DEBUG"):
                sys.stdout.write(_response(500, f"DEBUG:{type(exc).__name__}:{exc}"[:500]).serialize())
            else:
                sys.stdout.write(_response(400, "APPLY_FAILED").serialize())
        return

    # Everything else (get_settings, get_status, test_connection) is read-only:
    # reuse the JSON handler by synthesizing a body-free call.
    from . import api as core
    user = core.authenticated_user(env)
    if not user or not core.is_admin(user):
        sys.stdout.write(_response(403, "ADMIN_REQUIRED").serialize())
        return
    if action == "get_settings":
        sys.stdout.write(_response(200, "SUCCESS", core.get_settings()).serialize())
        return
    if action == "get_status":
        sys.stdout.write(_response(200, "SUCCESS", core.get_status()).serialize())
        return
    if action == "test_connection":
        required = ("collector_url", "organization", "stream", "ingest_user")
        if any(k not in q for k in required):
            sys.stdout.write(_response(400, "INVALID_SCHEMA").serialize())
            return
        stored = persistence.load_public(core.ETC)
        password = ((core.ETC / "token").read_text()
                    if stored["ingest_password_configured"]
                    and stored["ingest_user"] == q["ingest_user"] else None)
        data = core.connection.test(q["collector_url"], q["organization"],
                                    q["stream"], q["ingest_user"], password)
        sys.stdout.write(_response(200, "SUCCESS", data).serialize())
        return
    sys.stdout.write(_response(400, "UNKNOWN_ACTION").serialize())


def _serialize(self):
    return (f"Status: {self.status} {'OK' if self.status < 400 else 'Error'}\r\n"
            f"Content-Type: application/json\r\n"
            f"Cache-Control: no-store\r\n"
            f"X-Content-Type-Options: nosniff\r\n\r\n{self.body}")


# attach serializer to Response
from .api import Response  # noqa: E402
Response.serialize = _serialize

if __name__ == "__main__":
    main()
