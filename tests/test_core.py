import base64
import json
import socket
import ssl
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from idnnov_agent import config, connection, persistence, transaction


class UrlTests(unittest.TestCase):
    def test_normalizes_https_url(self):
        self.assertEqual(config.validate_collector("https://Logs.Example.com/"), "https://logs.example.com")

    def test_rejects_unsafe_urls(self):
        bad = ["http://example.com", "ftp://example.com", "file:///tmp/x", "https://localhost", "https://127.0.0.1", "https://[::1]", "https://u:p@example.com", "https://example.com/#x", "https://example.com\nX"]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.validate_collector(value)

    def test_rejects_ssrf_addresses(self):
        for address in ["10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.1.1", "224.0.0.1", "0.0.0.0", "fc00::1", "fe80::1"]:
            with self.subTest(address=address), self.assertRaises(ValueError):
                config.validate_resolved_addresses([address])

    def test_validates_case_sensitive_openobserve_organization_id_and_stream(self):
        organization = "3IpSzrDn5K5UpPiprhpEXsmj3bR"
        self.assertEqual(config.validate_organization_identifier(organization), organization)
        self.assertEqual(config.validate_stream_identifier("Synology_Logs"), "synology_logs")
        self.assertEqual(config.openobserve_endpoint(organization, "synology_logs"), f"/api/{organization}/synology_logs/_json")
        for value in ["", "two words", "../../admin", "name\nHeader"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.validate_organization_identifier(value)


class FluentConfigTests(unittest.TestCase):
    def settings(self):
        return {"collector_url":"https://logs.example.com", "organization":"3IpSzrDn5K5UpPiprhpEXsmj3bR", "company_name":"Laroche", "stream":"synology_logs", "nas_name":"GRLAROCHE-SRV", "device_id":"stable-device", "ingest_user":"nas-ingest"}

    def test_generation_is_deterministic_and_openobserve_native(self):
        password = "0123456789abcdef"
        first = config.render_fluent_bit(self.settings(), password, "/var/buffer", "/opt/idnnov/parsers.conf")
        second = config.render_fluent_bit(dict(reversed(list(self.settings().items()))), password, "/var/buffer", "/opt/idnnov/parsers.conf")
        self.assertEqual(first, second)
        for expected in ("Listen 127.0.0.1", "Port 5514", "Format octet_counting", "tls.verify On", "compress gzip", "storage.total_limit_size 128M", "Parsers_File /opt/idnnov/parsers.conf", "URI /api/3IpSzrDn5K5UpPiprhpEXsmj3bR/synology_logs/_json", "Format json", "HTTP_User nas-ingest", "HTTP_Passwd 0123456789abcdef", "Record idnnov_company Laroche", "Record idnnov_nas GRLAROCHE-SRV", "Record idnnov_device_id stable-device"):
            self.assertIn(expected, first)

    def test_invalid_labels_cannot_inject_fluent_bit_directives(self):
        settings = self.settings()
        settings["nas_name"] = "a\n[OUTPUT]"
        with self.assertRaises(ValueError):
            config.render_fluent_bit(settings, "0123456789abcdef", "/var/buffer", "/opt/parsers.conf")

    def test_password_requires_ingest_username(self):
        settings = self.settings()
        settings["ingest_user"] = ""
        with self.assertRaises(ValueError):
            config.render_fluent_bit(settings, "0123456789abcdef", "/var/buffer", "/opt/parsers.conf")


class PersistenceTests(unittest.TestCase):
    def test_password_create_preserve_and_delete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            settings = config.defaults("device")
            settings["ingest_user"] = "nas-ingest"
            persistence.save(root, settings, password_action="replace", password="0123456789abcdef")
            password_path = root / "token"
            self.assertEqual(stat.S_IMODE(password_path.stat().st_mode), 0o600)
            persistence.save(root, settings, password_action="preserve")
            self.assertEqual(password_path.read_text(), "0123456789abcdef")
            persistence.save(root, settings, password_action="delete")
            self.assertFalse(password_path.exists())

    def test_frontend_never_receives_password(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            settings = config.defaults("device")
            settings["ingest_user"] = "nas-ingest"
            persistence.save(root, settings, password_action="replace", password="0123456789abcdef")
            public = persistence.load_public(root)
            self.assertTrue(public["ingest_password_configured"])
            self.assertNotIn("token", public)
            self.assertNotIn("0123456789abcdef", json.dumps(public))

    def test_migration_preserves_identity_and_maps_legacy_fields(self):
        old = {"collector_url":"https://logs.example.com", "customer_id":"Laroche", "site_id":"GRLAROCHE-SRV", "device_id":"stable"}
        migrated = persistence.migrate(old)
        self.assertEqual(migrated["device_id"], "stable")
        self.assertEqual(migrated["organization"], "Laroche")
        self.assertEqual(migrated["nas_name"], "GRLAROCHE-SRV")
        self.assertEqual(migrated["stream"], "default")
    def test_legacy_bearer_token_is_not_advertised_as_basic_password(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "settings.json").write_text(json.dumps({"collector_url":"https://logs.example.com", "customer_id":"Laroche", "site_id":"GRLAROCHE-SRV", "device_id":"stable"}))
            (root / "token").write_text("legacy-bearer-token")
            self.assertFalse(persistence.load_public(root)["ingest_password_configured"])


class TransactionTests(unittest.TestCase):
    def test_validation_failure_keeps_current(self):
        with tempfile.TemporaryDirectory() as td:
            current = Path(td) / "fluent-bit.conf"
            current.write_text("GOOD")
            with self.assertRaises(transaction.ApplyError):
                transaction.apply_config(current, "BAD", validator=lambda _: False, restart=lambda: True, running=lambda: True)
            self.assertEqual(current.read_text(), "GOOD")

    def test_restart_failure_rolls_back_last_good(self):
        with tempfile.TemporaryDirectory() as td:
            current = Path(td) / "fluent-bit.conf"
            current.write_text("GOOD")
            restarts = []
            with self.assertRaises(transaction.ApplyError):
                transaction.apply_config(current, "NEW", validator=lambda _: True, restart=lambda: restarts.append(1) or True, running=mock.Mock(side_effect=[False, True]))
            self.assertEqual(current.read_text(), "GOOD")
            self.assertEqual(len(restarts), 2)


class ConnectionTests(unittest.TestCase):
    def test_classifies_dns(self):
        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror()):
            self.assertEqual(connection.test("https://no.test", "laroche", "synology_logs", "nas-ingest", "0123456789abcdef")["code"], "DNS_FAILED")

    def test_classifies_tcp(self):
        with mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]), mock.patch("socket.create_connection", side_effect=TimeoutError()):
            self.assertEqual(connection.test("https://example.test", "laroche", "synology_logs", "nas-ingest", "0123456789abcdef")["code"], "TCP_TIMEOUT")

    def test_classifies_certificate(self):
        with mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]), mock.patch("socket.create_connection"), mock.patch("ssl.create_default_context") as ctx:
            ctx.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError(1, "bad")
            self.assertEqual(connection.test("https://example.test", "laroche", "synology_logs", "nas-ingest", "0123456789abcdef")["code"], "TLS_CERTIFICATE_INVALID")

    def test_connection_uses_basic_auth_and_empty_json_batch(self):
        tls = mock.Mock()
        tls.makefile.return_value.readline.return_value = b"HTTP/1.1 200 OK\r\n"
        with mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]), mock.patch("socket.create_connection"), mock.patch("ssl.create_default_context") as ctx:
            ctx.return_value.wrap_socket.return_value = tls
            result = connection.test("https://example.test", "laroche", "synology_logs", "nas-ingest", "0123456789abcdef")
        payload = tls.sendall.call_args.args[0].decode()
        self.assertTrue(result["success"])
        self.assertIn("POST /api/laroche/synology_logs/_json HTTP/1.1", payload)
        self.assertIn("Authorization: Basic " + base64.b64encode(b"nas-ingest:0123456789abcdef").decode(), payload)
        self.assertTrue(payload.endswith("\r\n\r\n[]"))

    def test_classifies_http_and_auth(self):
        self.assertEqual(connection.classify_http(401), "AUTHENTICATION_REFUSED")
        self.assertEqual(connection.classify_http(403), "AUTHENTICATION_REFUSED")
        self.assertEqual(connection.classify_http(500), "HTTP_UNAVAILABLE")
        self.assertEqual(connection.classify_http(204), "SUCCESS")
