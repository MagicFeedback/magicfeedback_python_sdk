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

# With an API key, issued by Deepdots: the way for integrations.
client = Deepdots(api_key="dd_live_...", base_url="https://api.deepdots.com")

# With an API user's email and password.
client = Deepdots("email", "password", auth_source="identity",
                  base_url="https://api.deepdots.com")
```

The original names remain fully supported:

```python
from magicfeedback_sdk import MagicFeedback

client = MagicFeedback("email", "password")
```

## Authentication

**API key.** Pass `api_key="dd_live_..."` and the key is sent as the bearer
token on every request: no sign-in, nothing to refresh. Deepdots issues the
keys, one per integration; each acts as its API user, with the same
permissions. `user`, `password` and `auth_source` are ignored when a key is
given.

**Email and password.** Otherwise the client signs in through the API
(`POST /auth/token`), which asks Identity Platform for the token. The SDK no
longer calls Identity Platform itself, so it needs no Identity Platform key:
the `ip_key` argument is ignored (with a `DeprecationWarning`). The token lasts
one hour; the client keeps the refresh token the API returns.

The token is resolved from one of two sources, selected with `auth_source`:

- `"datastore"` **(default)** — read the token cached in Google Cloud Datastore
  by the `update-token` job (kind `token-storage`, email
  `robot@magicfeedback.io`, database `shared`). This avoids a sign-in on every
  use. If the cached token is missing, stale (older than `token_max_age_min`,
  default 50 min) or Datastore is unreachable, the client falls back to
  signing in with `email`/`password`.
- `"identity"` — always sign in with `email`/`password`, with no Datastore
  lookup.

```python
# API key (no sign-in):
client = MagicFeedback(api_key="dd_live_...", base_url="https://api.deepdots.com")

# Datastore-cached token (default), signing in as the fallback.
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

