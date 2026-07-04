"""LM Studio アダプタ（常用・無料）— spec §6.2。

`http://localhost:1234/v1`（OpenAI互換API）へHTTP。分類・要約・整形・
検証（maker≠checkerのVerify段階・§5.1/§18）など定常処理を寄せる先。
認証不要・完全無料・無制限。疎通不可・タイムアウト時は `AdapterUnavailable`
を送出し、呼び出し側でフォールバックする。
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..models import Category
from .base import AdapterUnavailable, ClassificationResult, Result

DEFAULT_TIMEOUT = 60.0  # §6.5: ローカル 60s

CLASSIFY_SYSTEM_PROMPT = (
    "あなたはタスク分類器です。与えられた日本語テキストを読み、"
    "category(Business|Engineering|Content), priority(1|2|3), "
    "decision_required(true|false), involves_external_send(true|false), "
    "involves_irreversible_action(true|false) をJSONで1行で返してください。"
    "他の説明は一切出力しないでください。"
)

VERIFY_SYSTEM_PROMPT = (
    "あなたは成果物のレビュー担当（checker）です。作成者（maker）とは独立した視点で、"
    "与えられた成果物が判定基準を満たすかを判定し、"
    '{"pass": true|false, "reason": "..."} の形式のJSONで1行だけ返してください。'
)


class LMStudioAdapter:
    worker = "lmstudio"

    def __init__(self, base_url: str, *, timeout: float = DEFAULT_TIMEOUT, model: str = "local-model") -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.model = model

    def _chat(self, system: str, user: str, *, temperature: float = 0) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise AdapterUnavailable(f"LM Studio unreachable: {exc}") from exc

        try:
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable(f"LM Studio returned unparseable response: {exc}") from exc

    def classify(self, text: str) -> ClassificationResult:
        content = self._chat(CLASSIFY_SYSTEM_PROMPT, text)
        try:
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

    def summarize(self, text: str, *, max_sentences: int = 3) -> str:
        system = f"以下の文章を日本語で{max_sentences}文以内に要約してください。他の説明は不要です。"
        return self._chat(system, text).strip()

    def verify(self, artifact: str, criteria: str) -> tuple[bool, str]:
        """maker≠checker のVerify段階（§5.1/§18）。(合格したか, 理由) を返す。"""
        user = f"判定基準:\n{criteria}\n\n成果物:\n{artifact}"
        content = self._chat(VERIFY_SYSTEM_PROMPT, user)
        try:
            parsed = json.loads(content)
            return bool(parsed["pass"]), str(parsed.get("reason", ""))
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable(f"LM Studio returned unparseable verify response: {exc}") from exc

    def list_models(self) -> list[str]:
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            response.raise_for_status()
            payload = response.json()
            return [m["id"] for m in payload.get("data", [])]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable(f"LM Studio unreachable: {exc}") from exc

    def is_reachable(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> Result:
        """§6共通IF。最終フォールバック先のため例外を投げず常にResultを返す。"""
        start = time.monotonic()
        try:
            text = self._chat("あなたは有能なアシスタントです。", prompt)
        except AdapterUnavailable as exc:
            return Result(ok=False, text="", worker=self.worker, elapsed=time.monotonic() - start, error=str(exc))
        return Result(ok=True, text=text, worker=self.worker, elapsed=time.monotonic() - start, error=None)
