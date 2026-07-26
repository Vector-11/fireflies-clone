"use client";

import { Clock, Search as SearchIcon, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useSearch, useTimeZone } from "@/hooks/use-api";
import { useDebounce } from "@/hooks/use-debounce";
import { useQueryParam } from "@/hooks/use-query-param";
import { formatDuration, formatShortDate, formatTimestamp, splitSnippet } from "@/lib/format";

export default function SearchPage() {
  const router = useRouter();
  const initial = useQueryParam("q");
  const timeZone = useTimeZone();

  const [query, setQuery] = React.useState("");
  const debounced = useDebounce(query, 300);
  const { data, isFetching } = useSearch(debounced);

  // Seed the box from ?q= once, so arriving from the top bar runs the search
  // immediately — but typing afterwards is not fought by the URL.
  const seeded = React.useRef(false);
  React.useEffect(() => {
    if (!seeded.current && initial) {
      seeded.current = true;
      setQuery(initial);
    }
  }, [initial]);

  // Keep the URL in step so a search is shareable and survives a refresh.
  React.useEffect(() => {
    const next = debounced.trim() ? `/search?q=${encodeURIComponent(debounced.trim())}` : "/search";
    router.replace(next, { scroll: false });
  }, [debounced, router]);

  const totalHits = data?.results.reduce((sum, result) => sum + result.match_count, 0) ?? 0;

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <h1 className="text-xl font-semibold text-grey-900">Search</h1>
      <p className="mt-0.5 text-[13px] text-grey-500">
        Full-text search across every transcript in the workspace.
      </p>

      <div className="relative mt-4">
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-grey-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try “pricing”, “offline recording”, “renewal risk”…"
          aria-label="Search transcripts"
          autoFocus
          className="h-11 w-full rounded-lg bg-white pr-4 pl-10 text-sm ring-1 ring-inset ring-grey-300 placeholder:text-grey-400 focus:ring-2 focus:ring-brand-500 focus:outline-none"
        />
      </div>

      {debounced.trim() ? (
        <p className="mt-3 flex items-center gap-2 text-[12px] text-grey-500">
          {isFetching ? (
            "Searching…"
          ) : (
            <>
              <span>
                {totalHits} {totalHits === 1 ? "result" : "results"} in {data?.total_meetings ?? 0}{" "}
                {data?.total_meetings === 1 ? "meeting" : "meetings"}
              </span>
              {/* The backend reports whether the FTS5 index answered or the
                  LIKE fallback did, so the UI can be honest about ranking
                  rather than implying relevance it does not have. */}
              {data?.ranked ? (
                <span
                  className="inline-flex items-center gap-1 rounded-sm bg-teal-50 px-1.5 py-0.5 text-[11px] font-medium text-teal-600 ring-1 ring-teal-100 ring-inset"
                  title="Ranked by SQLite FTS5 using bm25 relevance scoring"
                >
                  <Zap className="h-2.5 w-2.5" />
                  bm25 ranked
                </span>
              ) : null}
            </>
          )}
        </p>
      ) : null}

      <div className="mt-4 space-y-3">
        {isFetching && !data
          ? Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-28 w-full rounded-lg" />
            ))
          : null}

        {data?.results.map((result) => (
          <article key={result.meeting_id} className="rounded-lg bg-white p-4 ring-1 ring-grey-200">
            <div className="flex items-start justify-between gap-3">
              <Link
                href={`/meetings/${result.meeting_id}`}
                className="text-[14px] font-semibold text-grey-900 hover:text-brand-700"
              >
                {result.title}
              </Link>
              <span className="shrink-0 text-[11px] text-grey-400">
                {result.match_count} {result.match_count === 1 ? "match" : "matches"}
              </span>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-3 text-[11px] text-grey-500">
              <span>{formatShortDate(result.date, timeZone)}</span>
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDuration(result.duration_seconds)}
              </span>
              {result.meeting_type ? <span>{result.meeting_type}</span> : null}
            </div>

            {result.hits.length ? (
              <ul className="mt-3 space-y-1.5 border-t border-grey-100 pt-3">
                {result.hits.map((hit) => (
                  <li key={hit.sentence_id}>
                    {/* Deep link: opens the meeting with the player already
                        parked on the line that matched. */}
                    <Link
                      href={`/meetings/${result.meeting_id}?t=${hit.start_ms}`}
                      className="group flex gap-2.5 rounded-sm px-1.5 py-1 transition-colors hover:bg-grey-25"
                    >
                      <span className="mt-px w-10 shrink-0 text-[11px] text-brand-600 tabular-nums group-hover:text-brand-800">
                        {formatTimestamp(hit.start_ms)}
                      </span>
                      <span className="min-w-0 flex-1 text-[12px] leading-relaxed text-grey-600">
                        {hit.speaker_name ? (
                          <span className="font-medium text-grey-800">{hit.speaker_name}: </span>
                        ) : null}
                        {splitSnippet(hit.snippet).map((segment, index) =>
                          segment.match ? (
                            <mark key={index}>{segment.text}</mark>
                          ) : (
                            <React.Fragment key={index}>{segment.text}</React.Fragment>
                          ),
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-[12px] text-grey-400 italic">Matched on the meeting title.</p>
            )}
          </article>
        ))}

        {debounced.trim() && !isFetching && data?.results.length === 0 ? (
          <EmptyState
            icon={SearchIcon}
            title={`Nothing matches “${debounced.trim()}”`}
            description="Search covers every transcript line and every meeting title. Try a shorter or more common term."
          />
        ) : null}

        {!debounced.trim() ? (
          <EmptyState
            icon={SearchIcon}
            title="Search every conversation"
            description="Indexed with SQLite FTS5, so results come back ranked by relevance with the matching line quoted — not just a list of meetings that contain the word somewhere."
          />
        ) : null}
      </div>
    </div>
  );
}
