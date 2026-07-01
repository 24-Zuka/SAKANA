// Research（調査）— spec §7.2: MVPスコープ外のためスタブ（空状態＋説明のみ）。

export function Research() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-2xl font-bold">Research 調査</h1>
      <div className="rounded-[13px] border border-dashed border-jarvis-line bg-jarvis-panel p-8 text-center">
        <p className="text-sm text-jarvis-text3">
          このMVPスコープでは未実装です。自動スキャン（→Inboxブリーフ）や手動ステーション
          （Gemini Deep Research・NotebookLM）は将来のバージョンで追加予定です。
        </p>
      </div>
    </div>
  );
}
