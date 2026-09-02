import io
import json
import unittest
from unittest import mock

from idnnov_agent import api


class ApiSecurityTests(unittest.TestCase):
    def test_requires_dsm_session_and_admin(self):
        self.assertEqual(api.handle({}, b"{}").status, 403)
        with mock.patch.object(api, "is_admin", return_value=False):
            self.assertEqual(api.handle({"REMOTE_USER":"alice"}, b"{}").status, 403)

    def test_rejects_method_content_type_size_and_unknown_fields(self):
        base = {"REMOTE_USER":"admin", "REQUEST_METHOD":"POST", "CONTENT_TYPE":"application/json"}
        with mock.patch.object(api, "is_admin", return_value=True):
            self.assertEqual(api.handle({**base, "REQUEST_METHOD":"GET"}, b"").status, 405)
            self.assertEqual(api.handle({**base, "CONTENT_TYPE":"text/plain"}, b"{}").status, 415)
            self.assertEqual(api.handle(base, b"x" * 65537).status, 413)
            body = json.dumps({"action":"get_settings", "unexpected":1}).encode()
            self.assertEqual(api.handle(base, body).status, 400)

    def test_responses_do_not_leak_secrets(self):
        base = {"REMOTE_USER":"admin", "REQUEST_METHOD":"POST", "CONTENT_TYPE":"application/json"}
        with mock.patch.object(api, "is_admin", return_value=True), mock.patch.object(api, "get_settings", return_value={"token_configured":True}):
            response = api.handle(base, b'{"action":"get_settings"}')
        self.assertNotIn("token\"", response.body)

    def test_save_uses_strict_schema_and_token_action(self):
        env = {"REMOTE_USER":"admin", "REQUEST_METHOD":"POST", "CONTENT_TYPE":"application/json"}
        body = json.dumps({"action":"save_settings","settings":{"collector_url":"https://logs.example.com","endpoint":"/v1/logs","customer_id":"c","site_id":"s","device_id":"d"},"token_action":"preserve"}).encode()
        with mock.patch.object(api, "is_admin", return_value=True), mock.patch.object(api, "save_settings", return_value={"applied":True}) as save:
            response = api.handle(env, body)
        self.assertEqual(response.status, 200)
        save.assert_called_once()

    def test_status_is_secret_free(self):
        env = {"REMOTE_USER":"admin", "REQUEST_METHOD":"POST", "CONTENT_TYPE":"application/json"}
        with mock.patch.object(api, "is_admin", return_value=True), mock.patch.object(api, "get_status", return_value={"running":True,"buffer_bytes":0}):
            response = api.handle(env, b'{"action":"get_status"}')
        self.assertEqual(response.status, 200)
        self.assertNotIn("secret", response.body.lower())
