"""Unit tests for ContactsAPI.upsert and ContactsAPI.upsert_batch.

Pure unit tests — no network, no credentials (make_request is monkeypatched).
"""

import pytest

from magicfeedback_sdk.api import contacts as contacts_module
from magicfeedback_sdk.api.contacts import ContactsAPI, MAX_UPSERT_BATCH


def _api():
    return ContactsAPI(base_url="https://api.test", headers={"h": "1"}, logger=None)


def _record(i):
    return {"name": f"C{i}", "email": f"c{i}@e.com", "companyId": "A"}


# --- upsert (single) -------------------------------------------------------

def test_upsert_posts_to_upsert_route(monkeypatch):
    calls = []
    monkeypatch.setattr(
        contacts_module, "make_request",
        lambda method, url, headers, json=None, **kw: calls.append((method, url, json)) or {"id": "1"},
    )

    _api().upsert(_record(1))

    method, url, body = calls[0]
    assert method == "POST"
    assert url == "https://api.test/crm/contacts/upsert"
    assert body["email"] == "c1@e.com"


@pytest.mark.parametrize("missing", ["name", "email", "companyId"])
def test_upsert_requires_key_fields(monkeypatch, missing):
    monkeypatch.setattr(contacts_module, "make_request", lambda *a, **k: {})
    record = _record(1)
    del record[missing]
    with pytest.raises(ValueError):
        _api().upsert(record)


# --- upsert_batch ----------------------------------------------------------

def test_upsert_batch_chunks_and_aggregates(monkeypatch):
    """A >cap list is split into several requests and the totals are summed."""
    chunk_sizes = []

    def fake(method, url, headers, json=None, **kw):
        chunk = json["items"]
        chunk_sizes.append(len(chunk))
        return {"contacts": len(chunk), "created": len(chunk), "updated": 0, "failed": []}

    monkeypatch.setattr(contacts_module, "make_request", fake)

    items = [_record(i) for i in range(1201)]
    res = _api().upsert_batch(items)

    assert chunk_sizes == [500, 500, 201]         # chunked to the server cap
    assert res["contacts"] == 1201
    assert res["created"] == 1201
    assert res["failed"] == []


def test_upsert_batch_remaps_failed_index_to_original_list(monkeypatch):
    """failed[i]['index'] must point into the ORIGINAL items list, not the chunk."""

    def fake(method, url, headers, json=None, **kw):
        chunk = json["items"]
        # Fail the 2nd item (local index 1) of every chunk.
        return {
            "contacts": len(chunk),
            "created": len(chunk) - 1,
            "updated": 0,
            "failed": [{"index": 1, "email": chunk[1]["email"], "error": "boom"}],
        }

    monkeypatch.setattr(contacts_module, "make_request", fake)

    items = [_record(i) for i in range(1201)]
    res = _api().upsert_batch(items, chunk_size=500)

    assert [f["index"] for f in res["failed"]] == [1, 501, 1001]
    # the email still lines up with that global index
    assert res["failed"][1]["email"] == items[501]["email"]


def test_upsert_batch_custom_chunk_size(monkeypatch):
    chunk_sizes = []
    monkeypatch.setattr(
        contacts_module, "make_request",
        lambda method, url, headers, json=None, **kw: chunk_sizes.append(len(json["items"]))
        or {"contacts": len(json["items"]), "created": 0, "updated": len(json["items"]), "failed": []},
    )

    _api().upsert_batch([_record(i) for i in range(5)], chunk_size=2)
    assert chunk_sizes == [2, 2, 1]


def test_upsert_batch_empty_is_noop(monkeypatch):
    called = []
    monkeypatch.setattr(contacts_module, "make_request", lambda *a, **k: called.append(1) or {})

    res = _api().upsert_batch([])

    assert called == []  # no request made
    assert res == {"contacts": 0, "created": 0, "updated": 0, "failed": []}


@pytest.mark.parametrize("bad", [0, -1, MAX_UPSERT_BATCH + 1])
def test_upsert_batch_rejects_invalid_chunk_size(monkeypatch, bad):
    monkeypatch.setattr(contacts_module, "make_request", lambda *a, **k: {})
    with pytest.raises(ValueError):
        _api().upsert_batch([_record(1)], chunk_size=bad)


def test_upsert_batch_rejects_non_list(monkeypatch):
    monkeypatch.setattr(contacts_module, "make_request", lambda *a, **k: {})
    with pytest.raises(ValueError):
        _api().upsert_batch({"items": []})
