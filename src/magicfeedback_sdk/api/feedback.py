from magicfeedback_sdk.utils.request import make_request


class FeedbackAPI:
    def __init__(self, base_url, headers, logger):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger

    def create(self, feedback):
        url = f"{self.base_url}/feedbacks"
        required_fields = ["name", "type", "identity", "integrationId", "companyId", "productId"]
        for field in required_fields:
            if field not in feedback:
                raise ValueError(f"Missing required field: {field}")

        if "answers" in feedback and isinstance(feedback["answers"], list):
            for answer in feedback["answers"]:
                if "value" in answer and not isinstance(answer["value"], list):
                    answer["value"] = [answer["value"]]

        return make_request("POST", url, self.headers, json=feedback, logger=self.logger)

    def get_id(self, feedback_id, filter=None):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)
    
    def get(self, filter=None):
        url = f"{self.base_url}/feedbacks"
        if filter:
            import json
            url += f"?filter={json.dumps(filter)}"
        return make_request("GET", url, self.headers, logger=self.logger)

    def update(self, feedback_id, feedback):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return make_request("PUT", url, self.headers, json=feedback, logger=self.logger)

    def delete(self, feedback_id):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return make_request("DELETE", url, self.headers, logger=self.logger)
