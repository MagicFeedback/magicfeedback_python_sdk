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

def test_update_contact_fields_merges(client):
    """update_fields upserts customFields without clobbering the rest, removes
    a ref with None, and can write a native field alongside."""

    name = generate_random_string(5)
    last_name = generate_random_string(7)
    email = f"{name}.{last_name}@test.com"

    contact = client.contacts.create({
        "name": name,
        "lastname": last_name,
        "email": email,
        "companyId": "MAGICFEEDBACK_DEV_SDK",
    })
    contact_id = contact["id"]

    # Add one custom field.
    res = client.contacts.update_fields(contact_id, {"loyalty_tier": "gold"})
    assert res["customFields"]["loyalty_tier"] == "gold"

    # Add a second one; the first MUST survive (the whole point of the merge).
    res = client.contacts.update_fields(contact_id, {"nps_segment": "promoter"})
    assert res["customFields"]["loyalty_tier"] == "gold"
    assert res["customFields"]["nps_segment"] == "promoter"

    # An explicit None removes just that ref, keeping the others.
    res = client.contacts.update_fields(contact_id, {"loyalty_tier": None})
    assert "loyalty_tier" not in res["customFields"]
    assert res["customFields"]["nps_segment"] == "promoter"

    # A native field can be written in the same call; re-read to confirm it
    # landed (the endpoint's response only echoes customFields).
    client.contacts.update_fields(contact_id, {"vip": True}, city="Copenhagen")
    fetched = client.contacts.get({"where": {"id": contact_id}})[0]
    assert fetched["city"] == "Copenhagen"
    assert fetched["customFields"]["vip"] is True
    assert fetched["customFields"]["nps_segment"] == "promoter"


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
