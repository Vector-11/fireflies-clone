"use client";

import { Notebook } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { MeetingRowSkeleton } from "@/components/ui/skeleton";
import { useAnalytics, useMeetings } from "@/hooks/use-api";
import { useDebounce } from "@/hooks/use-debounce";
import { CreateMeetingDialog } from "./create-meeting-dialog";
import { EMPTY_FILTERS, FilterBar, type Filters } from "./filter-bar";
import { MeetingRow } from "./meeting-row";

const PAGE_SIZE = 10;

export function MeetingsView() {
  const [filters, setFilters] = React.useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = React.useState(1);

  // Free-text fields are debounced; the dropdowns and dates are not, because
  // those change once per interaction rather than once per keystroke.
  const debouncedQuery = useDebounce(filters.q, 300);
  const debouncedParticipant = useDebounce(filters.participant, 300);

  const { data: analytics } = useAnalytics();
  const { data, isPending, isError, error, refetch, isFetching } = useMeetings({
    q: debouncedQuery || undefined,
    participant: debouncedParticipant || undefined,
    tag: filters.tag || undefined,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
    sort: filters.sort,
    page,
    page_size: PAGE_SIZE,
  });

  // Any change to a filter invalidates the current page number.
  function updateFilters(next: Filters) {
    setFilters(next);
    setPage(1);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const hasFilters = Boolean(
    filters.q || filters.participant || filters.tag || filters.dateFrom || filters.dateTo,
  );

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      {/* No "New meeting" button here — it lives in the top bar, where it is
          reachable from every page. Two of them side by side read as a bug. */}
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-grey-900">Notebook</h1>
        <p className="mt-0.5 text-[13px] text-grey-500">
          Every meeting Fred has captured, with transcripts, summaries and action items.
        </p>
      </div>

      <FilterBar
        filters={filters}
        onChange={updateFilters}
        availableTags={(analytics?.top_tags ?? []).map((tag) => tag.name)}
        resultCount={data?.total}
      />

      <div className="mt-4 overflow-hidden rounded-lg bg-white ring-1 ring-grey-200">
        {isPending ? (
          Array.from({ length: 5 }).map((_, index) => <MeetingRowSkeleton key={index} />)
        ) : isError ? (
          <div className="px-6 py-14 text-center">
            <p className="text-sm font-medium text-grey-900">Could not load your meetings</p>
            <p className="mx-auto mt-1 max-w-md text-[13px] text-grey-500">
              {error instanceof Error ? error.message : "Something went wrong."}
            </p>
            <Button variant="secondary" className="mt-5" onClick={() => refetch()}>
              Try again
            </Button>
          </div>
        ) : data && data.items.length > 0 ? (
          <div className={isFetching ? "opacity-60 transition-opacity" : undefined}>
            {data.items.map((meeting) => (
              <MeetingRow key={meeting.id} meeting={meeting} />
            ))}
          </div>
        ) : hasFilters ? (
          <EmptyState
            icon={Notebook}
            title="No meetings match those filters"
            description="Try a different title, participant or tag — or clear the filters to see everything."
            action={
              <Button variant="secondary" onClick={() => updateFilters(EMPTY_FILTERS)}>
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={Notebook}
            title="Your notebook is empty"
            description="Add a meeting by pasting a transcript or uploading a .txt, .vtt, .srt or .json file."
            action={<CreateMeetingDialog />}
          />
        )}
      </div>

      {data && totalPages > 1 ? (
        <div className="mt-4 flex items-center justify-between text-[13px] text-grey-500">
          <span>
            Page {data.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
