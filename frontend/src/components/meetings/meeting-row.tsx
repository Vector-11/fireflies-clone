"use client";

import { CheckSquare, Clock, MessageSquareText, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { TagBadge } from "@/components/ui/badge";
import { AvatarStack } from "@/components/ui/avatar";
import {
  Dropdown,
  DropdownContent,
  DropdownItem,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import { useTimeZone } from "@/hooks/use-api";
import { formatDuration, formatMeetingDate } from "@/lib/format";
import type { MeetingListItem } from "@/lib/types";
import { DeleteMeetingDialog } from "./delete-meeting-dialog";
import { EditMeetingDialog } from "./edit-meeting-dialog";

export function MeetingRow({ meeting }: { meeting: MeetingListItem }) {
  const timeZone = useTimeZone();
  const [editing, setEditing] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  return (
    <>
      <div className="group relative flex items-start gap-4 border-b border-grey-100 px-5 py-3.5 transition-colors hover:bg-grey-25">
        <div className="min-w-0 flex-1">
          {/* The stretched link makes the whole row clickable while leaving the
              kebab menu above it clickable in its own right. */}
          <Link
            href={`/meetings/${meeting.id}`}
            className="text-[14px] font-semibold text-grey-900 hover:text-brand-700 after:absolute after:inset-0 after:content-['']"
          >
            {meeting.title}
          </Link>

          {meeting.gist ? (
            <p className="mt-0.5 line-clamp-1 text-[13px] text-grey-500">{meeting.gist}</p>
          ) : (
            <p className="mt-0.5 text-[13px] text-grey-400 italic">No transcript yet</p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-grey-500">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDuration(meeting.duration_seconds)}
            </span>
            <span className="inline-flex items-center gap-1">
              <MessageSquareText className="h-3 w-3" />
              {meeting.sentence_count} lines
            </span>
            {meeting.action_item_count > 0 ? (
              <span className="inline-flex items-center gap-1">
                <CheckSquare className="h-3 w-3" />
                {meeting.open_action_item_count} of {meeting.action_item_count} open
              </span>
            ) : null}
            {meeting.meeting_type ? (
              <span className="text-grey-400">{meeting.meeting_type}</span>
            ) : null}
            {meeting.tags.slice(0, 3).map((tag) => (
              <TagBadge key={tag.id} tag={tag} />
            ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-4 pt-0.5">
          <AvatarStack people={meeting.participants} max={4} />
          <span className="w-28 text-right text-[12px] text-grey-500">
            {formatMeetingDate(meeting.date, timeZone)}
          </span>

          <Dropdown>
            <DropdownTrigger asChild>
              <button
                type="button"
                aria-label={`Actions for ${meeting.title}`}
                className="relative z-10 rounded-sm p-1.5 text-grey-400 opacity-0 transition hover:bg-grey-100 hover:text-grey-700 group-hover:opacity-100 focus:opacity-100 data-[state=open]:opacity-100"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownTrigger>
            <DropdownContent>
              <DropdownItem onSelect={() => setEditing(true)}>
                <Pencil className="h-3.5 w-3.5 text-grey-400" />
                Edit details
              </DropdownItem>
              <DropdownItem destructive onSelect={() => setDeleting(true)}>
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </DropdownItem>
            </DropdownContent>
          </Dropdown>
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
      />
    </>
  );
}
