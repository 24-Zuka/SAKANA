import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ApprovalModal } from "../ApprovalModal";
import { CommandPalette } from "../CommandPalette";
import { Toasts } from "../common/Toasts";

export function AppShell() {
  return (
    <div className="flex h-screen bg-jarvis-bg text-jarvis-text">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <ApprovalModal />
      <CommandPalette />
      <Toasts />
    </div>
  );
}
