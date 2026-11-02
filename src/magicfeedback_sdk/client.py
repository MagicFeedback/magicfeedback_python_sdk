import warnings

from magicfeedback_sdk.api.campaigns import CampaignsAPI
from magicfeedback_sdk.api.contacts import ContactsAPI
from magicfeedback_sdk.api.crm import CrmAPI
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
        ip_key: str = None,
        auth_source: str = "datastore",
        api_key: str = None,
        gcp_project_id: str = None,
        datastore_database_id: str = "shared",
        token_kind: str = "token-storage",
        token_email: str = "robot@magicfeedback.io",
        token_max_age_min: int = 50,
        datastore_timeout_s: float = 5.0,
    ):
        """Create a MagicFeedback API client.

        With ``api_key`` (``"dd_live_..."``), the key is the bearer token: no
        sign-in, no refresh, and ``user``/``password``/``auth_source`` are
        ignored. This is the way for clients' integrations.

        Otherwise, by default (``auth_source="datastore"``) the bearer token is
        read from the Google Cloud Datastore cache maintained by the
        ``update-token`` job, avoiding a sign-in on every use. If the cached
        token is missing/stale/unreachable, the client signs in with
        ``user``/``password``. Pass ``auth_source="identity"`` to always sign
        in (no Datastore lookup). Signing in goes through the API's
        ``POST /auth/token``.

        :param user: the API user's email (required for the identity source
            and for the datastore fallback).
        :param password: the API user's password (see ``user``).
        :param ip_key: no longer used, and ignored: the SDK signs in through the
            API, which holds the Identity Platform key.
        :param auth_source: ``"datastore"`` (default) or ``"identity"``.
        :param api_key: a Deepdots API key; when given, used as is.
        :param gcp_project_id: GCP project owning the token Datastore; when
            omitted, resolved from Application Default Credentials.
        :param datastore_database_id: Datastore database holding the token
            (default ``"shared"``).
        :param token_kind: Datastore kind of the token entity
            (default ``"token-storage"``).
        :param token_email: ``email`` key identifying the token entity
            (default ``"robot@magicfeedback.io"``).
        :param token_max_age_min: cached tokens older than this (minutes) are
            treated as stale and trigger the sign-in fallback.
        :param datastore_timeout_s: wall-clock budget (seconds) for the
            Datastore lookup; on timeout/error the client falls back to signing
            in. Keeps the fallback fast instead of blocking on the
            Datastore client's default ~60s retry deadline.
        """
        self.logger = configure_logger()
        self.base_url = base_url
        if ip_key is not None:
            warnings.warn(
                "ip_key is ignored: the SDK signs in through the API's /auth/token",
                DeprecationWarning,
                stacklevel=2,
            )

        # Kept so refresh_token() can re-resolve the token the same way.
        self._user = user
        self._password = password
        self.auth_source = auth_source

        self.auth = AuthManager(
            base_url,
            self.logger,
            gcp_project_id=gcp_project_id,
            datastore_database_id=datastore_database_id,
            token_kind=token_kind,
            token_email=token_email,
            token_max_age_min=token_max_age_min,
            datastore_timeout_s=datastore_timeout_s,
        )
        self._static_key = bool(api_key)
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self.auth.get_api_key(user, password, source=auth_source)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # APIs
        self.feedbacks = FeedbackAPI(self.base_url, self.headers, self.logger)
        self.contacts = ContactsAPI(self.base_url, self.headers, self.logger)
        self.crm = CrmAPI(self.base_url, self.headers, self.logger, refresh_token=self.refresh_token)
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
        """Renew the API token and update the auth header in place.

        With the identity source, the refresh token of the last sign-in is used
        (``POST /auth/token/refresh``), signing in again if it was rejected.
        With the datastore source, the token is re-resolved as at construction
        (cache first). An API key does not expire and is returned unchanged.

        The sub-API clients (``self.feedbacks`` etc.) share this ``headers``
        dict by reference, so mutating it here transparently updates them all —
        useful for long-lived clients whose token has expired.

        :return: the new bearer token.
        """
        if self._static_key:
            return self.api_key
        if self.auth_source == "identity":
            self.api_key = self.auth.refresh(self._user, self._password)
        else:
            self.api_key = self.auth.get_api_key(
                self._user, self._password, source=self.auth_source
            )
        self.headers["Authorization"] = f"Bearer {self.api_key}"
        return self.api_key


# The company was renamed MagicFeedback -> Deepdots. ``Deepdots`` is the
# forward-looking name for this client; ``MagicFeedback`` remains the defining
# name so existing tracebacks and reprs are unchanged. Both refer to the same
# class object, so isinstance() and subclassing behave identically either way.
Deepdots = MagicFeedback
