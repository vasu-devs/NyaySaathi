import React, { useState } from "react";

/**
 * Reusable Sidebar component
 * Props:
 * - logoSrc: string (path to logo in /public)
 * - items: [{ key, label, icon (path or JSX), href? }]
 * - initialCollapsed: boolean
 *
 * Behavior:
 * - fixed on the left, overlays content (doesn't push page layout)
 * - smooth collapse/expand animation
 * - when collapsed only icons are visible; when expanded icon + label
 */
const SideBar = ({
  logoSrc = "/LogoSaathi.svg",
  items = [
    { key: "Chat", label: "Chat", icon: "/chat.svg", href: "#" },
    { key: "docs", label: "Docs", icon: "/Lens.svg", href: "#" },
  ],
  initialCollapsed = false,
}) => {
  const [collapsed, setCollapsed] = useState(!!initialCollapsed);

  const expandedWidth = 56; // rem? We'll use px classes via style
  const collapsedWidth = 64; // px for visual width when collapsed

  return (
    // Fixed sidebar positioned below navbar so it doesn't cover the nav
    <aside
      className={`fixed top-10 left-0 bottom-0 flex flex-col bg-white border-r border-[#E6EEF6] shadow-sm transition-all duration-300 ease-in-out z-40`}
      style={{ width: collapsed ? `${collapsedWidth}px` : "220px" }}
      aria-expanded={!collapsed}
    >
      {/* Items */}
      <nav className="flex-1 px-1 py-2">
        <p className="text-xs text-[#99BACE] uppercase tracking-wider mt-10"></p>
        <ul className="flex flex-col items-stretch gap-2">
          {items.map((it) => (
            <li key={it.key}>
              <a
                href={it.href || "#"}
                title={it.label}
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#F3F9FD] transition-colors text-[#0A2B42]`}
              >
                {/* Icon - accept string path or JSX */}
                {typeof it.icon === "string" ? (
                  <img
                    src={it.icon}
                    alt=""
                    className={
                      collapsed
                        ? "w-7 h-7 shrink-0"
                        : "w-7 h-7 shrink-0 sm:w-8 sm:h-8"
                    }
                  />
                ) : (
                  <span
                    className={
                      collapsed
                        ? "w-7 h-7 shrink-0"
                        : "w-7 h-7 shrink-0 sm:w-8 sm:h-8"
                    }
                  >
                    {it.icon}
                  </span>
                )}

                <span
                  className={`transition-all duration-200 ${
                    collapsed
                      ? "opacity-0 -translate-x-2 pointer-events-none text-sm"
                      : "opacity-100 translate-x-0 text-base"
                  }`}
                >
                  {it.label}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer - collapse toggle */}
      <div className="px-3 py-4 border-t border-[#EEF6FB]">
        <button
          onClick={() => setCollapsed((s) => !s)}
          aria-expanded={!collapsed}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#F3F9FD] transition-colors text-[#0A2B42]"
        >
          <img src="/Collapse.svg" alt="Collapse" className="w-5 h-5" />

          <span
            className={`text-sm ${
              collapsed ? "opacity-0 pointer-events-none" : "opacity-100"
            }`}
          >
            {collapsed ? "" : "Collapse"}
          </span>
        </button>
      </div>
    </aside>
  );
};

export default SideBar;
