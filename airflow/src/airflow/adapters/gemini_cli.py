"""Gemini アダプタ（補助・長文/マルチモーダル）— spec §6.3。

STUB: `gemini` CLI が本環境に存在しないため未検証。骨組みのみ。
Googleアカウントでログインして使う想定（APIキーは使わない）。
失敗時は LM Studio へフォールバック。
"""

from __future__ import annotations

import shutil
import subprocess

from .base import AdapterUnavailable


class GeminiCliAdapter:
    worker = "gemini"

    def __init__(self, *, timeout: float = 120.0) -> None:
        self.timeout = timeout

    def is_available(self) -> bool:
        return shutil.which("gemini") is not None

    def run(self, prompt: str) -> str:
        if not self.is_available():
            raise AdapterUnavailable("gemini CLI not found on PATH (not installed in this environment)")
        try:
            result = subprocess.run(
                ["gemini", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )
            return result.stdout
        except (subprocess.SubprocessError, OSError) as exc:
            raise AdapterUnavailable(f"gemini CLI failed: {exc}") from exc
