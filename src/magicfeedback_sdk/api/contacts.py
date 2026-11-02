from magicfeedback_sdk.utils.request import make_request

# Server-side cap on items per POST /crm/contacts/upsert/batch. `upsert_batch`
# chunks to this size, so callers can pass a list of any length.
MAX_UPSERT_BATCH = 500


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

    def update_fields(self, contact_id, custom_fields=None, **native_fields):
        """Merge custom fields (and a few native fields) into a contact.

        Hits ``PATCH /crm/contacts/{id}/fields``, the server-side
        read-modify-write endpoint, NOT ``update()`` (``PATCH
        /crm/contacts/{id}``). ``update()`` writes the ``customFields`` column
        *whole*, so setting one custom field there deletes every other one. Here
        the semantics are additive: the refs you send are added or overwritten,
        every other custom field is KEPT, and an explicit ``None`` removes its
        ref. Omitting ``custom_fields`` leaves the object untouched.

        :param contact_id: the contact's id.
        :param custom_fields: dict of ``ref -> value`` to upsert. Values may be
            ``str``, ``int``/``float`` or ``bool``; a value of ``None`` removes
            that ref. Pass ``None`` (the default) or omit it to touch only the
            native fields below. An empty dict ``{}`` is sent as-is (a no-op
            merge that still returns the current fields).
        :param native_fields: optional native columns to overwrite, any of
            ``name``, ``lastname``, ``phone``, ``address``, ``city``,
            ``state``, ``postalCode``. Any other column (``email``,
            ``externalId``, ``status``, ``country``, ``type``) is rejected by
            the API with a 400 — use :meth:`update` for those, deliberately.
        :returns: ``{"id": ..., "customFields": {...}}`` — the full custom-field
            set after the merge.
        """
        url = f"{self.base_url}/crm/contacts/{contact_id}/fields"
        payload = dict(native_fields)
        # Only include customFields when the caller passed something: the server
        # keys the merge off `customFields !== undefined`, so omitting it here
        # means "native-only update, leave custom fields alone" while `{}` is a
        # deliberate no-op merge.
        if custom_fields is not None:
            payload["customFields"] = custom_fields
        return make_request("PATCH", url, self.headers, json=payload, logger=self.logger)

    def upsert(self, contact):
        """Create-or-update a single contact, matched by ``(companyId, email)``.

        Hits ``POST /crm/contacts/upsert``. Unlike :meth:`create` (which always
        inserts — there is no unique constraint on email, so re-posting a known
        email silently creates a duplicate), this reconciles: if an ACTIVE
        contact with the normalized email already exists in the company it is
        PATCHed, otherwise a new one is created.

        On the update branch the write is additive, matching :meth:`update_fields`
        and the other server-side writers: the scalar columns you send are
        overwritten and ``customFields`` is MERGED (refs upserted, ``None``
        clears one, others kept) — never replaced wholesale. The match key
        (``email``/``companyId``) is never rewritten.

        :param contact: the contact record. ``name``, ``email`` and ``companyId``
            are required (an insert needs them); other columns and
            ``customFields`` are optional.
        :returns: the contact after the upsert.
        """
        url = f"{self.base_url}/crm/contacts/upsert"
        required_fields = ["name", "email", "companyId"]
        for field in required_fields:
            if field not in contact:
                raise ValueError(f"Missing required field: {field}")
        return make_request("POST", url, self.headers, json=contact, logger=self.logger)

    def upsert_batch(self, items, chunk_size=MAX_UPSERT_BATCH):
        """Upsert many contacts in one go, each matched by ``(companyId, email)``.

        Hits ``POST /crm/contacts/upsert/batch``, automatically CHUNKING ``items``
        to the server cap (500) so you can pass a list of any length — a 1,200-item
        list becomes three requests. Sending a batch instead of N single calls is
        the pool-friendly way to do bulk: the server runs each chunk sequentially,
        holding at most one DB connection at a time, rather than N parallel
        requests racing the connection pool.

        Best-effort per item: an item that fails on its own (invalid email, a
        company you cannot access, ...) is collected in ``failed`` and the rest
        still land. Each item upserts identically to :meth:`upsert`.

        :param items: list of contact records (same shape as :meth:`upsert`).
            An empty list is a no-op that returns zeroed totals.
        :param chunk_size: items per request; defaults to (and is capped at) the
            server maximum of 500.
        :returns: aggregated ``{"contacts", "created", "updated", "failed"}``
            across all chunks. Each ``failed`` entry's ``index`` is mapped back
            to the position in the ORIGINAL ``items`` list, not the chunk.
        """
        if not isinstance(items, list):
            raise ValueError("items must be a list")
        if not 1 <= chunk_size <= MAX_UPSERT_BATCH:
            raise ValueError(f"chunk_size must be between 1 and {MAX_UPSERT_BATCH}")

        url = f"{self.base_url}/crm/contacts/upsert/batch"
        totals = {"contacts": 0, "created": 0, "updated": 0, "failed": []}
        for start in range(0, len(items), chunk_size):
            chunk = items[start:start + chunk_size]
            res = make_request(
                "POST", url, self.headers, json={"items": chunk}, logger=self.logger
            )
            totals["contacts"] += res.get("contacts", len(chunk))
            totals["created"] += res.get("created", 0)
            totals["updated"] += res.get("updated", 0)
            for failure in res.get("failed", []):
                mapped = dict(failure)
                # Re-base the per-chunk index onto the original items list.
                if isinstance(failure.get("index"), int):
                    mapped["index"] = start + failure["index"]
                totals["failed"].append(mapped)
        return totals

    def delete(self, contact_id):
        url = f"{self.base_url}/crm/contacts/{contact_id}"
        return make_request("DELETE", url, self.headers, logger=self.logger)
