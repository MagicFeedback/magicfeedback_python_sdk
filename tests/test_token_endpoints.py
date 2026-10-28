"""Offline tests for signing in and refreshing through the API.

``requests.post`` is replaced by a fake that records each call and answers
from a script, so nothing reaches the network.
"""
import logging
import warnings

import pytest
import requests

from magicfeedback_sdk import MagicFeedback
from magicfeedback_sdk.auth import AuthManager

BASE = "https://api.test"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


@pytest.fixture
def api(monkeypatch):
    """Answers queued per path; every call recorded as (url, json body)."""
    calls = []
    answers = {}

    def fake_post(url, json=None, timeout=None, **kwargs):
        calls.append((url, json))
        path = url[len(BASE):]
        return answers[path].pop(0)

    monkeypatch.setattr(requests, "post", fake_post)
    return calls, answers


def _ok(id_token, refresh_token):
    return FakeResponse(200, {"idToken": id_token, "refreshToken": refresh_token, "expiresIn": 3600})


def _mgr():
    return AuthManager(BASE, logging.getLogger("test"))


def test_login_posts_to_the_api_and_keeps_the_refresh_token(api):
    calls, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    mgr = _mgr()

    assert mgr.identity_login("api@client.com", "secret") == "id-1"
    assert calls == [(BASE + "/auth/token", {"email": "api@client.com", "password": "secret"})]
    assert mgr.refresh_token == "rt-1"


def test_login_never_calls_identity_platform(api):
    calls, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    _mgr().identity_login("u", "p")
    assert all(url.startswith(BASE) for url, _ in calls)


def test_bad_credentials_raise_http_error(api):
    _, answers = api
    answers["/auth/token"] = [FakeResponse(401, {"error": {"message": "Invalid email or password"}})]
    with pytest.raises(requests.HTTPError):
        _mgr().identity_login("u", "wrong")


def test_refresh_uses_the_refresh_token_not_the_password(api):
    calls, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    answers["/auth/token/refresh"] = [_ok("id-2", "rt-2")]
    mgr = _mgr()
    mgr.identity_login("u", "p")

    assert mgr.refresh("u", "p") == "id-2"
    assert calls[-1] == (BASE + "/auth/token/refresh", {"refreshToken": "rt-1"})
    assert mgr.refresh_token == "rt-2"


def test_rejected_refresh_token_signs_in_again(api):
    calls, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1"), _ok("id-3", "rt-3")]
    answers["/auth/token/refresh"] = [FakeResponse(401, {})]
    mgr = _mgr()
    mgr.identity_login("u", "p")

    assert mgr.refresh("u", "p") == "id-3"
    assert [url for url, _ in calls] == [
        BASE + "/auth/token",
        BASE + "/auth/token/refresh",
        BASE + "/auth/token",
    ]


def test_other_refresh_errors_are_raised(api):
    _, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    answers["/auth/token/refresh"] = [FakeResponse(502, {})]
    mgr = _mgr()
    mgr.identity_login("u", "p")
    with pytest.raises(requests.HTTPError):
        mgr.refresh("u", "p")


def test_client_identity_source_refreshes_through_the_api(api):
    calls, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    answers["/auth/token/refresh"] = [_ok("id-2", "rt-2")]
    client = MagicFeedback("u", "p", base_url=BASE, auth_source="identity")
    assert client.headers["Authorization"] == "Bearer id-1"

    client.refresh_token()
    assert client.feedbacks.headers["Authorization"] == "Bearer id-2"
    assert calls[-1][0] == BASE + "/auth/token/refresh"


def test_client_with_api_key_never_signs_in(api):
    calls, _ = api
    client = MagicFeedback(api_key="dd_live_abc", base_url=BASE)
    assert client.headers["Authorization"] == "Bearer dd_live_abc"
    assert client.refresh_token() == "dd_live_abc"
    assert calls == []


def test_ip_key_is_ignored_with_a_warning(api):
    _, answers = api
    answers["/auth/token"] = [_ok("id-1", "rt-1")]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        MagicFeedback("u", "p", base_url=BASE, auth_source="identity", ip_key="AIza...")
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
