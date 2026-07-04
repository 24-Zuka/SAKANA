import subprocess

from airflow.devrepo import ensure_demo_repo


def test_ensure_demo_repo_initializes_git_repo(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    assert (repo / ".git").exists()
    assert (repo / "README.md").exists()

    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
    )
    assert "Initial commit" in log.stdout


def test_ensure_demo_repo_is_idempotent(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    first_log = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
    ).stdout

    ensure_demo_repo(repo)
    second_log = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
    ).stdout
    assert first_log == second_log


def test_ensure_demo_repo_default_branch_is_main(tmp_path):
    repo = tmp_path / "demo-repo"
    ensure_demo_repo(repo)
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()
    assert branch == "main"
