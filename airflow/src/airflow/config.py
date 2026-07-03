"""AirFlow設定・実データ格納場所の解決 — spec §4.2/§12.2。

DEVIATION: 仕様書は macOS の
`~/Library/Application Support/AirFlow/` を実パスとして前提にしている。
本実装は Linux/クロスプラットフォームの開発環境で動かすため、
既定を `~/.airflow` とし、`AIRFLOW_HOME` 環境変数で上書き可能にする。
（詳細は docs/DEVIATIONS.md を参照）

設定の優先順位（低→高）:
  既定値 → `<home>/config.toml`（人手編集用の静的設定）
  → `<home>/config.json`（GUI/CLIから書き換える動的設定・永続化）
  → 環境変数（テスト/CI向け・最優先）。
標準ライブラリにTOML書き込み機能が無いため、実行時に変更する設定は
config.json に保存する。
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOME = Path.home() / ".airflow"
DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_OBSIDIAN_BASE_URL = "http://127.0.0.1:27123"


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@dataclass(frozen=True)
class AirflowConfig:
    home: Path
    lm_studio_base_url: str = DEFAULT_LM_STUDIO_BASE_URL
    obsidian_base_url: str = DEFAULT_OBSIDIAN_BASE_URL
    obsidian_token: str = ""
    obsidian_export_enabled: bool = False
    vault_path: str = ""
    bridge_token: str = ""
    demo_repo_path: Path | None = None

    @property
    def tickets_dir(self) -> Path:
        return self.home / "tickets"

    @property
    def briefs_dir(self) -> Path:
        return self.home / "briefs"

    @property
    def inbox_dir(self) -> Path:
        return self.home / "inbox"

    @property
    def inbox_processed_dir(self) -> Path:
        return self.inbox_dir / "processed"

    @property
    def config_toml_path(self) -> Path:
        return self.home / "config.toml"

    @property
    def config_json_path(self) -> Path:
        return self.home / "config.json"

    def ensure_dirs(self) -> None:
        for d in (self.tickets_dir, self.briefs_dir, self.inbox_dir, self.inbox_processed_dir):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> "AirflowConfig":
        home = Path(os.environ.get("AIRFLOW_HOME", str(DEFAULT_HOME))).expanduser()

        toml_data = _load_toml(home / "config.toml")
        lm_studio_section = toml_data.get("lm_studio", {}) if isinstance(toml_data, dict) else {}
        obsidian_section = toml_data.get("obsidian", {}) if isinstance(toml_data, dict) else {}
        bridge_section = toml_data.get("bridge", {}) if isinstance(toml_data, dict) else {}

        base_url = lm_studio_section.get("base_url", DEFAULT_LM_STUDIO_BASE_URL)
        obsidian_base_url = obsidian_section.get("base_url", DEFAULT_OBSIDIAN_BASE_URL)
        obsidian_token = obsidian_section.get("token", "")
        vault_path = obsidian_section.get("vault_path", "")
        bridge_token = bridge_section.get("token", "")
        obsidian_export_enabled = False

        json_data = _load_json(home / "config.json")
        obsidian_export_enabled = bool(json_data.get("obsidian_export_enabled", obsidian_export_enabled))
        base_url = json_data.get("lm_studio_base_url", base_url)
        vault_path = json_data.get("vault_path", vault_path)
        obsidian_base_url = json_data.get("obsidian_base_url", obsidian_base_url)

        base_url = os.environ.get("AIRFLOW_LM_STUDIO_URL", base_url)
        obsidian_base_url = os.environ.get("AIRFLOW_OBSIDIAN_URL", obsidian_base_url)
        obsidian_token = os.environ.get("AIRFLOW_OBSIDIAN_TOKEN", obsidian_token)
        vault_path = os.environ.get("AIRFLOW_VAULT_PATH", vault_path)
        bridge_token = os.environ.get("AIRFLOW_BRIDGE_TOKEN", bridge_token)

        return cls(
            home=home,
            lm_studio_base_url=base_url,
            obsidian_base_url=obsidian_base_url,
            obsidian_token=obsidian_token,
            obsidian_export_enabled=obsidian_export_enabled,
            vault_path=vault_path,
            bridge_token=bridge_token,
            demo_repo_path=home / "workspace" / "demo-repo",
        )

    def _update_json(self, **kwargs) -> None:
        data = _load_json(self.config_json_path)
        data.update(kwargs)
        self.config_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_obsidian_export_enabled(self, enabled: bool) -> None:
        """§9.3: Obsidian書き出しの有効/無効を永続化する（既定OFF）。"""
        self._update_json(obsidian_export_enabled=enabled)

    def update_settings(
        self,
        *,
        lm_studio_base_url: str | None = None,
        vault_path: str | None = None,
        obsidian_base_url: str | None = None,
    ) -> "AirflowConfig":
        """Settings画面からの動的設定変更を永続化し、再読込した設定を返す。"""
        updates = {}
        if lm_studio_base_url is not None:
            updates["lm_studio_base_url"] = lm_studio_base_url
        if vault_path is not None:
            updates["vault_path"] = vault_path
        if obsidian_base_url is not None:
            updates["obsidian_base_url"] = obsidian_base_url
        if updates:
            self._update_json(**updates)
        return AirflowConfig.load()


def check_no_api_keys() -> list[str]:
    """P2/§8.4: 課金事故防止。APIキー環境変数を検出したら赤旗を返す（実行停止の判断は呼び出し側）。"""
    flagged = []
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            flagged.append(var)
    return flagged
