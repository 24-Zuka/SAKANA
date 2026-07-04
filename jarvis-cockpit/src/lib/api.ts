// 唯一の窓口 — spec §7.1/§7.3。
// 優先順位: Tauri → Bridge（localStorage設定 or ビルド時env） → Mock。
//
// bridgeUrl/bridgeTokenはSettings画面からlocalStorageへ永続化され、
// リビルド・リロード無しで次のAPI呼び出しから反映される
// （GitHub Pages公開版からもローカルbridgeへ接続できるようにするため）。
import type { AirflowApi } from "./apiTypes";
import { isTauriEnvironment, tauriTransport } from "./tauriTransport";
import { createBridgeTransport } from "./bridgeTransport";
import { browserMock } from "./browserMock";

const BRIDGE_URL_KEY = "jarvis.bridgeUrl";
const BRIDGE_TOKEN_KEY = "jarvis.bridgeToken";

export function getStoredBridgeUrl(): string {
  try {
    return localStorage.getItem(BRIDGE_URL_KEY) ?? "";
  } catch {
    return "";
  }
}

export function getStoredBridgeToken(): string {
  try {
    return localStorage.getItem(BRIDGE_TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setStoredBridgeConnection(url: string, token: string): void {
  try {
    if (url) localStorage.setItem(BRIDGE_URL_KEY, url);
    else localStorage.removeItem(BRIDGE_URL_KEY);
    if (token) localStorage.setItem(BRIDGE_TOKEN_KEY, token);
    else localStorage.removeItem(BRIDGE_TOKEN_KEY);
  } catch {
    // localStorage不可（プライベートモード等）でも静かに壊れない（P7）
  }
}

function resolveTransport(): AirflowApi {
  if (isTauriEnvironment()) return tauriTransport;
  const bridgeUrl = getStoredBridgeUrl() || import.meta.env.VITE_BRIDGE_URL;
  if (bridgeUrl) return createBridgeTransport(bridgeUrl, getStoredBridgeToken());
  return browserMock;
}

// 実行時トランスポート切替: 呼び出しの都度 resolveTransport() し直すことで、
// Settings画面での接続設定変更をリロード無しで反映する。
export const api: AirflowApi = new Proxy({} as AirflowApi, {
  get(_target, prop, receiver) {
    const transport = resolveTransport();
    const value = Reflect.get(transport as object, prop, receiver);
    return typeof value === "function" ? value.bind(transport) : value;
  },
});

export type { AirflowApi } from "./apiTypes";
