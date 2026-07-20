from magicfeedback_sdk.api.campaigns import CampaignsAPI
from magicfeedback_sdk.api.contacts import ContactsAPI
from magicfeedback_sdk.api.feedback import FeedbackAPI
from magicfeedback_sdk.api.integrations_questions import IntegrationsQuestionsAPI
from magicfeedback_sdk.api.metrics import MetricsAPI
from magicfeedback_sdk.api.products import ProductsAPI
from magicfeedback_sdk.api.reports import ReportsAPI
from magicfeedback_sdk.api.requests import RequestsAPI
from magicfeedback_sdk.api.companies import CompaniesAPI
from magicfeedback_sdk.api.signals import SignalsAPI
from magicfeedback_sdk.auth import AuthManager
from magicfeedback_sdk.logging_config import configure_logger


class MagicFeedback:
    def __init__(
        self,
        user: str = None,
        password: str = None,
        base_url: str = "https://api.magicfeedback.io",
        ip_key: str = "AIzaSyAKcR895VURSQZSN2T_RD6jX_9y5HRmH80",
        auth_source: str = "datastore",
        gcp_project_id: str = None,
        datastore_database_id: str = "shared",
        token_kind: str = "token-storage",
        token_email: str = "robot@magicfeedback.io",
        token_max_age_min: int = 50,
        datastore_timeout_s: float = 5.0,
    ):
        """Create a MagicFeedback API client.

        By default (``auth_source="datastore"``) the bearer token is read from
        the Google Cloud Datastore cache maintained by the ``update-token`` job,
        avoiding an Identity Platform login on every use. If the cached token is
        missing/stale/unreachable, the client falls back to Identity Platform
        (which needs ``user``/``password``). Pass ``auth_source="identity"`` to
        always log in via Identity Platform (the original behaviour, no
        Datastore lookup).

        :param user: Identity Platform email (required for the identity source
            and for the datastore fallback).
        :param password: Identity Platform password (see ``user``).
        :param auth_source: ``"datastore"`` (default) or ``"identity"``.
        :param gcp_project_id: GCP project owning the token Datastore; when
            omitted, resolved from Application Default Credentials.
        :param datastore_database_id: Datastore database holding the token
            (default ``"shared"``).
        :param token_kind: Datastore kind of the token entity
            (default ``"token-storage"``).
        :param token_email: ``email`` key identifying the token entity
            (default ``"robot@magicfeedback.io"``).
        :param token_max_age_min: cached tokens older than this (minutes) are
            treated as stale and trigger the Identity Platform fallback.
        :param datastore_timeout_s: wall-clock budget (seconds) for the
            Datastore lookup; on timeout/error the client falls back to Identity
            Platform. Keeps the fallback fast instead of blocking on the
            Datastore client's default ~60s retry deadline.
        """
        self.logger = configure_logger()
        self.base_url = base_url
        self.ip_key = ip_key

        # Kept so refresh_token() can re-resolve the token the same way.
        self._user = user
        self._password = password
        self.auth_source = auth_source

        self.auth = AuthManager(
            ip_key,
            self.logger,
            gcp_project_id=gcp_project_id,
            datastore_database_id=datastore_database_id,
            token_kind=token_kind,
            token_email=token_email,
            token_max_age_min=token_max_age_min,
            datastore_timeout_s=datastore_timeout_s,
        )
        self.api_key = self.auth.get_api_key(user, password, source=auth_source)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # APIs
        self.feedbacks = FeedbackAPI(self.base_url, self.headers, self.logger)
        self.contacts = ContactsAPI(self.base_url, self.headers, self.logger)
        self.campaigns = CampaignsAPI(self.base_url, self.headers, self.logger)
        self.metrics = MetricsAPI(self.base_url, self.headers, self.logger)
        self.integrations_questions = IntegrationsQuestionsAPI(self.base_url, self.headers, self.logger)
        self.products = ProductsAPI(self.base_url, self.headers, self.logger)   
        self.reports = ReportsAPI(self.base_url, self.headers, self.logger)
        self.companies = CompaniesAPI(self.base_url, self.headers, self.logger)
        self.requests = RequestsAPI(self.base_url, self.headers, self.logger)
        self.signals = SignalsAPI(self.base_url, self.headers, self.logger)

    def set_logging(self, level):
        self.logger.setLevel(level)

    def refresh_token(self):
        """Re-resolve the API token (same ``auth_source`` as construction) and
        update the auth header in place.

        The sub-API clients (``self.feedbacks`` etc.) share this ``headers``
        dict by reference, so mutating it here transparently updates them all —
        useful for long-lived clients whose token has expired.

        :return: the new bearer token.
        """
        self.api_key = self.auth.get_api_key(
            self._user, self._password, source=self.auth_source
        )
        self.headers["Authorization"] = f"Bearer {self.api_key}"
        return self.api_key
