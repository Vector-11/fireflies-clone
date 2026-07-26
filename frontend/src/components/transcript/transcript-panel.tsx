"use client";

import {
  CalendarDays,
  CheckSquare,
  ChevronDown,
  ChevronUp,
  Crosshair,
  HelpCircle,
  Search,
  TrendingUp,
  X,
} from "lucide-react";
import * as React from "react";

import { findActiveIndex, usePlayer } from "@/components/player/player-provider";
import { Button } from "@/components/ui/button";
import { TranscriptSkeleton } from "@/components/ui/skeleton";
import { useTranscript } from "@/hooks/use-api";
import { countMatches } from "@/lib/format";
import type { InsightFilter, Speaker } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TranscriptLine } from "./transcript-line";

const FILTERS: { value: InsightFilter | "all"; label: string; icon?: typeof CheckSquare }[] = [
  { value: "all", label: "All" },
  { value: "task", label: "Tasks", icon: CheckSquare },
  { value: "question", label: "Questions", icon: HelpCircle },
  { value: "metric", label: "Metrics", icon: TrendingUp },
  { value: "datetime", label: "Dates", icon: CalendarDays },
];

export function TranscriptPanel({
  meetingId,
  speakers,
}: {
  meetingId: number;
  speakers: Speaker[];
}) {
  const { currentMs, seek } = usePlayer();

  const [filter, setFilter] = React.useState<InsightFilter | "all">("all");
  const [query, setQuery] = React.useState("");
  const [matchCursor, setMatchCursor] = React.useState(0);
  // Auto-follow is on until the user scrolls, then it stays off until they ask
  // for it back. Listening for wheel/touch rather than the scroll event avoids
  // having to distinguish user scrolling from our own scrollIntoView calls.
  const [following, setFollowing] = React.useState(true);

  const { data, isPending } = useTranscript(meetingId, filter === "all" ? undefined : filter);
  const sentences = React.useMemo(() => data?.sentences ?? [], [data]);

  const speakersById = React.useMemo(
    () => new Map(speakers.map((speaker) => [speaker.id, speaker])),
    [speakers],
  );

  const startTimes = React.useMemo(
    () => sentences.map((sentence) => sentence.start_ms),
    [sentences],
  );
  const activeIndex = findActiveIndex(startTimes, currentMs);

  // Indices of every line containing the search text, in reading order.
  const matchIndices = React.useMemo(() => {
    if (!query.trim()) return [];
    return sentences.reduce<number[]>((accumulator, sentence, index) => {
      if (countMatches(sentence.text, query) > 0) accumulator.push(index);
      return accumulator;
    }, []);
  }, [sentences, query]);

  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const lineRefs = React.useRef(new Map<number, HTMLDivElement>());

  const scrollToIndex = React.useCallback((index: number, smooth = true) => {
    const element = lineRefs.current.get(index);
    element?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
  }, []);

  // Keep the playing line in view.
  React.useEffect(() => {
    if (!following || activeIndex < 0) return;
    scrollToIndex(activeIndex);
  }, [activeIndex, following, scrollToIndex]);

  // A new search jumps to the first hit.
  React.useEffect(() => {
    setMatchCursor(0);
    if (matchIndices.length) {
      setFollowing(false);
      scrollToIndex(matchIndices[0]);
    }
  }, [matchIndices, scrollToIndex]);

  function stepMatch(delta: number) {
    if (!matchIndices.length) return;
    const next = (matchCursor + delta + matchIndices.length) % matchIndices.length;
    setMatchCursor(next);
    setFollowing(false);
    scrollToIndex(matchIndices[next]);
  }

  function handleSeek(ms: number) {
    seek(ms);
    setFollowing(true);
  }

  const totalMatches = matchIndices.length;

  return (
    <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg bg-white ring-1 ring-grey-200">
      <div className="shrink-0 space-y-2.5 border-b border-grey-100 p-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-grey-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search in transcript…"
              aria-label="Search in transcript"
              className="h-8 w-full rounded-sm bg-grey-50 pr-20 pl-8 text-[13px] ring-1 ring-inset ring-grey-200 placeholder:text-grey-400 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
            {query ? (
              <div className="absolute top-1/2 right-1 flex -translate-y-1/2 items-center gap-0.5">
                <span className="mr-1 text-[11px] text-grey-500 tabular-nums">
                  {totalMatches ? `${matchCursor + 1}/${totalMatches}` : "0"}
                </span>
                <button
                  type="button"
                  onClick={() => stepMatch(-1)}
                  disabled={!totalMatches}
                  aria-label="Previous match"
                  className="rounded-xs p-0.5 text-grey-400 hover:bg-grey-200 disabled:opacity-40"
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => stepMatch(1)}
                  disabled={!totalMatches}
                  aria-label="Next match"
                  className="rounded-xs p-0.5 text-grey-400 hover:bg-grey-200 disabled:opacity-40"
                >
                  <ChevronDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Clear search"
                  className="rounded-xs p-0.5 text-grey-400 hover:bg-grey-200"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : null}
          </div>
        </div>

        {/* Filter pills, backed by the four boolean columns the insight tagger
            wrote at ingestion — so this is a filtered query, not a client-side
            regex run on every keystroke. */}
        <div className="flex flex-wrap items-center gap-1">
          {FILTERS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              className={cn(
                "inline-flex items-center gap-1 rounded-sm px-2 py-1 text-[12px] font-medium transition-colors",
                filter === option.value
                  ? "bg-brand-50 text-brand-700 ring-1 ring-brand-200 ring-inset"
                  : "text-grey-500 hover:bg-grey-100 hover:text-grey-700",
              )}
            >
              {option.icon ? <option.icon className="h-3 w-3" /> : null}
              {option.label}
            </button>
          ))}
          <span className="ml-auto text-[11px] text-grey-400 tabular-nums">
            {sentences.length} lines
          </span>
        </div>
      </div>

      <div
        ref={containerRef}
        onWheel={() => setFollowing(false)}
        onTouchMove={() => setFollowing(false)}
        className="relative min-h-0 flex-1 overflow-y-auto py-3"
      >
        {isPending ? (
          <TranscriptSkeleton />
        ) : sentences.length === 0 ? (
          <p className="px-5 py-10 text-center text-[13px] text-grey-500">
            {filter === "all"
              ? "This meeting has no transcript yet."
              : "No lines match that filter."}
          </p>
        ) : (
          sentences.map((sentence, index) => {
            const previous = sentences[index - 1];
            return (
              <div
                key={sentence.id}
                ref={(element) => {
                  if (element) lineRefs.current.set(index, element);
                  else lineRefs.current.delete(index);
                }}
              >
                <TranscriptLine
                  sentence={sentence}
                  speaker={
                    sentence.speaker_id ? speakersById.get(sentence.speaker_id) : undefined
                  }
                  isActive={index === activeIndex}
                  isCurrentMatch={matchIndices[matchCursor] === index}
                  query={query}
                  // Only label a line when the speaker changes, the way a
                  // written transcript groups a person's consecutive lines.
                  showSpeaker={!previous || previous.speaker_id !== sentence.speaker_id}
                  onSeek={handleSeek}
                />
              </div>
            );
          })
        )}
      </div>

      {!following && activeIndex >= 0 ? (
        <div className="pointer-events-none absolute right-0 bottom-4 left-0 flex justify-center">
          <Button
            variant="primary"
            size="sm"
            className="pointer-events-auto rounded-full shadow-lg"
            onClick={() => {
              setFollowing(true);
              scrollToIndex(activeIndex);
            }}
          >
            <Crosshair className="h-3.5 w-3.5" />
            Jump to current
          </Button>
        </div>
      ) : null}
    </section>
  );
}
