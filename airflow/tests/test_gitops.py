from airflow.devrepo import ensure_demo_repo
from airflow.gitops import (
    commit_all,
    create_worktree,
    diff_files,
    list_worktrees,
    merge_branch,
    sanitize_branch_name,
)


def test_sanitize_branch_name_replaces_unsafe_characters():
    assert sanitize_branch_name("feature/my task!") == "feature/my-task-"
    assert sanitize_branch_name("  ") == "unnamed"


def test_list_worktrees_shows_main_checkout(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    worktrees = list_worktrees(repo)
    assert len(worktrees) == 1
    assert worktrees[0]["branch"] == "main"


def test_create_worktree_adds_new_branch_and_directory(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/my-change")

    assert result["branch"] == "feature/my-change"
    from pathlib import Path

    assert Path(result["path"]).exists()

    worktrees = list_worktrees(repo)
    assert len(worktrees) == 2
    branches = {w["branch"] for w in worktrees}
    assert "feature/my-change" in branches


def test_diff_files_empty_when_no_changes(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/x")
    from pathlib import Path

    assert diff_files(Path(result["path"])) == []


def test_diff_files_reports_new_content(tmp_path):
    from pathlib import Path

    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/x")
    worktree_path = Path(result["path"])
    (worktree_path / "hello.txt").write_text("hello world\n", encoding="utf-8")

    # git diff HEAD で untracked ファイルも検出するには add が必要（git diffの仕様）
    import subprocess

    subprocess.run(["git", "-C", str(worktree_path), "add", "hello.txt"], check=True)
    files = diff_files(worktree_path, against="--cached")
    assert len(files) == 1
    assert files[0]["path"] == "hello.txt"
    assert "hello world" in files[0]["patch"]


def test_commit_all_commits_changes_and_reports_true(tmp_path):
    from pathlib import Path

    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/x")
    worktree_path = Path(result["path"])
    (worktree_path / "hello.txt").write_text("hello world\n", encoding="utf-8")

    committed = commit_all(worktree_path, "add hello.txt")
    assert committed is True
    assert diff_files(worktree_path) == []  # コミット後は差分無し


def test_commit_all_returns_false_when_nothing_to_commit(tmp_path):
    from pathlib import Path

    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/x")
    assert commit_all(Path(result["path"]), "noop") is False


def test_merge_branch_merges_into_main(tmp_path):
    from pathlib import Path

    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    result = create_worktree(repo, "feature/x")
    worktree_path = Path(result["path"])
    (worktree_path / "hello.txt").write_text("hello world\n", encoding="utf-8")
    commit_all(worktree_path, "add hello.txt")

    merge_branch(repo, "feature/x")
    assert (repo / "hello.txt").exists()