# Always sign in with email and password:
client = MagicFeedback("email", "password", auth_source="identity")
```

A wrong email or password raises `requests.HTTPError` with a **401** (the same
for both, so the API does not tell which accounts exist); a disabled user is a
**403**, and too many failed attempts on the account a **429**.

The Datastore lookup is bounded by `datastore_timeout_s` (default 5s): if the
cache is unreachable or the credentials are stale, the client falls back to
signing in within that budget instead of blocking on the Datastore client's
default ~60s retry deadline.

The Datastore path needs the `google-cloud-datastore` package (installed as a
dependency) and Google Application Default Credentials with read access to the
token entity (`gcloud auth application-default login` or
`GOOGLE_APPLICATION_CREDENTIALS`).

Helper methods:

- `client.refresh_token()` — renew the token and update the auth header in
  place across all sub-API clients. With `auth_source="identity"` it uses the
  refresh token (`POST /auth/token/refresh`), and signs in again if that was
  rejected; with `"datastore"` it re-reads the cache (signing in as the
  fallback); with an API key it does nothing. Useful for long-lived clients
  whose token has expired: `client.crm` calls it by itself on a 401.
- `client.auth.get_token_from_datastore(allow_stale=False)` — read the cached
  token directly; returns `None` when missing, stale or unreachable.

## API Reference

### `client.feedbacks`
- `create(feedback)` — creates a feedback via `POST /feedbacks`. The dict becomes the JSON body with your keys unchanged, so every field is top-level (the SDK's only change is wrapping a scalar `value` into a list, see below). The SDK requires `name`, `type`, `identity`, `integrationId`, `companyId`, `productId` (it raises `ValueError` before sending if one is missing). Use the `identity` of the integration the feedback belongs to: survey identities such as `MAGICFORM`, `MAGICSURVEY` and `CSV` analyse `answers`, while most others, such as `GENERAL` and `CUSTOM`, analyse only `text`, and some accepted values are not analysed at all. Optional fields include `text`, `answers`, `metadata`, `metrics`, `crmContactId` and the source-system fields `external_id`, `externalGeneratedAt`, `externalUpdatedAt` and `externalUrl` — see [Feedback source-system fields](#feedback-source-system-fields). Keys are case-sensitive. A misspelled required key (e.g. `company_id` instead of `companyId`) makes the SDK raise `ValueError: Missing required field: companyId`; any other key the API does not accept is rejected with **422** and nothing is created — a misspelling such as `externalId`, or a server-set field such as `id`, `status` or `createdAt`. When `external_id` matches an existing, non-deleted feedback of the same company, product and integration, the API returns that feedback **unchanged** (HTTP 200, nothing written) instead of creating a duplicate.
- `get(filter=None)` — lists feedback items. To find the feedback an SDK session became, filter on the `sessionId` that `POST /sdk/feedback` returned: `get(filter={"where": {"sdkSessionId": session_id}, "order": ["createdAt DESC"]})`. Set only on feedbacks created after the field shipped. Since 2026-10-07 a session that closes again updates the feedback it already has, so a session normally maps to one feedback. A session can still have two (one that closed twice between 2026-09-30 and 2026-10-07, or whose first feedback was deleted), so keep the `order` and take the first result.
- `get_id(feedback_id, filter=None)` — retrieves a specific feedback item.
- `update(feedback_id, feedback)` — `PATCH /feedbacks/{id}` with only the fields you pass; returns `{}` (the API answers 204). `external_id`, `type`, `identity`, `integrationId`, `productId`, `profile` and `data` cannot be changed (422), so never PATCH back a whole object read from `get_id()`. The change is saved immediately, but charts and reports pick up changes to the date, `text`, `answers`, `metrics` or `metadata` only when the feedback is re-analysed: include `"status": "REGISTERED"` in the same call to queue a full re-analysis — read what that does at the end of [Feedback source-system fields](#feedback-source-system-fields) first. `update()` needs an API user whose role may update feedback (otherwise **405**).
- `update_metadata_batch(items, mode=None)` — merges metadata into **many feedbacks in one request** and triggers re-analysis for each, so the change propagates through the analysis pipeline to BigQuery (`insight.metadata`) and the metadata table. `items` is a list of `{"feedbackId": ..., "metadata": [{"name": ..., "values": [...]}]}`; each metadata entry may use the SDK-native `{"key": ..., "value": ...}` shape instead, and a bare scalar value is wrapped into a list. Semantics are **additive** (upsert by key): the keys you send are added, or their values overwritten if the key already exists — every other existing key is kept, and **nothing is ever deleted** (an item with no metadata is a no-op). Pass `mode="append"` to add the values you send to the ones a key already holds instead of overwriting them (values it holds already are skipped, so a retry adds nothing twice) — use it for event-log keys such as `deepdots_message`, which the default would wipe. Feedbacks not listed are untouched. The feedback ids are checked **all or nothing**: if any does not exist, is deprecated or belongs to a company you cannot see, the API answers **404** naming them and nothing is written (the SDK raises `requests.HTTPError`); only a failure writing or re-queuing one feedback is listed in `failed` while the rest still land. Each updated feedback re-runs the full analysis pipeline. Returns e.g. `{"feedbacks": N, "triggered": M, "failed": [...]}`.
- `delete(feedback_id)` — soft-deletes the feedback: its status becomes `DEPRECATED`, it disappears from `get_id`, dashboards and reports, and from `get` unless your filter's `where` sets `status`; the SDK has no way to restore it. Returns `{}`. A later `create()` with the same `external_id` makes a new feedback.
- `upload_attachment(feedback_id, file_path, filename=None, extra_data=None, max_attachments=3, check_duplicate_content=True)` — uploads a file and attaches it to a feedback. Before uploading it fetches the feedback's existing attachments and enforces two guards (nothing is uploaded if either trips): a **maximum of `max_attachments` files** (default 3) per feedback, and **no duplicate content** — the new file's bytes are SHA-256 hashed and compared against each existing attachment by *content*, not filename, so re-attaching the same file under a different name raises `ValueError`. The duplicate check downloads each existing attachment to hash it (best-effort — attachments it cannot download, e.g. a private bucket returning 403, are skipped); pass `check_duplicate_content=False` to disable it. The cap fails **closed**: if the feedback's current attachments can't be fetched, the upload is refused rather than risk exceeding the limit.

`create`, `update`, `get` and `get_id` all normalize the `answers`,
`metadata`, `metrics` and `profile` fields: each entry is `{"key": ...,
"value": ...}`, and the raw API is inconsistent about `value`'s shape — the
same feedback can have one entry with a bare scalar (`"value": "voice"`) next
to another with a list (`"value": ["sln"]`). The SDK wraps every bare scalar
as `[value]`, both on what it sends (create/update) and on what it returns
(get/get_id), so callers only ever see/send the list form. `questions` is a
different shape (`title`/`ref`/`position`/...) and is left untouched; `data`
is not currently normalized. (`profile` can only be sent with `create()`:
`update()` rejects it with 422.)

#### Feedback source-system fields

When feedback comes from another system (a helpdesk, a review site, a CSV
export...), send these optional fields with `create()`. They go at the top
level, next to `integrationId` and `companyId`, not inside `answers` or
`metadata`:

| Field | Meaning |
|---|---|
| `external_id` | ID of the record in the source system, as a string (`"48213"`, not `48213`). Makes `create()` safe to retry: re-sending an id that already exists for the same company, product and integration returns the existing feedback unchanged and never updates it. Send retries for the same id one after another, not in parallel: two simultaneous requests can both create a feedback. Without it nothing is deduplicated, and a retry creates a second copy. |
| `externalGeneratedAt` | When the feedback happened in the source system. **This is the date dashboards, reports and date filters use.** If it is omitted, the API stores the time it received the request, so a historical import lands entirely on the import day. |
| `externalUpdatedAt` | When the record last changed in the source system (defaults to the request time). |
| `externalUrl` | Link to the original record, shown as the feedback's *Original source* link. |

The casing is mixed: `external_id` is the only snake_case field, and every
other field is camelCase (`companyId`, not `company_id`).

Send both dates as **UTC ISO 8601 strings ending in `Z`**, e.g.
`"2026-10-06T11:00:00.000Z"` (JavaScript's `toISOString()` format). The API
stores any string without checking it, but analytics can only read
`YYYY-MM-DDTHH:MM:SS[.ffffff]Z`, or `YYYY-MM-DDTHH:MM:SS` with no fraction and
no zone (charts read it as UTC, but the dashboard's feedback list shows it
unconverted, as if it were the viewer's local time, so add the `Z`). Any other
value is still stored, but analytics can't use it, and in `externalGeneratedAt`
it makes the feedback drop out of date-filtered charts and reports. That
includes an offset such as `+02:00` (Python's default `isoformat()` of an aware
datetime), fractional seconds without the `Z` (`isoformat()` of a naive
datetime that has microseconds, such as `datetime.utcnow()`), more than six
fractional digits, a date without a time, and a space instead of `T`. The API stores the value as text, so filters and
sorting compare it as a string. A `datetime` object raises `TypeError` in the
SDK, and `None` or a number gets a 422.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+; on Windows also: pip install tzdata

def to_api_datetime(dt):
    """Timezone-aware datetime -> '2026-10-06T11:00:00.000Z'."""
    if dt.utcoffset() is None:
        raise ValueError("Naive datetime: attach the source time zone first, e.g. dt.replace(tzinfo=ZoneInfo('Europe/Copenhagen'))")
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
```

