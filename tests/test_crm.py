"""Unit tests for CrmAPI (client.crm).

Pure unit tests — no network, no credentials (make_request and the retry
sleep are monkeypatched).
"""

import pytest
import requests

from magicfeedback_sdk.api import crm as crm_module
from magicfeedback_sdk.api.crm import CrmAPI, MAX_CRM_BATCH


def _api(refresh_token=None):
    return CrmAPI(base_url="https://api.test", headers={"Authorization": "Bearer old"}, logger=None,
                  refresh_token=refresh_token)


def _http_error(status):
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"{status}", response=response)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(crm_module.time, "sleep", sleeps.append)
    return sleeps


def _echo(calls, counters):
    """A fake make_request that records each call and reports every record as counted."""

    def fake(method, url, headers, json=None, **kw):
        calls.append((method, url, json))
        key = next(k for k in ("users", "lines", "items") if json and k in json)
        return {"count": len(json[key]), counters[0]: len(json[key]), counters[1]: 0, "failed": []}

    return fake


# --- connectors --------------------------------------------------------------

def test_sync_fck_users_posts_users_unchanged(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request", _echo(calls, ("created", "updated")))
    user = {"id": 78, "email": "a@fck.dk", "roboticket_id": "1058531", "agillic_id": ".WlXB"}

    res = _api().sync_fck_users([user])

    method, url, body = calls[0]
    assert method == "POST"
    assert url == "https://api.test/crm/connectors/fck/users"
    assert body == {"users": [user]}  # no companyId: a company's own user writes to its company
    assert res == {"count": 1, "created": 1, "updated": 0, "failed": []}


def test_ingest_roboticket_chunks_and_aggregates(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request", _echo(calls, ("applied", "ignored")))

    res = _api().ingest_roboticket([{"Id": i} for i in range(1201)])

    assert [len(body["lines"]) for _, _, body in calls] == [500, 500, 201]
    assert calls[0][1] == "https://api.test/crm/connectors/roboticket/ingest"
    assert res == {"count": 1201, "applied": 1201, "ignored": 0, "failed": []}


def test_a_single_record_may_be_passed_as_a_dict(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request", _echo(calls, ("applied", "ignored")))

    _api().ingest_roboticket({"Id": 1})

    assert calls[0][2] == {"lines": [{"Id": 1}]}


def test_company_id_is_sent_when_given(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request", _echo(calls, ("created", "updated")))

    _api().sync_fck_users([{"id": 1}], company_id="FCK")

    assert calls[0][2]["companyId"] == "FCK"


def test_failed_index_points_into_the_original_list(monkeypatch):
    def fake(method, url, headers, json=None, **kw):
        lines = json["lines"]
        return {"count": len(lines), "applied": len(lines) - 1, "ignored": 0,
                "failed": [{"index": 1, "id": str(lines[1]["Id"]), "error": "boom"}]}

    monkeypatch.setattr(crm_module, "make_request", fake)
    lines = [{"Id": i} for i in range(1201)]

    res = _api().ingest_roboticket(lines)

    assert [f["index"] for f in res["failed"]] == [1, 501, 1001]
    assert res["failed"][1]["id"] == "501"
    assert res["applied"] == 1198


def test_empty_list_is_a_noop(monkeypatch):
    called = []
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: called.append(1) or {})

    assert _api().sync_fck_users([]) == {"count": 0, "created": 0, "updated": 0, "failed": []}
    assert called == []


@pytest.mark.parametrize("bad", [0, -1, MAX_CRM_BATCH + 1])
def test_rejects_invalid_chunk_size(monkeypatch, bad):
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: {})
    with pytest.raises(ValueError):
        _api().ingest_roboticket([{"Id": 1}], chunk_size=bad)


def test_rejects_non_list(monkeypatch):
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: {})
    with pytest.raises(ValueError):
        _api().sync_fck_users("not a list")


# --- resending -----------------------------------------------------------------

def test_a_503_resends_the_same_chunk(monkeypatch, no_sleep):
    """The Roboticket ingest answers 503 when a line could not be stored: resend."""
    bodies = []
    answers = [_http_error(503), {"count": 1, "applied": 1, "ignored": 0, "failed": []}]

    def fake(method, url, headers, json=None, **kw):
        bodies.append(json)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(crm_module, "make_request", fake)

    res = _api().ingest_roboticket([{"Id": 1}])

    assert res["applied"] == 1
    assert bodies[0] == bodies[1]
    assert no_sleep == [2.0]


def test_a_connection_error_is_resent(monkeypatch):
    answers = [requests.ConnectionError("reset"), {"count": 1, "created": 1, "updated": 0, "failed": []}]

    def fake(*a, **k):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(crm_module, "make_request", fake)

    assert _api().sync_fck_users([{"id": 1}])["created"] == 1


def test_gives_up_after_the_retries_with_backoff(monkeypatch, no_sleep):
    calls = []

    def fake(*a, **k):
        calls.append(1)
        raise _http_error(503)

    monkeypatch.setattr(crm_module, "make_request", fake)

    with pytest.raises(requests.HTTPError):
        _api().ingest_roboticket([{"Id": 1}])
    assert len(calls) == 4  # first try + 3 retries
    assert no_sleep == [2.0, 4.0, 8.0]


@pytest.mark.parametrize("status", [400, 403, 422, 500])
def test_other_errors_are_not_resent(monkeypatch, status):
    calls = []

    def fake(*a, **k):
        calls.append(1)
        raise _http_error(status)

    monkeypatch.setattr(crm_module, "make_request", fake)

    with pytest.raises(requests.HTTPError):
        _api().sync_fck_users([{"id": 1}])
    assert len(calls) == 1


def test_an_expired_token_is_refreshed_once_and_the_chunk_resent(monkeypatch):
    headers_seen = []
    answers = [_http_error(401), {"count": 1, "created": 0, "updated": 1, "failed": []}]

    def fake(method, url, headers, json=None, **kw):
        headers_seen.append(headers["Authorization"])
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(crm_module, "make_request", fake)
    api = _api()
    api.refresh_token = lambda: api.headers.update({"Authorization": "Bearer new"})

    assert api.sync_fck_users([{"id": 1}])["updated"] == 1
    assert headers_seen == ["Bearer old", "Bearer new"]


def test_a_second_401_is_raised(monkeypatch):
    refreshes = []
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: (_ for _ in ()).throw(_http_error(401)))

    with pytest.raises(requests.HTTPError):
        _api(refresh_token=lambda: refreshes.append(1)).sync_fck_users([{"id": 1}])
    assert refreshes == [1]


