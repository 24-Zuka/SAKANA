import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ApprovalModal } from "../ApprovalModal";
import { CommandPalette } from "../CommandPalette";
import { Toasts } from "../common/Toasts";

// デザイン仕様書 §08: ウィンドウ幅1280px（Tauri .app想定）。ブラウザ実行時も
// その寸法感を再現するため、コンテンツを中央寄せの1280px枠に収める。
export function AppShell() {
  return (
    <div className="h-screen bg-jarvis-bg text-jarvis-text">
      <div className="mx-auto flex h-full max-w-[1280px] border-x border-jarvis-linesoft">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
      <ApprovalModal />
      <CommandPalette />
      <Toasts />
    </div>
  );
}
