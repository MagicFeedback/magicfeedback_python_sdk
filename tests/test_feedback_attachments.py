"""Unit tests for FeedbackAPI.upload_attachment guards (max files + dedupe).

These are pure/mocked tests — no network and no credentials. They construct a
FeedbackAPI directly and stub out the existing-attachment fetch, the GCS
download used for content comparison, and the multipart POST.
"""
import pytest

from magicfeedback_sdk.api import feedback as feedback_module
from magicfeedback_sdk.api.feedback import FeedbackAPI, MAX_ATTACHMENTS


class _FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


def _make_api():
    return FeedbackAPI(
        base_url="https://api.test",
        headers={"Authorization": "Bearer test"},
        logger=None,
    )


def _attachment(att_id, url, filename):
    return {"id": att_id, "url": url, "filename": filename}


@pytest.fixture
def tmp_file(tmp_path):
    def _write(content, name="new.pdf"):
        p = tmp_path / name
        p.write_bytes(content)
        return str(p)

    return _write


def test_rejects_when_max_attachments_reached(monkeypatch, tmp_file):
    api = _make_api()
    monkeypatch.setattr(
        api,
        "_get_existing_attachments",
        lambda fid: [
            _attachment(f"a{i}", f"http://x/{i}", f"f{i}.pdf")
            for i in range(MAX_ATTACHMENTS)
        ],
    )
    posted = []
    monkeypatch.setattr(
        feedback_module, "make_request", lambda *a, **k: posted.append((a, k)) or {}
    )

    path = tmp_file(b"hello")
    with pytest.raises(ValueError, match="maximum is 3"):
        api.upload_attachment("fb-1", path)
    assert posted == []  # nothing uploaded when the cap trips


def test_rejects_duplicate_content_under_different_name(monkeypatch, tmp_file):
    api = _make_api()
    content = b"identical-bytes-xyz"
    monkeypatch.setattr(
        api,
        "_get_existing_attachments",
        lambda fid: [_attachment("a1", "http://x/1", "original.pdf")],
    )
    # The existing attachment downloads to the SAME bytes as the new file.
    monkeypatch.setattr(
        feedback_module.requests, "get", lambda url, timeout=30: _FakeResponse(content)
    )
    posted = []
    monkeypatch.setattr(
        feedback_module, "make_request", lambda *a, **k: posted.append((a, k)) or {}
    )

    path = tmp_file(content, name="renamed.pdf")  # different name, same content
    with pytest.raises(ValueError, match="Duplicate content"):
        api.upload_attachment("fb-1", path)
    assert posted == []


def test_uploads_when_unique_and_under_cap(monkeypatch, tmp_file):
    api = _make_api()
    monkeypatch.setattr(
        api,
        "_get_existing_attachments",
        lambda fid: [_attachment("a1", "http://x/1", "original.pdf")],
    )
    monkeypatch.setattr(
        feedback_module.requests,
        "get",
        lambda url, timeout=30: _FakeResponse(b"other-content"),
    )
    calls = []

    def fake_make_request(method, url, headers, **kwargs):
        calls.append((method, url, kwargs))
        return {"id": "att-new"}

    monkeypatch.setattr(feedback_module, "make_request", fake_make_request)

    path = tmp_file(b"brand-new-content")
    result = api.upload_attachment("fb-1", path, filename="report.pdf")
    assert result == {"id": "att-new"}
    assert len(calls) == 1
    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url.endswith("/feedbacks/fb-1/attachments")
    assert kwargs["data"]["filename"] == "report.pdf"


def test_check_duplicate_content_false_skips_download(monkeypatch, tmp_file):
    api = _make_api()
    monkeypatch.setattr(
        api,
        "_get_existing_attachments",
        lambda fid: [_attachment("a1", "http://x/1", "original.pdf")],
    )

    def boom(*a, **k):
        raise AssertionError("requests.get must not run when check_duplicate_content=False")

    monkeypatch.setattr(feedback_module.requests, "get", boom)
    calls = []
    monkeypatch.setattr(
        feedback_module, "make_request", lambda *a, **k: calls.append(a) or {"id": "ok"}
    )

    path = tmp_file(b"same")
    result = api.upload_attachment("fb-1", path, check_duplicate_content=False)
    assert result == {"id": "ok"}
    assert len(calls) == 1  # still uploaded (cap not reached)


def test_fails_closed_when_existing_fetch_fails(monkeypatch, tmp_file):
    api = _make_api()

    def raising_get_id(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(api, "get_id", raising_get_id)  # cannot verify the count
    posted = []
    monkeypatch.setattr(
        feedback_module, "make_request", lambda *a, **k: posted.append(a) or {"id": "ok"}
    )

    path = tmp_file(b"whatever")
    # The cap is a hard limit -> fail closed: refuse rather than risk exceeding it.
    with pytest.raises(ValueError, match="Could not verify existing attachments"):
        api.upload_attachment("fb-1", path)
    assert posted == []  # nothing uploaded when the count is unknown


def test_undownloadable_existing_attachment_does_not_block(monkeypatch, tmp_file):
    api = _make_api()
    monkeypatch.setattr(
        api,
        "_get_existing_attachments",
        lambda fid: [_attachment("a1", "http://private/1", "original.pdf")],
    )

    def forbidden(url, timeout=30):
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(feedback_module.requests, "get", forbidden)
    calls = []
    monkeypatch.setattr(
        feedback_module, "make_request", lambda *a, **k: calls.append(a) or {"id": "ok"}
    )

    path = tmp_file(b"content-we-cannot-compare-against")
    result = api.upload_attachment("fb-1", path)  # can't verify -> proceeds
    assert result == {"id": "ok"}
    assert len(calls) == 1
