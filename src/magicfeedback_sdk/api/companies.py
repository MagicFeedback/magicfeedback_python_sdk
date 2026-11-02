from magicfeedback_sdk.utils.request import make_request


class CompaniesAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def get(self, filter=None):
        url = f"{self.base_url}/companies"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
    
    def get_id(self, id, filter=None):
        url = f"{self.base_url}/companies/{id}"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
