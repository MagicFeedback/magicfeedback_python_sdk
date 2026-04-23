import random
import string

import pytest

from magicfeedback_sdk import MagicFeedback


def test_create_contact(client):
    """Tests creating a new contact item."""

    name = generate_random_string(5)
    last_name = generate_random_string(7)
    email = f"{name}.{last_name}@test.com"

    #
    contact_data = {
        "name": name,
        "lastname": last_name,
        "email": email,
        "companyId": "MAGICFEEDBACK_DEV_SDK"
    }

    response = client.contacts.create(contact_data)

    assert "id" in response
    # Check if the created contact has the correct name
    assert response["name"] == name
    assert response["lastname"] == last_name
    assert response["email"] == email

    response = client.contacts.update(response["id"], {"name": "Updated Name"})

def test_list_contact(client):
    """Tests listing contact items."""

    filter = {
        "where": {
            "companyId": "MAGICFEEDBACK_DEV_SDK"
        }
    }

    response = client.contacts.get(filter)
    assert len(response) > 0

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client

# Generate random name, last name and email


def generate_random_string(length):
    """Generates a random string of given length."""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))
