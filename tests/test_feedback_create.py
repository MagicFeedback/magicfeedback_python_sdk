import pytest

from magicfeedback_sdk import MagicFeedback


def test_create_feedback(client):
    """Tests creating a new feedback item."""

    feedback_data = {
        "name": "Test SDK Feedback",
        "type": "APP",
        "identity": "MAGICFORM",
        "answers": [
            {"key": "name", "value": "John Doe"},
            {"key": "comment", "value": "This is a test comment."}
        ],
        "questions": [
            {
                "title": "Name",
                "ref": "name",
                "position": 1,
                "type": "TEXT"
            },
            {
                "title": "Comment",
                "ref": "comment",
                "position": 2,
                "type": "LONGTEXT"
            },
        ],
        "integrationId": "0eb9d270-6dd7-11ef-9987-21e04f383573",
        "companyId": "MAGICFEEDBACK_DEV_SDK",
        "productId": "MAGICFEEDBACK_DEV_SDK_GENERAL",
    }

    response = client.feedbacks.create(feedback_data)

    assert "id" in response
    # Check if the created feedback has the correct name
    assert response["name"] == "Test SDK Feedback"


def test_create_feedback_without_company_and_product(client):
    """companyId and productId left out are taken from the integration (SDK 1.0.25)."""

    integration_id = "0eb9d270-6dd7-11ef-9987-21e04f383573"
    response = client.feedbacks.create({
        "name": "Test SDK Feedback (integration defaults)",
        "type": "APP",
        "identity": "MAGICFORM",
        "answers": [{"key": "comment", "value": "Created without companyId and productId."}],
        "integrationId": integration_id,
    })

    integration = client.feedbacks._get_integration(integration_id)
    assert response["companyId"] == integration["companyId"]
    assert response["productId"] == integration["productId"]

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client
