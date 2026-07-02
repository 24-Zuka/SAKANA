"""秘密情報の保管 — spec §8.4。

macOSでは `security` コマンド（Keychain）経由でのみ保存し、画面・ログ・
設定ファイルへ平文を出さない。非macOS環境ではKeychainが無いため、
`<home>/secrets.json`（パーミッション0600）へ縮退する（P7: 静かに壊れない）。
この縮退経路は明示的に「平文保存」であることをdocs/DEVIATIONS.mdに明記する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .guard import GuardBlocked, run_guarded

SERVICE_NAME = "AirFlow"


def is_macos() -> bool:
    return sys.platform == "darwin"


class SecretStoreError(Exception):
    pass


def _fallback_path(home: Path) -> Path:
    return home / "secrets.json"


def _fallback_set(home: Path, account: str, value: str) -> None:
    path = _fallback_path(home)
    data: dict[str, str] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    data[account] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    path.chmod(0o600)


def _fallback_get(home: Path, account: str) -> str | None:
    path = _fallback_path(home)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get(account)


def set_secret(account: str, value: str, *, home: Path) -> None:
    """秘密情報を保存する。macOSではKeychain、それ以外は平文フォールバック。"""
    if is_macos():
        try:
            run_guarded(
                ["security", "add-generic-password", "-a", account, "-s", SERVICE_NAME, "-w", value, "-U"],
                capture_output=True,
                text=True,
            )
            return
        except GuardBlocked as exc:
            raise SecretStoreError(f"security コマンドが遮断されました: {exc}") from exc
    _fallback_set(home, account, value)


def get_secret(account: str, *, home: Path) -> str | None:
    """秘密情報を取得する。見つからない場合は None。"""
    if is_macos():
        try:
            result = run_guarded(
                ["security", "find-generic-password", "-a", account, "-s", SERVICE_NAME, "-w"],
                capture_output=True,
                text=True,
            )
        except GuardBlocked as exc:
            raise SecretStoreError(f"security コマンドが遮断されました: {exc}") from exc
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    return _fallback_get(home, account)
