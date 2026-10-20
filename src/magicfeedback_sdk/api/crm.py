import time
from urllib.parse import quote, urlencode

import requests

from magicfeedback_sdk.utils.request import make_request

# Server-side cap on items per request for every batch call here. The methods
# chunk to this size, so callers can pass a list of any length.
MAX_CRM_BATCH = 500

# Answers worth resending a request for. Every write here is an upsert keyed on
# the record's own id, so a resend never duplicates anything. A 503 from the
# Roboticket ingest specifically means "a line could not be stored, resend the
# batch".
RETRY_STATUSES = {502, 503, 504}

# (connect, read) seconds. Without a limit a connection that silently dies
# blocks a load forever instead of being resent. A full chunk takes far less.
REQUEST_TIMEOUT = (10, 300)


class CrmAPI:
    """CRM objects (tickets, matches, memberships, ...) and the connectors that
    take a client's own records as they are.

    A CRM object is any record a company keeps next to its contacts, stored as
    ``(companyId, type, externalId)`` plus a free-form ``data`` object. The
    connectors (:meth:`sync_fck_users`, :meth:`ingest_roboticket`) do the
    mapping server-side, so the sender passes its records unchanged.

    Every write method chunks to 500 records per request. Every request is
    resent on a transient failure (502/503/504, connection error, timeout) and
    logs in again once if the token expired, e.g. during a long load.
    """

    def __init__(self, base_url, headers, logger, refresh_token=None, retries=3, backoff_s=2.0):
        self.base_url = base_url
        self.headers = headers
        self.logger = logger
        # The client's refresh_token(): it mutates the shared headers dict, so
        # a retried request picks the new token up.
        self.refresh_token = refresh_token
        self.retries = retries
        self.backoff_s = backoff_s

    def sync_fck_users(self, users, company_id=None, chunk_size=MAX_CRM_BATCH):
        """Create-or-update CRM contacts from FCK user objects, sent as they are.

        Hits ``POST /crm/connectors/fck/users``. Each user becomes one contact,
        matched by its ``roboticket_id`` first and its email second, so the
        initial load and later changes are the same call. The last version
        sent wins: never send an older export after newer changes.

        :param users: a list of FCK user objects (or one user as a dict).
        :param company_id: only for admin accounts; a company's own API user
            writes to its own company.
        :param chunk_size: users per request (1-500).
        :returns: ``{"count", "created", "updated", "failed"}`` over all
            chunks. Each ``failed`` entry is ``{"index", "id", "error"}``, its
            ``index`` pointing into the list you passed.
        """
        return self._send_batches(
            "/crm/connectors/fck/users", "users", users, company_id, chunk_size, ("created", "updated")
        )

    def ingest_roboticket(self, lines, company_id=None, chunk_size=MAX_CRM_BATCH):
        """Store Roboticket ticket/membership lines, sent as they are.

        Hits ``POST /crm/connectors/roboticket/ingest``. The API maps each line
        to its ticket or membership and to the match or product it belongs to,
        handles returns and transfers, and drops the ``AccessToken`` field.
        Resending a line is safe: an older version of a ticket never
        overwrites a newer one, and a cancelled ticket stays cancelled.

        :param lines: a list of Roboticket lines (or one line as a dict).
        :param company_id: only for admin accounts.
        :param chunk_size: lines per request (1-500).
        :returns: ``{"count", "applied", "ignored", "failed"}`` over all
            chunks. ``ignored`` lines are neither a sale nor a return (they
            are kept in the raw log only). Each ``failed`` entry is ``{"index", "id",
            "error"}``, its ``index`` pointing into the list you passed.
        """
        return self._send_batches(
            "/crm/connectors/roboticket/ingest", "lines", lines, company_id, chunk_size, ("applied", "ignored")
        )

    def upsert_objects(self, object_type, items, company_id=None, chunk_size=MAX_CRM_BATCH):
        """Create-or-update CRM objects of one type, matched by ``externalId``.

        Hits ``POST /crm/objects/{type}/upsert/batch``. Item fields:
        ``externalId`` (required), ``status``, ``contactKey``, ``parentType``,
        ``parentKey``, ``startsAt``, ``endsAt``, ``sourceUpdatedAt`` and
        ``data``. A field left out keeps what is stored, and ``data`` is merged
        key by key. With ``sourceUpdatedAt``, an item older than the stored one
        only fills gaps.

        :param object_type: e.g. ``"match"`` (lowercase letters, digits, ``_``).
        :param items: list of objects (dicts). Anything else raises
            ``ValueError`` before a request is sent: the API would reject the
            whole chunk.
        :returns: ``{"count", "created", "updated", "failed"}``; each
            ``failed`` entry is ``{"index", "externalId", "error"}``.
        """
        if isinstance(items, list) and not all(isinstance(item, dict) for item in items):
            raise ValueError("every item must be a dict")
        path = f"/crm/objects/{quote(object_type, safe='')}/upsert/batch"
        return self._send_batches(path, "items", items, company_id, chunk_size, ("created", "updated"))

    def get_objects(
        self,
        object_type,
        company_id=None,
        external_id=None,
        status=None,
        parent_type=None,
        parent_key=None,
        contact_key=None,
        limit=None,
        after=None,
    ):
        """List CRM objects of one type, ordered by ``externalId``.

        Hits ``GET /crm/objects/{type}``. Every filter is an exact match. Pages
        hold ``limit`` objects (default 100, max 1000); for the next page pass
        the last ``externalId`` you got as ``after``.
        """
        params = {
            "companyId": company_id,
            "externalId": external_id,
            "status": status,
            "parentType": parent_type,
            "parentKey": parent_key,
            "contactKey": contact_key,
            "limit": limit,
            "after": after,
        }
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}/crm/objects/{quote(object_type, safe='')}"
        if query:
            url += f"?{query}"
        return self._request("GET", url)

    def _send_batches(self, path, key, records, company_id, chunk_size, counters):
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list):
            raise ValueError(f"{key} must be a list")
        if not 1 <= chunk_size <= MAX_CRM_BATCH:
            raise ValueError(f"chunk_size must be between 1 and {MAX_CRM_BATCH}")

        url = f"{self.base_url}{path}"
        totals = {"count": 0, **{c: 0 for c in counters}, "failed": []}
        for start in range(0, len(records), chunk_size):
            chunk = records[start:start + chunk_size]
            body = {key: chunk}
            if company_id:
                body["companyId"] = company_id
            res = self._request("POST", url, body)
            totals["count"] += res.get("count", len(chunk))
            for c in counters:
                totals[c] += res.get(c, 0)
            for failure in res.get("failed", []):
                mapped = dict(failure)
                # Re-base the per-chunk index onto the list the caller passed.
                if isinstance(failure.get("index"), int):
                    mapped["index"] = start + failure["index"]
                totals["failed"].append(mapped)
        return totals

    def _request(self, method, url, body=None):
        attempt = 0
        refreshed = False
        while True:
            try:
                return make_request(
                    method, url, self.headers, json=body, logger=self.logger, timeout=REQUEST_TIMEOUT
                )
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                # Tokens last an hour; a long load outlives one. Log in again
                # once, then let a second 401 (bad credentials) through.
                if status == 401 and self.refresh_token and not refreshed:
                    refreshed = True
                    self.refresh_token()
                    continue
                if status not in RETRY_STATUSES or attempt >= self.retries:
                    raise
                reason = f"HTTP {status}"
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt >= self.retries:
                    raise
                reason = type(e).__name__
            attempt += 1
            delay = self.backoff_s * 2 ** (attempt - 1)
            if self.logger:
                self.logger.warning(
                    "%s on %s, resending in %.0fs (%d/%d)", reason, url, delay, attempt, self.retries
                )
            time.sleep(delay)
