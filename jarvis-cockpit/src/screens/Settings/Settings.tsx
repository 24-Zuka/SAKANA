import { useEffect, useState } from "react";
import { api, getStoredBridgeToken, getStoredBridgeUrl, setStoredBridgeConnection } from "../../lib/api";
import { DEFAULT_BRIDGE_URL } from "../../lib/bridgeTransport";
import type { CockpitSettings } from "../../types/cockpit";
import { useAppStore } from "../../store/useAppStore";
import { Card, CardHeading } from "../../components/common/Card";
import { GhostButton } from "../../components/common/Button";

// Settings — spec §7.2: ブリッジ接続/パス/トークン/LM Studio疎通テスト/codex login起動。
// **APIキー入力欄は仕様通り存在させない**（P2）。
//
// bridgeUrl/bridgeTokenはサーバー設定ではなくクライアント側の接続先情報のため、
// api.getSettings/updateSettings（lmStudioBaseUrl/obsidianVaultPath用）とは別に
// localStorageへ直接永続化する（lib/api.ts参照）。

export function Settings() {
  const [settings, setSettings] = useState<CockpitSettings | null>(null);
  const [bridgeUrl, setBridgeUrl] = useState(getStoredBridgeUrl());
  const [bridgeToken, setBridgeToken] = useState(getStoredBridgeToken());
  const [testResult, setTestResult] = useState<string>("");
  const [bridgeTestResult, setBridgeTestResult] = useState<string>("");
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => undefined);
  }, []);

  async function save(patch: Partial<CockpitSettings>) {
    const updated = await api.updateSettings(patch);
    setSettings(updated);
    pushToast("設定を保存しました", "success");
  }

  function saveBridgeConnection(nextUrl: string, nextToken: string) {
    setStoredBridgeConnection(nextUrl, nextToken);
    pushToast("ブリッジ接続設定を保存しました（次回のAPI呼び出しから反映）", "success");
  }

  async function testLmStudio() {
    try {
      const health = await api.health();
      setTestResult(health.lm_studio_reachable ? "接続成功" : "接続できませんでした");
    } catch {
      setTestResult("接続できませんでした");
    }
  }

  async function testBridge() {
    try {
      const health = await api.health();
      setBridgeTestResult(`疎通成功（transport: ${api.transportName} / home: ${health.home}）`);
    } catch {
      setBridgeTestResult("疎通できませんでした（URL/トークン、またはブリッジの起動状況を確認してください）");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeading>ブリッジ接続</CardHeading>
        <p className="mt-1 text-xs text-jarvis-text3">
          現在のトランスポート: <span className="font-mono text-jarvis-text2">{api.transportName}</span>
          （URL未設定時はMockモードで動作します）
        </p>
        <div className="mt-3 flex flex-col gap-2">
          <label className="text-xs text-jarvis-text2">
            URL
            <input
              value={bridgeUrl}
              onChange={(e) => setBridgeUrl(e.target.value)}
              onBlur={() => saveBridgeConnection(bridgeUrl, bridgeToken)}
              placeholder={DEFAULT_BRIDGE_URL}
              className="mt-1 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
          <label className="text-xs text-jarvis-text2">
            トークン（`airflowctl show-bridge-token` で確認・端末のlocalStorageにのみ保存）
            <input
              type="password"
              value={bridgeToken}
              onChange={(e) => setBridgeToken(e.target.value)}
              onBlur={() => saveBridgeConnection(bridgeUrl, bridgeToken)}
              className="mt-1 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
            />
          </label>
          <div>
            <GhostButton
              onClick={testBridge}
              className="border-jarvis-accent/40 text-jarvis-accent hover:bg-jarvis-accent/20"
            >
              ブリッジ疎通テスト
            </GhostButton>
          </div>
          {bridgeTestResult && <p className="text-xs text-jarvis-text3">{bridgeTestResult}</p>}
        </div>
      </Card>

      <Card>
        <CardHeading>LM Studio</CardHeading>
        {settings ? (
          <>
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
          </>
        ) : (
          <p className="mt-2 text-xs text-jarvis-text3">
            取得できません（現在のブリッジ接続に到達できないか、まだ読み込み中です）。
          </p>
        )}
      </Card>

      <Card>
        <CardHeading>Obsidian Vault パス</CardHeading>
        {settings ? (
          <input
            defaultValue={settings.obsidianVaultPath}
            onBlur={(e) => save({ obsidianVaultPath: e.target.value })}
            placeholder="/path/to/vault（未設定＝書き出しOFF）"
            className="mt-3 w-full rounded-lg border border-jarvis-line bg-jarvis-bg px-3 py-1.5 text-sm outline-none focus:border-jarvis-accent"
          />
        ) : (
          <p className="mt-2 text-xs text-jarvis-text3">
            取得できません（現在のブリッジ接続に到達できないか、まだ読み込み中です）。
          </p>
        )}
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
