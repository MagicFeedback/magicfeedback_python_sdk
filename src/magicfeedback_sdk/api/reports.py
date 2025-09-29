# reports.py
from typing import Any, Dict, Optional
import json

from magicfeedback_sdk.utils.request import make_request


class ReportsAPI:
    """
    Lightweight client for reporting-related endpoints.

    Currently supports:
      - GET /reporting/report/newsletter?filter=<LoopBackFilterJSON>
    """

    def __init__(self, base_url: str, headers: Dict[str, str], logger: Any = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.logger = logger

   def get_newsletter(self, filter=None):
        url = f"{self.base_url}/reporting/report/newsletter"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
