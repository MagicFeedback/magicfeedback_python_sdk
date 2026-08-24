from magicfeedback_sdk.utils.request import make_request


class IntegrationsQuestionsAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def get(self, integration_id, filter=None):
        url = f"{self.base_url}/integrations/{integration_id}/questions"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
