import type * as React from "react";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

/**
 * Library-plus-detail shell: a fixed sidebar, a fixed top bar, and a single
 * scrolling content column. Only the content column scrolls, which is what
 * keeps the transcript's own scroll container behaving on the detail page.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
