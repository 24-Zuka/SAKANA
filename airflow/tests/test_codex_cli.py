import os
import sys
from pathlib import Path

import pytest

from airflow.adapters.codex_cli import CodexCliAdapter

FAKE_BIN_DIR = Path(__file__).parent / "fixtures" / "fake_bin"


@pytest.fixture
def fake_codex_on_path(monkeypatch):
    monkeypatch.setenv("PATH", f"{FAKE_BIN_DIR}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


def test_is_available_detects_fake_binary(fake_codex_on_path):
    adapter = CodexCliAdapter()
    assert adapter.is_available() is True


def test_login_status_true_when_logged_in(fake_codex_on_path, tmp_path):
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    assert adapter.login_status() is True


def test_run_parses_jsonl_output(fake_codex_on_path, tmp_path):
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    result = adapter.run("A社レート再交渉の方針を決める")
    assert result.ok is True
    assert result.worker == "codex"
    assert "計画を" in result.text
    assert "作成しました。" in result.text
    assert "echo:A社レート再交渉の方針を決める" in result.text
    assert result.error is None
    assert result.elapsed >= 0


def test_run_reports_failure_without_raising(fake_codex_on_path, tmp_path):
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    result = adapter.run("TRIGGER_FAILURE")
    assert result.ok is False
    assert result.text == ""
    assert result.error is not None


def test_run_refuses_when_api_key_present(fake_codex_on_path, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    result = adapter.run("何かのタスク")
    assert result.ok is False
    assert "OPENAI_API_KEY" in result.error


def test_run_reports_unavailable_when_binary_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    result = adapter.run("何かのタスク")
    assert result.ok is False
    assert "見つかりません" in result.error


def test_run_blocked_by_guard_for_dangerous_prompt_is_not_possible_via_prompt_alone(
    fake_codex_on_path, tmp_path
):
    # プロンプト文字列は1トークンとしてargvに渡るため、"rm -rf"等の文言を含んでいても
    # dcgのトークン単位マッチングには抵触しない（誤検知ゼロ）。
    adapter = CodexCliAdapter(workspace_root=tmp_path)
    result = adapter.run("please explain what rm -rf does")
    assert result.ok is True
