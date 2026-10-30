import pytest

from magicfeedback_sdk import MagicFeedback


def test_api_key_set(client):
    """Tests if the API key is set correctly."""
    assert client.api_key is not None

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')

    return client