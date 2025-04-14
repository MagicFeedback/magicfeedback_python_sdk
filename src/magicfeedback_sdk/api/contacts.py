from magicfeedback_sdk.utils.request import make_request


class ContactsAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def create(self, contact):
        url = f"{self.base_url}/crm/contacts"
        required_fields = ["name", "lastname", "email", "companyId"]
        for field in required_fields:
            if field not in contact:
                raise ValueError(f"Missing required field: {field}")
        return make_request("POST", url, self.headers, json=contact, logger=self.logger)

    def get(self, filter=None):
        url = f"{self.base_url}/crm/contacts"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)

    def update(self, contact_id, contact):
        url = f"{self.base_url}/crm/contacts/{contact_id}"
        return make_request("PATCH", url, self.headers, json=contact, logger=self.logger)

    def delete(self, contact_id):
        url = f"{self.base_url}/crm/contacts/{contact_id}"
        return make_request("DELETE", url, self.headers, logger=self.logger)
