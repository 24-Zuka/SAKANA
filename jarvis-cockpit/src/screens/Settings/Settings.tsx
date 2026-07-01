import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { CockpitSettings } from "../../types/cockpit";
import { useAppStore } from "../../store/useAppStore";

// Settings — spec §7.2: ブリッジ接続/パス/トークン/LM Studio疎通テスト/codex login起動。
// **APIキー入力欄は仕様通り存在させない**（P2）。

export function Settings() {
  const [settings, setSettings] = useState<CockpitSettings | null>(null);
  const [testResult, setTestResult] = useState<string>("");
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => undefined);
  }, []);

  if (!settings) {
    return <p className="text-sm text-jarvis-text-muted">読み込み中…</p>;
  }

  async function save(patch: Partial<CockpitSettings>) {
    const updated = await api.updateSettings(patch);
    setSettings(updated);
    pushToast("設定を保存しました", "success");
  }

  async function testLmStudio() {
    try {
      const health = await api.health();
      setTestResult(health.lm_studio_reachable ? "接続成功" : "接続できませんでした");
    } catch {
      setTestResult("接続できませんでした");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Settings</h1>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">ブリッジ接続</h2>
        <div className="mt-3 flex flex-col gap-2">
          <label className="text-xs text-jarvis-text-muted">
            URL
            <input
              defaultValue={settings.bridgeUrl}
              onBlur={(e) => save({ bridgeUrl: e.target.value })}
              className="mt-1 w-full rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
          <label className="text-xs text-jarvis-text-muted">
            トークン（Keychain保存想定・画面には平文表示しない）
            <input
              type="password"
              defaultValue={settings.bridgeToken}
              onBlur={(e) => save({ bridgeToken: e.target.value })}
              className="mt-1 w-full rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">LM Studio</h2>
        <div className="mt-3 flex gap-2">
          <input
            defaultValue={settings.lmStudioBaseUrl}
            onBlur={(e) => save({ lmStudioBaseUrl: e.target.value })}
            className="flex-1 rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
          <button
            type="button"
            onClick={testLmStudio}
            className="rounded border border-jarvis-accent-dim px-3 py-1.5 text-sm text-jarvis-accent hover:bg-jarvis-accent-dim/20"
          >
            疎通テスト
          </button>
        </div>
        {testResult && <p className="mt-2 text-xs text-jarvis-text-muted">{testResult}</p>}
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">Obsidian Vault パス</h2>
        <input
          defaultValue={settings.obsidianVaultPath}
          onBlur={(e) => save({ obsidianVaultPath: e.target.value })}
          placeholder="/path/to/vault（未設定＝書き出しOFF）"
          className="mt-3 w-full rounded border border-jarvis-border bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
        />
      </section>

      <section className="rounded-lg border border-jarvis-border bg-jarvis-surface p-4">
        <h2 className="text-sm font-semibold text-jarvis-text-muted">Codexログイン</h2>
        <p className="mt-2 text-xs text-jarvis-text-muted">
          `codex login`（ChatGPTアカウント）で認証してください。APIキー入力欄はP2に従いこのUIには存在しません。
        </p>
        <button
          type="button"
          disabled
          className="mt-2 cursor-not-allowed rounded border border-jarvis-border px-3 py-1.5 text-sm text-jarvis-text-muted opacity-50"
        >
          codex login を起動（デスクトップ実機のみ・本環境では未対応）
        </button>
      </section>
    </div>
  );
}
