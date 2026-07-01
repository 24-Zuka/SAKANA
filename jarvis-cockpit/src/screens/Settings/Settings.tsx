import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { CockpitSettings } from "../../types/cockpit";
import { useAppStore } from "../../store/useAppStore";
import { Card, CardHeading } from "../../components/common/Card";
import { GhostButton } from "../../components/common/Button";

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
    return <p className="text-sm text-jarvis-text3">読み込み中…</p>;
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
      <h1 className="font-display text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeading>ブリッジ接続</CardHeading>
        <div className="mt-3 flex flex-col gap-2">
          <label className="text-xs text-jarvis-text2">
            URL
            <input
              defaultValue={settings.bridgeUrl}
              onBlur={(e) => save({ bridgeUrl: e.target.value })}
              className="mt-1 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
          <label className="text-xs text-jarvis-text2">
            トークン（Keychain保存想定・画面には平文表示しない）
            <input
              type="password"
              defaultValue={settings.bridgeToken}
              onBlur={(e) => save({ bridgeToken: e.target.value })}
              className="mt-1 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
        </div>
      </Card>

      <Card>
        <CardHeading>LM Studio</CardHeading>
        <div className="mt-3 flex gap-2">
          <input
            defaultValue={settings.lmStudioBaseUrl}
            onBlur={(e) => save({ lmStudioBaseUrl: e.target.value })}
            className="flex-1 rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
          <GhostButton
            onClick={testLmStudio}
            className="border-jarvis-accent/40 text-jarvis-accent hover:bg-jarvis-accent/20"
          >
            疎通テスト
          </GhostButton>
        </div>
        {testResult && <p className="mt-2 text-xs text-jarvis-text3">{testResult}</p>}
      </Card>

      <Card>
        <CardHeading>Obsidian Vault パス</CardHeading>
        <input
          defaultValue={settings.obsidianVaultPath}
          onBlur={(e) => save({ obsidianVaultPath: e.target.value })}
          placeholder="/path/to/vault（未設定＝書き出しOFF）"
          className="mt-3 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
        />
      </Card>

      <Card>
        <CardHeading>Codexログイン</CardHeading>
        <p className="mt-2 text-xs text-jarvis-text3">
          `codex login`（ChatGPTアカウント）で認証してください。APIキー入力欄はP2に従いこのUIには存在しません。
        </p>
        <button
          type="button"
          disabled
          className="mt-2 cursor-not-allowed rounded-lg border border-jarvis-line px-3 py-1.5 text-sm text-jarvis-text3 opacity-50"
        >
          codex login を起動（デスクトップ実機のみ・本環境では未対応）
        </button>
      </Card>
    </div>
  );
}