The helper refuses naive datetimes because `astimezone()` would treat them as
machine-local time: attach the source zone first
(`dt.replace(tzinfo=ZoneInfo("Europe/Copenhagen"))`).

Re-sending a feedback does not fix its date (see `external_id`). Instead,
PATCH the date and re-run the analysis in the same call:

```python
client.feedbacks.update(feedback_id, {
    "externalGeneratedAt": "2026-10-06T11:00:00.000Z",
    "status": "REGISTERED",
})
```

Like every `update()` that sends `"status": "REGISTERED"`, that is a full re-analysis:
- The summary, issues and topics are regenerated, and issue triage starts over.
- Automations on feedback completion fire again.
- Once the new analysis finishes `DONE`, charts and reports can take up to an
  hour to settle. Check with `get_id()` that `status` is back to `DONE`: if the
  run ends `PARTIAL` or `ERROR`, charts keep showing the old date until a later
  analysis finishes `DONE`: send the same update again.

Send `"status": "REGISTERED"` only once the feedback has finished processing;
while it is still `REGISTERED` or `PROCESSING` it starts a second analysis.
If some feedbacks stay `REGISTERED` or `PROCESSING` long after the rest have
finished, they are probably not being analysed at all (for example because an
answer value is a number, or their `identity` is not analysed); ask your
Deepdots contact instead of re-sending them.
Patching the date without `"status": "REGISTERED"` updates the stored feedback
only, and charts and reports keep the old date until it is next re-analysed.
Any `update()` of a feedback whose status is `DONE`, even without `status`,
fires the feedback-completion automations again. The API user needs a role
with feedback-update permission (otherwise 405). Don't send an empty
`externalGeneratedAt` to `update()`: unlike `create()`, `update()` stores it as
it is, and the feedback then drops out of date-filtered charts and reports. If
you need to re-analyse many feedbacks, talk to your Deepdots contact before you
start.

