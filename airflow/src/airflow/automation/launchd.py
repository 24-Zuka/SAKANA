"""launchd 自動化 — spec §10。

`com.local.AirFlow.brief`（毎朝の朝礼）/ `com.local.AirFlow.grooming`（夜間
グルーミング）/ `com.local.AirFlow.inbox`（Inboxファイル監視）の plist 生成と、
ユーザー領域（`~/Library/LaunchAgents/`）への登録・解除を行う。

launchd は macOS 専用機能のため、非darwin環境では plist ファイルの生成のみ
行い、`launchctl load/unload` の実行は行わない（正直に「未対応」と扱う）。
plist生成はプラットフォームに依存しないため、この環境でも検証できる。
"""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

from ..guard import run_guarded

JOB_BRIEF = "com.local.AirFlow.brief"
JOB_GROOMING = "com.local.AirFlow.grooming"
JOB_INBOX = "com.local.AirFlow.inbox"

DEFAULT_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
DEFAULT_LOG_DIR = Path.home() / "Library" / "Logs"


def is_macos() -> bool:
    return sys.platform == "darwin"


def default_launch_agents_dir() -> Path:
    """`AIRFLOW_LAUNCH_AGENTS_DIR` でテスト/開発用に上書き可能にする（既定は実際のmacOSパス）。"""
    override = os.environ.get("AIRFLOW_LAUNCH_AGENTS_DIR")
    return Path(override) if override else DEFAULT_LAUNCH_AGENTS_DIR


def _plist_dict(
    label: str,
    program_args: list[str],
    *,
    calendar_interval: dict[str, int] | None = None,
    watch_paths: list[str] | None = None,
) -> dict:
    plist: dict = {
        "Label": label,
        "ProgramArguments": program_args,
        "RunAtLoad": False,
        "StandardOutPath": str(DEFAULT_LOG_DIR / f"{label}.log"),
        "StandardErrorPath": str(DEFAULT_LOG_DIR / f"{label}.err.log"),
    }
    if calendar_interval is not None:
        plist["StartCalendarInterval"] = calendar_interval
    if watch_paths is not None:
        plist["WatchPaths"] = watch_paths
    return plist


def generate_brief_plist(airflowctl_bin: str, *, hour: int = 7, minute: int = 30) -> bytes:
    """毎朝の朝礼レポート生成ジョブ（§10: 例7:30）。"""
    plist = _plist_dict(
        JOB_BRIEF,
        [airflowctl_bin, "brief"],
        calendar_interval={"Hour": hour, "Minute": minute},
    )
    return plistlib.dumps(plist)


def generate_grooming_plist(airflowctl_bin: str, *, hour: int = 23, minute: int = 0) -> bytes:
    """夜間グルーミングジョブ（§10: 例23:00）。"""
    plist = _plist_dict(
        JOB_GROOMING,
        [airflowctl_bin, "groom"],
        calendar_interval={"Hour": hour, "Minute": minute},
    )
    return plistlib.dumps(plist)


def generate_inbox_plist(airflowctl_bin: str, inbox_dir: Path) -> bytes:
    """Inboxファイル監視ジョブ（§10: WatchPathsによる常時監視）。"""
    plist = _plist_dict(
        JOB_INBOX,
        [airflowctl_bin, "import-inbox", "--once"],
        watch_paths=[str(inbox_dir)],
    )
    return plistlib.dumps(plist)


def install(label: str, plist_bytes: bytes, *, launch_agents_dir: Path | None = None) -> Path:
    """plistを書き出す。darwinの場合のみ `launchctl load` を実行する。"""
    target_dir = launch_agents_dir or default_launch_agents_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{label}.plist"
    path.write_bytes(plist_bytes)
    if is_macos():
        run_guarded(["launchctl", "load", str(path)], capture_output=True, text=True)
    return path


def uninstall(label: str, *, launch_agents_dir: Path | None = None) -> bool:
    """plistを削除する。darwinの場合のみ事前に `launchctl unload` を実行する。"""
    target_dir = launch_agents_dir or default_launch_agents_dir()
    path = target_dir / f"{label}.plist"
    if not path.exists():
        return False
    if is_macos():
        run_guarded(["launchctl", "unload", str(path)], capture_output=True, text=True)
    path.unlink()
    return True
