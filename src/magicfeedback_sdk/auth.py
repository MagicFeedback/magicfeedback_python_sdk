from datetime import datetime, timezone
from typing import Optional

import requests


class AuthManager:
    """Resolves the API bearer token from one of two sources.

    * ``"datastore"`` (default) — read the token cached in Google Cloud
      Datastore by the ``update-token`` job (kind=``token-storage``,
      email=``robot@magicfeedback.io``, database=``shared``). This avoids signing
      in on every SDK use. When the cached token is missing,
      stale (older than ``token_max_age_min`` minutes) or Datastore is
      unreachable, the client signs in with ``user``/``password`` as a
      fallback.
    * ``"identity"`` — always sign in with ``user``/``password``. This is the
      original SDK behaviour and performs no Datastore lookup.

    Signing in goes through the API (``POST /auth/token``), which asks Identity
    Platform for the token; the SDK no longer calls Identity Platform itself.
    The refresh token it returns renews the session (``refresh``,
    ``POST /auth/token/refresh``) without sending the password again.

    The Datastore path uses the ``google-cloud-datastore`` package (a declared
    dependency) and Google Application Default Credentials with read access to
    the token entity. Missing/invalid credentials or an unreachable Datastore
    degrade to the sign-in fallback; the lookup is bounded by
    ``datastore_timeout_s`` so the fallback happens in seconds rather than
    blocking on the client's default ~60s retry deadline.
    """

    TOKEN_PATH = "/auth/token"
    REFRESH_PATH = "/auth/token/refresh"

    def __init__(
        self,
        base_url: str,
        logger,
        *,
        gcp_project_id: Optional[str] = None,
        datastore_database_id: str = "shared",
        token_kind: str = "token-storage",
        token_email: str = "robot@magicfeedback.io",
        token_max_age_min: int = 50,
        datastore_timeout_s: float = 5.0,
        request_timeout_s: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.logger = logger
        self.request_timeout_s = request_timeout_s
        # From the last sign-in or refresh; None for a token read from Datastore.
        self.refresh_token: Optional[str] = None
        # Datastore token cache configuration (matches the update-token job).
        self.gcp_project_id = gcp_project_id
        self.datastore_database_id = datastore_database_id
        self.token_kind = token_kind
        self.token_email = token_email
        self.token_max_age_min = token_max_age_min
        # Wall-clock budget for the whole Datastore lookup. Without it the
        # client's default ~60s retry deadline would make the Identity
        # fallback block for up to a minute on stale/unreachable credentials.
        self.datastore_timeout_s = datastore_timeout_s

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def get_api_key(self, user=None, password=None, source: str = "datastore") -> str:
        """Return a bearer token from ``source``.

        ``"datastore"`` prefers the cached token and signs in with
        ``user``/``password`` when it is missing/stale/unreachable.
        ``"identity"`` always signs in.
        """
        if source == "identity":
            return self.identity_login(user, password)
        if source == "datastore":
            token = self.get_token_from_datastore()
            if token:
                return token
            self.logger.info(
                "No fresh token in Datastore (kind=%s, email=%s); "
                "falling back to signing in",
                self.token_kind,
                self.token_email,
            )
            return self.identity_login(user, password)
        raise ValueError(
            f"Unknown auth source {source!r}; expected 'datastore' or 'identity'"
        )

    # ------------------------------------------------------------------
    # Sign-in and refresh through the API
    # ------------------------------------------------------------------
    def identity_login(self, user, password) -> str:
        """Sign in with ``POST /auth/token`` and return the ID token.

        Keeps the refresh token for :meth:`refresh`. A wrong email or password
        is a 401 from the API (raised as ``requests.HTTPError``), the same for
        both so the API does not tell which accounts exist.
        """
        if not user or not password:
            raise ValueError(
                "Signing in requires both user and password. "
                "Provide them to MagicFeedback(...) or ensure a fresh token "
                "exists in Datastore."
            )
        self.logger.info("Logging in with user: %s", user)
        return self._token_request(
            self.TOKEN_PATH, {"email": user, "password": password}
        )

    def refresh(self, user=None, password=None) -> str:
        """Return a new ID token for the refresh token of the last sign-in.

        Without a refresh token, or when the API rejects it (401: expired or
        revoked), signs in again with ``user``/``password``.
        """
        if self.refresh_token:
            try:
                return self._token_request(
                    self.REFRESH_PATH, {"refreshToken": self.refresh_token}
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 401:
                    raise
                self.logger.info("Refresh token rejected; signing in again")
                self.refresh_token = None
        return self.identity_login(user, password)

    def _token_request(self, path: str, body: dict) -> str:
        response = requests.post(
            self.base_url + path, json=body, timeout=self.request_timeout_s
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("idToken")
        if not token:
            raise RuntimeError(f"idToken not found in the {path} response")
        self.refresh_token = data.get("refreshToken")
        return token

    # ------------------------------------------------------------------
    # Datastore token cache
    # ------------------------------------------------------------------
    def get_token_from_datastore(self, *, allow_stale: bool = False) -> Optional[str]:
        """Return the token cached in Datastore, or ``None``.

        Returns ``None`` (rather than raising) when the token entity is missing,
        has no ``token`` field, is stale (older than ``token_max_age_min`` and
        ``allow_stale`` is False), or Datastore is unreachable — so callers can
        fall back to another source.

        :param allow_stale: return the cached token even if older than
            ``token_max_age_min`` (still ``None`` when absent/unreachable).
        """
        try:
            entity = self._fetch_token_entity()
        except Exception as exc:  # noqa: BLE001 - Datastore optional; caller falls back
            self.logger.warning(
                "Datastore token lookup failed (%s); token unavailable from cache",
                exc,
            )
            return None

        if not entity:
            self.logger.info(
                "No token entity in Datastore (kind=%s, email=%s)",
                self.token_kind,
                self.token_email,
            )
            return None

        token = entity.get("token")
        if not token:
            self.logger.warning(
                "Datastore token entity found but missing 'token' field "
                "(kind=%s, email=%s)",
                self.token_kind,
                self.token_email,
            )
            return None

        age = self._entity_age_minutes(entity)
        if age is not None:
            self.logger.info("Cached token age: %s minutes", age)
            if age >= self.token_max_age_min and not allow_stale:
                self.logger.info(
                    "Datastore token is stale (age=%s min >= %s min)",
                    age,
                    self.token_max_age_min,
                )
                return None

        self.logger.info("Using token from Datastore cache")
        return str(token)

    def _ds_client(self):
        from google.cloud import datastore  # lazy: optional dependency
        if self.gcp_project_id:
            return datastore.Client(
                project=self.gcp_project_id,
                database=self.datastore_database_id,
            )
        return datastore.Client(database=self.datastore_database_id)

    def _fetch_token_entity(self):
        from google.api_core.retry import Retry  # lazy: ships with datastore

        client = self._ds_client()
        query = client.query(kind=self.token_kind)
        query.add_filter("email", "=", self.token_email)
        # Bound the total wall-clock: a per-call ``timeout`` alone does not cap
        # the retry loop, so also cap the retry deadline. This turns an
        # unreachable/reauth-needed Datastore into a fast fallback instead of a
        # ~60s stall.
        retry = Retry(deadline=self.datastore_timeout_s)
        results = list(
            query.fetch(limit=1, retry=retry, timeout=self.datastore_timeout_s)
        )
        return results[0] if results else None

    @staticmethod
    def _entity_age_minutes(entity) -> Optional[int]:
        """Minutes since the entity's ``generatedAt``, or ``None`` if unknown.

        Handles both a native ``datetime`` (as returned by the Datastore client)
        and an ISO-8601 string; naive values are treated as UTC.
        """
        ga = entity.get("generatedAt")
        if not ga:
            return None
        if isinstance(ga, str):
            try:
                if ga.endswith("Z"):
                    ga = ga[:-1] + "+00:00"
                dt = datetime.fromisoformat(ga)
            except Exception:  # noqa: BLE001 - unparseable timestamp => unknown age
                return None
        elif isinstance(ga, datetime):
            dt = ga
        else:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - dt).total_seconds() // 60)
