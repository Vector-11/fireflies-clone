"use client";

import {
  ArrowLeft,
  CalendarDays,
  Clock,
  ExternalLink,
  MoreHorizontal,
  Pencil,
  Trash2,
  Upload,
  Users,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { MediaPlayer } from "@/components/player/media-player";
import { PlayerProvider } from "@/components/player/player-provider";
import { ActionItems } from "@/components/summary/action-items";
import { SummaryPanel } from "@/components/summary/summary-panel";
import { TranscriptPanel } from "@/components/transcript/transcript-panel";
import { AvatarStack } from "@/components/ui/avatar";
import { TagBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import { Skeleton, TranscriptSkeleton } from "@/components/ui/skeleton";
import { useMeeting, useTimeZone, useTranscript, useUploadTranscript } from "@/hooks/use-api";
import { useQueryParam } from "@/hooks/use-query-param";
import { formatDuration, formatMeetingDate } from "@/lib/format";
import { DeleteMeetingDialog } from "./delete-meeting-dialog";
import { EditMeetingDialog } from "./edit-meeting-dialog";

export function MeetingDetail({ meetingId }: { meetingId: number }) {
  // Search results deep-link to a timestamp with ?t=<ms>, so opening a result
  // parks the player on the exact line that matched.
  const startAtMs = Number(useQueryParam("t") ?? 0) || 0;

  const timeZone = useTimeZone();
  const { data: meeting, isPending, isError, error } = useMeeting(meetingId);
  // The unfiltered transcript. The panel requests its own filtered copy; when
  // no filter is active React Query dedupes the two into one request.
  const { data: transcript } = useTranscript(meetingId);
  const uploadTranscript = useUploadTranscript(meetingId);

  const [editing, setEditing] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  if (isError) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h1 className="text-base font-semibold text-grey-900">Could not open this meeting</h1>
        <p className="mt-1 text-[13px] text-grey-500">
          {error instanceof Error ? error.message : "Something went wrong."}
        </p>
        <Button variant="secondary" className="mt-5" asChild>
          <Link href="/meetings">Back to notebook</Link>
        </Button>
      </div>
    );
  }

  if (isPending || !meeting) {
    return (
      <div className="px-6 py-6">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="mt-3 h-4 w-96" />
        <Skeleton className="mt-5 h-16 w-full" />
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_400px]">
          <div className="rounded-lg bg-white ring-1 ring-grey-200">
            <TranscriptSkeleton />
          </div>
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  // Duration comes from the meeting row; the transcript's last end time is the
  // authority once it has loaded, so the seek bar always matches the content.
  const durationMs = Math.max(
    meeting.duration_seconds * 1000,
    transcript?.sentences.at(-1)?.end_ms ?? 0,
  );

  return (
    <PlayerProvider durationMs={durationMs} audioUrl={meeting.audio_url} initialMs={startAtMs}>
      <div className="flex flex-col gap-4 px-6 py-5 lg:h-full">
        <header className="shrink-0">
          <Link
            href="/meetings"
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-grey-500 transition-colors hover:text-grey-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Notebook
          </Link>

          <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-grey-900">{meeting.title}</h1>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-grey-500">
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays className="h-3.5 w-3.5 text-grey-400" />
                  {formatMeetingDate(meeting.date, timeZone)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-grey-400" />
                  {formatDuration(meeting.duration_seconds)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Users className="h-3.5 w-3.5 text-grey-400" />
                  {meeting.participants.length} participants
                </span>
                {meeting.meeting_type ? (
                  <span className="text-grey-400">{meeting.meeting_type}</span>
                ) : null}
                {meeting.meeting_link ? (
                  <a
                    href={meeting.meeting_link}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-800"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Meeting link
                  </a>
                ) : null}
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {meeting.tags.map((tag) => (
                  <TagBadge key={tag.id} tag={tag} />
                ))}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-3">
              <AvatarStack people={meeting.participants} max={5} size="md" />

              <Button
                variant="secondary"
                size="md"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadTranscript.isPending}
              >
                <Upload className="h-3.5 w-3.5" />
                {uploadTranscript.isPending ? "Uploading…" : "Upload transcript"}
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.vtt,.srt,.json,.md"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) uploadTranscript.mutate(file);
                  // Reset so re-picking the same file fires change again.
                  event.target.value = "";
                }}
              />

              <Dropdown>
                <DropdownTrigger asChild>
                  <Button variant="secondary" size="icon" aria-label="More actions">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownTrigger>
                <DropdownContent>
                  <DropdownItem onSelect={() => setEditing(true)}>
                    <Pencil className="h-3.5 w-3.5 text-grey-400" />
                    Edit details
                  </DropdownItem>
                  <DropdownItem destructive onSelect={() => setDeleting(true)}>
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete meeting
                  </DropdownItem>
                </DropdownContent>
              </Dropdown>
            </div>
          </div>
        </header>

        <div className="shrink-0">
          <MediaPlayer meetingId={meeting.id} />
        </div>

        {/* grid-rows-[minmax(0,1fr)] is load-bearing: without an explicit row
            size the implicit row is auto-height, so the grid grows to fit the
            whole transcript and the *page* scrolls instead of the panel. */}
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_400px] lg:grid-rows-[minmax(0,1fr)]">
          <div className="min-h-0 lg:h-full">
            <TranscriptPanel meetingId={meeting.id} speakers={meeting.speakers} />
          </div>

          <div className="min-h-0 space-y-4 lg:h-full lg:overflow-y-auto lg:pr-1">
            <SummaryPanel
              meetingId={meeting.id}
              summary={meeting.summary}
              chapters={meeting.chapters}
              hasTranscript={meeting.sentence_count > 0}
            />
            <ActionItems meetingId={meeting.id} sentences={transcript?.sentences ?? []} />
          </div>
        </div>
      </div>

      <EditMeetingDialog
        meetingId={meeting.id}
        title={meeting.title}
        meetingType={meeting.meeting_type}
        participants={meeting.participants}
        tags={meeting.tags}
        open={editing}
        onOpenChange={setEditing}
      />
      <DeleteMeetingDialog
        meetingId={meeting.id}
        title={meeting.title}
        open={deleting}
        onOpenChange={setDeleting}
        redirectTo="/meetings"
      />
    </PlayerProvider>
  );
}
