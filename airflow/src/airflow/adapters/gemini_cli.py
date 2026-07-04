"""Gemini アダプタ（補助・長文/マルチモーダル）— spec §6.3。

`gemini` CLI を dcg 経由の subprocess で起動する。Googleアカウントでログイン
して使う想定（APIキーは使わない）。失敗時は呼び出し側（orchestrator.router）
で LM Studio へフォールバックする。

この環境には実際の `gemini` CLI が存在しないため、統合コードの検証は
`tests/test_gemini_cli.py` でPATH上に置いたフェイクスクリプトに対して行う。
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from ..config import check_no_api_keys
from ..guard import GuardBlocked, run_guarded
from .base import Result

DEFAULT_TIMEOUT = 120.0  # §6.5: CLI 120s
RETRY_COUNT = 1  # §6.5: リトライ1回


class GeminiCliAdapter:
    worker = "gemini"

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT, workspace_root: Path | None = None) -> None:
        self.timeout = timeout
        self.workspace_root = workspace_root or Path.cwd()

    def is_available(self) -> bool:
        import shutil

        return shutil.which("gemini") is not None

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> Result:
        """§6共通IF。例外を投げず、常に Result を返す。"""
        start = time.monotonic()

        flagged = check_no_api_keys()
        if flagged:
            return Result(
                ok=False,
                text="",
                worker=self.worker,
                elapsed=time.monotonic() - start,
                error=(
                    "課金対象のAPIキー環境変数が検出されたため実行を停止しました: "
                    f"{', '.join(flagged)}（P2: Googleログインのみ許可）"
                ),
            )

        if not self.is_available():
            return Result(
                ok=False,
                text="",
                worker=self.worker,
                elapsed=time.monotonic() - start,
                error="gemini CLI がPATH上に見つかりません。",
            )

        last_error: str | None = None
        for _attempt in range(RETRY_COUNT + 1):
            try:
                result = run_guarded(
                    ["gemini", prompt],
                    workspace_root=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            except GuardBlocked as exc:
                last_error = f"dcgにより遮断されました: {exc}"
                continue
            except subprocess.TimeoutExpired:
                last_error = f"gemini がタイムアウトしました（{self.timeout}秒）。"
                continue
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = f"gemini の起動に失敗しました: {exc}"
                continue

            if result.returncode != 0:
                last_error = f"gemini が失敗しました（exit={result.returncode}）: {result.stderr.strip()}"
                continue

            return Result(
                ok=True,
                text=result.stdout,
                worker=self.worker,
                elapsed=time.monotonic() - start,
                error=None,
            )

        return Result(
            ok=False,
            text="",
            worker=self.worker,
            elapsed=time.monotonic() - start,
            error=last_error or "unknown error",
        )
