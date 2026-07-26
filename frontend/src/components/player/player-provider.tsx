"use client";

import * as React from "react";

/**
 * Playback state for a meeting.
 *
 * There is no real audio in this dataset, which leaves two options: fake the
 * seek bar so it looks right but does nothing, or make playback real against a
 * synthetic clock. This does the second.
 *
 * The provider exposes one interface and satisfies it two ways — from a real
 * `<audio>` element when the meeting has an `audio_url`, and from a
 * requestAnimationFrame clock when it does not. Nothing downstream knows or
 * cares which: the transcript's click-to-seek, the active-line highlight and
 * the progress bar all work identically. Attaching real media later means
 * setting one field on the meeting row.
 */
interface PlayerContextValue {
  currentMs: number;
  durationMs: number;
  isPlaying: boolean;
  rate: number;
  /** True when a real media element is driving the clock. */
  hasRealMedia: boolean;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (ms: number) => void;
  skip: (deltaMs: number) => void;
  setRate: (rate: number) => void;
}

const PlayerContext = React.createContext<PlayerContextValue | null>(null);

export function usePlayer(): PlayerContextValue {
  const context = React.useContext(PlayerContext);
  if (!context) throw new Error("usePlayer must be used inside a <PlayerProvider>");
  return context;
}

export function PlayerProvider({
  durationMs,
  audioUrl,
  initialMs = 0,
  children,
}: {
  durationMs: number;
  audioUrl?: string | null;
  /** Start position, used by ?t= deep links from search results. */
  initialMs?: number;
  children: React.ReactNode;
}) {
  const [currentMs, setCurrentMs] = React.useState(initialMs);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [rate, setRateState] = React.useState(1);

  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const hasRealMedia = Boolean(audioUrl);

  // Mirror of currentMs, so the frame loop and the callbacks can read the
  // latest position without taking it as a dependency and re-subscribing.
  const currentMsRef = React.useRef(currentMs);
  currentMsRef.current = currentMs;

  /*
   * The synthetic clock is anchored to wall time rather than accumulated from
   * per-frame deltas: on each frame the position is
   * `anchor.media + (now - anchor.wall) * rate`.
   *
   * Summing deltas looks equivalent and is not. It accrues rounding drift over
   * a long meeting, and — the visible problem — browsers suspend
   * requestAnimationFrame entirely while a tab is hidden, so a delta-summing
   * clock silently pauses and resumes minutes behind. Anchoring means the
   * position is always derived from elapsed real time, so returning to the tab
   * lands where audio would have been.
   */
  const anchorRef = React.useRef<{ wall: number; media: number } | null>(null);

  // One animation-frame loop drives both modes. Reading the media element on
  // every frame rather than listening for `timeupdate` matters: that event
  // fires roughly four times a second, which is visibly choppy when it is
  // moving a highlight down a transcript.
  React.useEffect(() => {
    if (!isPlaying) return;

    anchorRef.current ??= { wall: performance.now(), media: currentMsRef.current };

    let frame = requestAnimationFrame(function tick() {
      const audio = audioRef.current;

      if (audio) {
        setCurrentMs(audio.currentTime * 1000);
      } else {
        const anchor = anchorRef.current;
        if (anchor) {
          const next = anchor.media + (performance.now() - anchor.wall) * rate;
          if (next >= durationMs) {
            setCurrentMs(durationMs);
            setIsPlaying(false);
            anchorRef.current = null;
            return;
          }
          setCurrentMs(next);
        }
      }

      frame = requestAnimationFrame(tick);
    });

    return () => cancelAnimationFrame(frame);
  }, [isPlaying, rate, durationMs]);

  // Restart from the beginning if play is pressed at the end of the meeting.
  const play = React.useCallback(() => {
    const from = currentMsRef.current >= durationMs ? 0 : currentMsRef.current;
    setCurrentMs(from);
    anchorRef.current = { wall: performance.now(), media: from };
    audioRef.current?.play().catch(() => undefined);
    setIsPlaying(true);
  }, [durationMs]);

  const pause = React.useCallback(() => {
    audioRef.current?.pause();
    anchorRef.current = null;
    setIsPlaying(false);
  }, []);

  const toggle = React.useCallback(() => {
    if (isPlaying) pause();
    else play();
  }, [isPlaying, pause, play]);

  const seek = React.useCallback(
    (ms: number) => {
      const clamped = Math.min(Math.max(ms, 0), durationMs);
      setCurrentMs(clamped);
      // Re-anchor, or the next frame would compute from the old origin and
      // undo the seek.
      if (anchorRef.current) anchorRef.current = { wall: performance.now(), media: clamped };
      if (audioRef.current) audioRef.current.currentTime = clamped / 1000;
    },
    [durationMs],
  );

  const skip = React.useCallback(
    (deltaMs: number) => seek(currentMs + deltaMs),
    [currentMs, seek],
  );

  const setRate = React.useCallback((next: number) => {
    // Re-anchor first, so a rate change applies from this moment rather than
    // retroactively rescaling the time already played.
    if (anchorRef.current) {
      anchorRef.current = { wall: performance.now(), media: currentMsRef.current };
    }
    setRateState(next);
    if (audioRef.current) audioRef.current.playbackRate = next;
  }, []);

  const value = React.useMemo<PlayerContextValue>(
    () => ({
      currentMs,
      durationMs,
      isPlaying,
      rate,
      hasRealMedia,
      play,
      pause,
      toggle,
      seek,
      skip,
      setRate,
    }),
    [currentMs, durationMs, isPlaying, rate, hasRealMedia, play, pause, toggle, seek, skip, setRate],
  );

  return (
    <PlayerContext.Provider value={value}>
      {audioUrl ? (
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          onEnded={() => setIsPlaying(false)}
          className="hidden"
        />
      ) : null}
      {children}
    </PlayerContext.Provider>
  );
}

/**
 * Find the index of the line playing at `ms`.
 *
 * Binary search, not a linear scan: this runs on every animation frame, and a
 * 400-line transcript at 60fps is 24,000 comparisons a second the naive way.
 * Sentences are already ordered by start time, so the search is valid.
 */
export function findActiveIndex(starts: number[], ms: number): number {
  if (!starts.length || ms < starts[0]) return -1;

  let low = 0;
  let high = starts.length - 1;
  let answer = 0;

  while (low <= high) {
    const middle = (low + high) >> 1;
    if (starts[middle] <= ms) {
      answer = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }

  return answer;
}
