import random
import string

import pytest

from magicfeedback_sdk import MagicFeedback


def test_list_questions(client):
    """Tests listing questions items."""

    filter = {
        "where": {
            "integrationid": "0eb9d270-6dd7-11ef-9987-21e04f383573"
        }
    }

    response = client.integrations_questions.get(filter)
    assert len(response) > 0

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client