### `client.contacts`
- `create(contact)`, `get(filter=None)`, `update(contact_id, contact)`, `delete(contact_id)`
- `upsert(contact)` — **create-or-update** a single contact, matched by `(companyId, email)`, via `POST /crm/contacts/upsert`. Prefer this over `create()` when the record may already exist: `create()` always inserts (there is no unique constraint on email, so it silently makes duplicates), whereas `upsert()` PATCHes the existing ACTIVE contact if one is found. On the update branch scalars are overwritten and `customFields` is **merged** (same additive semantics as `update_fields`); the match key is never rewritten. `name`, `email`, `companyId` are required. Returns the contact after the upsert.

  ```python
  client.contacts.upsert({
      "name": "Ada", "email": "ada@example.com", "companyId": "ACME",
      "customFields": {"loyalty_tier": "gold"},
  })
  ```
- `upsert_batch(items, chunk_size=500)` — upsert **many** contacts via `POST /crm/contacts/upsert/batch`, automatically **chunking** `items` to the server cap (500) so you can pass a list of any length. Sending a batch is the pool-friendly way to do bulk (one sequential request per chunk instead of N parallel calls racing the DB connection pool). Best-effort per item: an item that fails on its own (bad email, inaccessible company, ...) is collected in `failed` and the rest still land. Returns aggregated `{"contacts", "created", "updated", "failed"}`; each `failed` entry's `index` points into the **original** `items` list.

  ```python
  result = client.contacts.upsert_batch([
      {"name": "Ada",  "email": "ada@example.com",  "companyId": "ACME", "customFields": {"tier": "gold"}},
      {"name": "Alan", "email": "alan@example.com", "companyId": "ACME"},
      # ... pass thousands; the SDK splits them into 500-item requests
  ])
  print(result["created"], result["updated"], result["failed"])
  ```
- `update_fields(contact_id, custom_fields=None, **native_fields)` — **additively** merge custom fields into a contact via `PATCH /crm/contacts/{id}/fields`. The refs you send are upserted, **every other custom field is kept**, and a value of `None` removes its ref. Prefer this over `update()` for custom fields: `update()` writes the `customFields` object whole, so setting one field there deletes all the others. `custom_fields` values may be `str`/`int`/`float`/`bool`. You may also pass native columns as keywords — `name`, `lastname`, `phone`, `address`, `city`, `state`, `postalCode` — anything else (`email`, `externalId`, `status`, `country`, `type`) is rejected with a 400; use `update()` for those. Returns `{"id": ..., "customFields": {...}}`, the full field set after the merge.

  ```python
  # Add / overwrite custom fields, keeping any others the contact already has
  client.contacts.update_fields(contact_id, {"loyalty_tier": "gold", "vip": True})

  # Remove a custom field
  client.contacts.update_fields(contact_id, {"loyalty_tier": None})

  # Custom fields + a native column in one call
  client.contacts.update_fields(contact_id, {"nps_segment": "promoter"}, city="Copenhagen")
  ```

