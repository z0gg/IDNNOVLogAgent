"""Bounded TLS connection testing with safe error classification."""
import json
import socket
import ssl
from urllib.parse import urlsplit
from .config import validate_collector, validate_endpoint, validate_resolved_addresses

def classify_http(status):
    if status in (401, 403): return "AUTHENTICATION_REFUSED"
    if 200 <= status < 400: return "SUCCESS"
    return "HTTP_UNAVAILABLE"

def _result(code):
    return {"success": code == "SUCCESS", "code": code}

def test(collector, endpoint, token, timeout=5):
    try:
        p = urlsplit(validate_collector(collector)); validate_endpoint(endpoint)
        port = p.port or 443
        records = socket.getaddrinfo(p.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror: return _result("DNS_FAILED")
    except ValueError: return _result("DESTINATION_FORBIDDEN")
    addresses = list(dict.fromkeys(r[4][0] for r in records))
    try: validate_resolved_addresses(addresses)
    except ValueError: return _result("DESTINATION_FORBIDDEN")
    last = "TCP_TIMEOUT"
    for address in addresses:
        try:
            raw = socket.create_connection((address, port), timeout=timeout)
            context = ssl.create_default_context()
            tls = context.wrap_socket(raw, server_hostname=p.hostname)
            headers = [f"HEAD {endpoint} HTTP/1.1", f"Host: {p.hostname}", "Connection: close"]
            if token: headers.append("Authorization: Bearer " + token)
            tls.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
            line = tls.makefile("rb", buffering=0).readline(4096).decode("ascii", "replace")
            tls.close()
            status = int(line.split()[1])
            return _result(classify_http(status))
        except ssl.SSLCertVerificationError: return _result("TLS_CERTIFICATE_INVALID")
        except ssl.SSLError: last = "TLS_HANDSHAKE_FAILED"
        except (TimeoutError, socket.timeout, ConnectionError, OSError): last = "TCP_TIMEOUT"
        except (ValueError, IndexError): return _result("HTTP_UNAVAILABLE")
    return _result(last)
