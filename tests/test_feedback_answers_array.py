import pytest

from magicfeedback_sdk import MagicFeedback


def test_create_feedback_with_answer_wrapping(client):
    """Tests creating a new feedback item and ensures answers.value is wrapped in a list if not already."""

    feedback_data = {
        "name": "Test SDK Feedback",
        "type": "APP",
        "identity": "MAGICFORM",
        "answers": [
            {"key": "name", "value": "John Doe"},  # Single value (should be wrapped)
            {"key": "comment", "value": ["This is a test comment."]}  # Already a list
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

    # Validate answers are properly wrapped
    for answer in feedback_data["answers"]:
        assert isinstance(answer["value"], list), f"Answer value for key '{answer['key']}' is not a list."

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client
