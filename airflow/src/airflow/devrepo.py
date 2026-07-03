"""Build画面用の隔離デモrepo。

**このSAKANAリポジトリ自体には一切触れない。** Build画面のworktree作成・
ビルド・レビュー・Diff・マージは、`<AIRFLOW_HOME>/workspace/demo-repo/` に
自動初期化される専用のサンドボックスgitリポジトリに対してのみ実行される。
リモートを持たないため、このリポジトリ内でのマージ操作が外部に影響することは無い。
"""

from __future__ import annotations

from pathlib import Path

from .guard import run_guarded


def ensure_demo_repo(path: Path) -> Path:
    """デモ用リポジトリが存在しなければ初期化する（冪等）。"""
    path.mkdir(parents=True, exist_ok=True)
    if (path / ".git").exists():
        return path

    run_guarded(["git", "init", "-b", "main"], cwd=path, capture_output=True, text=True)
    run_guarded(["git", "config", "user.email", "airflow-demo@example.com"], cwd=path, capture_output=True, text=True)
    run_guarded(["git", "config", "user.name", "AirFlow Demo"], cwd=path, capture_output=True, text=True)

    readme = path / "README.md"
    readme.write_text(
        "# AirFlow Demo Repo\n\n"
        "JARVIS Cockpit の Build 画面が操作する隔離されたサンドボックスです。\n"
        "実際のプロジェクトリポジトリではありません。リモートは存在しません。\n",
        encoding="utf-8",
    )
    run_guarded(["git", "add", "README.md"], cwd=path, capture_output=True, text=True)
    run_guarded(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return path
