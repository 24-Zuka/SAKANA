"""dcg（Destructive Command Guard）Python統合 — spec §8.2。

エンジン/ブリッジが起動する全subprocessは、この`run_guarded()`を必ず経由する。
コンパイル済みの`dcg`バイナリ（`AIRFLOW_DCG_BIN`環境変数 or PATH）があればそれを
前段の判定に使い、無ければ同一ルールを内蔵実装で判定する（P7: 静かに壊れない）。

dcgの守備範囲の限界: 直接起動するプロセスのみを遮断できる。`codex exec`の内側で
Codex自身が発行するコマンドはこの改札を通らないため、Tier3実行はCodex側の
sandbox/approval設定と併用する二重防御とする。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ALLOWLIST = {"codex", "gemini", "git", "launchctl", "security"}

TRIGGER_TOKENS = {"rm", "reset", "push", "dd", "mkfs", "fdisk"}


@dataclass
class Blocked:
    rule_id: str
    reason: str
    suggestion: str


class GuardBlocked(Exception):
    def __init__(self, blocked: Blocked) -> None:
        self.blocked = blocked
        super().__init__(f"blocked by rule {blocked.rule_id}: {blocked.reason}")


class CommandNotAllowlisted(Exception):
    pass


def _quick_reject_passes(argv: list[str]) -> bool:
    return not any(tok in TRIGGER_TOKENS or tok.startswith("mkfs") for tok in argv)


def _has_flag(argv: list[str], *flags: str) -> bool:
    return any(a in flags for a in argv)


def _contains_rf_flag(argv: list[str]) -> bool:
    return any(a in ("-rf", "-fr") for a in argv) or (
        any(a in ("-r", "-R", "--recursive") for a in argv) and _has_flag(argv, "--force", "-f")
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _check_rm(argv: list[str], workspace_root: Path) -> Blocked | None:
    if not argv or argv[0] != "rm":
        return None
    if not _contains_rf_flag(argv):
        return None

    tmp_root = workspace_root / "tmp"
    targets = [a for a in argv[1:] if not a.startswith("-")]

    if not targets:
        return Blocked(
            "core.filesystem",
            "rm -rf に削除対象が指定されていません（危険なため遮断）。",
            f"{tmp_root} 配下のパスを明示的に指定してください。",
        )

    def resolved(t: str) -> Path:
        p = Path(t)
        return p if p.is_absolute() else workspace_root / p

    all_within_tmp = all(_is_relative_to(resolved(t), tmp_root) for t in targets)
    if all_within_tmp:
        return None
    return Blocked(
        "core.filesystem",
        "システムルート/管理外への rm -rf は遮断されます。",
        f"{tmp_root} 配下のみ削除が許可されています。",
    )


def _check_git_reset_hard(argv: list[str]) -> Blocked | None:
    if not argv or argv[0] != "git":
        return None
    if "reset" in argv and "--hard" in argv:
        return Blocked(
            "core.git",
            "git reset --hard は未コミット変更を失うリスクがあります。",
            "git stash を使い、変更を退避してください。",
        )
    return None


def _check_git_force_push(argv: list[str]) -> Blocked | None:
    if not argv or argv[0] != "git":
        return None
    if "push" not in argv or not _has_flag(argv, "--force", "-f"):
        return None

    targets_protected = any(
        a in ("main", "master") or a.endswith((":main", ":master", "/main", "/master"))
        for a in argv
    )

    try:
        push_index = argv.index("push")
    except ValueError:
        push_index = -1
    remaining = argv[push_index + 1 :] if push_index >= 0 else []
    has_explicit_non_main_target = any(
        not a.startswith("-") and a not in ("main", "master") for a in remaining
    )

    if targets_protected or not has_explicit_non_main_target:
        return Blocked(
            "core.git:force-push",
            "main/master への git push --force は強制上書きのリスクがあります。",
            "--force-with-lease への置き換えを検討してください。",
        )
    return None


def _check_disk_tools(argv: list[str]) -> Blocked | None:
    cmd = argv[0] if argv else ""
    if cmd in ("dd", "fdisk") or cmd.startswith("mkfs"):
        return Blocked(
            "system.disk",
            f"{cmd} は物理デバイスを対象にしうるため実行できません。",
            "代替手段はありません（ハードブロック）。",
        )
    return None


def evaluate_builtin(argv: list[str], workspace_root: Path) -> Blocked | None:
    """内蔵ルールでの判定（dcgバイナリが無い場合のフォールバック）。"""
    if not argv:
        return None
    if _quick_reject_passes(argv):
        return None
    return (
        _check_disk_tools(argv)
        or _check_rm(argv, workspace_root)
        or _check_git_reset_hard(argv)
        or _check_git_force_push(argv)
    )


def _find_dcg_binary() -> str | None:
    explicit = os.environ.get("AIRFLOW_DCG_BIN")
    if explicit and Path(explicit).exists():
        return explicit
    return shutil.which("dcg")


_KNOWN_RULE_IDS = (
    "core.git:force-push",
    "core.git",
    "core.filesystem",
    "system.disk",
)


def _extract_rule_id(reason_line: str) -> str:
    for rule_id in _KNOWN_RULE_IDS:
        if f"rule {rule_id}:" in reason_line:
            return rule_id
    return "unknown"


def check(argv: list[str], *, workspace_root: Path | None = None) -> None:
    """遮断対象なら GuardBlocked を送出する。dcgバイナリがあればそれを使う。"""
    workspace_root = workspace_root or Path.cwd()
    dcg_bin = _find_dcg_binary()

    if dcg_bin:
        env = {**os.environ, "WORKSPACE_ROOT": str(workspace_root)}
        result = subprocess.run(
            [dcg_bin, "--", *argv],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 2:
            reason_line = next(
                (line for line in result.stderr.splitlines() if "blocked by rule" in line), ""
            )
            suggestion_line = next(
                (line for line in result.stderr.splitlines() if "suggestion:" in line), ""
            )
            rule_id = _extract_rule_id(reason_line)
            raise GuardBlocked(
                Blocked(rule_id, reason_line, suggestion_line.split("suggestion:")[-1].strip())
            )
        return

    blocked = evaluate_builtin(argv, workspace_root)
    if blocked:
        raise GuardBlocked(blocked)


def run_guarded(
    argv: list[str],
    *,
    workspace_root: Path | None = None,
    **subprocess_kwargs,
) -> subprocess.CompletedProcess:
    """allowlist確認 → dcg/内蔵ルールでcheck() → 通過したらsubprocess実行。"""
    if not argv:
        raise ValueError("argv must not be empty")
    if argv[0] not in ALLOWLIST:
        raise CommandNotAllowlisted(f"{argv[0]!r} is not in the allowlist {ALLOWLIST}")

    check(argv, workspace_root=workspace_root)
    return subprocess.run(argv, **subprocess_kwargs)
