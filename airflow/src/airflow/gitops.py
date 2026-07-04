"""Build画面が使う実git操作 — worktree一覧/作成・Diff・マージ — spec §7.2。

すべて `guard.run_guarded` 経由（allowlistの"git"）で実行する。対象は
`devrepo.ensure_demo_repo()` が用意する隔離サンドボックスのみ。
"""

from __future__ import annotations

import re
from pathlib import Path

from .guard import run_guarded


def _run_git(cwd: Path, args: list[str]):
    return run_guarded(["git", *args], cwd=cwd, capture_output=True, text=True)


def list_worktrees(repo_path: Path) -> list[dict]:
    """`git worktree list --porcelain` をパースする。"""
    result = _run_git(repo_path, ["worktree", "list", "--porcelain"])
    entries: list[dict] = []
    current: dict = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"path": line.split(" ", 1)[1], "branch": "main"}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line == "bare":
            continue
    if current:
        entries.append(current)
    return entries


def sanitize_branch_name(branch: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_./-]", "-", branch.strip()) or "unnamed"


def create_worktree(repo_path: Path, branch: str) -> dict:
    """新しいブランチ＋worktreeを作成する。"""
    safe_branch = sanitize_branch_name(branch)
    dir_name = safe_branch.replace("/", "-")
    worktree_path = repo_path / ".worktrees" / dir_name
    _run_git(repo_path, ["worktree", "add", "-b", safe_branch, str(worktree_path)])
    return {"branch": safe_branch, "path": str(worktree_path)}


def diff_files(worktree_path: Path, *, against: str = "HEAD") -> list[dict]:
    """作業ツリーの差分をファイル単位に分割して返す。差分が無ければ空リスト。"""
    result = _run_git(worktree_path, ["diff", against])
    text = result.stdout
    if not text.strip():
        return []

    files: list[dict] = []
    current_path: str | None = None
    current_lines: list[str] = []
    header_re = re.compile(r"^diff --git a/(.+) b/(.+)$")

    for line in text.splitlines():
        match = header_re.match(line)
        if match:
            if current_path is not None:
                files.append({"path": current_path, "patch": "\n".join(current_lines)})
            current_path = match.group(2)
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_path is not None:
        files.append({"path": current_path, "patch": "\n".join(current_lines)})
    return files


def status(worktree_path: Path) -> str:
    """`git status` の生出力を返す（Build画面のログ代替に使う・§7.2）。"""
    result = _run_git(worktree_path, ["status"])
    return result.stdout


def commit_all(worktree_path: Path, message: str) -> bool:
    """作業ツリーの変更を全てコミットする。変更が無ければFalseを返す。"""
    status = _run_git(worktree_path, ["status", "--porcelain"])
    if not status.stdout.strip():
        return False
    _run_git(worktree_path, ["add", "-A"])
    _run_git(worktree_path, ["commit", "-m", message])
    return True


def merge_branch(repo_path: Path, branch: str, *, into: str = "main") -> None:
    """隔離サンドボックス内でのローカルマージ（リモート無し・pushは行わない）。"""
    safe_branch = sanitize_branch_name(branch)
    _run_git(repo_path, ["merge", "--no-ff", "-m", f"Merge {safe_branch} into {into}", safe_branch])


def remove_worktree(repo_path: Path, worktree_path: Path) -> None:
    _run_git(repo_path, ["worktree", "remove", "--force", str(worktree_path)])
