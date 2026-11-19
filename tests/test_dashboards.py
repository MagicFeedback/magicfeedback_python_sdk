"""Unit tests for DashboardsAPI (client.dashboards).

Pure unit tests — no network, no credentials (make_request is monkeypatched).
"""

from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from magicfeedback_sdk import MagicFeedback
from magicfeedback_sdk.api import dashboards as dashboards_module
from magicfeedback_sdk.api.dashboards import DashboardsAPI

DOC = {"dashboard": {"id": "dash-1"}, "widgets": []}


def _api():
    return DashboardsAPI(base_url="https://api.test", headers={"Authorization": "Bearer key"}, logger=None)


@pytest.fixture
def calls(monkeypatch):
    """Record every make_request call and answer with DOC."""
    seen = []

    def fake(method, url, headers, **kw):
        seen.append((method, url, headers))
        return DOC

    monkeypatch.setattr(dashboards_module, "make_request", fake)
    return seen


def test_get_data_reads_the_dashboard(calls):
    res = _api().get_data("dash-1")

    assert calls == [("GET", "https://api.test/dashboard/dash-1/data", {"Authorization": "Bearer key"})]
    assert res == DOC


def test_another_period(calls):
    _api().get_data("dash-1", start_date="2026-10-01", end_date=date(2026, 10, 31))

    url = calls[0][1]
    assert url.startswith("https://api.test/dashboard/dash-1/data?")
    assert parse_qs(urlsplit(url).query) == {"startDate": ["2026-10-01"], "endDate": ["2026-10-31"]}


def test_datetimes_are_sent_as_days(calls):
    _api().get_data("dash-1", start_date=datetime(2026, 11, 1, 8, 30), end_date=datetime(2026, 11, 17, 23, 59))

    assert parse_qs(urlsplit(calls[0][1]).query) == {"startDate": ["2026-11-01"], "endDate": ["2026-11-17"]}


def test_the_id_is_url_encoded(calls):
    _api().get_data("a/b c")

    assert calls[0][1] == "https://api.test/dashboard/a%2Fb%20c/data"


@pytest.mark.parametrize(
    "args, kwargs, message",
    [
        ((None,), {}, "dashboard_id"),
        (("",), {}, "dashboard_id"),
        (("dash-1",), {"start_date": "2026-10-01"}, "go together"),
        (("dash-1",), {"end_date": "2026-10-31"}, "go together"),
    ],
)
def test_bad_arguments_raise_before_any_request(calls, args, kwargs, message):
    with pytest.raises(ValueError, match=message):
        _api().get_data(*args, **kwargs)

    assert calls == []


def test_the_client_offers_it_with_its_own_token():
    client = MagicFeedback(api_key="dd_test_key", base_url="https://api.test")

    assert isinstance(client.dashboards, DashboardsAPI)
    assert client.dashboards.base_url == "https://api.test"
    # The same headers dict, so a renewed token reaches it too.
    assert client.dashboards.headers is client.headers