### `client.crm`
CRM objects are the records a company keeps next to its contacts (tickets,
matches, memberships, ...). Each is stored as `(companyId, type, externalId)`
plus a free-form `data` object, and survey answers can be linked to them
through the survey link's URL parameters. The connectors take your own records
**as they are** and do the mapping on our side.

Every write method below sends 500 records per request (pass a list of any
length, or one record as a dict) and returns totals over all requests, with
each `failed` entry's `index` pointing into the list you passed. Failures are
per record: a record the API cannot store is listed in `failed` and the others
still land. A request must stay under the API's 1 MB body limit (500 typical
FCK users or Roboticket lines are about 0.4 MB); for larger records pass a
smaller `chunk_size`.

Every request, reads included, is resent up to 3 times (after 2s, 4s, 8s) when
it fails temporarily (502/503/504, a connection error, or no answer within 300
s), and if the token has expired the client logs in again once and resends. If
a request still fails after that, the call raises a
`requests.RequestException` (`HTTPError` for an error answer, `ConnectionError`
or `Timeout` for the network); the requests before it have already been
applied.

Resending records never creates duplicates: they are matched by their own id.
Whether an older copy can overwrite a newer one depends on the method:
`ingest_roboticket` and `upsert_objects` items with `sourceUpdatedAt` keep the
newest version, while `sync_fck_users` and `upsert_objects` items without
`sourceUpdatedAt` store the last one sent. So after a failure, resend the same
list right away, but never resend an older export of users after newer changes
have been sent.

- `sync_fck_users(users, company_id=None, chunk_size=500)` — create-or-update
  contacts from FCK user objects via `POST /crm/connectors/fck/users`. Matched
  by `roboticket_id`, then by email, so the first load and later changes are
  the same call. The last version sent wins. Returns `{"count", "created", "updated",
  "failed"}`; a `failed` entry is `{"index", "id", "error"}` (e.g. a user
  without a valid email).
- `ingest_roboticket(lines, company_id=None, chunk_size=500)` — store
  Roboticket ticket and membership lines via
  `POST /crm/connectors/roboticket/ingest`. Each line updates its ticket or
  membership and the match or product it belongs to; returns and transfers are
  handled, a cancelled ticket stays cancelled, and the `AccessToken` field is
  dropped. Returns `{"count", "applied", "ignored", "failed"}`: `ignored` lines
  are neither a sale nor a return.
- `upsert_objects(object_type, items, company_id=None, chunk_size=500)` —
  create-or-update objects of one type via `POST
  /crm/objects/{type}/upsert/batch`, matched by `externalId` (required). Other
  item fields: `status`, `contactKey`, `parentType`, `parentKey`, `startsAt`,
  `endsAt`, `sourceUpdatedAt`, `data`. A field left out keeps what is stored,
  and `data` is merged key by key. Returns `{"count", "created", "updated",
  "failed"}`.
- `get_objects(object_type, company_id=None, external_id=None, status=None,
  parent_type=None, parent_key=None, contact_key=None, limit=None, after=None)`
  — list objects of one type, ordered by `externalId`, via `GET
  /crm/objects/{type}`. Filters match exactly. Pages hold `limit` objects
  (default 100, max 1000); for the next page pass the last `externalId` as
  `after`.

`company_id` is required for admin accounts (the API answers 400 without it).
Other users read and write their own company by default; they can also name
another company they belong to, and any other company is refused with 403.

```python
from deepdots_sdk import Deepdots

client = Deepdots("api-user@example.com", "password",
                  auth_source="identity", base_url="https://api.deepdots.com")

result = client.crm.sync_fck_users(users)        # users: list of user dicts
print(result["created"], result["updated"], result["failed"])

result = client.crm.ingest_roboticket(lines)     # lines: list of Roboticket lines
print(result["applied"], result["ignored"], result["failed"])

tickets = client.crm.get_objects("ticket", contact_key="1058531")
```

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
    # Optional source-system fields: top level, see "Feedback source-system fields"
    "external_id": "48213",
    "externalGeneratedAt": "2026-10-06T11:00:00.000Z",
    "externalUrl": "https://forms.example.com/responses/48213",
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
