# Actions API Guide

The MagicFeedback SDK now includes an `ActionsAPI` module that lets you create and manage actions without calling the API directly.

## Basic Usage

### Simple: Create an INTEGRATION_DONE action that resends a report

```python
from magicfeedback_sdk import MagicFeedback

mf = MagicFeedback(email="user@example.com", password="your_password")

# Create action in one call
definition, step = mf.actions.create_resend_report_action(
    company_id="company-uuid",
    product_id="product-uuid",
    report_id="report-uuid",
)

print(f"Created action: {definition['id']}")
```

### Advanced: Create custom action definition + steps

```python
# Create the action definition
definition = mf.actions.create_definition(
    event_type="INTEGRATION_DONE",
    company_id="company-uuid",
    product_id="product-uuid",
    name="My Custom Action",
    trigger_conditions=[
        {"field": "integrationId", "operator": "EQ", "values": ["specific-integration-id"]}
    ],
)

# Link a step to it
step = mf.actions.create_definition_step(
    action_definition_id=definition["id"],
    step_id="7c4e0f10-2761-11f1-b106-9f23b7c2b80a",  # publish-report step
    company_id="company-uuid",
    product_id="product-uuid",
    config={"reportId": "report-uuid"},
)
```

## Available Methods

### `create_resend_report_action()`

Creates a ready-made action that resends a report when an integration finishes.

**Parameters:**
- `company_id` (str, required): Company UUID
- `product_id` (str, required): Product UUID
- `report_id` (str, required): Report UUID to republish
- `name` (str, optional): Human-readable name
- `integration_id` (str, optional): Only trigger for this specific integration

**Returns:** Tuple of (ActionDefinition, ActionsDefinitionStep)

### `create_report_email_action()`

Creates a ready-made action that sends an email with the report PDF when a report is ready.

**Parameters:**
- `company_id` (str, required): Company UUID
- `product_id` (str, required): Product UUID
- `report_id` (str, required): Report UUID to filter by
- `recipient_email` (str, required): Email address to send to
- `name` (str, optional): Human-readable name
- `subject` (str, optional): Email subject (supports templating with `{{ title }}`, `{{ id }}`)
- `html` (str, optional): HTML email body

**Returns:** Tuple of (ActionDefinition, ActionsDefinitionStep)

### `create_definition()`

Creates a new action definition. Use this for custom event types and configurations.

**Parameters:**
- `event_type` (str, required): Event type (e.g., "INTEGRATION_DONE", "REPORT_CREATED")
- `company_id` (str, required): Company UUID
- `product_id` (str, required): Product UUID
- `schedule_type` (str): "trigger" (default) or "cron"
- `name` (str, optional): Human-readable name
- `status` (str): "ACTIVE" (default) or "INACTIVE"
- `trigger_conditions` (list, optional): Conditions to match on event data
- `condition_logic` (str): "ALL" (default) or "ANY"
- `cron_expr` (str, optional): Cron expression (required if schedule_type is "cron")

**Returns:** ActionDefinition object

### `create_definition_step()`

Links an action step to an action definition.

**Parameters:**
- `action_definition_id` (str, required): ActionDefinition UUID
- `step_id` (str, required): ActionStep UUID
- `company_id` (str, required): Company UUID
- `product_id` (str, required): Product UUID
- `order` (int): Execution order (default: 1)
- `config` (dict, optional): Step-specific configuration
- `status` (str): "ACTIVE" (default) or "INACTIVE"

**Returns:** ActionsDefinitionStep object

### `get_definitions()`

Get all action definitions (optionally filtered).

**Parameters:**
- `filter` (dict, optional): LoopBack filter JSON

**Returns:** List of ActionDefinition objects

### `get_definition()`

Get a specific action definition by ID.

**Parameters:**
- `definition_id` (str, required): ActionDefinition UUID

**Returns:** ActionDefinition object with included steps

## Common Step IDs

| Step Name | Step ID | Purpose |
|-----------|---------|---------|
| publish-report | `7c4e0f10-2761-11f1-b106-9f23b7c2b80a` | POST to `/reporting/report/{reportId}/publish` |
| send-email | `5de425e0-2761-11f1-9a66-95604e7ffd2e` | Send email (supports PDF attachment) |
| get-report | `3b866350-2761-11f1-b106-9f23b7c2b80a` | Fetch report data |
| attach-pdf | `532g32-2761-11f1-9a66-95604e7ffd2e` | Attach PDF to email |
| transform-pdf | `49c14570-2761-11f1-b106-9f23b7c2b80a` | Transform/render PDF |

## Examples

### Example 1: Send email when integration finishes

```python
from magicfeedback_sdk import MagicFeedback

mf = MagicFeedback("user@example.com", "password")

# Create action that sends email when integration finishes
definition = mf.actions.create_definition(
    event_type="INTEGRATION_DONE",
    company_id="abc-123",
    product_id="def-456",
    name="Integration finished - send notification",
)

# Link send-email step
step = mf.actions.create_definition_step(
    action_definition_id=definition["id"],
    step_id="5de425e0-2761-11f1-9a66-95604e7ffd2e",  # send-email
    company_id="abc-123",
    product_id="def-456",
    config={
        "to": "alerts@example.com",
        "subject": "Integration {{ name }} finished",
        "html": "<p>Integration <b>{{ name }}</b> finished processing {{ feedbackCount }} feedbacks.</p>",
    },
)
```

### Example 2: Publish report for specific integration only

```python
definition, step = mf.actions.create_resend_report_action(
    company_id="abc-123",
    product_id="def-456",
    report_id="report-xyz",
    name="Google Play integration - auto publish report",
    integration_id="google-play-source-123",  # Only for this integration
)
```

### Example 3: Complete workflow (integration → report → email)

See `examples/create_full_workflow.py` for a complete example that:
1. Creates INTEGRATION_DONE → publish report action
2. Creates REPORT_CREATED → send email action
3. Results in automatic report republishing and emailing when integration finishes

## Error Handling

All methods use standard HTTP requests and will raise an exception on API errors:

```python
try:
    definition = mf.actions.create_definition(...)
except Exception as e:
    print(f"Error creating action: {e}")
```

## Environment Variables

For the example scripts, set these environment variables:

```bash
export MF_EMAIL=your-email@example.com
export MF_PASSWORD=your-password
export COMPANY_ID=company-uuid
export PRODUCT_ID=product-uuid
export REPORT_ID=report-uuid
export RECIPIENT_EMAIL=recipient@example.com
export INTEGRATION_ID=optional-integration-uuid  # Only needed for filtering

python examples/create_integration_done_action.py
python examples/create_full_workflow.py
```
