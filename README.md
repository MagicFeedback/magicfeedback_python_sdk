# MagicFeedback Python SDK

Python SDK for the MagicFeedback API.

## Installation

```bash
pip install MagicFeedback
```

## Quick start

```python
from magicfeedback_sdk import MagicFeedback

client = MagicFeedback(
    user="your@email.com",
    password="your_password"
)
```

By default the client points to the production API. For dev/staging pass `base_url`:

```python
client = MagicFeedback(
    user="your@email.com",
    password="your_password",
    base_url="https://dev-api.magicfeedback.io"
)
```

## Available modules

| Module | Access via |
|---|---|
| Feedbacks | `client.feedbacks` |
| Campaigns | `client.campaigns` |
| Contacts | `client.contacts` |
| Metrics | `client.metrics` |
| Products | `client.products` |
| Reports | `client.reports` |
| Integration questions | `client.integrations_questions` |

## Feedback examples

```python
# Create
response = client.feedbacks.create({
    "name": "My feedback",
    "type": "APP",
    "identity": "MAGICFORM",
    "integrationId": "<id>",
    "companyId": "<id>",
    "productId": "<id>",
    "answers": [{"key": "comment", "value": "Great product"}]
})

# Get by ID (with optional relations)
feedback = client.feedbacks.get_id(
    "<feedback_id>",
    filter={"include": [{"relation": "feedbackAttachments"}]}
)

# Upload a file attachment
client.feedbacks.upload_attachment(
    "<feedback_id>",
    file_path="/path/to/file.pdf",
    filename="report.pdf",          # optional, defaults to file name
    extra_data={"source": "crm"}    # optional, any JSON-serialisable dict
)

# List, update, delete
feedbacks = client.feedbacks.get()
client.feedbacks.update("<feedback_id>", {"name": "Updated"})
client.feedbacks.delete("<feedback_id>")
```

## License

MIT
