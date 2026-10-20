"""
Example: authenticate using the token cached in Google Cloud Datastore.

By default the SDK reads the bearer token from the Datastore cache maintained
by the `update-token` job (kind=token-storage, email=robot@magicfeedback.io,
database=shared) instead of calling Identity Platform on every use. When the
cached token is missing, stale (older than token_max_age_min) or Datastore is
unreachable, the SDK falls back to Identity Platform — which is why email and
password are still worth providing.

Requirements:
  - pip install google-cloud-datastore
  - Google Application Default Credentials with read access to the token
    entity, e.g. `gcloud auth application-default login` or
    GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account key.

For DEV, set gcp_project_id / base_url to the DEV project accordingly.
"""

import logging
import os

from dotenv import load_dotenv
from magicfeedback_sdk import MagicFeedback

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
# Optional: only used for the Identity Platform fallback (missing/stale cache).
EMAIL = os.environ.get("MF_EMAIL")
PASSWORD = os.environ.get("MF_PASSWORD")
# GCP project that owns the token Datastore. When omitted it is resolved from
# Application Default Credentials.
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
# ──────────────────────────────────────────────────────────────────────────────


def main():
    # Datastore is the default source; these kwargs are shown explicitly.
    client = MagicFeedback(
        EMAIL,
        PASSWORD,
        auth_source="datastore",          # default
        gcp_project_id=GCP_PROJECT_ID,    # None => inferred from ADC
        # The rest match the update-token job defaults and can be omitted:
        datastore_database_id="shared",
        token_kind="token-storage",
        token_email="robot@magicfeedback.io",
        token_max_age_min=50,
        datastore_timeout_s=5.0,          # bound the lookup; fall back fast
    )
    client.set_logging(logging.INFO)  # see which source was used

    # The client is now authenticated with the cached token.
    print(f"Authenticated. Token prefix: {client.api_key[:12]}…")

    # Long-lived clients can re-read the token (from the same source) once it
    # expires; this updates every sub-API in place.
    # client.refresh_token()

    # You can also read the cached token directly, without constructing a client
    # (returns None when missing/stale/unreachable):
    cached = client.auth.get_token_from_datastore()
    print("Cached token present:", cached is not None)

    # Example call using the resolved token:
    # feedbacks = client.feedbacks.get(filter={"limit": 1})
    # print(feedbacks)


if __name__ == "__main__":
    main()
