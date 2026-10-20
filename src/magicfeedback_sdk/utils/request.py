from typing import Any, Dict

import requests


def make_request(method: str, url: str, headers: Dict[str, str], json=None, files=None, data=None, logger=None, timeout=None) -> Dict[str, Any]:
    # timeout=None (no limit) keeps the behaviour every existing caller relies on.
    response = requests.request(method, url, headers=headers, json=json, files=files, data=data, timeout=timeout)
    response.raise_for_status()

    if logger:
        logger.debug("Status code: %s", response.status_code)
        logger.debug("Response: %s", response.text)

    if response.text:
        return response.json()
    return {}
