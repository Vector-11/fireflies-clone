"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError, type MeetingCreatePayload, type MeetingUpdatePayload } from "@/lib/api";
import type { ActionItem, MeetingFilters } from "@/lib/types";

/**
 * Query keys in one object rather than scattered string arrays.
 *
 * Invalidation is the thing that goes wrong in a React Query codebase, and it
 * goes wrong because a mutation invalidates `["meeting", id]` while the query
 * registered `["meetings", id]`. Naming them once makes that impossible.
 */
export const keys = {
  me: ["me"] as const,
  analytics: ["analytics"] as const,
  meetings: (filters: MeetingFilters) => ["meetings", filters] as const,
  meeting: (id: number) => ["meeting", id] as const,
  transcript: (id: number, insight?: string) => ["transcript", id, insight ?? null] as const,
  actionItems: (id: number) => ["action-items", id] as const,
  search: (q: string) => ["search", q] as const,
};

function reportError(error: unknown, fallback: string) {
  const message = error instanceof ApiError ? error.message : fallback;
  toast.error(message);
}

/* ------------------------------------------------------------------ reads */

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: api.me, staleTime: Infinity });
}

/**
 * The workspace timezone, for rendering meeting times.
 *
 * `undefined` while the profile loads, which makes the formatters fall back to
 * the browser's zone — a sensible default rather than a blank.
 */
export function useTimeZone(): string | undefined {
  return useMe().data?.timezone;
}

export function useAnalytics() {
  return useQuery({ queryKey: keys.analytics, queryFn: api.analytics });
}

export function useMeetings(filters: MeetingFilters) {
  return useQuery({
    queryKey: keys.meetings(filters),
    queryFn: () => api.listMeetings(filters),
    // Keeps the previous page on screen while the next one loads, so typing in
    // the search box does not flash an empty table on every keystroke.
    placeholderData: (previous) => previous,
  });
}

export function useMeeting(id: number) {
  return useQuery({
    queryKey: keys.meeting(id),
    queryFn: () => api.getMeeting(id),
    enabled: Number.isFinite(id),
  });
}

export function useTranscript(id: number, insight?: string) {
  return useQuery({
    queryKey: keys.transcript(id, insight),
    queryFn: () => api.getTranscript(id, insight ? { insight } : {}),
    enabled: Number.isFinite(id),
  });
}

export function useActionItems(id: number) {
  return useQuery({
    queryKey: keys.actionItems(id),
    queryFn: () => api.listActionItems(id),
    enabled: Number.isFinite(id),
  });
}

export function useSearch(q: string) {
  return useQuery({
    queryKey: keys.search(q),
    queryFn: () => api.search(q),
    enabled: q.trim().length > 0,
    placeholderData: (previous) => previous,
  });
}

/* -------------------------------------------------------------- mutations */

export function useCreateMeeting() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: MeetingCreatePayload) => api.createMeeting(payload),
    onSuccess: (meeting) => {
      client.invalidateQueries({ queryKey: ["meetings"] });
      client.invalidateQueries({ queryKey: keys.analytics });
      toast.success(`"${meeting.title}" created`);
    },
    onError: (error) => reportError(error, "Could not create the meeting."),
  });
}

export function useUpdateMeeting(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: MeetingUpdatePayload) => api.updateMeeting(id, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.meeting(id) });
      client.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("Meeting updated");
    },
    onError: (error) => reportError(error, "Could not update the meeting."),
  });
}

export function useDeleteMeeting() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteMeeting(id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["meetings"] });
      client.invalidateQueries({ queryKey: keys.analytics });
      toast.success("Meeting deleted");
    },
    onError: (error) => reportError(error, "Could not delete the meeting."),
  });
}

export function useUploadTranscript(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.uploadTranscript(id, file),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.meeting(id) });
      client.invalidateQueries({ queryKey: ["transcript", id] });
      client.invalidateQueries({ queryKey: keys.actionItems(id) });
      client.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("Transcript uploaded and summarised");
    },
    onError: (error) => reportError(error, "Could not read that transcript."),
  });
}

export function useRegenerateSummary(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.regenerateSummary(id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.meeting(id) });
      client.invalidateQueries({ queryKey: keys.actionItems(id) });
      toast.success("Summary regenerated");
    },
    onError: (error) => reportError(error, "Could not regenerate the summary."),
  });
}

export function useCreateActionItem(meetingId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { text: string; assignee_participant_id?: number | null }) =>
      api.createActionItem(meetingId, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.actionItems(meetingId) });
      client.invalidateQueries({ queryKey: ["meetings"] });
      client.invalidateQueries({ queryKey: keys.analytics });
    },
    onError: (error) => reportError(error, "Could not add the action item."),
  });
}

/**
 * Ticking a checkbox has to feel instant, so the cache is updated before the
 * request goes out and rolled back if it fails. The snapshot returned from
 * `onMutate` is what makes that rollback exact rather than a guess.
 */
export function useUpdateActionItem(meetingId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: number;
      text?: string;
      status?: "open" | "completed";
      assignee_participant_id?: number | null;
    }) => api.updateActionItem(id, payload),

    onMutate: async (variables) => {
      await client.cancelQueries({ queryKey: keys.actionItems(meetingId) });
      const previous = client.getQueryData<ActionItem[]>(keys.actionItems(meetingId));

      client.setQueryData<ActionItem[]>(keys.actionItems(meetingId), (current) =>
        current?.map((item) =>
          item.id === variables.id
            ? {
                ...item,
                ...variables,
                completed_at:
                  variables.status === "completed"
                    ? new Date().toISOString()
                    : variables.status === "open"
                      ? null
                      : item.completed_at,
              }
            : item,
        ),
      );

      return { previous };
    },

    onError: (error, _variables, context) => {
      if (context?.previous) {
        client.setQueryData(keys.actionItems(meetingId), context.previous);
      }
      reportError(error, "Could not update the action item.");
    },

    onSettled: () => {
      client.invalidateQueries({ queryKey: keys.actionItems(meetingId) });
      client.invalidateQueries({ queryKey: ["meetings"] });
      client.invalidateQueries({ queryKey: keys.analytics });
    },
  });
}

export function useDeleteActionItem(meetingId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteActionItem(id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.actionItems(meetingId) });
      client.invalidateQueries({ queryKey: ["meetings"] });
      client.invalidateQueries({ queryKey: keys.analytics });
      toast.success("Action item removed");
    },
    onError: (error) => reportError(error, "Could not remove the action item."),
  });
}
