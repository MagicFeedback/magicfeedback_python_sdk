from magicfeedback_sdk.api.campaigns import CampaignsAPI
from magicfeedback_sdk.api.contacts import ContactsAPI
from magicfeedback_sdk.api.feedback import FeedbackAPI
from magicfeedback_sdk.api.metrics import MetricsAPI
from magicfeedback_sdk.api.integrations_questions import IntegrationsQuestionsAPI
from magicfeedback_sdk.auth import AuthManager
from magicfeedback_sdk.logging_config import configure_logger


class MagicFeedback:
    def __init__(self, user: str, password: str, base_url: str = "https://api.magicfeedback.io", ip_key: str = "AIzaSyAKcR895VURSQZSN2T_RD6jX_9y5HRmH80"):
        self.logger = configure_logger()
        self.base_url = base_url
        self.ip_key = ip_key

        self.auth = AuthManager(ip_key, self.logger)
        self.api_key = self.auth.get_api_key(user, password)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # APIs
        self.feedbacks = FeedbackAPI(self.base_url, self.headers, self.logger)
        self.contacts = ContactsAPI(self.base_url, self.headers, self.logger)
        self.campaigns = CampaignsAPI(self.base_url, self.headers, self.logger)
        self.metrics = MetricsAPI(self.base_url, self.headers, self.logger)
        self.integrations_questions = IntegrationsQuestionsAPI(self.base_url, self.headers, self.logger)

    def set_logging(self, level):
        self.logger.setLevel(level)
