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
        return make_request("PATCH", url, self.headers, json=feedback, logger=self.logger)

    def delete(self, feedback_id):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return make_request("DELETE", url, self.headers, logger=self.logger)

    def upload_attachment(self, feedback_id, file_path, filename=None, extra_data=None):
        url = f"{self.base_url}/feedbacks/{feedback_id}/attachments"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        display_name = filename or file_path.split("/")[-1]

        files = {"file": (display_name, file_bytes)}
        data = {"filename": display_name}
        if extra_data is not None:
            import json
            data["extraData"] = json.dumps(extra_data) if not isinstance(extra_data, str) else extra_data

        # Remove Content-Type so requests sets it automatically with the multipart boundary
        headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}

        return make_request("POST", url, headers, files=files, data=data, logger=self.logger)
