# signals.py
from typing import Any, Dict

from magicfeedback_sdk.utils.request import make_request


class SignalsAPI:
    """
    Lightweight client for signals endpoints.

    Currently supports:
      - GET /signals?filter=<LoopBackFilterJSON>
      - GET /signals/count?filter=<LoopBackFilterJSON>
    """

    def __init__(self, base_url: str, headers: Dict[str, str], logger: Any = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.logger = logger

    def get(self, filter=None, filter_by_metrics=None):
        url = f"{self.base_url}/signals"
        params = []
        if filter:
            import json
            params.append(f"filter={json.dumps(filter)}")
        if filter_by_metrics:
            import json
            params.append(f"filterByMetrics={json.dumps(filter_by_metrics)}")
        if params:
            url += "?" + "&".join(params)
        return make_request("GET", url, self.headers, logger=self.logger)

    def count(self, filter=None, filter_by_metrics=None):
        url = f"{self.base_url}/signals/count"
        params = []
        if filter:
            import json
            params.append(f"filter={json.dumps(filter)}")
        if filter_by_metrics:
            import json
            params.append(f"filterByMetrics={json.dumps(filter_by_metrics)}")
        if params:
            url += "?" + "&".join(params)
        return make_request("GET", url, self.headers, logger=self.logger)
