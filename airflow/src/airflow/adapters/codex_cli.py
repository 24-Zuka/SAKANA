"""Codex アダプタ（主・実行）— spec §6.1。

`codex exec --json <prompt>` を dcg 経由の subprocess で起動し、JSONL出力を
逐次パースする。認証は `codex login`（ChatGPTアカウント）。起動前に
`OPENAI_API_KEY` が環境に無いことを確認し、検出時は実行を拒否する（P2/§8.4）。

この環境には実際の `codex` CLI が存在しないため、統合コードの検証は
`tests/test_codex_cli.py` でPATH上に置いたフェイクスクリプトに対して行う。
実機での `codex login` 済みCLIに対する最終確認は docs/DEVIATIONS.md に記載。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..config import check_no_api_keys
from ..guard import GuardBlocked, run_guarded
from .base import Result

DEFAULT_TIMEOUT = 120.0  # §6.5: CLI 120s
RETRY_COUNT = 1  # §6.5: リトライ1回


def _extract_text_fragment(obj: dict[str, Any]) -> str | None:
    """codexのJSONL 1行分から人間可読テキストを抽出する（ベストエフォート）。

    実際の `codex exec --json` 出力仕様はCLIバージョン依存のため（spec §13）、
    "content"/"text"/"message"/"delta" のいずれかのキーを持つ行からテキストを
    拾う寛容なパーサーとして実装する。
    """
    if obj.get("type") == "error":
        return None
    for key in ("content", "text", "message", "delta"):
        value = obj.get(key)
        if isinstance(value, str):
            return value
    return None


class CodexCliAdapter:
    worker = "codex"

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT, workspace_root: Path | None = None) -> None:
        self.timeout = timeout
        self.workspace_root = workspace_root or Path.cwd()

    def is_available(self) -> bool:
        return shutil.which("codex") is not None

    def login_status(self) -> bool:
        """`codex login status` の結果を返す。CLI不在・失敗時は False。"""
        if not self.is_available():
            return False
        try:
            result = run_guarded(
                ["codex", "login", "status"],
                workspace_root=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=10.0,
            )
            return result.returncode == 0
        except (GuardBlocked, subprocess.SubprocessError, OSError):
            return False

    def _exec_once(self, prompt: str) -> subprocess.CompletedProcess:
        return run_guarded(
            ["codex", "exec", "--json", prompt],
            workspace_root=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

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
                    f"{', '.join(flagged)}（P2: サブスクログインのみ許可）"
                ),
            )

        if not self.is_available():
            return Result(
                ok=False,
                text="",
                worker=self.worker,
                elapsed=time.monotonic() - start,
                error="codex CLI がPATH上に見つかりません。",
            )

        last_error: str | None = None
        for attempt in range(RETRY_COUNT + 1):
            try:
                result = self._exec_once(prompt)
            except GuardBlocked as exc:
                last_error = f"dcgにより遮断されました: {exc}"
                continue
            except subprocess.TimeoutExpired:
                last_error = f"codex exec がタイムアウトしました（{self.timeout}秒）。"
                continue
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = f"codex exec の起動に失敗しました: {exc}"
                continue

            if result.returncode != 0:
                last_error = f"codex exec が失敗しました（exit={result.returncode}）: {result.stderr.strip()}"
                continue

            fragments: list[str] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                fragment = _extract_text_fragment(obj)
                if fragment:
                    fragments.append(fragment)

            return Result(
                ok=True,
                text="".join(fragments),
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
