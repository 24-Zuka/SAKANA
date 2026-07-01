import { create } from "zustand";

export interface ApprovalRequest {
  id: string;
  title: string;
  description: string;
  riskScore?: number;
  // デザイン仕様書 §07: 対象・検証結果・レビュー件数などを明示するための任意の詳細行。
  details?: { label: string; value: string }[];
  onApprove: () => void | Promise<void>;
  onReject?: () => void;
}

export interface Toast {
  id: string;
  message: string;
  kind: "info" | "success" | "error";
}

interface AppState {
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  approvalRequest: ApprovalRequest | null;
  requestApproval: (req: Omit<ApprovalRequest, "id">) => void;
  resolveApproval: (approved: boolean) => void;

  toasts: Toast[];
  pushToast: (message: string, kind?: Toast["kind"]) => void;
  dismissToast: (id: string) => void;
}

let toastSeq = 0;

export const useAppStore = create<AppState>((set, get) => ({
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),

  approvalRequest: null,
  requestApproval: (req) => set({ approvalRequest: { ...req, id: crypto.randomUUID() } }),
  resolveApproval: (approved) => {
    const req = get().approvalRequest;
    set({ approvalRequest: null });
    if (!req) return;
    if (approved) {
      void req.onApprove();
    } else {
      req.onReject?.();
    }
  },

  toasts: [],
  pushToast: (message, kind = "info") => {
    toastSeq += 1;
    const id = `toast-${toastSeq}`;
    set((s) => ({ toasts: [...s.toasts, { id, message, kind }] }));
    setTimeout(() => get().dismissToast(id), 4000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
