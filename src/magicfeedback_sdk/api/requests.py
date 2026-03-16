# reports.py
from typing import Any, Dict, Optional
import json

from magicfeedback_sdk.utils.request import make_request


class RequestsAPI:
    """
    Lightweight client for reporting-related endpoints.

    Currently supports:
      - GET /requests?filter=<LoopBackFilterJSON>
      - GET /requests/{id}?filter=<LoopBackFilterJSON>
      - PATCH /requests/{id}
    """

    def __init__(self, base_url: str, headers: Dict[str, str], logger: Any = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.logger = logger

    def get(self, filter=None):
        url = f"{self.base_url}/requests"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)

    def get_id(self, request_id, filter=None):
        url = f"{self.base_url}/requests/{request_id}"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
    
    def update(self, request_id, request):
        url = f"{self.base_url}/requests/{request_id}"
        return make_request("PATCH", url, self.headers, json=request, logger=self.logger)