def test_without_a_refresher_a_401_is_raised(monkeypatch):
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: (_ for _ in ()).throw(_http_error(401)))

    with pytest.raises(requests.HTTPError):
        _api().sync_fck_users([{"id": 1}])


# --- generic objects -----------------------------------------------------------

def test_upsert_objects_posts_items_for_the_type(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request", _echo(calls, ("created", "updated")))

    _api().upsert_objects("match", [{"externalId": "1201", "data": {"name": "FCK - BIF"}}])

    assert calls[0][1] == "https://api.test/crm/objects/match/upsert/batch"
    assert calls[0][2] == {"items": [{"externalId": "1201", "data": {"name": "FCK - BIF"}}]}


def test_get_objects_sends_only_the_filters_given(monkeypatch):
    calls = []
    monkeypatch.setattr(crm_module, "make_request",
                        lambda method, url, headers, **kw: calls.append((method, url)) or [])

    _api().get_objects("ticket", contact_key="1058531", limit=1000, after="215")

    assert calls == [("GET", "https://api.test/crm/objects/ticket?contactKey=1058531&limit=1000&after=215")]


def test_the_client_wires_crm_to_its_token_refresh(monkeypatch):
    from magicfeedback_sdk import client as client_module

    monkeypatch.setattr(client_module.AuthManager, "get_api_key", lambda self, *a, **k: "tok")
    client = client_module.MagicFeedback("u", "p", auth_source="identity")

    assert client.crm.headers is client.headers
    assert client.crm.refresh_token == client.refresh_token


# --- reads, timeouts, item checks ----------------------------------------------

def test_reads_are_resent_and_refresh_an_expired_token_too(monkeypatch, no_sleep):
    headers_seen = []
    answers = [_http_error(503), _http_error(401), [{"externalId": "1"}]]

    def fake(method, url, headers, **kw):
        headers_seen.append(headers["Authorization"])
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(crm_module, "make_request", fake)
    api = _api()
    api.refresh_token = lambda: api.headers.update({"Authorization": "Bearer new"})

    assert api.get_objects("match") == [{"externalId": "1"}]
    assert headers_seen == ["Bearer old", "Bearer old", "Bearer new"]
    assert no_sleep == [2.0]


def test_every_request_has_a_timeout(monkeypatch):
    timeouts = []

    def fake(method, url, headers, json=None, timeout=None, **kw):
        timeouts.append(timeout)
        return [] if method == "GET" else {"count": 1, "created": 1, "updated": 0, "failed": []}

    monkeypatch.setattr(crm_module, "make_request", fake)

    _api().sync_fck_users([{"id": 1}])
    _api().get_objects("match")

    assert timeouts == [crm_module.REQUEST_TIMEOUT] * 2


def test_a_timeout_is_resent(monkeypatch):
    answers = [requests.ReadTimeout("slow"), {"count": 1, "applied": 1, "ignored": 0, "failed": []}]

    def fake(*a, **k):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(crm_module, "make_request", fake)

    assert _api().ingest_roboticket([{"Id": 1}])["applied"] == 1


def test_a_persistent_connection_error_is_raised_as_itself(monkeypatch):
    """Callers must catch requests.RequestException, not only HTTPError."""
    monkeypatch.setattr(crm_module, "make_request",
                        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("down")))

    with pytest.raises(requests.RequestException) as raised:
        _api().sync_fck_users([{"id": 1}])
    assert isinstance(raised.value, requests.ConnectionError)


def test_upsert_objects_rejects_a_non_dict_item_before_sending(monkeypatch):
    called = []
    monkeypatch.setattr(crm_module, "make_request", lambda *a, **k: called.append(1) or {})

    with pytest.raises(ValueError):
        _api().upsert_objects("match", [{"externalId": "1"}, None])
    assert called == []
