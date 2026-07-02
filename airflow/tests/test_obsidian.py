from datetime import date, datetime, timezone

import httpx
import pytest

from airflow.obsidian import (
    HANDOFF_ANCHOR,
    BRIEF_MARKER,
    ObsidianClient,
    ObsidianError,
    ObsidianFileNotFound,
    ObsidianWriteRefused,
    export_brief,
)


def _resp(status_code, *, text="", json_body=None, url="http://x"):
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=httpx.Request("GET", url))
    return httpx.Response(status_code, text=text, request=httpx.Request("GET", url))


def test_read_success(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200, text="本文です"))
    client = ObsidianClient()
    assert client.read("notes/foo.md") == "本文です"


def test_read_404_raises_file_not_found(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(404))
    client = ObsidianClient()
    with pytest.raises(ObsidianFileNotFound):
        client.read("notes/missing.md")


def test_read_connection_error_raises_obsidian_error(monkeypatch):
    def fake_get(url, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", fake_get)
    client = ObsidianClient()
    with pytest.raises(ObsidianError):
        client.read("notes/foo.md")


def test_write_success(monkeypatch):
    calls = []

    def fake_put(url, **kw):
        calls.append((url, kw))
        return _resp(200)

    monkeypatch.setattr(httpx, "put", fake_put)
    client = ObsidianClient()
    client.write("notes/foo.md", "内容")
    assert len(calls) == 1
    assert calls[0][0].endswith("/vault/notes/foo.md")


def test_write_failure_raises(monkeypatch):
    monkeypatch.setattr(httpx, "put", lambda url, **kw: _resp(500))
    client = ObsidianClient()
    with pytest.raises(ObsidianError):
        client.write("notes/foo.md", "内容")


def test_append_after_heading_sends_patch_headers(monkeypatch):
    captured = {}

    def fake_patch(url, **kw):
        captured["headers"] = kw["headers"]
        captured["content"] = kw["content"]
        return _resp(200)

    monkeypatch.setattr(httpx, "patch", fake_patch)
    client = ObsidianClient(token="secret")
    client.append_after_heading("notes/foo.md", "## 今日の要判断", "- 新しい項目")

    assert captured["headers"]["Operation"] == "append"
    assert captured["headers"]["Target-Type"] == "heading"
    assert captured["headers"]["Target"] == "## 今日の要判断"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "新しい項目".encode() in captured["content"]


def test_handoff_append_creates_file_with_anchor_when_missing(monkeypatch):
    written = {}

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(404))

    def fake_put(url, **kw):
        written["content"] = kw["content"].decode("utf-8")
        return _resp(200)

    monkeypatch.setattr(httpx, "put", fake_put)
    client = ObsidianClient()
    client.handoff_append("AI_Handoff.md", "新しい引き継ぎ内容", now=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))

    assert written["content"].startswith(HANDOFF_ANCHOR)
    assert "新しい引き継ぎ内容" in written["content"]


def test_handoff_append_preserves_existing_history_and_inserts_after_anchor(monkeypatch):
    existing = f"{HANDOFF_ANCHOR}\n\n## 旧エントリ\n古い内容"
    written = {}

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200, text=existing))

    def fake_put(url, **kw):
        written["content"] = kw["content"].decode("utf-8")
        return _resp(200)

    monkeypatch.setattr(httpx, "put", fake_put)
    client = ObsidianClient()
    client.handoff_append("AI_Handoff.md", "新しい内容", now=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))

    content = written["content"]
    assert content.startswith(HANDOFF_ANCHOR)
    # 新しい内容がアンカー直後・旧エントリより前（逆順スタック＝最新が最上部）
    assert content.index("新しい内容") < content.index("旧エントリ")
    assert "古い内容" in content  # 既存履歴は保持される


def test_handoff_append_refuses_when_anchor_missing(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200, text="アンカーの無いファイル"))
    client = ObsidianClient()
    with pytest.raises(ObsidianWriteRefused):
        client.handoff_append("AI_Handoff.md", "内容")


def test_delete_moves_to_trash_then_deletes_original(monkeypatch):
    calls = []

    def fake_get(url, **kw):
        return _resp(200, text="削除対象の内容")

    def fake_put(url, **kw):
        calls.append(("PUT", url))
        return _resp(200)

    def fake_delete(url, **kw):
        calls.append(("DELETE", url))
        return _resp(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "put", fake_put)
    monkeypatch.setattr(httpx, "delete", fake_delete)

    client = ObsidianClient()
    trash_path = client.delete("notes/old.md")

    assert trash_path.startswith(".trash/")
    assert calls[0][0] == "PUT"
    assert calls[0][1].endswith(f"/vault/{trash_path}")
    assert calls[1] == ("DELETE", "http://127.0.0.1:27123/vault/notes/old.md")


def test_search_returns_parsed_json(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, **kw: _resp(200, json_body=[{"filename": "a.md", "score": 1.0}])
    )
    client = ObsidianClient()
    results = client.search("契約")
    assert results == [{"filename": "a.md", "score": 1.0}]


def test_is_reachable_true_and_false(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200))
    assert ObsidianClient().is_reachable() is True

    def fake_get_fail(url, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", fake_get_fail)
    assert ObsidianClient().is_reachable() is False


def test_export_brief_creates_new_file_with_marker(monkeypatch):
    written = {}

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(404))

    def fake_put(url, **kw):
        written["url"] = url
        written["content"] = kw["content"].decode("utf-8")
        return _resp(200)

    monkeypatch.setattr(httpx, "put", fake_put)
    client = ObsidianClient()
    path = export_brief(client, date(2026, 7, 1), "# 朝礼 2026-07-01\n...")

    assert path == "90_Daily/AirFlow_2026-07-01_朝礼.md"
    assert written["content"].startswith(BRIEF_MARKER)


def test_export_brief_overwrites_existing_marked_file(monkeypatch):
    existing = f"{BRIEF_MARKER}\n# 古い朝礼"
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200, text=existing))

    written = {}

    def fake_put(url, **kw):
        written["content"] = kw["content"].decode("utf-8")
        return _resp(200)

    monkeypatch.setattr(httpx, "put", fake_put)
    client = ObsidianClient()
    export_brief(client, date(2026, 7, 1), "# 新しい朝礼")
    assert "新しい朝礼" in written["content"]


def test_export_brief_refuses_to_overwrite_handwritten_note(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _resp(200, text="# 手書きの日誌\n今日は良い天気でした。"))
    client = ObsidianClient()
    with pytest.raises(ObsidianWriteRefused):
        export_brief(client, date(2026, 7, 1), "# 朝礼")
