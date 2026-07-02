import os
import shutil
import subprocess
from pathlib import Path

import pytest

from airflow.guard import (
    CommandNotAllowlisted,
    GuardBlocked,
    check,
    evaluate_builtin,
    run_guarded,
)

DCG_RELEASE_BIN = Path(__file__).resolve().parents[2] / "dcg" / "target" / "release" / "dcg"
DCG_DEBUG_BIN = Path(__file__).resolve().parents[2] / "dcg" / "target" / "debug" / "dcg"


def _compiled_dcg_available() -> bool:
    return DCG_RELEASE_BIN.exists() or DCG_DEBUG_BIN.exists()


# --- 内蔵ルール（dcgバイナリ不在時のフォールバック）のテスト ---


def test_builtin_allows_harmless_command(tmp_path):
    assert evaluate_builtin(["git", "status"], tmp_path) is None


def test_builtin_blocks_rm_rf_outside_tmp(tmp_path):
    blocked = evaluate_builtin(["rm", "-rf", "/"], tmp_path)
    assert blocked is not None
    assert blocked.rule_id == "core.filesystem"


def test_builtin_allows_rm_rf_inside_tmp(tmp_path):
    target = tmp_path / "tmp" / "scratch"
    assert evaluate_builtin(["rm", "-rf", str(target)], tmp_path) is None


def test_builtin_blocks_reset_hard(tmp_path):
    blocked = evaluate_builtin(["git", "reset", "--hard"], tmp_path)
    assert blocked is not None
    assert blocked.rule_id == "core.git"


def test_builtin_blocks_force_push_to_main(tmp_path):
    blocked = evaluate_builtin(["git", "push", "--force", "origin", "main"], tmp_path)
    assert blocked is not None
    assert blocked.rule_id == "core.git:force-push"


def test_builtin_allows_force_push_to_feature_branch(tmp_path):
    assert evaluate_builtin(["git", "push", "--force", "origin", "feature/x"], tmp_path) is None


def test_builtin_blocks_disk_tools(tmp_path):
    blocked = evaluate_builtin(["dd", "if=/dev/zero", "of=/dev/sda"], tmp_path)
    assert blocked is not None
    assert blocked.rule_id == "system.disk"


def test_builtin_commit_message_false_positive(tmp_path):
    assert (
        evaluate_builtin(["git", "commit", "-m", "fix: remove rm -rf usage"], tmp_path) is None
    )


# --- check() / run_guarded() のテスト（AIRFLOW_DCG_BINを空にして内蔵ルール経路を強制） ---


@pytest.fixture(autouse=True)
def _force_builtin_path(monkeypatch):
    # PATH上にdcgバイナリが無い状態を保証し、内蔵ルール経路を確実にテストする。
    monkeypatch.delenv("AIRFLOW_DCG_BIN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)


def test_check_raises_on_blocked(tmp_path):
    with pytest.raises(GuardBlocked):
        check(["git", "reset", "--hard"], workspace_root=tmp_path)


def test_check_passes_silently_when_allowed(tmp_path):
    check(["git", "status"], workspace_root=tmp_path)  # should not raise


def test_run_guarded_rejects_non_allowlisted_command(tmp_path):
    with pytest.raises(CommandNotAllowlisted):
        run_guarded(["curl", "http://example.com"], workspace_root=tmp_path)


def test_run_guarded_blocks_dangerous_git_command(tmp_path):
    with pytest.raises(GuardBlocked):
        run_guarded(["git", "reset", "--hard"], workspace_root=tmp_path, cwd=tmp_path)


def test_run_guarded_executes_allowed_command(tmp_path):
    result = run_guarded(
        ["git", "status"], workspace_root=tmp_path, cwd=tmp_path, capture_output=True, text=True
    )
    assert isinstance(result, subprocess.CompletedProcess)


# --- コンパイル済みdcgバイナリ経路の統合テスト（バイナリがビルド済みの場合のみ） ---


@pytest.mark.skipif(not _compiled_dcg_available(), reason="dcg binary not built")
def test_compiled_dcg_binary_blocks_and_reports(tmp_path, monkeypatch):
    monkeypatch.undo()  # revert the autouse fixture's shutil.which patch for this test
    dcg_bin = str(DCG_RELEASE_BIN if DCG_RELEASE_BIN.exists() else DCG_DEBUG_BIN)
    monkeypatch.setenv("AIRFLOW_DCG_BIN", dcg_bin)

    with pytest.raises(GuardBlocked) as exc_info:
        check(["git", "push", "--force", "origin", "main"], workspace_root=tmp_path)
    assert exc_info.value.blocked.rule_id == "core.git:force-push"
