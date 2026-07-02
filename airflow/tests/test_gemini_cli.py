import os
from pathlib import Path

import pytest

from airflow.adapters.gemini_cli import GeminiCliAdapter

FAKE_BIN_DIR = Path(__file__).parent / "fixtures" / "fake_bin"


@pytest.fixture
def fake_gemini_on_path(monkeypatch):
    monkeypatch.setenv("PATH", f"{FAKE_BIN_DIR}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


def test_is_available_detects_fake_binary(fake_gemini_on_path):
    adapter = GeminiCliAdapter()
    assert adapter.is_available() is True


def test_run_returns_stdout(fake_gemini_on_path, tmp_path):
    adapter = GeminiCliAdapter(workspace_root=tmp_path)
    result = adapter.run("次回動画のテーマ確定")
    assert result.ok is True
    assert result.worker == "gemini"
    assert "次回動画のテーマ確定" in result.text


def test_run_reports_failure_without_raising(fake_gemini_on_path, tmp_path):
    adapter = GeminiCliAdapter(workspace_root=tmp_path)
    result = adapter.run("TRIGGER_FAILURE")
    assert result.ok is False
    assert result.error is not None


def test_run_refuses_when_api_key_present(fake_gemini_on_path, monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "should-not-be-used")
    adapter = GeminiCliAdapter(workspace_root=tmp_path)
    result = adapter.run("何かのタスク")
    assert result.ok is False
    assert "GEMINI_API_KEY" in result.error


def test_run_reports_unavailable_when_binary_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    adapter = GeminiCliAdapter(workspace_root=tmp_path)
    result = adapter.run("何かのタスク")
    assert result.ok is False
    assert "見つかりません" in result.error
