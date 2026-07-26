"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogFooter,
} from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { useUpdateMeeting } from "@/hooks/use-api";
import type { Participant, Tag } from "@/lib/types";

/**
 * Edit meeting metadata: title, type, participants and tags.
 *
 * Participants are edited as a comma-separated list of emails. The backend
 * reconciles that list against the existing rows by email rather than replacing
 * them wholesale, so an action item assigned to someone who stays on the list
 * keeps its assignee.
 */
export function EditMeetingDialog({
  meetingId,
  title,
  meetingType,
  participants,
  tags,
  open,
  onOpenChange,
}: {
  meetingId: number;
  title: string;
  meetingType: string | null;
  participants: Participant[];
  tags: Tag[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateMeeting = useUpdateMeeting(meetingId);

  const [draftTitle, setDraftTitle] = React.useState(title);
  const [draftType, setDraftType] = React.useState(meetingType ?? "");
  const [draftParticipants, setDraftParticipants] = React.useState("");
  const [draftTags, setDraftTags] = React.useState("");

  // Reload the form from props each time it opens, so a cancelled edit does
  // not leak into the next one.
  React.useEffect(() => {
    if (!open) return;
    setDraftTitle(title);
    setDraftType(meetingType ?? "");
    setDraftParticipants(participants.map((person) => person.email).join(", "));
    setDraftTags(tags.map((tag) => tag.name).join(", "));
  }, [open, title, meetingType, participants, tags]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const emails = draftParticipants
      .split(/[,\n]/)
      .map((entry) => entry.trim())
      .filter(Boolean);
    const existingByEmail = new Map(participants.map((person) => [person.email, person.name]));

    await updateMeeting.mutateAsync({
      title: draftTitle.trim(),
      meeting_type: draftType.trim() || undefined,
      participants: emails.map((email) => ({
        email,
        // Preserve the display name we already know for this person.
        name: existingByEmail.get(email) ?? undefined,
      })),
      tags: draftTags
        .split(/[,\n]/)
        .map((entry) => entry.trim())
        .filter(Boolean),
    });

    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Edit meeting" description="Update the title, type, participants and tags.">
        <form onSubmit={handleSubmit}>
          <DialogBody>
            <Field label="Title">
              <Input value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} />
            </Field>
            <Field label="Meeting type">
              <Input
                value={draftType}
                onChange={(event) => setDraftType(event.target.value)}
                placeholder="Team Meeting"
              />
            </Field>
            <Field label="Participants" hint="Comma separated email addresses.">
              <Input
                value={draftParticipants}
                onChange={(event) => setDraftParticipants(event.target.value)}
              />
            </Field>
            <Field label="Tags" hint="Comma separated.">
              <Input value={draftTags} onChange={(event) => setDraftTags(event.target.value)} />
            </Field>
          </DialogBody>

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              variant="primary"
              disabled={updateMeeting.isPending || !draftTitle.trim()}
            >
              {updateMeeting.isPending ? "Saving…" : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
