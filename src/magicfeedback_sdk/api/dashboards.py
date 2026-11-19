from urllib.parse import quote, urlencode

from magicfeedback_sdk.api.metrics import _day
from magicfeedback_sdk.utils.request import make_request


class DashboardsAPI:
    """Your custom dashboards (``client.dashboards``)."""

    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def get_data(self, dashboard_id, start_date=None, end_date=None):
        """A dashboard with what each of its widgets shows, as one dict.

        The figures the dashboard shows, for the period and filters it opens
        on (``GET /dashboard/{id}/data``), so a report built from it matches
        what your team sees on screen.

        Args:
            dashboard_id: The dashboard's ID: the ``dashboard=`` value in its
                address in Deepdots.
            start_date, end_date: Another period instead of the dashboard's
                own: first and last day, both included, as ``"YYYY-MM-DD"`` or
                a ``date``, in UTC. Both or neither.

        Returns:
            A dict with ``dashboard`` (``id``, ``name``, ``description``,
            ``companyId``), ``period`` (``name``, ``startDate``, ``endDate``),
            ``filters``, ``generatedAt`` and ``widgets``, top to bottom. Each
            widget has ``id``, ``title``, ``type``, ``layout``, ``config`` and
            ``data``: what it shows, or ``None`` for a widget whose data is
            not available this way. The KPI widgets give:

            - ``prefab.counter-kpi``: ``formula``, ``label``, ``unit``,
              ``dimension``, ``kpi`` and ``total`` (its responses).
            - ``prefab.kpi-ranking``: ``dimension``, ``kpis``, ``reference``
              (all the values together) and ``rows``: every value, with
              ``rank``, ``value``, ``total``, ``shown`` (whether the dashboard
              displays it) and its ``kpis``.
            - ``prefab.kpi-graph``: ``formula``, ``label``, ``unit``,
              ``dimension``, ``average`` and ``rows`` (``value``, ``kpi``,
              ``total``).

        Raises:
            ValueError: No ``dashboard_id``, or only one of the two dates.
            requests.HTTPError: The API refused the call: **404** for a
                dashboard that doesn't exist or that you can't see, **403**
                for another company's, **400** for a date it can't read.
        """
        if not dashboard_id:
            raise ValueError("dashboard_id is required")
        if bool(start_date) != bool(end_date):
            raise ValueError("start_date and end_date go together")

        url = f"{self.base_url}/dashboard/{quote(str(dashboard_id), safe='')}/data"
        if start_date:
            url += "?" + urlencode({"startDate": _day(start_date), "endDate": _day(end_date)})
        return make_request("GET", url, self.headers, logger=self.logger)
