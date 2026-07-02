"""`airflowctl` CLI — spec §10.1。

実装するサブコマンド:
  status / brief / add / import-inbox / list / run / groom /
  configure-obsidian / install-launchd / uninstall-launchd

macOS専用のため一部未対応（docs/DEVIATIONS.md参照）:
  watch-inbox はポーリング版のみ提供。install-launchd/uninstall-launchd は
  plist生成・ファイル配置は行うが、実際の `launchctl load/unload` はdarwin
  でのみ実行する（非macOSでは正直に「未対応」と表示する・P7）。
"""

from __future__ import annotations

import shutil
import sys
import time
from datetime import date
from pathlib import Path

import click

from .automation.launchd import JOB_BRIEF, JOB_GROOMING, JOB_INBOX
from .automation.launchd import generate_brief_plist, generate_grooming_plist, generate_inbox_plist
from .automation.launchd import install as launchd_install
from .automation.launchd import is_macos as launchd_is_macos
from .automation.launchd import uninstall as launchd_uninstall
from .config import AirflowConfig, check_no_api_keys
from .inbox import import_inbox
from .models import Category, Status
from .obsidian import ObsidianClient, ObsidianError, ObsidianWriteRefused, export_brief
from .orchestrator.run import run_ticket
from .scheduler.brief import generate_brief
from .scheduler.groom import groom as groom_store
from .store.ticket_store import TicketStore


def _airflowctl_bin() -> str:
    return shutil.which("airflowctl") or str(Path(sys.executable).parent / "airflowctl")


def _get_store(config: AirflowConfig) -> TicketStore:
    config.ensure_dirs()
    return TicketStore(config.home)


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """AirFlow — AI自動化タスクボード CLI（MVP実装）。"""
    ctx.obj = AirflowConfig.load()
    flagged = check_no_api_keys()
    if flagged:
        click.secho(
            f"🚩 赤旗: 課金対象のAPIキー環境変数が検出されました: {', '.join(flagged)}。"
            " サブスクログイン（codex login / gemini login）を使い、これらは unset してください。",
            fg="red",
            err=True,
        )


@main.command()
@click.pass_obj
def status(config: AirflowConfig) -> None:
    """今日のボード状況を表示する。"""
    store = _get_store(config)
    tickets = store.list()
    click.echo(f"AirFlow store: {config.home}")
    click.echo(f"合計チケット数: {len(tickets)}")
    for s in Status:
        count = len([t for t in tickets if t.status == s])
        click.echo(f"  {s.value}: {count}")
    decision_count = len([t for t in tickets if t.decision_required])
    click.echo(f"要判断（decision_required）: {decision_count}")


@main.command()
@click.option("--show/--no-show", default=False, help="生成した朝礼の内容を表示する")
@click.pass_obj
def brief(config: AirflowConfig, show: bool) -> None:
    """朝礼レポートを即時生成する。"""
    store = _get_store(config)
    path = generate_brief(store, config.briefs_dir)
    click.echo(f"朝礼を生成しました: {path}")
    if show:
        click.echo(path.read_text(encoding="utf-8"))

    if config.obsidian_export_enabled:
        client = ObsidianClient(base_url=config.obsidian_base_url, token=config.obsidian_token or None)
        try:
            vault_path = export_brief(client, date.today(), path.read_text(encoding="utf-8"))
            click.echo(f"Obsidianへ書き出しました: {vault_path}")
        except ObsidianWriteRefused as exc:
            click.secho(f"Obsidian書き出しをスキップしました（手書きノート保護）: {exc}", fg="yellow")
        except ObsidianError as exc:
            click.secho(f"Obsidian書き出しに失敗しました（接続不可）: {exc}", fg="yellow")


@main.command()
@click.argument("text")
@click.pass_obj
def add(config: AirflowConfig, text: str) -> None:
    """自然文からチケットを起票する。"""
    store = _get_store(config)
    ticket = import_inbox(store, text)
    click.echo(f"起票しました: {ticket.id} [{ticket.category.value}/{ticket.status.value}] {ticket.title}")


@main.command(name="import-inbox")
@click.option("--once", is_flag=True, default=True, help="1回だけ取り込む（既定）")
@click.pass_obj
def import_inbox_cmd(config: AirflowConfig, once: bool) -> None:
    """inbox/ 配下の .md / .txt を取り込み、起票して processed/ へ退避する。"""
    store = _get_store(config)
    count = _import_inbox_once(store, config)
    click.echo(f"{count} 件のファイルを取り込みました。")


def _import_inbox_once(store: TicketStore, config: AirflowConfig) -> int:
    count = 0
    for path in sorted(config.inbox_dir.glob("*")):
        if path.is_dir() or path.suffix not in (".md", ".txt"):
            continue
        text = path.read_text(encoding="utf-8")
        import_inbox(store, text)
        dest = config.inbox_processed_dir / path.name
        shutil.move(str(path), str(dest))
        count += 1
    return count


