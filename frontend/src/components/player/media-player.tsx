"use client";

import { Pause, Play, Redo2, Undo2, Volume2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import { formatTimestamp } from "@/lib/format";
import { cn } from "@/lib/utils";
import { usePlayer } from "./player-provider";

const BAR_COUNT = 96;
const RATES = [0.75, 1, 1.25, 1.5, 2];

/**
 * Deterministic pseudo-random bar heights, seeded from the meeting id.
 *
 * Fireflies renders a waveform behind its seek bar. There is no audio here to
 * analyse, so the shape is generated — but generated *stably*, from a seeded
 * PRNG rather than Math.random(). A waveform that reshuffles on every render
 * would be worse than no waveform at all.
 */
function waveformBars(seed: number): number[] {
  let state = seed * 2654435761;
  return Array.from({ length: BAR_COUNT }, (_, index) => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    const random = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    // Taper the ends so it reads as a clip rather than a bar chart.
    const envelope = Math.sin((index / BAR_COUNT) * Math.PI) * 0.55 + 0.45;
    return Math.max(0.16, random * envelope);
  });
}

export function MediaPlayer({ meetingId }: { meetingId: number }) {
  const { currentMs, durationMs, isPlaying, rate, hasRealMedia, toggle, seek, skip, setRate } =
    usePlayer();

  const bars = React.useMemo(() => waveformBars(meetingId), [meetingId]);
  const trackRef = React.useRef<HTMLDivElement | null>(null);
  const progress = durationMs > 0 ? currentMs / durationMs : 0;

  function seekFromPointer(event: React.PointerEvent<HTMLDivElement>) {
    const track = trackRef.current;
    if (!track) return;
    const bounds = track.getBoundingClientRect();
    const ratio = (event.clientX - bounds.left) / bounds.width;
    seek(Math.min(Math.max(ratio, 0), 1) * durationMs);
  }

  return (
    <div className="rounded-lg bg-white p-3.5 ring-1 ring-grey-200">
      <div className="flex items-center gap-3">
        <Button
          variant="primary"
          size="icon"
          onClick={toggle}
          aria-label={isPlaying ? "Pause" : "Play"}
          className="h-9 w-9 rounded-full"
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="ml-0.5 h-4 w-4" />}
        </Button>

        <Button variant="ghost" size="icon" onClick={() => skip(-15_000)} aria-label="Back 15 seconds">
          <Undo2 className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={() => skip(15_000)} aria-label="Forward 15 seconds">
          <Redo2 className="h-4 w-4" />
        </Button>

        <span className="w-[92px] shrink-0 text-[12px] text-grey-500 tabular-nums">
          {formatTimestamp(currentMs)} / {formatTimestamp(durationMs)}
        </span>

        {/* The waveform doubles as the seek bar: click or drag anywhere on it. */}
        <div
          ref={trackRef}
          role="slider"
          tabIndex={0}
          aria-label="Seek"
          aria-valuemin={0}
          aria-valuemax={Math.round(durationMs / 1000)}
          aria-valuenow={Math.round(currentMs / 1000)}
          aria-valuetext={`${formatTimestamp(currentMs)} of ${formatTimestamp(durationMs)}`}
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            seekFromPointer(event);
          }}
          onPointerMove={(event) => {
            if (event.buttons === 1) seekFromPointer(event);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") skip(5_000);
            if (event.key === "ArrowLeft") skip(-5_000);
            if (event.key === " ") {
              event.preventDefault();
              toggle();
            }
          }}
          className="flex h-10 flex-1 cursor-pointer items-center gap-px focus:outline-2 focus:outline-offset-2 focus:outline-brand-500"
        >
          {bars.map((height, index) => (
            <span
              key={index}
              style={{ height: `${Math.round(height * 100)}%` }}
              className={cn(
                "flex-1 rounded-xs transition-colors",
                index / BAR_COUNT <= progress ? "bg-brand-500" : "bg-grey-200",
              )}
            />
          ))}
        </div>

        <Dropdown>
          <DropdownTrigger asChild>
            <Button variant="ghost" size="sm" className="w-14 shrink-0 justify-center tabular-nums">
              {rate}×
            </Button>
          </DropdownTrigger>
          <DropdownContent className="min-w-20">
            {RATES.map((option) => (
              <DropdownItem
                key={option}
                onSelect={() => setRate(option)}
                className={cn(rate === option && "font-semibold text-brand-700")}
              >
                {option}×
              </DropdownItem>
            ))}
          </DropdownContent>
        </Dropdown>
      </div>

      {!hasRealMedia ? (
        <p className="mt-2 flex items-center gap-1.5 border-t border-grey-100 pt-2 text-[11px] text-grey-400">
          <Volume2 className="h-3 w-3" />
          No audio file attached — playback runs on a synthetic clock derived from the transcript
          timings, so seeking and transcript sync still work.
        </p>
      ) : null}
    </div>
  );
}
