import json
import os
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

    def test_validates_endpoint(self):
        self.assertEqual(config.validate_endpoint("/v1/logs"), "/v1/logs")
        for value in ["v1/logs", "//evil.test/x", "/x\ny", "/../admin", "/x#frag"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.validate_endpoint(value)


class FluentConfigTests(unittest.TestCase):
    def test_generation_is_deterministic_and_safe(self):
        settings = {"collector_url":"https://logs.example.com", "endpoint":"/v1/logs", "customer_id":"a\nb", "site_id":"s", "device_id":"d"}
        first = config.render_fluent_bit(settings, "/run/token", "/var/buffer")
        second = config.render_fluent_bit(dict(reversed(list(settings.items()))), "/run/token", "/var/buffer")
        self.assertEqual(first, second)
        self.assertIn("Listen 127.0.0.1", first)
        self.assertIn("Port 5514", first)
        self.assertIn("tls.verify On", first)
        self.assertIn("storage.total_limit_size 128M", first)
        self.assertNotIn("a\nb", first)


class PersistenceTests(unittest.TestCase):
    def test_token_create_preserve_and_delete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            persistence.save(root, config.defaults("device"), token_action="replace", token="secret-value")
            token_path = root / "token"
            self.assertEqual(stat.S_IMODE(token_path.stat().st_mode), 0o600)
            persistence.save(root, config.defaults("device"), token_action="preserve")
            self.assertEqual(token_path.read_text(), "secret-value")
            persistence.save(root, config.defaults("device"), token_action="delete")
            self.assertFalse(token_path.exists())

    def test_frontend_never_receives_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            persistence.save(root, config.defaults("device"), token_action="replace", token="never-return-me")
            public = persistence.load_public(root)
            self.assertTrue(public["token_configured"])
            self.assertNotIn("token", public)
            self.assertNotIn("never-return-me", json.dumps(public))

    def test_migration_preserves_identity(self):
        old = {"collector_url":"https://logs.example.com", "customer_id":"c", "site_id":"s", "device_id":"stable"}
        migrated = persistence.migrate(old)
        self.assertEqual(migrated["device_id"], "stable")
        self.assertEqual(migrated["endpoint"], "/v1/logs")


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
            self.assertEqual(connection.test("https://no.test", "/v1/logs", None)["code"], "DNS_FAILED")

    def test_classifies_tcp(self):
        with mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]), mock.patch("socket.create_connection", side_effect=TimeoutError()):
            self.assertEqual(connection.test("https://example.test", "/v1/logs", None)["code"], "TCP_TIMEOUT")

    def test_classifies_certificate(self):
        with mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]), mock.patch("socket.create_connection") as tcp, mock.patch("ssl.create_default_context") as ctx:
            ctx.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError(1, "bad")
            self.assertEqual(connection.test("https://example.test", "/v1/logs", None)["code"], "TLS_CERTIFICATE_INVALID")

    def test_classifies_http_and_auth(self):
        self.assertEqual(connection.classify_http(401), "AUTHENTICATION_REFUSED")
        self.assertEqual(connection.classify_http(403), "AUTHENTICATION_REFUSED")
        self.assertEqual(connection.classify_http(500), "HTTP_UNAVAILABLE")
        self.assertEqual(connection.classify_http(204), "SUCCESS")
