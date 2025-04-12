from .api.campaigns import CampaignsAPI
from .api.contacts import ContactsAPI
from .api.feedback import FeedbackAPI
from .api.metrics import MetricsAPI
from .auth import AuthManager
from .logging_config import configure_logger


class MagicFeedbackClient:
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

    def set_logging(self, level):
        self.logger.setLevel(level)
