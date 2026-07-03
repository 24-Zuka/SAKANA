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
import shutil
import sys
from datetime import datetime
from pathlib import Path

from ..guard import run_guarded

JOB_BRIEF = "com.local.AirFlow.brief"
JOB_GROOMING = "com.local.AirFlow.grooming"
JOB_INBOX = "com.local.AirFlow.inbox"

JOB_SCHEDULES: dict[str, str] = {
    JOB_BRIEF: "毎朝 07:30",
    JOB_GROOMING: "毎晩 23:00",
    JOB_INBOX: "ファイル変更時（WatchPaths）",
}

DEFAULT_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
DEFAULT_LOG_DIR = Path.home() / "Library" / "Logs"


def is_macos() -> bool:
    return sys.platform == "darwin"


def default_launch_agents_dir() -> Path:
    """`AIRFLOW_LAUNCH_AGENTS_DIR` でテスト/開発用に上書き可能にする（既定は実際のmacOSパス）。"""
    override = os.environ.get("AIRFLOW_LAUNCH_AGENTS_DIR")
    return Path(override) if override else DEFAULT_LAUNCH_AGENTS_DIR


def default_log_dir() -> Path:
    """`AIRFLOW_LOG_DIR` でテスト/開発用に上書き可能にする（既定は実際のmacOSパス）。

    実機のlaunchdはplistの`StandardOutPath`へジョブ出力を書くが、ブリッジ経由の
    手動実行（`/launchd/{id}/run`）でも同じログファイルへ追記することで、
    最終実行時刻・末尾ログをmacOS実機/この開発環境の双方で一貫して確認できる。
    """
    override = os.environ.get("AIRFLOW_LOG_DIR")
    return Path(override) if override else DEFAULT_LOG_DIR


def resolve_airflowctl_bin() -> str:
    return shutil.which("airflowctl") or str(Path(sys.executable).parent / "airflowctl")


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
        "StandardOutPath": str(default_log_dir() / f"{label}.log"),
        "StandardErrorPath": str(default_log_dir() / f"{label}.err.log"),
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


def _disabled_path(target_dir: Path, label: str) -> Path:
    return target_dir / f"{label}.plist.disabled"


def list_jobs(*, launch_agents_dir: Path | None = None) -> list[dict]:
    """Cockpit の Schedule 画面向けに3ジョブの現況を返す（未登録でも一覧には出す）。"""
    target_dir = launch_agents_dir or default_launch_agents_dir()
    jobs = []
    for label, schedule in JOB_SCHEDULES.items():
        plist_path = target_dir / f"{label}.plist"
        log_path = default_log_dir() / f"{label}.log"
        last_run_at = None
        last_log_tail = ""
        if log_path.exists():
            try:
                stat = log_path.stat()
                last_run_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                last_log_tail = "\n".join(lines[-20:])
            except OSError:
                pass
        jobs.append(
            {
                "id": label,
                "label": label,
                "schedule": schedule,
                "enabled": plist_path.exists(),
                "lastRunAt": last_run_at,
                "lastLogTail": last_log_tail,
            }
        )
    return jobs


def set_enabled(label: str, enabled: bool, *, launch_agents_dir: Path | None = None) -> None:
    """既に登録済みのジョブをplist名の付け替えで有効/無効切替する（darwinではlaunchctlも連動）。"""
    target_dir = launch_agents_dir or default_launch_agents_dir()
    plist_path = target_dir / f"{label}.plist"
    disabled_path = _disabled_path(target_dir, label)
    if enabled:
        if disabled_path.exists() and not plist_path.exists():
            disabled_path.rename(plist_path)
            if is_macos():
                run_guarded(["launchctl", "load", str(plist_path)], capture_output=True, text=True)
    else:
        if plist_path.exists():
            if is_macos():
                run_guarded(["launchctl", "unload", str(plist_path)], capture_output=True, text=True)
            plist_path.rename(disabled_path)


def append_job_log(label: str, text: str, *, now: datetime | None = None) -> None:
    """ブリッジ経由の手動実行結果を、実機launchdと同じログファイルへ追記する。"""
    log_dir = default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now().astimezone()
    with (log_dir / f"{label}.log").open("a", encoding="utf-8") as f:
        f.write(f"[{now.isoformat(timespec='seconds')}] {text}\n")
