from magicfeedback_sdk.utils.request import make_request


class CampaignsAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def create(self, campaign):
        url = f"{self.base_url}/campaigns"
        required_fields = ["name", "companyId"]
        for field in required_fields:
            if field not in campaign:
                raise ValueError(f"Missing required field: {field}")
        return make_request("POST", url, self.headers, json=campaign, logger=self.logger)

    def get(self, filter=None):
        url = f"{self.base_url}/campaigns"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)

    def create_session(self, campaign_id, session):
        url = f"{self.base_url}/campaigns/{campaign_id}/session"
        required_fields = ["crmContactId"]
        for field in required_fields:
            if field not in session:
                raise ValueError(f"Missing required field: {field}")
        if not session.get("crmContactId"):
            raise ValueError("Contact ID cannot be empty.")
        return make_request("POST", url, self.headers, json=session, logger=self.logger)

    def get_sessions(self, campaign_id, filter=None):
        url = f"{self.base_url}/campaigns/{campaign_id}/session"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
