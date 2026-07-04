import plistlib
from pathlib import Path

import pytest

from airflow.automation import launchd
from airflow.automation.launchd import (
    JOB_BRIEF,
    JOB_GROOMING,
    JOB_INBOX,
    generate_brief_plist,
    generate_grooming_plist,
    generate_inbox_plist,
    install,
    uninstall,
)


def test_generate_brief_plist_has_expected_schedule():
    data = plistlib.loads(generate_brief_plist("/usr/local/bin/airflowctl", hour=7, minute=30))
    assert data["Label"] == JOB_BRIEF
    assert data["ProgramArguments"] == ["/usr/local/bin/airflowctl", "brief"]
    assert data["StartCalendarInterval"] == {"Hour": 7, "Minute": 30}
    assert data["RunAtLoad"] is False


def test_generate_grooming_plist_has_expected_schedule():
    data = plistlib.loads(generate_grooming_plist("/usr/local/bin/airflowctl", hour=23, minute=0))
    assert data["Label"] == JOB_GROOMING
    assert data["ProgramArguments"] == ["/usr/local/bin/airflowctl", "groom"]
    assert data["StartCalendarInterval"] == {"Hour": 23, "Minute": 0}


def test_generate_inbox_plist_watches_inbox_dir(tmp_path):
    inbox_dir = tmp_path / "inbox"
    data = plistlib.loads(generate_inbox_plist("/usr/local/bin/airflowctl", inbox_dir))
    assert data["Label"] == JOB_INBOX
    assert data["ProgramArguments"] == ["/usr/local/bin/airflowctl", "import-inbox", "--once"]
    assert data["WatchPaths"] == [str(inbox_dir)]


def test_install_writes_plist_file(tmp_path):
    plist_bytes = generate_brief_plist("/usr/local/bin/airflowctl")
    path = install(JOB_BRIEF, plist_bytes, launch_agents_dir=tmp_path)
    assert path == tmp_path / f"{JOB_BRIEF}.plist"
    assert path.exists()
    assert plistlib.loads(path.read_bytes())["Label"] == JOB_BRIEF


def test_uninstall_removes_plist_file(tmp_path):
    plist_bytes = generate_brief_plist("/usr/local/bin/airflowctl")
    path = install(JOB_BRIEF, plist_bytes, launch_agents_dir=tmp_path)
    assert path.exists()

    removed = uninstall(JOB_BRIEF, launch_agents_dir=tmp_path)
    assert removed is True
    assert not path.exists()


def test_uninstall_returns_false_when_not_installed(tmp_path):
    assert uninstall(JOB_BRIEF, launch_agents_dir=tmp_path) is False


def test_install_does_not_call_launchctl_on_non_macos(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(launchd, "run_guarded", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(launchd, "is_macos", lambda: False)
    install(JOB_BRIEF, generate_brief_plist("/bin/airflowctl"), launch_agents_dir=tmp_path)
    assert calls == []


def test_install_calls_launchctl_load_when_macos(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(launchd, "run_guarded", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(launchd, "is_macos", lambda: True)
    path = install(JOB_BRIEF, generate_brief_plist("/bin/airflowctl"), launch_agents_dir=tmp_path)
    assert len(calls) == 1
    assert calls[0][0] == ["launchctl", "load", str(path)]


def test_uninstall_calls_launchctl_unload_when_macos(tmp_path, monkeypatch):
    install(JOB_BRIEF, generate_brief_plist("/bin/airflowctl"), launch_agents_dir=tmp_path)

    calls = []
    monkeypatch.setattr(launchd, "run_guarded", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(launchd, "is_macos", lambda: True)
    uninstall(JOB_BRIEF, launch_agents_dir=tmp_path)
    assert len(calls) == 1
    assert calls[0][0][:2] == ["launchctl", "unload"]
