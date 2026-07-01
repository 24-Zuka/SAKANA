import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/agents", label: "Agents" },
  { to: "/build", label: "Build" },
  { to: "/memory", label: "Memory" },
  { to: "/schedule", label: "Schedule" },
  { to: "/research", label: "Research" },
  { to: "/quota", label: "Quota & Cost" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  return (
    <nav
      aria-label="主要画面"
      className="flex w-56 shrink-0 flex-col border-r border-jarvis-border bg-jarvis-surface p-3"
    >
      <div className="mb-4 px-2 text-sm font-semibold tracking-wide text-jarvis-accent">
        JARVIS Cockpit
      </div>
      <ul className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-jarvis-accent-dim/30 text-jarvis-accent"
                    : "text-jarvis-text-muted hover:bg-jarvis-surface-raised hover:text-jarvis-text"
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
