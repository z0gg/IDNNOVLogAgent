"""OpenObserve settings validation and deterministic Fluent Bit configuration."""
import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit

DEFAULT_COLLECTOR = "https://logs.idnnov.com"
DEFAULT_ORGANIZATION = "default"
DEFAULT_STREAM = "synology_logs"
STREAM_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
# OpenObserve organization IDs are opaque, case-sensitive strings. Example:
# 3IpSzrDn5K5UpPiprhpEXsmj3bR. Never normalize their case.
ORGANIZATION_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
INGEST_USER = re.compile(r"^[A-Za-z0-9_.@+-]{1,256}$")
SECRET = re.compile(r"^[A-Za-z0-9_-]{16,512}$")


def _default_nas_name():
    try:
        return _safe_label(socket.gethostname())
    except OSError:
        return "synology-nas"


def defaults(device_id):
    return {
        "collector_url": DEFAULT_COLLECTOR,
        "organization": DEFAULT_ORGANIZATION,
        "company_name": "",
        "stream": DEFAULT_STREAM,
        "nas_name": _default_nas_name(),
        "device_id": device_id,
        "ingest_user": "",
    }


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


def validate_stream_identifier(value):
    if not isinstance(value, str):
        raise ValueError("invalid OpenObserve stream identifier")
    normalized = value.strip().lower()
    if not STREAM_IDENTIFIER.fullmatch(normalized):
        raise ValueError("invalid OpenObserve stream identifier")
    return normalized


def validate_organization_identifier(value):
    if not isinstance(value, str):
        raise ValueError("invalid OpenObserve organization identifier")
    normalized = value.strip()
    if not ORGANIZATION_IDENTIFIER.fullmatch(normalized):
        raise ValueError("invalid OpenObserve organization identifier")
    return normalized


def validate_identifier(value):
    """Compatibility alias for existing callers that validate stream names."""
    return validate_stream_identifier(value)


def _safe_label(value):
    if not isinstance(value, str) or len(value) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid label")
    normalized = re.sub(r"[^A-Za-z0-9_.:@/-]", "_", value.strip())
    if not normalized:
        raise ValueError("invalid label")
    return normalized


def validate_ingest_user(value):
    if value == "":
        return ""
    if not isinstance(value, str) or not INGEST_USER.fullmatch(value):
        raise ValueError("invalid ingestion username")
    return value


def validate_ingest_password(value):
    if not isinstance(value, str) or not SECRET.fullmatch(value):
        raise ValueError("invalid ingestion password")
    return value


def openobserve_endpoint(organization, stream):
    return f"/api/{validate_organization_identifier(organization)}/{validate_stream_identifier(stream)}/_json"


def validate_settings(settings):
    clean = dict(settings)
    clean["collector_url"] = validate_collector(clean["collector_url"])
    clean["organization"] = validate_organization_identifier(clean["organization"])
    clean["company_name"] = _safe_label(clean["company_name"]) if clean["company_name"].strip() else ""
    clean["stream"] = validate_stream_identifier(clean["stream"])
    clean["nas_name"] = _safe_label(clean["nas_name"])
    clean["device_id"] = _safe_label(clean["device_id"])
    clean["ingest_user"] = validate_ingest_user(clean["ingest_user"])
    return clean


def render_fluent_bit(settings, password, storage_path, parsers_file, lua_script=None):
    clean = validate_settings(settings)
    origin = urlsplit(clean["collector_url"])
    port = origin.port or 443
    auth = ""
    if password is not None:
        password = validate_ingest_password(password)
        if not clean["ingest_user"]:
            raise ValueError("ingestion username required")
        auth = f"    HTTP_User {clean['ingest_user']}\n    HTTP_Passwd {password}\n"
    elif clean["ingest_user"]:
        raise ValueError("ingestion password required")
    company = clean["company_name"] or clean["organization"]
    # 1.1.10-1027: lua filter explodes DSM SD-PARAMS ([synolog@6574 k="v" ...])
    # into indexed fields (event, ip, username, luser, fname, fsize...) and
    # derives `severity` from `pri`. Optional only for unit tests of the
    # renderer; production always passes the shipped script.
    lua_filter = ""
    if lua_script:
        lua_filter = (
            f"\n[FILTER]\n    Name lua\n    Match *\n"
            f"    script {lua_script}\n    call cb_synology_extract\n"
            f"    protected_mode true\n"
        )
    return f"""[SERVICE]\n    Flush 5\n    Log_Level info\n    Parsers_File {parsers_file}\n    storage.path {storage_path}\n    storage.sync normal\n    storage.checksum on\n\n[INPUT]\n    Name syslog\n    Mode tcp\n    Listen 127.0.0.1\n    Port 5514\n    # DSM Log Center uses RFC 6587 octet-counting framing over TCP.\n    Format octet_counting\n    Parser syslog-rfc5424\n    storage.type filesystem\n\n[FILTER]\n    Name record_modifier\n    Match *\n    Record idnnov_company {company}\n    Record idnnov_nas {clean['nas_name']}\n    Record idnnov_device_id {clean['device_id']}\n{lua_filter}\n[OUTPUT]\n    Name http\n    Match *\n    Host {origin.hostname}\n    Port {port}\n    URI {openobserve_endpoint(clean['organization'], clean['stream'])}\n    Format json\n    Json_date_key _timestamp\n    Json_date_format iso8601\n    tls On\n    tls.verify On\n    compress gzip\n{auth}    storage.total_limit_size 128M\n"""
