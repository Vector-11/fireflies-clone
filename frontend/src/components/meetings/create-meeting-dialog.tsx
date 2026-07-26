"use client";

import { FileUp, Loader2, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/input";
import { useCreateMeeting } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

const ACCEPTED = ".txt,.vtt,.srt,.json,.md";
const MAX_BYTES = 5 * 1024 * 1024;

/** Split a comma or newline separated field into clean values. */
function splitList(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function CreateMeetingDialog({ trigger }: { trigger?: React.ReactNode }) {
  const router = useRouter();
  const createMeeting = useCreateMeeting();

  const [open, setOpen] = React.useState(false);
  const [mode, setMode] = React.useState<"paste" | "upload">("paste");
  const [title, setTitle] = React.useState("");
  const [meetingType, setMeetingType] = React.useState("");
  const [participants, setParticipants] = React.useState("");
  const [tags, setTags] = React.useState("");
  const [transcript, setTranscript] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [dragging, setDragging] = React.useState(false);

  function reset() {
    setMode("paste");
    setTitle("");
    setMeetingType("");
    setParticipants("");
    setTags("");
    setTranscript("");
    setFile(null);
  }

  function acceptFile(candidate: File | undefined | null) {
    if (!candidate) return;
    if (candidate.size > MAX_BYTES) {
      toast.error("That file is larger than 5 MB.");
      return;
    }
    setFile(candidate);
    // A filename is a much better default title than "Untitled".
    if (!title.trim()) {
      setTitle(candidate.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "));
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      toast.error("Give the meeting a title.");
      return;
    }

    // The file is read here rather than posted as multipart so that creating a
    // meeting stays a single request — same endpoint, same validation, whether
    // the transcript was typed or dropped in.
    let content = transcript;
    let filename: string | undefined;
    if (mode === "upload" && file) {
      content = await file.text();
      filename = file.name;
    }

    const meeting = await createMeeting.mutateAsync({
      title: title.trim(),
      meeting_type: meetingType.trim() || undefined,
      transcript: content.trim() || undefined,
      transcript_filename: filename,
      tags: splitList(tags),
      participants: splitList(participants).map((email) => ({ email })),
    });

    setOpen(false);
    reset();
    router.push(`/meetings/${meeting.id}`);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="primary" size="md">
            <Plus className="h-4 w-4" />
            New meeting
          </Button>
        )}
      </DialogTrigger>

      <DialogContent
        title="Add a meeting"
        description="Paste a transcript or upload a file. The summary, chapters and action items are generated from it."
      >
        <form onSubmit={handleSubmit}>
          <DialogBody>
            <Field label="Title">
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Weekly Product Sync"
                autoFocus
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Meeting type">
                <Input
                  value={meetingType}
                  onChange={(event) => setMeetingType(event.target.value)}
                  placeholder="Team Meeting"
                />
              </Field>
              <Field label="Tags">
                <Input
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="Product, Roadmap"
                />
              </Field>
            </div>

            <Field
              label="Participants"
              hint="Comma separated. Anyone who speaks in the transcript is added automatically."
            >
              <Input
                value={participants}
                onChange={(event) => setParticipants(event.target.value)}
                placeholder="maya@example.com, dan@example.com"
              />
            </Field>

            <div>
              <div className="mb-2 flex items-center gap-1 rounded-sm bg-grey-100 p-0.5">
                {(["paste", "upload"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setMode(option)}
                    className={cn(
                      "flex-1 rounded-xs px-3 py-1.5 text-[13px] font-medium transition-colors",
                      mode === option
                        ? "bg-white text-grey-900 shadow-sm"
                        : "text-grey-500 hover:text-grey-700",
                    )}
                  >
                    {option === "paste" ? "Paste transcript" : "Upload file"}
                  </button>
                ))}
              </div>

              {mode === "paste" ? (
                <Textarea
                  rows={7}
                  value={transcript}
                  onChange={(event) => setTranscript(event.target.value)}
                  placeholder={"Maya Chen: Let's start with the roadmap.\nDan Oyelaran: Two things moved this week."}
                  className="font-mono text-[12px] leading-relaxed"
                />
              ) : (
                <label
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragging(false);
                    acceptFile(event.dataTransfer.files?.[0]);
                  }}
                  className={cn(
                    "flex cursor-pointer flex-col items-center justify-center rounded-sm border-2 border-dashed px-4 py-8 text-center transition-colors",
                    dragging ? "border-brand-400 bg-brand-25" : "border-grey-300 hover:bg-grey-25",
                  )}
                >
                  <FileUp className="h-5 w-5 text-grey-400" />
                  <p className="mt-2 text-[13px] font-medium text-grey-700">
                    {file ? file.name : "Drop a transcript, or click to browse"}
                  </p>
                  <p className="mt-0.5 text-[11px] text-grey-500">.txt, .vtt, .srt, .json — up to 5 MB</p>
                  <input
                    type="file"
                    accept={ACCEPTED}
                    className="hidden"
                    onChange={(event) => acceptFile(event.target.files?.[0])}
                  />
                </label>
              )}

              <p className="mt-2 text-[11px] text-grey-500">
                Leave this empty to create the meeting now and add a transcript later.
              </p>
            </div>
          </DialogBody>

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" variant="primary" disabled={createMeeting.isPending}>
              {createMeeting.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing…
                </>
              ) : (
                "Create meeting"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
