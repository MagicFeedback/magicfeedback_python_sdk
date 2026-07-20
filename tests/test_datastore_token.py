"""Offline unit tests for the Datastore-first auth flow.

These tests never touch the network or Google Cloud: the Datastore lookup
(``_fetch_token_entity``) and the Identity Platform login (``identity_login``)
are monkeypatched, so ``google-cloud-datastore`` need not be installed.
"""
import logging
from datetime import datetime, timedelta, timezone

import pytest

from magicfeedback_sdk import MagicFeedback
from magicfeedback_sdk.auth import AuthManager


def _mgr(**kwargs):
    return AuthManager("ip-key", logging.getLogger("test"), **kwargs)


def _entity(token="cached-token", age_min=0):
    """Fake token entity (dict) with a ``generatedAt`` ``age_min`` minutes ago."""
    return {
        "token": token,
        "generatedAt": datetime.now(timezone.utc) - timedelta(minutes=age_min),
    }


# ---------------------------------------------------------------------------
# get_token_from_datastore
# ---------------------------------------------------------------------------
def test_fresh_token_returned(monkeypatch):
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=10))
    assert mgr.get_token_from_datastore() == "cached-token"


def test_stale_token_returns_none(monkeypatch):
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=60))
    assert mgr.get_token_from_datastore() is None


def test_stale_token_returned_when_allow_stale(monkeypatch):
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=60))
    assert mgr.get_token_from_datastore(allow_stale=True) == "cached-token"


def test_boundary_age_equal_to_max_is_stale(monkeypatch):
    # age == token_max_age_min must count as stale (`age >= max`). Guards the
    # boundary against a `>=` -> `>` regression. Elapsed only ever grows, so the
    # computed age stays == 50 (never truncates below).
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=50))
    assert mgr.get_token_from_datastore() is None


def test_boundary_age_just_under_max_is_fresh(monkeypatch):
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=49))
    assert mgr.get_token_from_datastore() == "cached-token"


def test_missing_entity_returns_none(monkeypatch):
    mgr = _mgr()
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: None)
    assert mgr.get_token_from_datastore() is None


def test_entity_without_token_field_returns_none(monkeypatch):
    mgr = _mgr()
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: {"email": "robot@x"})
    assert mgr.get_token_from_datastore() is None


def test_datastore_unreachable_returns_none(monkeypatch):
    mgr = _mgr()

    def boom():
        raise RuntimeError("no credentials")

    monkeypatch.setattr(mgr, "_fetch_token_entity", boom)
    assert mgr.get_token_from_datastore() is None


def test_token_without_generatedat_is_used(monkeypatch):
    # No age info => treated as fresh (age unknown), not stale.
    mgr = _mgr(token_max_age_min=50)
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: {"token": "t"})
    assert mgr.get_token_from_datastore() == "t"


# ---------------------------------------------------------------------------
# get_api_key dispatch + fallback
# ---------------------------------------------------------------------------
def test_datastore_source_uses_cache_without_identity(monkeypatch):
    mgr = _mgr()
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=1))

    def fail_login(*a, **k):
        raise AssertionError("identity_login must not be called when cache is fresh")

    monkeypatch.setattr(mgr, "identity_login", fail_login)
    assert mgr.get_api_key("u", "p", source="datastore") == "cached-token"


def test_datastore_source_falls_back_to_identity(monkeypatch):
    mgr = _mgr()
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: None)
    monkeypatch.setattr(mgr, "identity_login", lambda u, p: "fresh-id-token")
    assert mgr.get_api_key("u", "p", source="datastore") == "fresh-id-token"


def test_identity_source_skips_datastore(monkeypatch):
    mgr = _mgr()

    def fail_fetch():
        raise AssertionError("datastore must not be queried for the identity source")

    monkeypatch.setattr(mgr, "_fetch_token_entity", fail_fetch)
    monkeypatch.setattr(mgr, "identity_login", lambda u, p: "id-token")
    assert mgr.get_api_key("u", "p", source="identity") == "id-token"


def test_default_source_is_datastore(monkeypatch):
    # No source arg => must route through Datastore (the headline requirement).
    # identity_login raising proves the cached token was used, not a login.
    mgr = _mgr()
    monkeypatch.setattr(mgr, "_fetch_token_entity", lambda: _entity(age_min=1))

    def fail_login(*a, **k):
        raise AssertionError("default source must be 'datastore', not identity login")

    monkeypatch.setattr(mgr, "identity_login", fail_login)
    assert mgr.get_api_key("u", "p") == "cached-token"


def test_client_default_auth_source_is_datastore(monkeypatch):
    # The MagicFeedback constructor must default auth_source to "datastore".
    captured = {}

    def fake_get_api_key(self, user=None, password=None, source="datastore"):
        captured["source"] = source
        return "tok"

    monkeypatch.setattr(AuthManager, "get_api_key", fake_get_api_key)
    client = MagicFeedback("u", "p")
    assert client.auth_source == "datastore"
    assert captured["source"] == "datastore"


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        _mgr().get_api_key("u", "p", source="bogus")


def test_identity_login_requires_credentials():
    with pytest.raises(ValueError):
        _mgr().identity_login(None, None)


# ---------------------------------------------------------------------------
# _entity_age_minutes parsing
# ---------------------------------------------------------------------------
def test_age_from_naive_datetime_treated_as_utc():
    naive = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(tzinfo=None)
    assert AuthManager._entity_age_minutes({"generatedAt": naive}) in (29, 30)


def test_age_from_iso_string_with_z():
    iso = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert AuthManager._entity_age_minutes({"generatedAt": iso}) in (14, 15)


def test_age_none_when_missing_or_unparseable():
    assert AuthManager._entity_age_minutes({}) is None
    assert AuthManager._entity_age_minutes({"generatedAt": "not-a-date"}) is None


# ---------------------------------------------------------------------------
# Client wiring: refresh_token propagates through the shared headers dict
# ---------------------------------------------------------------------------
def test_refresh_token_propagates_to_sub_apis(monkeypatch):
    tokens = iter(["tok1", "tok2"])
    monkeypatch.setattr(
        AuthManager,
        "get_api_key",
        lambda self, user=None, password=None, source="datastore": next(tokens),
    )
    client = MagicFeedback("u", "p")
    assert client.headers["Authorization"] == "Bearer tok1"
    # Sub-APIs share the same headers dict.
    assert client.feedbacks.headers["Authorization"] == "Bearer tok1"

    client.refresh_token()
    assert client.headers["Authorization"] == "Bearer tok2"
    assert client.feedbacks.headers["Authorization"] == "Bearer tok2"
    assert client.requests.headers["Authorization"] == "Bearer tok2"
