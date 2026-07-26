"use client";

import {
  BarChart3,
  Hash,
  Home,
  LayoutGrid,
  type LucideIcon,
  Notebook,
  Plug,
  Scissors,
  Search,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Mocked surfaces get a muted "Soon" chip, as the brief permits. */
  soon?: boolean;
}

/**
 * Navigation mirrors Fireflies' own information architecture and vocabulary —
 * Notebook, Soundbites, Channels, AI Apps, AskFred. Getting the *names* right
 * matters as much as the layout: a sidebar reading "Notes / Files / Reports"
 * would feel like a different product no matter how it were styled.
 */
const SECTIONS: { heading: string | null; items: NavItem[] }[] = [
  {
    heading: null,
    items: [
      { href: "/", label: "Home", icon: Home },
      { href: "/meetings", label: "Notebook", icon: Notebook },
      { href: "/search", label: "Search", icon: Search },
      { href: "/askfred", label: "AskFred", icon: Sparkles, soon: true },
    ],
  },
  {
    heading: "Workspace",
    items: [
      { href: "/soundbites", label: "Soundbites", icon: Scissors, soon: true },
      { href: "/channels", label: "Channels", icon: Hash, soon: true },
      { href: "/apps", label: "AI Apps", icon: LayoutGrid, soon: true },
      { href: "/analytics", label: "Analytics", icon: BarChart3, soon: true },
    ],
  },
  {
    heading: "Setup",
    items: [
      { href: "/integrations", label: "Integrations", icon: Plug, soon: true },
      { href: "/team", label: "Team", icon: Users, soon: true },
      { href: "/settings", label: "Settings", icon: Settings, soon: true },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <aside className="flex h-full w-[228px] shrink-0 flex-col border-r border-grey-200 bg-white">
      <Link href="/" className="flex items-center gap-2.5 px-5 py-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-500 text-sm">
          <span aria-hidden>🪰</span>
        </span>
        <span className="font-display text-[15px] font-semibold text-grey-900">Fireflies</span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {SECTIONS.map((section, index) => (
          <div key={section.heading ?? index} className={cn(index > 0 && "mt-5")}>
            {section.heading ? (
              <p className="px-2.5 pb-1.5 text-[11px] font-semibold tracking-wide text-grey-400 uppercase">
                {section.heading}
              </p>
            ) : null}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group flex items-center gap-2.5 rounded-sm px-2.5 py-[7px] text-[13px] font-medium transition-colors",
                        active
                          ? "bg-brand-50 text-brand-700"
                          : "text-grey-600 hover:bg-grey-50 hover:text-grey-900",
                      )}
                    >
                      <item.icon
                        className={cn(
                          "h-[15px] w-[15px] shrink-0",
                          active ? "text-brand-600" : "text-grey-400 group-hover:text-grey-600",
                        )}
                      />
                      <span className="flex-1 truncate">{item.label}</span>
                      {item.soon ? (
                        <span className="rounded-xs bg-grey-100 px-1 py-px text-[9px] font-semibold tracking-wide text-grey-400 uppercase">
                          Soon
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-grey-100 p-3">
        <div className="rounded-lg bg-grey-25 p-3 ring-1 ring-grey-100">
          <p className="text-[11px] font-semibold text-grey-700">Fred is idle</p>
          <p className="mt-0.5 text-[11px] leading-snug text-grey-500">
            Live meeting capture is not available in this build.
          </p>
        </div>
      </div>
    </aside>
  );
}
