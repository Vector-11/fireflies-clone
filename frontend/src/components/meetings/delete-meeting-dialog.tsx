"use client";

import * as AlertDialog from "@radix-ui/react-alert-dialog";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useDeleteMeeting } from "@/hooks/use-api";

/**
 * Destructive confirmation.
 *
 * Radix's AlertDialog rather than a plain Dialog on purpose: it traps focus on
 * the *cancel* action and cannot be dismissed by clicking the backdrop, which
 * is the right behaviour for something irreversible.
 */
export function DeleteMeetingDialog({
  meetingId,
  title,
  open,
  onOpenChange,
  redirectTo,
}: {
  meetingId: number;
  title: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Where to go afterwards — set when deleting from the detail page. */
  redirectTo?: string;
}) {
  const router = useRouter();
  const deleteMeeting = useDeleteMeeting();

  async function handleDelete() {
    await deleteMeeting.mutateAsync(meetingId);
    onOpenChange(false);
    if (redirectTo) router.push(redirectTo);
  }

  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-navy/40 backdrop-blur-[2px]" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-5 shadow-2xl ring-1 ring-grey-200">
          <AlertDialog.Title className="text-base font-semibold text-grey-900">
            Delete this meeting?
          </AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-[13px] leading-relaxed text-grey-600">
            <span className="font-medium text-grey-800">{title}</span> and everything belonging to
            it — the transcript, summary, chapters and action items — will be permanently removed.
            This cannot be undone.
          </AlertDialog.Description>

          <div className="mt-5 flex justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary">Cancel</Button>
            </AlertDialog.Cancel>
            <Button variant="danger" onClick={handleDelete} disabled={deleteMeeting.isPending}>
              {deleteMeeting.isPending ? "Deleting…" : "Delete meeting"}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
