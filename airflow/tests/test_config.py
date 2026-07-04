import json

import pytest

from airflow.config import AirflowConfig, DEFAULT_LM_STUDIO_BASE_URL, DEFAULT_OBSIDIAN_BASE_URL


def _clear_env(monkeypatch):
    for var in (
        "AIRFLOW_HOME",
        "AIRFLOW_LM_STUDIO_URL",
        "AIRFLOW_OBSIDIAN_URL",
        "AIRFLOW_OBSIDIAN_TOKEN",
        "AIRFLOW_VAULT_PATH",
    ):
        monkeypatch.delenv(var, raising=False)


def test_load_uses_defaults_when_nothing_configured(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    config = AirflowConfig.load()
    assert config.lm_studio_base_url == DEFAULT_LM_STUDIO_BASE_URL
    assert config.obsidian_base_url == DEFAULT_OBSIDIAN_BASE_URL
    assert config.vault_path == ""
    assert config.obsidian_export_enabled is False


def test_config_toml_overrides_defaults(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text(
        """
[lm_studio]
base_url = "http://localhost:9999/v1"

[obsidian]
base_url = "http://127.0.0.1:9998"
token = "toml-token"
vault_path = "/path/to/vault"
""",
        encoding="utf-8",
    )
    config = AirflowConfig.load()
    assert config.lm_studio_base_url == "http://localhost:9999/v1"
    assert config.obsidian_base_url == "http://127.0.0.1:9998"
    assert config.obsidian_token == "toml-token"
    assert config.vault_path == "/path/to/vault"


def test_env_var_overrides_config_toml(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text(
        '[lm_studio]\nbase_url = "http://from-toml:1234/v1"\n', encoding="utf-8"
    )
    monkeypatch.setenv("AIRFLOW_LM_STUDIO_URL", "http://from-env:1234/v1")
    config = AirflowConfig.load()
    assert config.lm_studio_base_url == "http://from-env:1234/v1"


def test_malformed_config_toml_is_ignored_gracefully(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text("this is not [valid toml", encoding="utf-8")
    config = AirflowConfig.load()  # must not raise
    assert config.lm_studio_base_url == DEFAULT_LM_STUDIO_BASE_URL


def test_set_obsidian_export_enabled_persists_and_is_independent_of_toml(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    config = AirflowConfig.load()
    config.set_obsidian_export_enabled(True)

    reloaded = AirflowConfig.load()
    assert reloaded.obsidian_export_enabled is True

    data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert data["obsidian_export_enabled"] is True


def test_set_obsidian_export_enabled_preserves_other_json_keys(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    (tmp_path / "config.json").write_text(json.dumps({"some_other_key": "value"}), encoding="utf-8")

    config = AirflowConfig.load()
    config.set_obsidian_export_enabled(True)

    data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert data["some_other_key"] == "value"
    assert data["obsidian_export_enabled"] is True


def test_update_settings_persists_and_is_visible_on_reload(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    config = AirflowConfig.load()
    updated = config.update_settings(lm_studio_base_url="http://updated:1234/v1", vault_path="/new/vault")

    assert updated.lm_studio_base_url == "http://updated:1234/v1"
    assert updated.vault_path == "/new/vault"

    reloaded = AirflowConfig.load()
    assert reloaded.lm_studio_base_url == "http://updated:1234/v1"
    assert reloaded.vault_path == "/new/vault"


def test_update_settings_env_var_still_wins_over_json(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    config = AirflowConfig.load()
    config.update_settings(lm_studio_base_url="http://from-json:1234/v1")

    monkeypatch.setenv("AIRFLOW_LM_STUDIO_URL", "http://from-env:1234/v1")
    reloaded = AirflowConfig.load()
    assert reloaded.lm_studio_base_url == "http://from-env:1234/v1"
