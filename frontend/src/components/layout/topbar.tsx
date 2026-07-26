"use client";

import { Bell, ChevronDown, LifeBuoy, LogOut, Search, Settings, UserCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { CreateMeetingDialog } from "@/components/meetings/create-meeting-dialog";
import { Avatar } from "@/components/ui/avatar";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownLabel,
  DropdownSeparator,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import { useMe } from "@/hooks/use-api";

export function Topbar() {
  const router = useRouter();
  const { data: user } = useMe();
  const [query, setQuery] = React.useState("");

  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-grey-200 bg-white px-5">
      <form onSubmit={submitSearch} className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-grey-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search across all meetings…"
          aria-label="Search across all meetings"
          className="h-9 w-full rounded-sm bg-grey-50 pr-3 pl-9 text-sm text-grey-900 ring-1 ring-inset ring-grey-200 placeholder:text-grey-400 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
        />
      </form>

      <div className="ml-auto flex items-center gap-2">
        <CreateMeetingDialog />

        <button
          type="button"
          onClick={() => toast("No new notifications")}
          aria-label="Notifications"
          className="relative rounded-sm p-2 text-grey-500 transition-colors hover:bg-grey-100 hover:text-grey-700"
        >
          <Bell className="h-[18px] w-[18px]" />
        </button>

        <Dropdown>
          <DropdownTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-sm py-1 pr-1.5 pl-1 transition-colors hover:bg-grey-100"
            >
              <Avatar name={user?.name} colorKey={0} size="md" />
              <ChevronDown className="h-3.5 w-3.5 text-grey-400" />
            </button>
          </DropdownTrigger>

          <DropdownContent className="min-w-56">
            <div className="px-2.5 py-2">
              <p className="text-[13px] font-semibold text-grey-900">{user?.name ?? "Loading…"}</p>
              <p className="truncate text-[11px] text-grey-500">{user?.email}</p>
            </div>
            <DropdownSeparator />
            <DropdownLabel>Account</DropdownLabel>
            {/* Settings surfaces are placeholders, which the brief permits.
                They are wired to a toast rather than silently doing nothing —
                a dead menu item reads as a bug. */}
            <DropdownItem onSelect={() => toast("Profile settings are not part of this build")}>
              <UserCircle className="h-4 w-4 text-grey-400" />
              Profile
            </DropdownItem>
            <DropdownItem onSelect={() => router.push("/settings")}>
              <Settings className="h-4 w-4 text-grey-400" />
              Settings
            </DropdownItem>
            <DropdownItem onSelect={() => toast("Support is not part of this build")}>
              <LifeBuoy className="h-4 w-4 text-grey-400" />
              Help & support
            </DropdownItem>
            <DropdownSeparator />
            <DropdownItem
              destructive
              onSelect={() => toast("Authentication is mocked — you are always signed in")}
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </DropdownItem>
          </DropdownContent>
        </Dropdown>
      </div>
    </header>
  );
}
