"""Obsidian Local REST API 連携 — spec §7.3/§9.3/§4.7。

`vault_read`(GET) / `vault_write`(PUT) / heading単位PATCHによる外科的追記 /
`vault_delete`(ゴミ箱経由) / `vault_search`(全文検索)。

§4.7 AI_Handoff.md 追記規約: ファイル最上部の一意アンカー
`<!-- AI_HANDOFF_ANCHOR -->` の直下に新規ブロックを挿入し、アンカー自体と
既存履歴は決して削除・改変しない（時系列降順の逆順スタック）。

実装上の注記: Obsidian Local REST API の PATCH は heading/block/frontmatter
をターゲットにする方式であり、コメント文字列アンカーへの直接挿入はサポート
されない。そのため `handoff_append()` は「全文読取→アンカー直後に挿入→
全文PUT」で非破壊追記の意味論（アンカー・既存履歴を変更しない）を実現する。
一般的な見出し単位の追記には `append_after_heading()`（真のPATCH）を使う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import httpx

HANDOFF_ANCHOR = "<!-- AI_HANDOFF_ANCHOR -->"


class ObsidianError(Exception):
    """Obsidian REST APIとの通信一般の失敗。"""


class ObsidianFileNotFound(ObsidianError):
    pass


class ObsidianWriteRefused(ObsidianError):
    """マーカー無し（＝手書き）ノートへの上書きを拒否した場合。"""


@dataclass
class ObsidianClient:
    base_url: str = "http://127.0.0.1:27123"
    token: str | None = None
    timeout: float = 10.0

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def is_reachable(self) -> bool:
        try:
            response = httpx.get(self.base_url, headers=self._headers(), timeout=5.0)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def read(self, path: str) -> str:
        try:
            response = httpx.get(f"{self.base_url}/vault/{path}", headers=self._headers(), timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise ObsidianError(f"Obsidian Local REST API に接続できません: {exc}") from exc
        if response.status_code == 404:
            raise ObsidianFileNotFound(path)
        if response.status_code >= 400:
            raise ObsidianError(f"vault_read failed ({response.status_code}): {path}")
        return response.text

    def write(self, path: str, content: str) -> None:
        try:
            response = httpx.put(
                f"{self.base_url}/vault/{path}",
                headers=self._headers({"Content-Type": "text/markdown"}),
                content=content.encode("utf-8"),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ObsidianError(f"Obsidian Local REST API に接続できません: {exc}") from exc
        if response.status_code >= 400:
            raise ObsidianError(f"vault_write failed ({response.status_code}): {path}")

    def append_after_heading(self, path: str, heading: str, content: str) -> None:
        """見出し単位PATCH（外科的追記）。"""
        try:
            response = httpx.patch(
                f"{self.base_url}/vault/{path}",
                headers=self._headers(
                    {
                        "Operation": "append",
                        "Target-Type": "heading",
                        "Target": heading,
                        "Content-Type": "text/markdown",
                    }
                ),
                content=content.encode("utf-8"),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ObsidianError(f"Obsidian Local REST API に接続できません: {exc}") from exc
        if response.status_code >= 400:
            raise ObsidianError(f"heading PATCH failed ({response.status_code}): {path}")

    def handoff_append(self, path: str, entry: str, *, now: datetime | None = None) -> None:
        """§4.7: AI_HANDOFF_ANCHOR 直下への非破壊・逆順スタック追記。"""
        now = now or datetime.now().astimezone()
        try:
            existing = self.read(path)
        except ObsidianFileNotFound:
            existing = f"{HANDOFF_ANCHOR}\n"

        if HANDOFF_ANCHOR not in existing:
            raise ObsidianWriteRefused(f"{path} に {HANDOFF_ANCHOR} が見つからないため追記を拒否しました。")

        anchor_index = existing.index(HANDOFF_ANCHOR) + len(HANDOFF_ANCHOR)
        before = existing[:anchor_index]
        after = existing[anchor_index:]
        new_block = f"\n\n## {now.isoformat(timespec='seconds')}\n{entry.strip()}"
        updated = before + new_block + after
        self.write(path, updated)

    def delete(self, path: str) -> str:
        """ゴミ箱経由の削除。`.trash/<timestamp>-<name>` へ退避してから元ファイルを削除する。"""
        content = self.read(path)
        timestamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
        name = path.rsplit("/", 1)[-1]
        trash_path = f".trash/{timestamp}-{name}"
        self.write(trash_path, content)
        try:
            response = httpx.delete(f"{self.base_url}/vault/{path}", headers=self._headers(), timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise ObsidianError(f"Obsidian Local REST API に接続できません: {exc}") from exc
        if response.status_code >= 400:
            raise ObsidianError(f"vault_delete failed ({response.status_code}): {path}")
        return trash_path

    def search(self, query: str) -> list[dict]:
        try:
            response = httpx.get(
                f"{self.base_url}/search/simple/",
                params={"query": query, "contextLength": 100},
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ObsidianError(f"Obsidian Local REST API に接続できません: {exc}") from exc
        if response.status_code >= 400:
            raise ObsidianError(f"vault_search failed ({response.status_code}): {query}")
        return response.json()


BRIEF_MARKER = "<!-- AIRFLOW_GENERATED -->"


def export_brief(client: ObsidianClient, on: date, content: str) -> str:
    """§9.3: マーカー付きファイルのみ上書きする、朝礼のvault書き出し。

    書き出し先: `90_Daily/AirFlow_YYYY-MM-DD_朝礼.md`
    """
    path = f"90_Daily/AirFlow_{on.isoformat()}_朝礼.md"
    try:
        existing = client.read(path)
    except ObsidianFileNotFound:
        existing = None

    if existing is not None and BRIEF_MARKER not in existing:
        raise ObsidianWriteRefused(
            f"{path} はAirFlow生成マーカーを含まない既存ノートのため上書きしません（§9.3）。"
        )

    client.write(path, f"{BRIEF_MARKER}\n{content}")
    return path
