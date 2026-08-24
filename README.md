# Deepdots Python SDK

Python SDK for the Deepdots API (the company was formerly called MagicFeedback).

## Installation

```bash
pip install deepdots
```

The original distribution is still published and still works:

```bash
pip install magicfeedback
```

## Naming

MagicFeedback was renamed **Deepdots**. Both sets of names work and refer to the
*same* objects, so **no existing code needs to change**:

| | Current name | Original name |
|---|---|---|
| PyPI distribution | `deepdots` | `magicfeedback` |
| Import package | `deepdots_sdk` | `magicfeedback_sdk` |
| Client class | `Deepdots` | `MagicFeedback` |

Distribution names are written lowercase throughout — that is the packaging
convention, and PyPI treats names case-insensitively anyway, so
`pip install MagicFeedback` keeps working for anyone who has it written that way.

`deepdots_sdk` re-exports `magicfeedback_sdk` module by module, and `Deepdots`
is the same class object as `MagicFeedback` — `MagicFeedback is Deepdots` is
`True`, so `isinstance()` checks and subclasses behave identically. Submodule
imports work under either name (`from deepdots_sdk.api.feedback import
FeedbackAPI`). New code should prefer the Deepdots names.

## Usage

```python
from deepdots_sdk import Deepdots

client = Deepdots("email", "password")
```

The original names remain fully supported:

```python
from magicfeedback_sdk import MagicFeedback

client = MagicFeedback("email", "password")
```

## Authentication

The bearer token is resolved from one of two sources, selected with
`auth_source`:

- `"datastore"` **(default)** — read the token cached in Google Cloud Datastore
  by the `update-token` job (kind `token-storage`, email
  `robot@magicfeedback.io`, database `shared`). This avoids an Identity Platform
  login on every use. If the cached token is missing, stale (older than
  `token_max_age_min`, default 50 min) or Datastore is unreachable, the client
  falls back to Identity Platform using `email`/`password`.
- `"identity"` — always log in via Identity Platform (`signInWithPassword`), the
  original behaviour, with no Datastore lookup.

```python
# Datastore-cached token (default), with Identity Platform fallback.
# email/password are only needed for the fallback.
client = MagicFeedback("email", "password")

# Tune the Datastore lookup (all optional; shown with their defaults):
client = MagicFeedback(
    "email", "password",
    auth_source="datastore",
    gcp_project_id=None,             # None => inferred from Application Default Credentials
    datastore_database_id="shared",
    token_kind="token-storage",
    token_email="robot@magicfeedback.io",
    token_max_age_min=50,
    datastore_timeout_s=5.0,         # cap the lookup so the fallback stays fast
)

# Original behaviour — always mint a fresh token via Identity Platform:
client = MagicFeedback("email", "password", auth_source="identity")
```

The Datastore lookup is bounded by `datastore_timeout_s` (default 5s): if the
cache is unreachable or the credentials are stale, the client falls back to
Identity Platform within that budget instead of blocking on the Datastore
client's default ~60s retry deadline.

The Datastore path needs the `google-cloud-datastore` package (installed as a
dependency) and Google Application Default Credentials with read access to the
token entity (`gcloud auth application-default login` or
`GOOGLE_APPLICATION_CREDENTIALS`).

Helper methods:

- `client.refresh_token()` — re-resolve the token (same `auth_source`) and
  update the auth header in place across all sub-API clients. Useful for
  long-lived clients whose token has expired.
- `client.auth.get_token_from_datastore(allow_stale=False)` — read the cached
  token directly; returns `None` when missing, stale or unreachable.

## API Reference

### `client.feedbacks`
- `create(feedback)` — creates a new feedback item. Required fields: `name`, `type`, `identity`, `integrationId`, `companyId`, `productId`.
- `get(filter=None)` — lists feedback items.
- `get_id(feedback_id, filter=None)` — retrieves a specific feedback item.
- `update(feedback_id, feedback)` — updates a feedback item.

