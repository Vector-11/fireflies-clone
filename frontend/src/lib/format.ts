/** Player-style clock: 4:07, or 1:04:07 once a meeting passes an hour. */
export function formatTimestamp(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (value: number) => value.toString().padStart(2, "0");
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`;
}

/** Human duration for the library rows: "8m", "1h 12m". */
export function formatDuration(totalSeconds: number): string {
  if (!totalSeconds) return "0m";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.round((totalSeconds % 3600) / 60);
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${Math.max(minutes, 1)}m`;
}

/*
 * Dates are rendered in the *workspace* timezone, not the browser's.
 *
 * The backend stores every timestamp in UTC, which is correct. Rendering it in
 * whatever timezone the viewer happens to be sitting in is not: a 10am standup
 * would read as 04:30 to one person and 23:00 to another, and "Today" would
 * flip depending on who opened the page. A meeting happened at a time, in a
 * place — so the user's configured timezone is the one that means something.
 *
 * `Intl.DateTimeFormat` does the conversion natively, so this needs no
 * timezone library. Passing `undefined` falls back to the browser, which is the
 * right behaviour while the user profile is still loading.
 */

/** YYYY-MM-DD in the given zone — used to compare calendar days. */
function dayKey(date: Date, timeZone?: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function clockTime(date: Date, timeZone?: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function calendarLabel(date: Date, timeZone: string | undefined, sameYear: boolean): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone,
    weekday: "short",
    day: "numeric",
    month: "short",
    ...(sameYear ? {} : { year: "numeric" }),
  }).format(date);
}

/** "Today · 10:00", "Yesterday · 09:30", "Mon, 21 Jul · 15:00". */
export function formatMeetingDate(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  const now = new Date();
  const time = clockTime(date, timeZone);

  const key = dayKey(date, timeZone);
  const todayKey = dayKey(now, timeZone);
  if (key === todayKey) return `Today · ${time}`;
  if (key === dayKey(new Date(now.getTime() - 86_400_000), timeZone)) {
    return `Yesterday · ${time}`;
  }

  return `${calendarLabel(date, timeZone, key.slice(0, 4) === todayKey.slice(0, 4))} · ${time}`;
}

export function formatShortDate(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  const now = new Date();
  const key = dayKey(date, timeZone);
  const todayKey = dayKey(now, timeZone);

  if (key === todayKey) return "Today";
  if (key === dayKey(new Date(now.getTime() - 86_400_000), timeZone)) return "Yesterday";

  return new Intl.DateTimeFormat("en-GB", {
    timeZone,
    day: "numeric",
    month: "short",
    ...(key.slice(0, 4) === todayKey.slice(0, 4) ? {} : { year: "numeric" }),
  }).format(date);
}

/** Up to two initials, e.g. "Priyanshu Giri" -> "PG". */
export function initials(name: string | null | undefined, fallback = "?"): string {
  if (!name?.trim()) return fallback;
  const parts = name.trim().split(/\s+/);
  const letters = parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[parts.length - 1][0];
  return letters.toUpperCase();
}

/**
 * Look up a speaker's colour by the index stored on their row.
 * Modulo keeps it in range if a meeting somehow has more than eight voices.
 */
export function speakerColor(colorKey: number): string {
  return `var(--speaker-${((colorKey % 8) + 8) % 8})`;
}

const TAG_STYLES: Record<string, string> = {
  purple: "bg-brand-50 text-brand-700 ring-brand-200",
  teal: "bg-teal-50 text-teal-600 ring-teal-100",
  blue: "bg-blue-50 text-blue-600 ring-blue-100",
  yellow: "bg-warning-50 text-warning-700 ring-warning-100",
  green: "bg-success-50 text-success-700 ring-success-100",
  fuchsia: "bg-fuchsia-50 text-fuchsia-600 ring-fuchsia-100",
  orange: "bg-orange-50 text-orange-600 ring-orange-100",
};

export function tagClasses(color: string): string {
  return TAG_STYLES[color] ?? TAG_STYLES.purple;
}

export interface TextSegment {
  text: string;
  match: boolean;
}

/**
 * Split text into matched and unmatched runs for highlighting.
 *
 * Returns segments rather than an HTML string on purpose: React renders them as
 * elements, so a transcript line containing "<script>" is displayed, never
 * executed. The alternative — building markup and using
 * dangerouslySetInnerHTML — would make every transcript an injection vector.
 */
export function splitOnQuery(text: string, query: string): TextSegment[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [{ text, match: false }];

  const segments: TextSegment[] = [];
  const haystack = text.toLowerCase();
  let cursor = 0;

  for (;;) {
    const found = haystack.indexOf(needle, cursor);
    if (found === -1) break;
    if (found > cursor) segments.push({ text: text.slice(cursor, found), match: false });
    segments.push({ text: text.slice(found, found + needle.length), match: true });
    cursor = found + needle.length;
  }

  if (cursor < text.length) segments.push({ text: text.slice(cursor), match: false });
  return segments.length ? segments : [{ text, match: false }];
}

/**
 * Split a server-rendered FTS5 snippet into segments.
 *
 * `snippet()` wraps matches in <mark> tags, and the obvious way to render that
 * is dangerouslySetInnerHTML — which would be an XSS hole, because everything
 * around those tags is raw transcript text that a user uploaded. Splitting on
 * the markers and returning segments means React renders every part as a text
 * node: a transcript containing "<script>" is displayed, never executed.
 */
export function splitSnippet(snippet: string): TextSegment[] {
  const segments: TextSegment[] = [];
  const pattern = /<mark>([\s\S]*?)<\/mark>/g;
  let cursor = 0;
  let found: RegExpExecArray | null;

  while ((found = pattern.exec(snippet)) !== null) {
    if (found.index > cursor) {
      segments.push({ text: snippet.slice(cursor, found.index), match: false });
    }
    segments.push({ text: found[1], match: true });
    cursor = found.index + found[0].length;
  }

  if (cursor < snippet.length) segments.push({ text: snippet.slice(cursor), match: false });
  return segments;
}

export function countMatches(text: string, query: string): number {
  const needle = query.trim().toLowerCase();
  if (!needle) return 0;
  return splitOnQuery(text, needle).filter((segment) => segment.match).length;
}
