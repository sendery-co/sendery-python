# Sendery for Python

Send published Sendery templates from Python.

[Documentation](https://sendery.co/en/docs/python) · [API reference](https://sendery.co/en/docs/send-email) · [Changelog](CHANGELOG.md)

## Requirements

Python 3.10+.

## Install

```bash
pip install sendery
```

## Set up

Publish a `welcome` template with `name` and `action_url` variables, and create a [project API key](https://sendery.co/en/docs/authentication). Store it as `SENDERY_API_KEY` on your server.

```bash
export SENDERY_API_KEY="your_project_api_key"
```

## Send an email

The response contains the accepted email’s `id` and `status`. Calls are synchronous; use `asyncio.to_thread()` when sending from async code.

```python
import os
from sendery import Sendery

sendery = Sendery(os.environ["SENDERY_API_KEY"])
receipt = sendery.send(
    to="alex@example.com",
    template="welcome",
    data={"name": "Alex", "action_url": "https://example.com/start"},
)

print(receipt["id"])
```

## Retrieve an email

Use the returned ID to [check delivery status](https://sendery.co/en/docs/get-email).

```python
message = sendery.get(receipt["id"])
print(message["status"])
```

## Retry a send

Use a key such as `welcome-123` for one email, and [keep the payload unchanged on retries](https://sendery.co/en/docs/idempotency). `retry(3)` allows up to three additional attempts for temporary failures; `send()` alone makes one attempt.

```python
email = sendery.prepare(
    to="alex@example.com",
    template="welcome",
    data={"name": "Alex", "action_url": "https://example.com/start"},
    idempotency_key="welcome-123",
)
receipt = email.retry(3).send()
```

## Handle errors

Catch the SDK exception to inspect the [status and code](https://sendery.co/en/docs/errors). Retry delays are in seconds. The example uses the prepared `email` from the [retry example above](#retry-a-send).

```python
from sendery import SenderyError

try:
    receipt = email.retry(3).send()
except SenderyError as error:
    print(error.status, error.code, error.errors)
    # error.retry_after is a delay in seconds, when provided.
    raise
```

## More

See [idempotency and retries](https://sendery.co/en/docs/idempotency) for retry conditions, delays, and reusing a key across attempts.

## License

[MIT](LICENSE).
