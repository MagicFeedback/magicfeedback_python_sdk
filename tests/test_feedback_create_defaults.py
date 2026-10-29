"""Unit tests for FeedbackAPI.create's integration defaults: companyId and
productId are optional and, when missing, copied from the integration.

Pure unit tests — no network, no credentials (make_request is monkeypatched).
"""

import pytest
import requests

from magicfeedback_sdk.api import feedback as feedback_module
from magicfeedback_sdk.api.feedback import FeedbackAPI

INTEGRATIONS = {
    "https://api.test/integrations/int-1": {"id": "int-1", "companyId": "ACME", "productId": "ACME_GENERAL", "questions": []},
    "https://api.test/integrations/int-2": {"id": "int-2", "companyId": "GLOBEX", "productId": "GLOBEX_GENERAL"},
    "https://api.test/integrations/no-product": {"id": "no-product", "companyId": "ACME", "productId": None},
}


def _api():
    return FeedbackAPI(base_url="https://api.test", headers={}, logger=None)


def _payload(**overrides):
    payload = {
        "name": "Review",
        "type": "APP",
        "identity": "MAGICFORM",
        "integrationId": "int-1",
        "answers": [{"key": "nps", "value": "9"}],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def calls(monkeypatch):
    """Record every request; GET /integrations/{id} answers from INTEGRATIONS."""
    recorded = []

    def fake_make_request(method, url, headers, json=None, logger=None, **kwargs):
        recorded.append((method, url, json))
        if method == "GET":
            if url not in INTEGRATIONS:
                raise requests.HTTPError("406 Client Error: Not Acceptable")
            return dict(INTEGRATIONS[url])
        return {"id": "fb-1", **(json or {})}

    monkeypatch.setattr(feedback_module, "make_request", fake_make_request)
    return recorded


def _posts(calls):
    return [body for method, _, body in calls if method == "POST"]


def test_missing_company_and_product_are_copied_from_the_integration(calls):
    _api().create(_payload())

    assert [(method, url) for method, url, _ in calls] == [
        ("GET", "https://api.test/integrations/int-1"),
        ("POST", "https://api.test/feedbacks"),
    ]
    sent = _posts(calls)[0]
    assert sent["companyId"] == "ACME"
    assert sent["productId"] == "ACME_GENERAL"


def test_given_values_skip_the_lookup(calls):
    _api().create(_payload(companyId="OTHER", productId="OTHER_P"))

    assert [method for method, _, _ in calls] == ["POST"]
    assert _posts(calls)[0]["companyId"] == "OTHER"
    assert _posts(calls)[0]["productId"] == "OTHER_P"


def test_only_the_missing_field_is_filled(calls):
    _api().create(_payload(productId="ACME_OTHER"))

    sent = _posts(calls)[0]
    assert sent["companyId"] == "ACME"
    assert sent["productId"] == "ACME_OTHER"  # never overwritten


def test_company_of_another_integration_raises_and_creates_nothing(calls):
    with pytest.raises(ValueError, match="belongs to company ACME, not OTHER"):
        _api().create(_payload(companyId="OTHER"))

    assert [method for method, _, _ in calls] == ["GET"]


def test_product_of_an_integration_without_company_is_never_copied(calls, monkeypatch):
    monkeypatch.setitem(
        INTEGRATIONS,
        "https://api.test/integrations/no-company",
        {"id": "no-company", "companyId": None, "productId": "P_X"},
    )

    with pytest.raises(ValueError, match="has no company"):
        _api().create(_payload(integrationId="no-company", companyId="ACME"))
    assert [method for method, _, _ in calls] == ["GET"]


@pytest.mark.parametrize("empty", [None, ""])
def test_empty_values_are_filled_too(calls, empty):
    _api().create(_payload(companyId=empty, productId=empty))

    sent = _posts(calls)[0]
    assert sent["companyId"] == "ACME"
    assert sent["productId"] == "ACME_GENERAL"


def test_reused_dict_does_not_carry_ids_to_another_integration(calls):
    """The copied ids go into the request only, never into the caller's dict."""
    api = _api()
    payload = _payload()
    api.create(payload)
    assert "companyId" not in payload and "productId" not in payload

    payload["integrationId"] = "int-2"
    api.create(payload)

    first, second = _posts(calls)
    assert (first["companyId"], first["productId"]) == ("ACME", "ACME_GENERAL")
    assert (second["companyId"], second["productId"]) == ("GLOBEX", "GLOBEX_GENERAL")


def test_answer_values_are_still_wrapped_in_the_callers_dict(calls):
    payload = _payload()
    _api().create(payload)

    assert payload["answers"] == [{"key": "nps", "value": ["9"]}]
    assert _posts(calls)[0]["answers"] == [{"key": "nps", "value": ["9"]}]


def test_each_integration_is_read_once_per_client(calls):
    api = _api()
    for integration_id in ("int-1", "int-2", "int-1"):
        api.create(_payload(integrationId=integration_id))

    assert [method for method, _, _ in calls] == ["GET", "POST", "GET", "POST", "POST"]


def test_integration_without_product_raises_and_is_not_cached(calls):
    api = _api()
    for _ in range(2):
        with pytest.raises(ValueError, match="Missing required field: productId"):
            api.create(_payload(integrationId="no-product"))

    assert [method for method, _, _ in calls] == ["GET", "GET"]  # no POST, read again


def test_integration_without_product_is_fine_when_product_is_passed(calls):
    api = _api()
    for _ in range(2):
        api.create(_payload(integrationId="no-product", productId="ACME_MINE"))

    assert [(sent["companyId"], sent["productId"]) for sent in _posts(calls)] == [("ACME", "ACME_MINE")] * 2
    assert [method for method, _, _ in calls] == ["GET", "POST", "GET", "POST"]  # read again, not cached


@pytest.mark.parametrize("field", ["name", "type", "identity", "integrationId"])
def test_required_fields_still_raise_before_any_request(calls, field):
    payload = _payload()
    del payload[field]

    with pytest.raises(ValueError, match=f"Missing required field: {field}"):
        _api().create(payload)
    assert calls == []


@pytest.mark.parametrize("empty", ["", None])
def test_empty_integration_id_raises_before_any_request(calls, empty):
    with pytest.raises(ValueError, match="Missing required field: integrationId"):
        _api().create(_payload(integrationId=empty))
    assert calls == []


def test_non_string_integration_id_raises_before_any_request(calls):
    with pytest.raises(ValueError, match="integrationId must be a string"):
        _api().create(_payload(integrationId=123))
    assert calls == []


def test_integration_id_is_quoted_in_the_lookup_url(calls):
    with pytest.raises(requests.HTTPError):
        _api().create(_payload(integrationId="a/b?c"))

    assert calls == [("GET", "https://api.test/integrations/a%2Fb%3Fc", None)]


def test_unreadable_integration_raises_and_creates_nothing(calls):
    with pytest.raises(requests.HTTPError):
        _api().create(_payload(integrationId="unknown"))

    assert [method for method, _, _ in calls] == ["GET"]


def test_unexpected_lookup_response_raises(monkeypatch):
    monkeypatch.setattr(feedback_module, "make_request", lambda *args, **kwargs: [{"id": "int-1"}])

    with pytest.raises(ValueError, match="Unexpected response"):
        _api().create(_payload())
