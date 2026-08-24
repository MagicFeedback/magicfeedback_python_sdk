import pytest

from magicfeedback_sdk import MagicFeedback
from magicfeedback_sdk.api import feedback as feedback_module
from magicfeedback_sdk.api.feedback import FeedbackAPI, PAIR_VALUE_FIELDS, _normalize_pair_values


@pytest.mark.parametrize("field", PAIR_VALUE_FIELDS)
def test_normalize_pair_values_wraps_bare_scalar(field):
    """A bare scalar `value` is wrapped in a list; an existing list is left alone."""

    feedback = {
        field: [
            {"key": "channel", "value": "voice"},
            {"key": "agent", "value": ["sln"]},
        ]
    }

    _normalize_pair_values(feedback)

    assert feedback[field][0]["value"] == ["voice"]
    assert feedback[field][1]["value"] == ["sln"]


def test_normalize_pair_values_ignores_missing_or_non_list_fields():
    """Fields that are absent, None, or not lists (e.g. `questions`) are left untouched."""

    feedback = {
        "metrics": None,
        "questions": [{"title": "Name", "position": 1}],
    }

    _normalize_pair_values(feedback)

    assert feedback["metrics"] is None
    assert feedback["questions"] == [{"title": "Name", "position": 1}]


def test_create_feedback_with_mixed_metric_value_types(client):
    """Reproduces the real-world shape where `metrics.value` mixes strings and lists."""

    feedback_data = {
        "name": "Test SDK Feedback - mixed metric values",
        "type": "APP",
        "identity": "MAGICFORM",
        "answers": [
            {"key": "name", "value": "John Doe"},
        ],
        "metrics": [
            {"key": "channel", "value": "voice"},
            {"key": "direction", "value": "inbound"},
            {"key": "agent", "value": ["sln"]},
        ],
        "metadata": [
            {"key": "genesysConversationId", "value": "f35ff71b-c3c6-42b7-9fb9-b05791791c2f"},
        ],
        "questions": [
            {"title": "Name", "ref": "name", "position": 1, "type": "TEXT"},
        ],
        "integrationId": "0eb9d270-6dd7-11ef-9987-21e04f383573",
        "companyId": "MAGICFEEDBACK_DEV_SDK",
        "productId": "MAGICFEEDBACK_DEV_SDK_GENERAL",
    }

    response = client.feedbacks.create(feedback_data)

    assert "id" in response

    for metric in feedback_data["metrics"]:
        assert isinstance(metric["value"], list), f"metrics value for '{metric['key']}' is not a list."
    for entry in feedback_data["metadata"]:
        assert isinstance(entry["value"], list), f"metadata value for '{entry['key']}' is not a list."


@pytest.fixture
def client():
    """Provides a MagicFeedbackClient instance for testing."""

    client = MagicFeedback('sdk_tester@magicfeedback.io', 'caracter')
    return client


def _api():
    return FeedbackAPI(base_url="https://api.test", headers={}, logger=None)


def _mixed_type_feedback(feedback_id="fb-1"):
    return {
        "id": feedback_id,
        "metrics": [
            {"key": "channel", "value": "voice"},
            {"key": "direction", "value": "inbound"},
            {"key": "agent", "value": ["sln"]},
        ],
        "metadata": [
            {"key": "genesysConversationId", "value": "f35ff71b-c3c6-42b7-9fb9-b05791791c2f"},
        ],
        "questions": [
            {"title": "Name", "position": 1},
        ],
    }


def test_get_id_normalizes_mixed_type_values(monkeypatch):
    """get_id() must return metrics/metadata values as lists even when the raw API mixes shapes."""

    monkeypatch.setattr(feedback_module, "make_request", lambda *a, **k: _mixed_type_feedback())

    feedback = _api().get_id("fb-1")

    for metric in feedback["metrics"]:
        assert isinstance(metric["value"], list)
    for entry in feedback["metadata"]:
        assert isinstance(entry["value"], list)
    # untouched: not a pair field
    assert feedback["questions"] == [{"title": "Name", "position": 1}]


def test_get_normalizes_every_feedback_in_the_list(monkeypatch):
    """get() must normalize every item in the returned array, not just the first."""

    raw = [_mixed_type_feedback("fb-1"), _mixed_type_feedback("fb-2")]
    monkeypatch.setattr(feedback_module, "make_request", lambda *a, **k: raw)

    feedbacks = _api().get()

    assert len(feedbacks) == 2
    for feedback in feedbacks:
        for metric in feedback["metrics"]:
            assert isinstance(metric["value"], list)
