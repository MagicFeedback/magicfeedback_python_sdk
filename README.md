# MagicFeedback SDK

**A Python SDK for interacting with the MagicFeedback API**

## Installation

```bash
pip install MagicFeedback
```

> Note: the distribution name on PyPI is `MagicFeedback`, but the import name is `magicfeedback_sdk`.

## Usage

```python
from magicfeedback_sdk import MagicFeedback

# Create a client instance
client = MagicFeedback("email", "password")

# Create a new feedback item
feedback_data = {
    "name": "Test Feedback",
    "type": "APP",
    "identity": "MAGICFORM",
    "integrationId": "your-integration-id",
    "companyId": "YOUR_COMPANY",
    "productId": "YOUR_PRODUCT",
    "external_id": "YOUR EXTERNAL ID",
    "answers": [
        {"key": "score", "value": "4"},
        {"key": "comment", "value": "Great service!"},
    ],
}

response = client.feedbacks.create(feedback_data)
print(response)
```

Required fields for `feedbacks.create()`: `name`, `type`, `identity`, `integrationId`, `companyId`, `productId`.

## API Reference

The client exposes several sub-APIs:

### `client.feedbacks`
- `create(feedback)` — creates a new feedback item.
- `get(filter=None)` — lists feedback items.
- `get_id(feedback_id, filter=None)` — retrieves a specific feedback item.
- `update(feedback_id, feedback)` — updates a feedback item.
- `delete(feedback_id)` — deletes a feedback item.

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

## Logging

```python
import logging
client.set_logging(logging.DEBUG)
```

## Additional Information

- **Authentication:** the SDK requires a user / password obtained from the MagicFeedback platform.
- **Error Handling:** the SDK handles common API errors and raises appropriate exceptions.
- **Custom base URL:** pass `base_url="..."` to `MagicFeedback(...)` to target a non-default environment.

## License

This project is licensed under the MIT License.

## Contact

For any questions or support, please contact farias@magicfeedback.io.
