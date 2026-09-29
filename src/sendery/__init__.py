"""Server-side Sendery template API client."""
import base64
import json
import math
import random
import re
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError


def attachment(filename, content, content_type="application/octet-stream"):
    """Encode file bytes for a per-send attachment."""
    if not isinstance(content, bytes) or not 0 < len(content) <= 5242880:
        raise ValueError("Attachments must contain 1 to 5,242,880 bytes.")
    return {"filename": filename, "content": base64.b64encode(content).decode("ascii"), "content_type": content_type}


class SenderyError(Exception):
    def __init__(self, status, code="request_error", errors=None, retry_after=None):
        super().__init__(f"Sendery API error: {code}")
        self.status, self.code, self.errors, self.retry_after = status, code, errors or {}, retry_after

    @property
    def retryable(self):
        return self.status in (0, 500, 502, 503, 504) or (self.status == 429 and self.code == "rate_limited")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PendingEmail:
    def __init__(self, client, payload, key):
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", key):
            raise ValueError("Invalid idempotency key.")
        self.client, self._key, self._body, self._retries = client, key, json.dumps(payload, allow_nan=False).encode(), 0

    @property
    def idempotency_key(self):
        return self._key

    def retry(self, retries=3):
        if type(retries) is not int or not 0 <= retries <= 5:
            raise ValueError("Choose 0 to 5 retries.")
        self._retries = retries
        return self

    def send(self):
        for attempt in range(self._retries + 1):
            try:
                return self.client._request("POST", "/api/v1/emails", self._body, self._key)
            except SenderyError as error:
                if attempt == self._retries or not error.retryable:
                    raise
                delay = error.retry_after if error.retry_after is not None else min(8, .25 * 2 ** attempt + random.random() * .1)
                if delay > 30:
                    raise
                time.sleep(delay)


class Sendery:
    def __init__(self, api_key, base_url="https://sendery.co"):
        url = urlparse(base_url)
        if not api_key or not url.hostname or url.username or url.password or url.query or url.fragment or (url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))):
            raise ValueError("Provide an API key and an HTTPS URL (HTTP allowed only on loopback).")
        self._api_key, self._base_url, self._opener = api_key, base_url.rstrip("/"), build_opener(_NoRedirect)

    def prepare(self, *, to, template, data, locale=None, idempotency_key=None, attachments=None):
        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary.")
        payload = {"to": to, "template": template, "data": data}
        if attachments:
            if len(attachments) > 10 or sum(len(base64.b64decode(item["content"], validate=True)) for item in attachments) > 5242880:
                raise ValueError("Use at most 10 attachments, up to 5 MB combined.")
            payload["attachments"] = attachments
        if locale is not None:
            payload["locale"] = locale
        return PendingEmail(self, payload, idempotency_key if idempotency_key is not None else str(uuid.uuid4()))

    def send(self, **kwargs):
        return self.prepare(**kwargs).send()

    def get(self, message_id):
        return self._request("GET", "/api/v1/emails/" + quote(message_id, safe=""))

    def _request(self, method, path, body=None, key=None):
        headers = {"Authorization": "Bearer " + self._api_key, "Content-Type": "application/json", "Accept": "application/json"}
        if key is not None:
            headers["Idempotency-Key"] = key
        try:
            with self._opener.open(Request(self._base_url + path, body, headers, method=method), timeout=10) as response:
                try:
                    result = json.load(response)
                except (ValueError, UnicodeError):
                    raise SenderyError(0, "invalid_response") from None
                if not isinstance(result, dict) or not isinstance(result.get("id"), str) or not isinstance(result.get("status"), str):
                    raise SenderyError(0, "invalid_response")
                return result
        except HTTPError as error:
            try:
                details = json.loads(error.read())
                if not isinstance(details, dict):
                    details = {}
            except (ValueError, UnicodeError):
                details = {}
            retry_after = error.headers.get("Retry-After")
            try:
                delay = max(0, float(retry_after)) if retry_after is not None else None
            except ValueError:
                try:
                    delay = max(0, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError):
                    delay = None
            if delay is not None and not math.isfinite(delay):
                delay = None
            raise SenderyError(error.code, details.get("code", "request_error"), details.get("errors"), delay) from None
        except (URLError, TimeoutError, OSError):
            raise SenderyError(0, "connection_error") from None
