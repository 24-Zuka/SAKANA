"""Budget Guard（利用枠ガード）— spec §5.3。

Codex/Gemini 呼び出し回数・時刻を `budget.json` に記録し、5時間ローリング
ウィンドウでの呼び出し数が閾値に近づいたら LM Studio へ自動ダウングレードする
判断材料を提供する。実残枠を取得する公式APIは無いため（§16）、これは
自前カウントによるベストエフォートの推定であり、実枠との乖離を許容する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_WINDOW_HOURS = 5.0
DEFAULT_THRESHOLDS: dict[str, int] = {"codex": 30, "gemini": 30}


@dataclass
class BudgetTracker:
    path: Path
    _calls: list[dict[str, str]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._calls = self._load()

    def _load(self) -> list[dict[str, str]]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return list(data.get("calls", []))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"calls": self._calls}, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_call(self, worker: str, *, now: datetime | None = None) -> None:
        now = now or datetime.now().astimezone()
        self._calls.append({"worker": worker, "ts": now.isoformat()})
        self._save()

    def calls_in_window(
        self, worker: str, *, window_hours: float = DEFAULT_WINDOW_HOURS, now: datetime | None = None
    ) -> int:
        now = now or datetime.now().astimezone()
        cutoff = now - timedelta(hours=window_hours)
        count = 0
        for call in self._calls:
            if call.get("worker") != worker:
                continue
            try:
                ts = datetime.fromisoformat(call["ts"])
            except ValueError:
                continue
            if ts >= cutoff:
                count += 1
        return count

    def should_downgrade(
        self,
        worker: str,
        *,
        threshold: int | None = None,
        window_hours: float = DEFAULT_WINDOW_HOURS,
        now: datetime | None = None,
    ) -> bool:
        threshold = threshold if threshold is not None else DEFAULT_THRESHOLDS.get(worker, 30)
        return self.calls_in_window(worker, window_hours=window_hours, now=now) >= threshold
