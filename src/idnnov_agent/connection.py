"""Bounded TLS OpenObserve connection testing with safe error classification."""
import base64
import socket
import ssl
from urllib.parse import urlsplit
from .config import (openobserve_endpoint, validate_collector, validate_ingest_password,
                     validate_ingest_user, validate_resolved_addresses)


def classify_http(status):
    if status in (401, 403):
        return "AUTHENTICATION_REFUSED"
    if 200 <= status < 400:
        return "SUCCESS"
    return "HTTP_UNAVAILABLE"


def _result(code):
    return {"success": code == "SUCCESS", "code": code}


def test(collector, organization, stream, ingest_user, password, timeout=5):
    try:
        p = urlsplit(validate_collector(collector))
        endpoint = openobserve_endpoint(organization, stream)
        ingest_user = validate_ingest_user(ingest_user)
        if password is not None:
            validate_ingest_password(password)
        if not ingest_user or not password:
            return _result("AUTHENTICATION_NOT_CONFIGURED")
        port = p.port or 443
        records = socket.getaddrinfo(p.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return _result("DNS_FAILED")
    except ValueError:
        return _result("CONFIGURATION_INVALID")
    addresses = list(dict.fromkeys(r[4][0] for r in records))
    try:
        validate_resolved_addresses(addresses)
    except ValueError:
        return _result("DESTINATION_FORBIDDEN")
    authorization = base64.b64encode(f"{ingest_user}:{password}".encode("ascii")).decode("ascii")
    last = "TCP_TIMEOUT"
    for address in addresses:
        try:
            raw = socket.create_connection((address, port), timeout=timeout)
            context = ssl.create_default_context()
            tls = context.wrap_socket(raw, server_hostname=p.hostname)
            # An empty OpenObserve JSON batch validates TLS, route and Basic auth
            # without creating a log event.
            headers = [
                f"POST {endpoint} HTTP/1.1", f"Host: {p.hostname}",
                "Content-Type: application/json", "Content-Length: 2",
                f"Authorization: Basic {authorization}", "Connection: close",
            ]
            tls.sendall(("\r\n".join(headers) + "\r\n\r\n[]").encode("ascii"))
            line = tls.makefile("rb", buffering=0).readline(4096).decode("ascii", "replace")
            tls.close()
            status = int(line.split()[1])
            return _result(classify_http(status))
        except ssl.SSLCertVerificationError:
            return _result("TLS_CERTIFICATE_INVALID")
        except ssl.SSLError:
            last = "TLS_HANDSHAKE_FAILED"
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            last = "TCP_TIMEOUT"
        except (ValueError, IndexError):
            return _result("HTTP_UNAVAILABLE")
    return _result(last)
