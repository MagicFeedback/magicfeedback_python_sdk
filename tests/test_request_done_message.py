import json

import pytest

from magicfeedback_sdk.api.requests import build_done_message


def test_minimal_message_defaults_to_success():
    msg = build_done_message("req-1", "company-1")
    assert msg == {"id": "req-1", "companyId": "company-1", "success": True}


def test_optional_fields_included_only_when_provided():
    msg = build_done_message(
        "req-2",
        "company-2",
        output={"value": "hi"},
        sources=["a", "b"],
        sources_key="feedbackIds",
        logs="done",
        quality={"should_retry": False},
    )
    assert msg["id"] == "req-2"
    assert msg["companyId"] == "company-2"
    assert msg["success"] is True
    assert msg["output"] == {"value": "hi"}
    assert msg["sources"] == ["a", "b"]
    assert msg["sourcesKey"] == "feedbackIds"
    assert msg["logs"] == "done"
    assert msg["quality"] == {"should_retry": False}
    # nothing extra
    assert "status" not in msg
    assert "error" not in msg


def test_failure_message():
    msg = build_done_message(
        "req-3", "company-3", success=False, error={"message": "boom"}
    )
    assert msg["success"] is False
    assert msg["error"] == {"message": "boom"}


def test_explicit_status_included():
    msg = build_done_message("req-4", "company-4", status="ERROR", success=False)
    assert msg["status"] == "ERROR"


def test_message_is_json_serialisable():
    msg = build_done_message("req-5", "company-5", output={"n": 1}, sources=[1, 2])
    # Mirrors what publish_done sends over the wire.
    encoded = json.dumps(msg).encode("utf-8")
    assert json.loads(encoded.decode("utf-8")) == msg


def test_missing_ids_raise():
    with pytest.raises(ValueError):
        build_done_message("", "company")
    with pytest.raises(ValueError):
        build_done_message("req", "")
