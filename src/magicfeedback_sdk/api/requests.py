# requests.py
from typing import Any, Dict, List, Optional

from magicfeedback_sdk.utils.request import make_request


def build_done_message(
    request_id: str,
    company_id: str,
    output: Any = None,
    success: bool = True,
    status: Optional[str] = None,
    sources: Optional[List[Any]] = None,
    sources_key: Optional[str] = None,
    logs: Optional[str] = None,
    quality: Optional[Dict[str, Any]] = None,
    error: Any = None,
) -> Dict[str, Any]:
    """
    Build the completion envelope consumed by the `request-done` Cloud Function
    (MagicFeedback_Functions/functions/request-done). The CF PATCHes
    /requests/{id} to DONE (or ERROR) from this payload.

    The SDK does not publish this message itself — producers (e.g. notebooks /
    workers) build the envelope with this helper and publish it to the
    `request-done` Pub/Sub topic directly. See examples/mark_request_done.py.

    Only `id`, `companyId` and `success` are always present; the rest are
    included only when provided, to keep messages small.
    """
    if not request_id:
        raise ValueError("request_id is required")
    if not company_id:
        raise ValueError("company_id is required")

    message: Dict[str, Any] = {
        "id": request_id,
        "companyId": company_id,
        "success": bool(success),
    }
    if status is not None:
        message["status"] = status
    if output is not None:
        message["output"] = output
    if sources is not None:
        message["sources"] = list(sources)
    if sources_key is not None:
        message["sourcesKey"] = sources_key
    if logs is not None:
        message["logs"] = logs
    if quality is not None:
        message["quality"] = quality
    if error is not None:
        message["error"] = error
    return message


class RequestsAPI:
    """
    Lightweight client for reporting-related endpoints.

    Currently supports:
      - GET /requests?filter=<LoopBackFilterJSON>
      - GET /requests/{id}?filter=<LoopBackFilterJSON>
      - PATCH /requests/{id}
    """

    def __init__(
        self,
        base_url: str,
        headers: Dict[str, str],
        logger: Any = None,
    ):
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
