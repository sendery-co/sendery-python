import json
import unittest
from unittest.mock import patch
from sendery import Sendery, SenderyError


class ClientTests(unittest.TestCase):
    def test_retry_preserves_key_and_original_data(self):
        client = Sendery("test")
        data = {"name": "Original"}
        email = client.prepare(to="alex@example.com", template="welcome", data=data)
        data["name"] = "Changed"
        with patch.object(client, "_request", side_effect=[SenderyError(503), {"id": "one", "status": "queued"}]) as request, patch("sendery.time.sleep"):
            email.retry().send()
        self.assertEqual(request.call_args_list[0], request.call_args_list[1])
        self.assertEqual("Original", json.loads(request.call_args.args[2])["data"]["name"])
        self.assertEqual(email.idempotency_key, request.call_args.args[3])

    def test_capacity_is_not_retried(self):
        client = Sendery("test")
        with patch.object(client, "_request", side_effect=SenderyError(429, "email_capacity_exceeded")) as request:
            with self.assertRaises(SenderyError):
                client.prepare(to="a@example.com", template="welcome", data={}).retry().send()
        self.assertEqual(1, request.call_count)

    def test_explicit_key_and_get(self):
        client = Sendery("test")
        self.assertEqual("event-12", client.prepare(to="a@example.com", template="welcome", data={}, idempotency_key="event-12").idempotency_key)
        with patch.object(client, "_request") as request:
            client.get("message/12")
        request.assert_called_once_with("GET", "/api/v1/emails/message%2F12")

    def test_remote_http_and_credential_urls_rejected(self):
        for url in ["http://example.com", "https://user:pass@example.com"]:
            with self.assertRaises(ValueError):
                Sendery("test", url)
