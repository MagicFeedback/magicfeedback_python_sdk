import random
import string

import pytest

from src.magicfeedback import MagicFeedbackClient

'''
def test_create_campaign(client):
    """Tests creating a new campaign item."""

    campaign_name = generate_random_string(10)

    #
    campaign_data = {
        "name": campaign_name,
        "companyId": "MAGICFEEDBACK_DEV_SDK"
    }

    response = client.create_campaign(campaign_data)

    assert "id" in response
    # Check if the created contact has the correct name
    assert response["name"] == campaign_name

def test_list_campaign(client):
    """Tests listing campaign items."""

    filter = {
        "where": {
            "companyId": "MAGICFEEDBACK_DEV_SDK"
        }
    }

    response = client.get_campaigns(filter)
    assert len(response) > 0
'''

def test_create_campaign_session(client):
    """Tests creating a new campaign session item."""

    # Create a new campaign
    campaign_name = generate_random_string(10)

    campaign_data = {
        "name": campaign_name,
        "companyId": "MAGICFEEDBACK_DEV_SDK"
    }

    campaign = client.create_campaign(campaign_data)
    assert "id" in campaign

    # List only 2 contacts from the company
    filter = {
        "where": {
            "companyId": "MAGICFEEDBACK_DEV_SDK",
            "status": "ACTIVE"
        },
        "limit": 2
    }

    contacts = client.get_contacts(filter)
    assert len(contacts) > 0

    # Asign the contacts to the campaign
    session_data = {
        "crmContactId": []
    }
    for contact in contacts:
        session_data.get("crmContactId").append(contact["id"])

    response = client.create_campaign_session(campaign["id"], session_data)

@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedbackClient('sdk_tester@magicfeedback.io', 'caracter')
    return client

# Generate random name, last name and email


def generate_random_string(length):
    """Generates a random string of given length."""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))
