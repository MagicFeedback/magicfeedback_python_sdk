"""Unit tests for the batch metadata replace: FeedbackAPI.update_metadata_batch
and its _normalize_metadata_item helper.

Pure unit tests — no network, no credentials (make_request is monkeypatched).
"""

import pytest

from magicfeedback_sdk.api import feedback as feedback_module
from magicfeedback_sdk.api.feedback import FeedbackAPI, _normalize_metadata_item


def _api():
    return FeedbackAPI(base_url="https://api.test", headers={}, logger=None)


# --- _normalize_metadata_item ---------------------------------------------

def test_normalize_accepts_name_values_shape():
    item = {"feedbackId": "fb1", "metadata": [{"name": "agent", "values": ["jpe", "abc"]}]}

    assert _normalize_metadata_item(item) == {
        "feedbackId": "fb1",
        "metadata": [{"name": "agent", "values": ["jpe", "abc"]}],
    }


def test_normalize_accepts_sdk_key_value_shape():
    """The SDK-native {key, value} pair shape maps to {name, values}."""
    item = {"feedbackId": "fb1", "metadata": [{"key": "channel", "value": "voice"}]}

    assert _normalize_metadata_item(item) == {
        "feedbackId": "fb1",
        "metadata": [{"name": "channel", "values": ["voice"]}],
    }


def test_normalize_wraps_bare_scalar_and_handles_empty():
    item = {
        "feedbackId": "fb1",
        "metadata": [
            {"name": "channel", "values": "voice"},   # scalar -> list
            {"name": "agent", "values": ["sln"]},      # already a list -> untouched
            {"name": "empty", "values": None},         # None -> []
        ],
    }

    assert _normalize_metadata_item(item)["metadata"] == [
        {"name": "channel", "values": ["voice"]},
        {"name": "agent", "values": ["sln"]},
        {"name": "empty", "values": []},
    ]


def test_normalize_trims_name_but_does_not_lowercase():
    item = {"feedbackId": "fb1", "metadata": [{"name": "  Agent  ", "values": ["X"]}]}

    entry = _normalize_metadata_item(item)["metadata"][0]
    assert entry["name"] == "Agent"          # trimmed
    assert entry["values"] == ["X"]          # values left as-is


def test_normalize_empty_metadata_passes_through():
    """An empty metadata list is preserved (means 'deprecate all' server-side)."""
    assert _normalize_metadata_item({"feedbackId": "fb2", "metadata": []}) == {
        "feedbackId": "fb2",
        "metadata": [],
    }
    # missing metadata key is treated as empty too
    assert _normalize_metadata_item({"feedbackId": "fb2"}) == {
        "feedbackId": "fb2",
        "metadata": [],
    }


def test_normalize_requires_feedback_id():
    with pytest.raises(ValueError):
        _normalize_metadata_item({"metadata": [{"name": "agent", "values": ["x"]}]})


# --- update_metadata_batch -------------------------------------------------

def test_update_metadata_batch_posts_normalized_payload(monkeypatch):
    captured = {}

    def fake_make_request(method, url, headers, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return {"feedbacks": 2, "triggered": 2, "failed": []}

    monkeypatch.setattr(feedback_module, "make_request", fake_make_request)

    result = _api().update_metadata_batch(
        [
            {"feedbackId": "fb1", "metadata": [{"key": "channel", "value": "voice"}]},
            {"feedbackId": "fb2", "metadata": []},
        ]
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.test/feedbacks/metadata/batch"
    assert captured["json"] == {
        "items": [
            {"feedbackId": "fb1", "metadata": [{"name": "channel", "values": ["voice"]}]},
            {"feedbackId": "fb2", "metadata": []},
        ]
    }
    assert result == {"feedbacks": 2, "triggered": 2, "failed": []}


def test_update_metadata_batch_empty_items(monkeypatch):
    captured = {}

    def fake_make_request(method, url, headers, **kwargs):
        captured["json"] = kwargs.get("json")
        return {"feedbacks": 0, "triggered": 0, "failed": []}

    monkeypatch.setattr(feedback_module, "make_request", fake_make_request)

    _api().update_metadata_batch(None)
    assert captured["json"] == {"items": []}
