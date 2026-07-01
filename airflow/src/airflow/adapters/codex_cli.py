"""Codex アダプタ（主・実行）— spec §6.1。

STUB: このセッションはmacOS実機ではなく、ログイン済みCodex CLIが存在しない
ため、実際の subprocess 実行は未検証。骨組みのみを提供し、将来 macOS環境で
接続する際の実装の土台とする（docs/DEVIATIONS.md 参照）。

本来の設計:
- `codex exec "<prompt>"`（または `codex exec --json`）を subprocess で起動。
- 認証は `codex login`（ChatGPTアカウント）。APIキーは使わない。
- 起動前に `OPENAI_API_KEY` が環境に無いことを確認（config.check_no_api_keys）。
- 失敗時は LM Studio へフォールバック。
"""

from __future__ import annotations

import shutil
import subprocess

from .base import AdapterUnavailable


class CodexCliAdapter:
    worker = "codex"

    def __init__(self, *, timeout: float = 120.0) -> None:
        self.timeout = timeout

    def is_available(self) -> bool:
        return shutil.which("codex") is not None

    def run(self, prompt: str) -> str:
        if not self.is_available():
            raise AdapterUnavailable("codex CLI not found on PATH (not installed in this environment)")
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )
            return result.stdout
        except (subprocess.SubprocessError, OSError) as exc:
            raise AdapterUnavailable(f"codex exec failed: {exc}") from exc
