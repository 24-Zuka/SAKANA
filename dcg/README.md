# dcg — Destructive Command Guard

破壊的コマンド改札（spec §8.2）。`AirFlow`/`Cockpit` が起動する外部プロセスの前段に
挟み込むガード。3段解析（Quick Reject → Context Classification → 遮断判定）で
`rm -rf` の管理外実行・`git reset --hard`・`main`/`master` への `git push --force`・
`dd`/`mkfs`/`fdisk` を遮断する。

## ビルド・テスト

```bash
cargo build --release
cargo test
```

## 使い方

```bash
dcg -- <command> [args...]
```

- 許可: 何も出力せず exit code 0。
- 遮断: 理由と代替案を stderr に出力し exit code 2。

`WORKSPACE_ROOT` 環境変数で `rm -rf` の許可領域（`${WORKSPACE_ROOT}/tmp`）を指定する
（未設定時はカレントディレクトリ）。

## 守備範囲の限界

dcg が遮断できるのは、AirFlow/Cockpit が直接起動するプロセスのみ。`codex exec` の
**内側**で Codex 自身が発行するシェル/gitコマンドは dcg を通らないため、Codex実行時は
Codex側の sandbox/approval設定を併用する二重防御とする（spec §8.2）。
