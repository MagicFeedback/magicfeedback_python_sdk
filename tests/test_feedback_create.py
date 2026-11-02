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
    
@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client
