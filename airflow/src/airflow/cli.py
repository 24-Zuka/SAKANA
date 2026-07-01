"""`airflowctl` CLI — spec §10.1。

実装するサブコマンド（MVPスコープ）:
  status / brief / add / import-inbox / list

macOS専用のため未対応（docs/DEVIATIONS.md参照）:
  watch-inbox（ポーリング版のみ提供）/ install-launchd / uninstall-launchd /
  configure-obsidian（P7に従い、クラッシュせず「未対応」と正直に表示する）
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import click

from .config import AirflowConfig, check_no_api_keys
from .inbox import import_inbox
from .models import Category, Status
from .scheduler.brief import generate_brief
from .store.ticket_store import TicketStore


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


@main.command(name="install-launchd")
def install_launchd() -> None:
    """launchd登録（macOS専用・本環境では未対応）。"""
    click.secho(
        "未対応: launchdはmacOS専用機能です。本環境（Linux）では登録できません。"
        " docs/DEVIATIONS.md を参照してください。",
        fg="yellow",
    )


@main.command(name="uninstall-launchd")
def uninstall_launchd() -> None:
    """launchd解除（macOS専用・本環境では未対応）。"""
    click.secho(
        "未対応: launchdはmacOS専用機能です。本環境（Linux）では解除対象がありません。",
        fg="yellow",
    )


@main.command(name="configure-obsidian")
@click.option("--detect", is_flag=True, default=False)
@click.option("--enable", is_flag=True, default=False)
@click.option("--disable", is_flag=True, default=False)
def configure_obsidian(detect: bool, enable: bool, disable: bool) -> None:
    """Obsidian書き出し設定（本MVPでは未実装・スタブ）。"""
    click.secho(
        "未実装: Obsidian書き出し（§9.3）はこのMVPスコープでは見送りました。"
        " docs/DEVIATIONS.md を参照してください。",
        fg="yellow",
    )
