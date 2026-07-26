"use client";

import { CalendarDays, CheckSquare, HelpCircle, TrendingUp } from "lucide-react";
import * as React from "react";

import { Avatar } from "@/components/ui/avatar";
import { formatTimestamp, splitOnQuery } from "@/lib/format";
import type { Sentence, Speaker } from "@/lib/types";
import { cn } from "@/lib/utils";

const INSIGHTS = [
  { key: "is_task", icon: CheckSquare, label: "Task", className: "text-brand-500" },
  { key: "is_question", icon: HelpCircle, label: "Question", className: "text-blue-500" },
  { key: "is_metric", icon: TrendingUp, label: "Metric", className: "text-teal-500" },
  { key: "is_date_time", icon: CalendarDays, label: "Date or time", className: "text-orange-500" },
] as const;

/**
 * One transcript line.
 *
 * Memoised because the parent re-renders on every animation frame while
 * playback runs. Without this, a 400-line transcript would re-render every line
 * sixty times a second; with it, only the two lines whose `isActive` actually
 * changed do any work.
 */
export const TranscriptLine = React.memo(function TranscriptLine({
  sentence,
  speaker,
  isActive,
  isCurrentMatch,
  query,
  showSpeaker,
  onSeek,
}: {
  sentence: Sentence;
  speaker: Speaker | undefined;
  isActive: boolean;
  isCurrentMatch: boolean;
  query: string;
  showSpeaker: boolean;
  onSeek: (ms: number) => void;
}) {
  const segments = React.useMemo(() => splitOnQuery(sentence.text, query), [sentence.text, query]);

  return (
    <div
      className={cn(
        "group flex gap-3 border-l-2 px-4 py-1.5 transition-colors",
        isActive ? "border-brand-500 bg-brand-25" : "border-transparent hover:bg-grey-25",
        showSpeaker && "mt-3 first:mt-0",
      )}
    >
      <div className="w-8 shrink-0">
        {showSpeaker ? (
          <Avatar name={speaker?.name ?? "Unknown"} colorKey={speaker?.color_key ?? 0} size="md" />
        ) : null}
      </div>

      <div className="min-w-0 flex-1">
        {showSpeaker ? (
          <p className="mb-0.5 text-[12px] font-semibold text-grey-900">
            {speaker?.name ?? "Unknown speaker"}
          </p>
        ) : null}

        <div className="flex items-start gap-2">
          {/* Clicking the timestamp seeks the player — the same action as
              clicking the line, kept visible because that is the affordance
              users look for. */}
          <button
            type="button"
            onClick={() => onSeek(sentence.start_ms)}
            className={cn(
              "mt-px w-11 shrink-0 text-left text-[11px] tabular-nums transition-colors",
              isActive ? "font-semibold text-brand-700" : "text-grey-400 hover:text-brand-600",
            )}
          >
            {formatTimestamp(sentence.start_ms)}
          </button>

          <button
            type="button"
            onClick={() => onSeek(sentence.start_ms)}
            className="min-w-0 flex-1 text-left text-[13px] leading-relaxed text-grey-700"
          >
            {segments.map((segment, index) =>
              segment.match ? (
                <mark key={index} data-active={isCurrentMatch ? "true" : undefined}>
                  {segment.text}
                </mark>
              ) : (
                <React.Fragment key={index}>{segment.text}</React.Fragment>
              ),
            )}
          </button>

          <span className="mt-0.5 flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            {INSIGHTS.filter((insight) => sentence[insight.key]).map((insight) => (
              <insight.icon
                key={insight.key}
                className={cn("h-3 w-3", insight.className)}
                aria-label={insight.label}
              />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
});