@main.command(name="watch-inbox")
@click.option("--interval", default=5.0, show_default=True, help="ポーリング間隔（秒）")
@click.pass_obj
def watch_inbox(config: AirflowConfig, interval: float) -> None:
    """Inboxを常時監視する（ポーリング実装。本来はfswatch/launchdだが本環境では未対応）。"""
    store = _get_store(config)
    click.echo(
        "注意: launchd/fswatchの代わりにポーリングで監視します"
        f"（{interval}秒間隔）。Ctrl+Cで停止。"
    )
    try:
        while True:
            _import_inbox_once(store, config)
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("停止しました。")


@main.command(name="list")
@click.option("--status", "status_filter", type=click.Choice([s.value for s in Status]), default=None)
@click.option("--category", "category_filter", type=click.Choice([c.value for c in Category]), default=None)
@click.pass_obj
def list_cmd(config: AirflowConfig, status_filter: str | None, category_filter: str | None) -> None:
    """チケット一覧を表示する。"""
    store = _get_store(config)
    tickets = store.list(
        status=Status(status_filter) if status_filter else None,
        category=Category(category_filter) if category_filter else None,
    )
    if not tickets:
        click.echo("該当するチケットはありません。")
        return
    for t in tickets:
        click.echo(f"[{t.id}] ({t.category.value}/{t.status.value}, risk={t.risk_score}) {t.title}")


@main.command(name="run")
@click.argument("ticket_id")
@click.pass_obj
def run_cmd(config: AirflowConfig, ticket_id: str) -> None:
    """チケットに対して Plan→Route→Execute→Verify のクローズドループを実行する（§5.1）。"""
    store = _get_store(config)
    updated = run_ticket(ticket_id, store, config)
    click.echo(f"{ticket_id}: status={updated.status.value} decision_required={updated.decision_required}")
    for line in updated.log[-6:]:
        click.echo(f"  {line}")


@main.command(name="groom")
@click.pass_obj
def groom_cmd(config: AirflowConfig) -> None:
    """夜間グルーミング（§10）: 期限切れ注記・Doneチケット圧縮・索引再構築。"""
    store = _get_store(config)
    result = groom_store(store)
    click.echo(f"期限切れ注記: {len(result['flagged_overdue'])}件")
    click.echo(f"Done圧縮（アーカイブ）: {len(result['archived_done'])}件")
    click.echo(f"索引再構築: {result['indexed_count']}件")


@main.command(name="install-launchd")
@click.pass_obj
def install_launchd(config: AirflowConfig) -> None:
    """launchd登録（§10）: 朝礼・夜間グルーミング・Inbox監視の3ジョブを登録する。"""
    bin_path = _airflowctl_bin()
    jobs = [
        (JOB_BRIEF, generate_brief_plist(bin_path)),
        (JOB_GROOMING, generate_grooming_plist(bin_path)),
        (JOB_INBOX, generate_inbox_plist(bin_path, config.inbox_dir)),
    ]
    for label, plist_bytes in jobs:
        path = launchd_install(label, plist_bytes)
        click.echo(f"登録しました: {path}")
    if not launchd_is_macos():
        click.secho(
            "注意: launchdはmacOS専用機能のため、本環境ではplistファイルの生成のみ行い"
            "launchctl loadは実行していません。",
            fg="yellow",
        )


@main.command(name="uninstall-launchd")
def uninstall_launchd() -> None:
    """launchd解除（§10）。"""
    removed_any = False
    for label in (JOB_BRIEF, JOB_GROOMING, JOB_INBOX):
        if launchd_uninstall(label):
            click.echo(f"解除しました: {label}")
            removed_any = True
    if not removed_any:
        click.echo("登録されているジョブはありませんでした。")
    if not launchd_is_macos():
        click.secho(
            "注意: launchdはmacOS専用機能のため、本環境ではlaunchctl unloadは実行していません。",
            fg="yellow",
        )


@main.command(name="configure-obsidian")
@click.option("--detect", is_flag=True, default=False)
@click.option("--enable", is_flag=True, default=False)
@click.option("--disable", is_flag=True, default=False)
@click.pass_obj
def configure_obsidian(config: AirflowConfig, detect: bool, enable: bool, disable: bool) -> None:
    """Obsidian書き出し設定（§9.3）。既定OFF。"""
    if disable:
        config.set_obsidian_export_enabled(False)
        click.echo("Obsidian書き出しを無効化しました。")
        return

    reachable = None
    if detect:
        client = ObsidianClient(base_url=config.obsidian_base_url, token=config.obsidian_token or None)
        reachable = client.is_reachable()
        click.echo(
            f"Obsidian Local REST API（{config.obsidian_base_url}）疎通: "
            f"{'OK' if reachable else '不可（未接続）'}"
        )

    if enable:
        if detect and not reachable:
            click.secho("疎通できなかったため有効化をスキップしました。", fg="yellow")
            return
        config.set_obsidian_export_enabled(True)
        click.echo("Obsidian書き出しを有効化しました（次回の朝礼生成から反映）。")
    elif not disable and not detect:
        click.echo("使い方: --detect / --enable / --disable のいずれかを指定してください。")
