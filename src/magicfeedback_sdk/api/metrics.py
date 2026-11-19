import json
from datetime import date
from urllib.parse import quote, urlencode

from magicfeedback_sdk.utils.request import make_request


def _json_list(value, name):
    """A list parameter as the API takes it: a JSON array in the query string."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list")
    return json.dumps(list(value), separators=(",", ":"))


def _day(value):
    """A date bound as the API takes it: YYYY-MM-DD (dates and datetimes are formatted)."""
    if isinstance(value, date):  # datetime is a date too
        return value.strftime("%Y-%m-%d")
    return value


class MetricsAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def get(self, filter=None):
        url = f"{self.base_url}/metrics"
        if filter:
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)

    def kpi_ranking(
        self,
        company_id,
        dimension,
        formulas,
        start_date=None,
        end_date=None,
        integrations=None,
        products=None,
        min_responses=None,
        limit=None,
        filters=None,
        breakdown=None,
        compare_start_date=None,
        compare_end_date=None,
    ):
        """KPIs per value of a metric, e.g. CSAT per agent, as the dashboards show them.

        Returns one item per value of ``dimension`` (an agent, a team, a
        store...) with each KPI in ``formulas`` and its distance to the KPI of
        all of them together (the "team"). It is the data behind the dashboard
        ranking, KPI and KPI-by-group widgets (``GET
        /metrics/insights/kpi-ranking``).

        Args:
            company_id: Your company ID.
            dimension: Name of the metric whose values are compared, e.g.
                ``"agent"``.
            formulas: Names of the KPI metrics, e.g. ``["csat", "nps"]``. One
                name can be passed as a plain string.
            start_date, end_date: First and last day, both included, as
                ``"YYYY-MM-DD"`` or a ``date``. Days are UTC days of the date
                the feedback happened (``externalGeneratedAt``). Without them,
                all dates.
            integrations: Integration IDs to keep. Without it, all of them.
            products: Product IDs to keep. Without it, all of them.
            min_responses: Leave out the values with fewer responses than this
                in the KPI the items are sorted by. They still count in the team.
            limit: Return only the first N items.
            filters: Keep only the feedback that has these metric values, e.g.
                ``[{"name": "team", "values": ["north", "south"]}]``. A
                feedback must match every block and, in a block, any of its
                values. Upper and lower case are the same.
            breakdown: ``"integration"`` adds each item's KPIs per integration
                (``breakdown``), compared with the team of that integration.
            compare_start_date, compare_end_date: A second period to compare
                with (both or neither). Adds ``prev_kpi``, ``prev_total`` and
                ``change`` to each KPI.

        Returns:
            A list of dicts, best first by the first KPI in ``formulas`` that
            has responses::

                {
                    "value": "jane doe",      # as stored: lower case
                    "total": 20,              # responses with any of the KPIs
                    "kpis": [{                # one per formula, in your order
                        "formula": "csat",
                        "kpi": 95.0,          # None without responses
                        "total": 20,          # responses in this KPI
                        "promoters": 19,      # positive responses
                        "detractors": 0,      # negative responses
                        "team_kpi": 85.0,     # the KPI of all values together
                        "team_total": 140,    # each feedback counted once
                        "delta": 10.0,        # kpi - team_kpi
                        "impact": 1.43,       # delta * total / team_total
                        "higher_is_better": True,
                    }],
                }

        Raises:
            ValueError: ``company_id``, ``dimension`` or ``formulas`` is
                missing, or only one of the two comparison dates is given.
            requests.HTTPError: The API refused the call, e.g. **403** for a
                company that is not yours.
        """
        if not company_id:
            raise ValueError("company_id is required")
        if not dimension:
            raise ValueError("dimension is required")
        if not formulas:
            raise ValueError("formulas requires at least one KPI metric name")
        if bool(compare_start_date) != bool(compare_end_date):
            raise ValueError("compare_start_date and compare_end_date go together")

        params = {
            "companyId": company_id,
            "dimension": dimension,
            "formulas": _json_list(formulas, "formulas"),
        }
        if start_date:
            params["startDate"] = _day(start_date)
        if end_date:
            params["endDate"] = _day(end_date)
        if integrations:
            params["integrations"] = _json_list(integrations, "integrations")
        if products:
            params["products"] = _json_list(products, "products")
        if min_responses:
            params["minResponses"] = min_responses
        if limit:
            params["limit"] = limit
        if filters:
            if isinstance(filters, dict):  # a single block
                filters = [filters]
            params["filters"] = json.dumps(list(filters), separators=(",", ":"))
        if breakdown:
            params["breakdown"] = breakdown
        if compare_start_date:
            params["compareStartDate"] = _day(compare_start_date)
            params["compareEndDate"] = _day(compare_end_date)

        # Encoded, unlike the `filter` of get(): names can have spaces, accents or "&".
        url = f"{self.base_url}/metrics/insights/kpi-ranking?{urlencode(params, quote_via=quote)}"
        return make_request("GET", url, self.headers, logger=self.logger)