`create`, `update`, `get` and `get_id` all normalize the `answers`,
`metadata`, `metrics` and `profile` fields: each entry is `{"key": ...,
"value": ...}`, and the raw API is inconsistent about `value`'s shape — the
same feedback can have one entry with a bare scalar (`"value": "voice"`) next
to another with a list (`"value": ["sln"]`). The SDK wraps every bare scalar
as `[value]`, both on what it sends (create/update) and on what it returns
(get/get_id), so callers only ever see/send the list form. `questions` is a
different shape (`title`/`ref`/`position`/...) and is left untouched; `data`
is not currently normalized.
- `delete(feedback_id)` — deletes a feedback item.
- `upload_attachment(feedback_id, file_path, filename=None, extra_data=None, max_attachments=3, check_duplicate_content=True)` — uploads a file and attaches it to a feedback. Before uploading it fetches the feedback's existing attachments and enforces two guards (nothing is uploaded if either trips): a **maximum of `max_attachments` files** (default 3) per feedback, and **no duplicate content** — the new file's bytes are SHA-256 hashed and compared against each existing attachment by *content*, not filename, so re-attaching the same file under a different name raises `ValueError`. The duplicate check downloads each existing attachment to hash it (best-effort — attachments it cannot download, e.g. a private bucket returning 403, are skipped); pass `check_duplicate_content=False` to disable it. The cap fails **closed**: if the feedback's current attachments can't be fetched, the upload is refused rather than risk exceeding the limit.

### `client.contacts`
- `create(contact)`, `get(filter=None)`, `update(contact_id, contact)`, `delete(contact_id)`

### `client.campaigns`
- `create(campaign)`, `get(filter=None)`
- `create_session(campaign_id, session)`, `get_sessions(campaign_id, filter=None)`, `get_sessions_feedbacks(campaign_id, filter=None)`

### `client.metrics`
- `get(filter=None)`

### `client.products`
- `get(filter=None)`

### `client.companies`
- `get(filter=None)`, `get_id(id, filter=None)`

### `client.integrations_questions`
- `get(integration_id, filter=None)`

### `client.reports`
- `get(filter=None)`, `get_newsletter(filter=None)`, `update(report_id, report)`

### `client.requests`
- `get(filter=None)`, `get_id(request_id, filter=None)`, `update(request_id, request)`

To mark a request DONE/ERROR asynchronously, publish a completion event to the
`request-done` Pub/Sub topic (project `magicfeedback-prod-api`, topic
`request-done`); the `request-done` Cloud Function consumes it and PATCHes the
request. The SDK does not publish this itself — build the envelope with
`build_done_message` and publish it directly. See
[`examples/mark_request_done.py`](examples/mark_request_done.py).

## Examples

```python
# Create a feedback
client.feedbacks.create({
    "name": "Test Feedback",
    "type": "APP",
    "identity": "MAGICFORM",
    "integrationId": "your-integration-id",
    "companyId": "YOUR_COMPANY",
    "productId": "YOUR_PRODUCT",
    "answers": [
        {"key": "score", "value": "4"},
        {"key": "comment", "value": "Great service!"},
    ],
})

# Get a feedback with its attachments
client.feedbacks.get_id(
    "<feedback_id>",
    filter={"include": [{"relation": "feedbackAttachments"}]}
)

# Upload a file attachment.
# A feedback holds at most 3 attachments, and a file whose bytes are identical
# to one already attached (even under a different name) is rejected with a
# ValueError — nothing is uploaded in either case.
client.feedbacks.upload_attachment(
    "<feedback_id>",
    file_path="/path/to/file.pdf",
    filename="report.pdf",              # optional, defaults to file name
    extra_data={"source": "crm"},       # optional, any JSON-serialisable dict
    # max_attachments=3,                # optional, override the per-feedback cap
    # check_duplicate_content=False,    # optional, skip the byte-for-byte dedupe
)

# Mark a request DONE via the request-done Pub/Sub topic.
# The SDK builds the envelope; the producer publishes it directly.
import json
from google.cloud import pubsub_v1
from magicfeedback_sdk.api.requests import build_done_message

message = build_done_message(
    "<request_id>",
    "<company_id>",
    output={"value": "…final result…"},
    sources=["<feedbackId1>", "<feedbackId2>"],  # optional
    logs="processed 2 items",                     # optional
    # success=False, error={"message": "processing failed"}  # to mark ERROR
)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("magicfeedback-prod-api", "request-done")
publisher.publish(topic_path, json.dumps(message).encode("utf-8")).result()
```

## Logging

```python
import logging
client.set_logging(logging.DEBUG)
```

## License

MIT

## Contributing

Developing on the SDK itself — layout, tests, and how to cut a release — is
documented in [DEVELOPERS.md](DEVELOPERS.md).

## Contact

farias@magicfeedback.io
