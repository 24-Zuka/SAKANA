"""AirFlow設定・実データ格納場所の解決 — spec §4.2。

DEVIATION: 仕様書は macOS の
`~/Library/Application Support/AirFlow/` を実パスとして前提にしている。
本実装は Linux/クロスプラットフォームの開発環境で動かすため、
既定を `~/.airflow` とし、`AIRFLOW_HOME` 環境変数で上書き可能にする。
（詳細は docs/DEVIATIONS.md を参照）
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOME = Path.home() / ".airflow"
DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234/v1"


@dataclass(frozen=True)
class AirflowConfig:
    home: Path
    lm_studio_base_url: str = DEFAULT_LM_STUDIO_BASE_URL

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

    def ensure_dirs(self) -> None:
        for d in (self.tickets_dir, self.briefs_dir, self.inbox_dir, self.inbox_processed_dir):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> "AirflowConfig":
        home = Path(os.environ.get("AIRFLOW_HOME", str(DEFAULT_HOME))).expanduser()
        base_url = os.environ.get("AIRFLOW_LM_STUDIO_URL", DEFAULT_LM_STUDIO_BASE_URL)
        return cls(home=home, lm_studio_base_url=base_url)


def check_no_api_keys() -> list[str]:
    """P2/§8.4: 課金事故防止。APIキー環境変数を検出したら赤旗を返す（実行停止の判断は呼び出し側）。"""
    flagged = []
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            flagged.append(var)
    return flagged
