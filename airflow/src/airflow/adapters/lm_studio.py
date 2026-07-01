"""LM Studio アダプタ（常用・無料）— spec §6.2。

`http://localhost:1234/v1`（OpenAI互換API）へHTTP。分類・要約・整形・
検証など定常処理を寄せる先。認証不要・完全無料・無制限。
疎通不可・タイムアウト時は `AdapterUnavailable` を送出し、呼び出し側
（orchestrator.classify）でローカル規則へフォールバックする。
"""

from __future__ import annotations

import json

import httpx

from ..models import Category
from .base import AdapterUnavailable, ClassificationResult

DEFAULT_TIMEOUT = 60.0  # §6.5: ローカル 60s

CLASSIFY_SYSTEM_PROMPT = (
    "あなたはタスク分類器です。与えられた日本語テキストを読み、"
    "category(Business|Engineering|Content), priority(1|2|3), "
    "decision_required(true|false), involves_external_send(true|false), "
    "involves_irreversible_action(true|false) をJSONで1行で返してください。"
    "他の説明は一切出力しないでください。"
)


class LMStudioAdapter:
    worker = "lmstudio"

    def __init__(self, base_url: str, *, timeout: float = DEFAULT_TIMEOUT, model: str = "local-model") -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.model = model

    def classify(self, text: str) -> ClassificationResult:
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise AdapterUnavailable(f"LM Studio unreachable: {exc}") from exc

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return ClassificationResult(
                category=Category(parsed["category"]),
                priority=int(parsed["priority"]),
                decision_required=bool(parsed["decision_required"]),
                involves_external_send=bool(parsed["involves_external_send"]),
                involves_irreversible_action=bool(parsed["involves_irreversible_action"]),
                worker=self.worker,
                summary=text.strip().splitlines()[0][:80] if text.strip() else "",
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable(f"LM Studio returned unparseable response: {exc}") from exc

    def is_reachable(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
