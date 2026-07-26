"use client";

import { ArrowUpDown, Search, SlidersHorizontal, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownLabel,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import type { SortOption } from "@/lib/types";
import { cn } from "@/lib/utils";

const SORT_LABELS: Record<SortOption, string> = {
  recent: "Most recent",
  oldest: "Oldest first",
  longest: "Longest",
  shortest: "Shortest",
  title: "Title A–Z",
};

export interface Filters {
  q: string;
  participant: string;
  tag: string;
  dateFrom: string;
  dateTo: string;
  sort: SortOption;
}

export const EMPTY_FILTERS: Filters = {
  q: "",
  participant: "",
  tag: "",
  dateFrom: "",
  dateTo: "",
  sort: "recent",
};

export function FilterBar({
  filters,
  onChange,
  availableTags,
  resultCount,
}: {
  filters: Filters;
  onChange: (next: Filters) => void;
  availableTags: string[];
  resultCount?: number;
}) {
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    onChange({ ...filters, [key]: value });

  const hasActiveFilter = Boolean(
    filters.q || filters.participant || filters.tag || filters.dateFrom || filters.dateTo,
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-grey-400" />
          <input
            value={filters.q}
            onChange={(event) => set("q", event.target.value)}
            placeholder="Filter by title…"
            aria-label="Filter meetings by title"
            className="h-9 w-full rounded-sm bg-white pr-3 pl-9 text-sm ring-1 ring-inset ring-grey-300 placeholder:text-grey-400 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        <div className="relative min-w-[190px]">
          <input
            value={filters.participant}
            onChange={(event) => set("participant", event.target.value)}
            placeholder="Participant name or email"
            aria-label="Filter by participant"
            className="h-9 w-full rounded-sm bg-white px-3 text-sm ring-1 ring-inset ring-grey-300 placeholder:text-grey-400 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        <Dropdown>
          <DropdownTrigger asChild>
            <Button variant="secondary" size="md">
              <SlidersHorizontal className="h-3.5 w-3.5 text-grey-400" />
              {filters.tag || "All tags"}
            </Button>
          </DropdownTrigger>
          <DropdownContent align="start" className="max-h-72 overflow-y-auto">
            <DropdownLabel>Tag</DropdownLabel>
            <DropdownItem onSelect={() => set("tag", "")}>All tags</DropdownItem>
            {availableTags.map((tag) => (
              <DropdownItem key={tag} onSelect={() => set("tag", tag)}>
                {tag}
              </DropdownItem>
            ))}
          </DropdownContent>
        </Dropdown>

        <Dropdown>
          <DropdownTrigger asChild>
            <Button variant="secondary" size="md">
              <ArrowUpDown className="h-3.5 w-3.5 text-grey-400" />
              {SORT_LABELS[filters.sort]}
            </Button>
          </DropdownTrigger>
          <DropdownContent align="end">
            <DropdownLabel>Sort by</DropdownLabel>
            {(Object.keys(SORT_LABELS) as SortOption[]).map((option) => (
              <DropdownItem
                key={option}
                onSelect={() => set("sort", option)}
                className={cn(filters.sort === option && "font-semibold text-brand-700")}
              >
                {SORT_LABELS[option]}
              </DropdownItem>
            ))}
          </DropdownContent>
        </Dropdown>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[12px] text-grey-500">
        <label className="inline-flex items-center gap-1.5">
          <span>From</span>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(event) => set("dateFrom", event.target.value)}
            className="h-8 rounded-sm bg-white px-2 text-[12px] ring-1 ring-inset ring-grey-300 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </label>
        <label className="inline-flex items-center gap-1.5">
          <span>to</span>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(event) => set("dateTo", event.target.value)}
            className="h-8 rounded-sm bg-white px-2 text-[12px] ring-1 ring-inset ring-grey-300 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </label>

        {hasActiveFilter ? (
          <button
            type="button"
            onClick={() => onChange({ ...EMPTY_FILTERS, sort: filters.sort })}
            className="inline-flex items-center gap-1 rounded-sm px-2 py-1 text-brand-700 transition-colors hover:bg-brand-50"
          >
            <X className="h-3 w-3" />
            Clear filters
          </button>
        ) : null}

        {resultCount !== undefined ? (
          <span className="ml-auto tabular-nums">
            {resultCount} {resultCount === 1 ? "meeting" : "meetings"}
          </span>
        ) : null}
      </div>
    </div>
  );
}
