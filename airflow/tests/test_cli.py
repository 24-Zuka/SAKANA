from click.testing import CliRunner

from airflow.cli import main


def _runner_env(tmp_path):
    return {"AIRFLOW_HOME": str(tmp_path / "home")}


def test_status_on_empty_store(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["status"], env=_runner_env(tmp_path))
    assert result.exit_code == 0
    assert "合計チケット数: 0" in result.output


def test_add_creates_ticket_then_list_shows_it(tmp_path):
    runner = CliRunner()
    env = _runner_env(tmp_path)

    add_result = runner.invoke(main, ["add", "A社との提携レート再交渉の方針を決めたい"], env=env)
    assert add_result.exit_code == 0
    assert "起票しました" in add_result.output

    list_result = runner.invoke(main, ["list"], env=env)
    assert list_result.exit_code == 0
    assert "A社との提携レート再交渉の方針を決めたい" in list_result.output

    status_result = runner.invoke(main, ["status"], env=env)
    assert "合計チケット数: 1" in status_result.output


def test_brief_generates_file(tmp_path):
    runner = CliRunner()
    env = _runner_env(tmp_path)
    runner.invoke(main, ["add", "A社との提携レート再交渉の方針を決めたい"], env=env)

    result = runner.invoke(main, ["brief", "--show"], env=env)
    assert result.exit_code == 0
    assert "朝礼を生成しました" in result.output
    assert "今日の要判断" in result.output


def test_import_inbox_moves_files_to_processed(tmp_path):
    runner = CliRunner()
    env = _runner_env(tmp_path)
    home = tmp_path / "home"
    inbox = home / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "task1.txt").write_text("バグを至急修正してデプロイする", encoding="utf-8")

    result = runner.invoke(main, ["import-inbox", "--once"], env=env)
    assert result.exit_code == 0
    assert "1 件のファイルを取り込みました" in result.output
    assert not (inbox / "task1.txt").exists()
    assert (inbox / "processed" / "task1.txt").exists()


def test_list_filters_by_status_and_category(tmp_path):
    runner = CliRunner()
    env = _runner_env(tmp_path)
    runner.invoke(main, ["add", "動画のサムネイル案を3パターン作る"], env=env)
    runner.invoke(main, ["add", "A社との提携レート再交渉の方針を決めたい"], env=env)

    result = runner.invoke(main, ["list", "--category", "Content"], env=env)
    assert "サムネイル" in result.output
    assert "A社" not in result.output


def test_stub_commands_do_not_crash(tmp_path):
    runner = CliRunner()
    env = _runner_env(tmp_path)
    for args in (["install-launchd"], ["uninstall-launchd"], ["configure-obsidian", "--enable"]):
        result = runner.invoke(main, args, env=env)
        assert result.exit_code == 0
        assert "未対応" in result.output or "未実装" in result.output


def test_red_flag_when_api_key_env_present(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    runner = CliRunner()
    env = _runner_env(tmp_path)
    env["OPENAI_API_KEY"] = "sk-fake"
    result = runner.invoke(main, ["status"], env=env)
    assert "赤旗" in result.output
