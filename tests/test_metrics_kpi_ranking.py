"""Unit tests for MetricsAPI.kpi_ranking (client.metrics.kpi_ranking).

Pure unit tests — no network, no credentials (make_request is monkeypatched).
"""

import json
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from magicfeedback_sdk.api import metrics as metrics_module
from magicfeedback_sdk.api.metrics import MetricsAPI

ROWS = [{"value": "jane doe", "total": 20, "kpis": [{"formula": "csat", "kpi": 95.0}]}]


def _api():
    return MetricsAPI(base_url="https://api.test", headers={"Authorization": "Bearer key"}, logger=None)


@pytest.fixture
def calls(monkeypatch):
    """Record every make_request call and answer with ROWS."""
    seen = []

    def fake(method, url, headers, **kw):
        seen.append((method, url, headers))
        return ROWS

    monkeypatch.setattr(metrics_module, "make_request", fake)
    return seen


def _query(url):
    """The query string, decoded: {name: value}."""
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query, keep_blank_values=True).items()}


def test_required_parameters_only(calls):
    res = _api().kpi_ranking("ACME", "agent", ["csat"])

    method, url, headers = calls[0]
    assert method == "GET"
    assert url.startswith("https://api.test/metrics/insights/kpi-ranking?")
    assert headers == {"Authorization": "Bearer key"}
    assert _query(url) == {"companyId": "ACME", "dimension": "agent", "formulas": '["csat"]'}
    assert res == ROWS


def test_one_formula_as_a_string(calls):
    _api().kpi_ranking("ACME", "agent", "csat")

    assert json.loads(_query(calls[0][1])["formulas"]) == ["csat"]


def test_every_parameter_is_sent_under_the_api_name(calls):
    _api().kpi_ranking(
        "ACME",
        "agent",
        ["csat", "nps"],
        start_date="2026-11-17",
        end_date="2026-11-17",
        integrations=["int-1", "int-2"],
        products=["ACME_GENERAL"],
        min_responses=5,
        limit=3,
        filters=[{"name": "team", "values": ["north"]}],
        breakdown="integration",
        compare_start_date="2026-11-16",
        compare_end_date="2026-11-16",
    )

    query = _query(calls[0][1])
    assert json.loads(query.pop("formulas")) == ["csat", "nps"]
    assert json.loads(query.pop("integrations")) == ["int-1", "int-2"]
    assert json.loads(query.pop("products")) == ["ACME_GENERAL"]
    assert json.loads(query.pop("filters")) == [{"name": "team", "values": ["north"]}]
    assert query == {
        "companyId": "ACME",
        "dimension": "agent",
        "startDate": "2026-11-17",
        "endDate": "2026-11-17",
        "minResponses": "5",
        "limit": "3",
        "breakdown": "integration",
        "compareStartDate": "2026-11-16",
        "compareEndDate": "2026-11-16",
    }


def test_dates_and_datetimes_are_sent_as_days(calls):
    _api().kpi_ranking(
        "ACME", "agent", ["csat"],
        start_date=date(2026, 11, 1), end_date=datetime(2026, 11, 17, 23, 59),
    )

    query = _query(calls[0][1])
    assert (query["startDate"], query["endDate"]) == ("2026-11-01", "2026-11-17")


def test_values_are_url_encoded(calls):
    """A raw "&", "#", "+" or space in a name must not cut or change the query."""
    _api().kpi_ranking(
        "ACME", "team & region #1", ["sentiment score"],
        filters=[{"name": "agent", "values": ["test agent æøå", "a+b"]}],
    )

    raw = urlsplit(calls[0][1]).query
    assert " " not in raw and "#" not in calls[0][1] and "+" not in raw
    assert raw.count("&") == 3  # only the separators between the 4 parameters
    query = _query(calls[0][1])
    assert query["dimension"] == "team & region #1"
    assert json.loads(query["formulas"]) == ["sentiment score"]
    assert json.loads(query["filters"]) == [{"name": "agent", "values": ["test agent æøå", "a+b"]}]


def test_a_single_filter_block_can_be_passed_without_a_list(calls):
    _api().kpi_ranking("ACME", "agent", ["csat"], filters={"name": "channel", "values": ["chat"]})

    assert json.loads(_query(calls[0][1])["filters"]) == [{"name": "channel", "values": ["chat"]}]


def test_empty_optionals_are_left_out(calls):
    _api().kpi_ranking(
        "ACME", "agent", ["csat"],
        integrations=[], products=None, min_responses=0, limit=0, filters=[], breakdown=None,
    )

    assert set(_query(calls[0][1])) == {"companyId", "dimension", "formulas"}


@pytest.mark.parametrize(
    "args, kwargs, message",
    [
        (("", "agent", ["csat"]), {}, "company_id"),
        (("ACME", "", ["csat"]), {}, "dimension"),
        (("ACME", "agent", []), {}, "formulas"),
        (("ACME", "agent", None), {}, "formulas"),
        (("ACME", "agent", ["csat"]), {"compare_start_date": "2026-11-16"}, "go together"),
        (("ACME", "agent", ["csat"]), {"compare_end_date": "2026-11-16"}, "go together"),
        (("ACME", "agent", ["csat"]), {"integrations": {"a": 1}}, "integrations"),
    ],
)
def test_bad_arguments_raise_before_any_request(calls, args, kwargs, message):
    with pytest.raises(ValueError, match=message):
        _api().kpi_ranking(*args, **kwargs)

    assert calls == []


def test_get_is_unchanged(calls):
    """get() keeps building its URL exactly as before."""
    api = _api()

    api.get()
    api.get({"where": {"companyId": "ACME"}})

    assert calls[0][1] == "https://api.test/metrics"
    assert calls[1][1] == 'https://api.test/metrics?filter={"where": {"companyId": "ACME"}}'
