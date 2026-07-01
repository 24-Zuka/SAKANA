import { NavLink } from "react-router-dom";

// デザイン仕様書 §08: サイドバー幅236px。管制→運用の2グループ・8ナビ。
const NAV_GROUPS = [
  {
    label: "管制",
    items: [
      { to: "/", label: "Dashboard", end: true },
      { to: "/agents", label: "Agents" },
      { to: "/build", label: "Build" },
      { to: "/memory", label: "Memory" },
    ],
  },
  {
    label: "運用",
    items: [
      { to: "/schedule", label: "Schedule" },
      { to: "/research", label: "Research" },
      { to: "/quota", label: "Quota & Cost" },
      { to: "/settings", label: "Settings" },
    ],
  },
];

export function Sidebar() {
  return (
    <nav
      aria-label="主要画面"
      className="flex w-[236px] shrink-0 flex-col border-r border-jarvis-line bg-jarvis-panel p-3"
    >
      <div className="mb-5 px-2 font-display text-[15px] font-semibold tracking-wide text-jarvis-text">
        JARVIS Cockpit
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-4">
          <div className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-[1.3px] text-jarvis-text3">
            {group.label}
          </div>
          <ul className="flex flex-col gap-1">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `block rounded-lg px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-jarvis-accent/12 text-jarvis-accent"
                        : "text-jarvis-text2 hover:bg-jarvis-panel2 hover:text-jarvis-text"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
