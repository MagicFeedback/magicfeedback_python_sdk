import hashlib
import json
import os

import requests

from magicfeedback_sdk.utils.request import make_request

# Hard cap on how many files a single feedback may hold. Kept as a module
# constant so callers can reference it (and override per-call via
# `upload_attachment(..., max_attachments=...)`).
MAX_ATTACHMENTS = 3

# Feedback fields whose entries are {"key": ..., "value": ...} pairs. The API
# is inconsistent about `value`'s shape: the backend tables it maps to
# (FeedbackMetrics.values / FeedbackMetadata.values) are `array<string>`, but
# the inline JSON the API actually reads and writes stores whatever shape was
# last sent, so the same feedback can have `{"key": "channel", "value":
# "voice"}` next to `{"key": "agent", "value": ["sln"]}`. The SDK normalizes
# every bare scalar to a single-item list, both on the way out (create/update)
# and on the way in (get/get_id), so callers only ever see/send lists.
# `questions` is excluded: it is a distinct object shape (title/ref/position/
# ...), not a pair.
PAIR_VALUE_FIELDS = ("answers", "metadata", "metrics", "profile")


def _normalize_pair_values(feedback):
    """Wrap any bare scalar `value` in PAIR_VALUE_FIELDS entries into a list, in place."""
    for field in PAIR_VALUE_FIELDS:
        pairs = feedback.get(field)
        if not isinstance(pairs, list):
            continue
        for pair in pairs:
            if isinstance(pair, dict) and "value" in pair and not isinstance(pair["value"], list):
                pair["value"] = [pair["value"]]


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

        _normalize_pair_values(feedback)

        return make_request("POST", url, self.headers, json=feedback, logger=self.logger)

    def get_id(self, feedback_id, filter=None):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        if filter:
            url += f"?filter={json.dumps(filter)}"
        feedback = make_request("GET", url, self.headers, logger=self.logger)
        if isinstance(feedback, dict):
            _normalize_pair_values(feedback)
        return feedback

    def get(self, filter=None):
        url = f"{self.base_url}/feedbacks"
        if filter:
            url += f"?filter={json.dumps(filter)}"
        feedbacks = make_request("GET", url, self.headers, logger=self.logger)
        if isinstance(feedbacks, list):
            for feedback in feedbacks:
                if isinstance(feedback, dict):
                    _normalize_pair_values(feedback)
        return feedbacks

    def update(self, feedback_id, feedback):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        _normalize_pair_values(feedback)
        return make_request("PATCH", url, self.headers, json=feedback, logger=self.logger)

    def delete(self, feedback_id):
        url = f"{self.base_url}/feedbacks/{feedback_id}"
        return make_request("DELETE", url, self.headers, logger=self.logger)

    def upload_attachment(
        self,
        feedback_id,
        file_path,
        filename=None,
        extra_data=None,
        max_attachments=MAX_ATTACHMENTS,
        check_duplicate_content=True,
    ):
        """Upload a file and attach it to a feedback.

        Before uploading, the feedback's existing attachments are fetched to
        enforce two guards (nothing is uploaded when a guard trips):

        * **At most ``max_attachments`` files** (default 3) per feedback. If the
          feedback already holds that many, ``ValueError`` is raised.
        * **No duplicate content.** The new file's bytes are SHA-256 hashed and
          compared against every existing attachment by *content*, not filename,
          so an identical file already attached under a different name is caught.
          On a match ``ValueError`` is raised. Set ``check_duplicate_content=
          False`` to skip this — it downloads each existing attachment to hash
          its bytes, which can be slow (and silently no-ops for attachments the
          SDK cannot download, e.g. a private bucket returning 403).

        The cap is a hard limit, so it fails **closed**: if the feedback's
        current attachments cannot be fetched, the upload is refused (rather than
        risk exceeding the cap). The per-file content download used for the
        duplicate check stays best-effort.

        :param max_attachments: cap on total attachments for the feedback.
        :param check_duplicate_content: when True (default), reject a file whose
            bytes are identical to one already attached.
        """
        # Read the new file once; the same bytes are hashed for the duplicate
        # check and streamed in the multipart upload (no double read).
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        display_name = filename or os.path.basename(file_path)

        # --- Guards over the feedback's current attachments ------------------
        # Fail CLOSED on the cap: if we cannot determine the current count we
        # refuse rather than risk exceeding max_attachments. (Only the per-file
        # content download below — _attachment_content_hash — is best-effort.)
        try:
            existing = self._get_existing_attachments(feedback_id)
        except Exception as exc:
            raise ValueError(
                f"Could not verify existing attachments for feedback {feedback_id} "
                f"({exc}); refusing to upload '{display_name}' to avoid exceeding "
                f"the maximum of {max_attachments} attachment(s)."
            ) from exc

        # 1) Cap the number of files. `>=` because adding one more would exceed
        #    the cap (e.g. 3 existing + this one = 4 > 3).
        if len(existing) >= max_attachments:
            raise ValueError(
                f"Feedback {feedback_id} already has {len(existing)} attachment(s); "
                f"the maximum is {max_attachments}. '{display_name}' was not uploaded."
            )

        # 2) Reject content byte-for-byte identical to an existing attachment.
        if check_duplicate_content and existing:
            new_hash = hashlib.sha256(file_bytes).hexdigest()
            for att in existing:
                if self._attachment_content_hash(att) == new_hash:
                    raise ValueError(
                        f"Duplicate content: '{display_name}' is byte-for-byte "
                        f"identical to already-attached file "
                        f"'{att.get('filename') or att.get('id')}'. Nothing was uploaded."
                    )

        # --- Upload ----------------------------------------------------------
        url = f"{self.base_url}/feedbacks/{feedback_id}/attachments"
        files = {"file": (display_name, file_bytes)}
        data = {"filename": display_name}
        if extra_data is not None:
            data["extraData"] = json.dumps(extra_data) if not isinstance(extra_data, str) else extra_data

        # Remove Content-Type so requests sets it automatically with the multipart boundary
        headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}

        return make_request("POST", url, headers, files=files, data=data, logger=self.logger)

    def _get_existing_attachments(self, feedback_id):
        """Return the feedback's current attachments (list of dicts).

        Propagates on a fetch failure (network / feedback not found) so the
        caller can fail closed on the hard max-files cap instead of silently
        allowing an upload that might exceed it.
        """
        feedback = self.get_id(
            feedback_id,
            filter={"include": [{"relation": "feedbackAttachments"}]},
        )
        attachments = (feedback or {}).get("feedbackAttachments") or []
        return attachments if isinstance(attachments, list) else []

    def _attachment_content_hash(self, attachment):
        """SHA-256 hex of an existing attachment's content, or ``None``.

        The server stores a URL, not a content hash, so the file is downloaded
        to hash it. Best-effort: any failure (no URL, 403 on a private bucket,
        network error) returns ``None``, so that attachment is simply ignored in
        the duplicate check instead of blocking the upload.
        """
        url = attachment.get("url")
        if not url:
            return None
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return hashlib.sha256(resp.content).hexdigest()
        except Exception as exc:
            if self.logger:
                self.logger.warning(
                    "Could not download existing attachment %s to check for "
                    "duplicate content (%s); ignoring it in the check.",
                    attachment.get("id") or url, exc,
                )
            return None
