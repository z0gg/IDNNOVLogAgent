"""Strict settings validation and deterministic Fluent Bit configuration."""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

DEFAULT_COLLECTOR = "https://logs.idnnov.com"
DEFAULT_ENDPOINT = "/v1/logs"

def defaults(device_id):
    return {"collector_url": DEFAULT_COLLECTOR, "endpoint": DEFAULT_ENDPOINT,
            "customer_id": "", "site_id": "", "device_id": device_id}

def validate_collector(value):
    if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid collector URL")
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username is not None or p.password is not None or p.fragment or p.query or p.path not in ("", "/"):
        raise ValueError("collector must be an HTTPS origin")
    host = p.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("local destination forbidden")
    try:
        validate_resolved_addresses([host])
    except ValueError:
        raise
    except Exception:
        pass
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("invalid port")
    authority = f"[{host}]" if ":" in host else host
    if port and port != 443:
        authority += f":{port}"
    return urlunsplit(("https", authority, "", "", ""))

def validate_resolved_addresses(addresses):
    for raw in addresses:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if (not ip.is_global or ip.is_multicast or ip.is_loopback or ip.is_link_local
                or ip.is_private or ip.is_unspecified or ip.is_reserved):
            raise ValueError("destination address forbidden")
    return True

def validate_endpoint(value):
    if not isinstance(value, str) or len(value) > 256 or not value.startswith("/") or value.startswith("//"):
        raise ValueError("invalid endpoint")
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or "#" in value or "?" in value:
        raise ValueError("invalid endpoint")
    if any(part in (".", "..") for part in value.split("/")):
        raise ValueError("invalid endpoint")
    return value

def _safe_label(value):
    if not isinstance(value, str) or len(value) > 128:
        raise ValueError("invalid label")
    return re.sub(r"[^A-Za-z0-9_.:@/-]", "_", value)

def render_fluent_bit(settings, token, storage_path):
    origin = urlsplit(validate_collector(settings["collector_url"]))
    endpoint = validate_endpoint(settings["endpoint"])
    port = origin.port or 443
    host = origin.hostname
    customer = _safe_label(settings.get("customer_id", ""))
    site = _safe_label(settings.get("site_id", ""))
    device = _safe_label(settings["device_id"])
    auth = ""
    if token:
        if not isinstance(token, str) or len(token) > 8192 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token): raise ValueError("invalid token")
        auth = f"    Header Authorization Bearer {token}\n"
    return f"""[SERVICE]\n    Flush 5\n    Log_Level info\n    storage.path {storage_path}\n    storage.sync normal\n    storage.checksum on\n\n[INPUT]\n    Name syslog\n    Mode tcp\n    Listen 127.0.0.1\n    Port 5514\n    Parser syslog-rfc5424\n    storage.type filesystem\n\n[OUTPUT]\n    Name http\n    Match *\n    Host {host}\n    Port {port}\n    URI {endpoint}\n    Format json_lines\n    tls On\n    tls.verify On\n{auth}    Header X-IDNNOV-Customer {customer}\n    Header X-IDNNOV-Site {site}\n    Header X-IDNNOV-Device {device}\n    storage.total_limit_size 128M\n"""
