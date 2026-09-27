# Sendery — Python integration

Send template emails from Python with the Sendery SDK.

MIT licensed. Repository: https://github.com/sendery-co/sendery-python

Documentation: https://sendery.co/en/docs/python

## Install

```
pip install sendery
```

## Install

Python 3.10+

## Configure the client

Set SENDERY_API_KEY in your server environment. The client uses Python’s standard HTTP library and has no runtime dependencies.

## Send from synchronous code

The client is synchronous. In an async application, run it in a worker or thread rather than blocking the event loop. Catch SenderyError for status, code, errors, and retry_after.

## Example

```
import os
from sendery import Sendery

sendery = Sendery(os.environ["SENDERY_API_KEY"])
email = sendery.prepare(
    to="alex@example.com", template="welcome", data={"name": "Alex"},
)
receipt = email.retry(3).send()
```

## Retries and queues

Reuse a prepared email for retries. New requests receive new keys; when reconstructing a request in another process, supply the original key and unchanged data. Keep API keys server-side. Framework mailers send Sendery templates, not arbitrary HTML or attachments.
