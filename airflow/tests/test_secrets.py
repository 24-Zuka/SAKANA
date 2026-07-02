import subprocess

import pytest

from airflow import secrets
from airflow.guard import GuardBlocked


def test_fallback_set_and_get_roundtrip(tmp_path):
    secrets.set_secret("bridge_token", "s3cr3t", home=tmp_path)
    assert secrets.get_secret("bridge_token", home=tmp_path) == "s3cr3t"


def test_fallback_get_missing_returns_none(tmp_path):
    assert secrets.get_secret("does_not_exist", home=tmp_path) is None


def test_fallback_file_has_restrictive_permissions(tmp_path):
    secrets.set_secret("bridge_token", "s3cr3t", home=tmp_path)
    mode = (tmp_path / "secrets.json").stat().st_mode & 0o777
    assert mode == 0o600


def test_fallback_preserves_other_accounts(tmp_path):
    secrets.set_secret("account_a", "value_a", home=tmp_path)
    secrets.set_secret("account_b", "value_b", home=tmp_path)
    assert secrets.get_secret("account_a", home=tmp_path) == "value_a"
    assert secrets.get_secret("account_b", home=tmp_path) == "value_b"


def test_set_secret_uses_keychain_on_macos(tmp_path, monkeypatch):
    calls = []

    def fake_run_guarded(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(secrets, "is_macos", lambda: True)
    monkeypatch.setattr(secrets, "run_guarded", fake_run_guarded)

    secrets.set_secret("bridge_token", "s3cr3t", home=tmp_path)

    assert len(calls) == 1
    assert calls[0][:2] == ["security", "add-generic-password"]
    assert "s3cr3t" in calls[0]
    # 非macOSフォールバックファイルは作成されない
    assert not (tmp_path / "secrets.json").exists()


def test_get_secret_reads_from_keychain_on_macos(tmp_path, monkeypatch):
    def fake_run_guarded(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout="s3cr3t\n", stderr="")

    monkeypatch.setattr(secrets, "is_macos", lambda: True)
    monkeypatch.setattr(secrets, "run_guarded", fake_run_guarded)

    assert secrets.get_secret("bridge_token", home=tmp_path) == "s3cr3t"


def test_get_secret_returns_none_when_keychain_lookup_fails(tmp_path, monkeypatch):
    def fake_run_guarded(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 44, stdout="", stderr="not found")

    monkeypatch.setattr(secrets, "is_macos", lambda: True)
    monkeypatch.setattr(secrets, "run_guarded", fake_run_guarded)

    assert secrets.get_secret("bridge_token", home=tmp_path) is None


def test_set_secret_raises_when_guard_blocks(tmp_path, monkeypatch):
    def fake_run_guarded(argv, **kwargs):
        from airflow.guard import Blocked

        raise GuardBlocked(Blocked("core.git", "reason", "suggestion"))

    monkeypatch.setattr(secrets, "is_macos", lambda: True)
    monkeypatch.setattr(secrets, "run_guarded", fake_run_guarded)

    with pytest.raises(secrets.SecretStoreError):
        secrets.set_secret("bridge_token", "s3cr3t", home=tmp_path)
