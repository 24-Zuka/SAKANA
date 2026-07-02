"""AirFlow設定・実データ格納場所の解決 — spec §4.2/§12.2。

DEVIATION: 仕様書は macOS の
`~/Library/Application Support/AirFlow/` を実パスとして前提にしている。
本実装は Linux/クロスプラットフォームの開発環境で動かすため、
既定を `~/.airflow` とし、`AIRFLOW_HOME` 環境変数で上書き可能にする。
（詳細は docs/DEVIATIONS.md を参照）

設定の優先順位（低→高）: 既定値 → `<home>/config.toml`（人手編集用の静的設定）
→ 環境変数（テスト/CI向け・最優先）。`obsidian_export_enabled` のような
CLIから書き換える真偽フラグのみ `<home>/config.json` に永続化する
（標準ライブラリにTOML書き込み機能が無いため）。
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


@dataclass(frozen=True)
class AirflowConfig:
    home: Path
    lm_studio_base_url: str = DEFAULT_LM_STUDIO_BASE_URL
    obsidian_base_url: str = DEFAULT_OBSIDIAN_BASE_URL
    obsidian_token: str = ""
    obsidian_export_enabled: bool = False
    vault_path: str = ""

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

        base_url = os.environ.get(
            "AIRFLOW_LM_STUDIO_URL", lm_studio_section.get("base_url", DEFAULT_LM_STUDIO_BASE_URL)
        )
        obsidian_base_url = os.environ.get(
            "AIRFLOW_OBSIDIAN_URL", obsidian_section.get("base_url", DEFAULT_OBSIDIAN_BASE_URL)
        )
        obsidian_token = os.environ.get("AIRFLOW_OBSIDIAN_TOKEN", obsidian_section.get("token", ""))
        vault_path = os.environ.get("AIRFLOW_VAULT_PATH", obsidian_section.get("vault_path", ""))

        obsidian_export_enabled = False
        config_json_path = home / "config.json"
        if config_json_path.exists():
            try:
                data = json.loads(config_json_path.read_text(encoding="utf-8"))
                obsidian_export_enabled = bool(data.get("obsidian_export_enabled", False))
            except (OSError, json.JSONDecodeError):
                pass

        return cls(
            home=home,
            lm_studio_base_url=base_url,
            obsidian_base_url=obsidian_base_url,
            obsidian_token=obsidian_token,
            obsidian_export_enabled=obsidian_export_enabled,
            vault_path=vault_path,
        )

    def set_obsidian_export_enabled(self, enabled: bool) -> None:
        """§9.3: Obsidian書き出しの有効/無効を永続化する（既定OFF）。"""
        data: dict = {}
        if self.config_json_path.exists():
            try:
                data = json.loads(self.config_json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        data["obsidian_export_enabled"] = enabled
        self.config_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_no_api_keys() -> list[str]:
    """P2/§8.4: 課金事故防止。APIキー環境変数を検出したら赤旗を返す（実行停止の判断は呼び出し側）。"""
    flagged = []
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            flagged.append(var)
    return flagged
