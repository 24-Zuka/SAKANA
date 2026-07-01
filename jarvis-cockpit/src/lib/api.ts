// 唯一の窓口 — spec §7.1/§7.3。
// 優先順位: Tauri → Bridge → Mock。
import type { AirflowApi } from "./apiTypes";
import { isTauriEnvironment, tauriTransport } from "./tauriTransport";
import { bridgeTransport } from "./bridgeTransport";
import { browserMock } from "./browserMock";

function resolveTransport(): AirflowApi {
  if (isTauriEnvironment()) return tauriTransport;
  if (import.meta.env.VITE_BRIDGE_URL) return bridgeTransport;
  return browserMock;
}

export const api: AirflowApi = resolveTransport();
export type { AirflowApi } from "./apiTypes";
