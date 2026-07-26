/**
 * The single place this app talks to the backend.
 *
 * Every call goes through `request`, so error handling, JSON parsing and the
 * base URL are defined once. Components never touch `fetch` directly — that is
 * what keeps error toasts consistent and makes the API surface greppable.
 */

import type {
  ActionItem,
  AnalyticsOverview,
  MeetingDetail,
  MeetingFilters,
  MeetingListItem,
  Page,
  SearchResponse,
  Sentence,
  Summary,
  Transcript,
  User,
} from "./types";

const ORIGIN = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const API_BASE = `${ORIGIN.replace(/\/$/, "")}/api/v1`;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers:
        init?.body instanceof FormData
          ? init?.headers
          : { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    // A network-level failure is nearly always the backend being asleep — the
    // free Render tier spins down after inactivity and takes ~50s to wake.
    throw new ApiError(0, "Cannot reach the server. It may be waking up — try again in a moment.");
  }

  if (response.status === 204) return undefined as T;

  const body = await response.text();
  const parsed = body ? safeJson(body) : null;

  if (!response.ok) {
    const detail =
      (parsed && typeof parsed === "object" && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : null) ?? `Request failed with status ${response.status}`;
    const code =
      parsed && typeof parsed === "object" && "code" in parsed
        ? String((parsed as { code: unknown }).code)
        : undefined;
    throw new ApiError(response.status, detail, code);
  }

  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export interface MeetingCreatePayload {
  title: string;
  date?: string;
  transcript?: string;
  transcript_filename?: string;
  participants?: { email: string; name?: string; is_fireflies_user?: boolean }[];
  tags?: string[];
  meeting_type?: string;
  meeting_link?: string;
}

export interface MeetingUpdatePayload {
  title?: string;
  meeting_type?: string;
  meeting_link?: string;
  participants?: { email: string; name?: string }[];
  tags?: string[];
}

export const api = {
  me: () => request<User>("/me"),

  analytics: () => request<AnalyticsOverview>("/analytics/overview"),

  listMeetings: (filters: MeetingFilters = {}) =>
    request<Page<MeetingListItem>>(`/meetings${query({ ...filters })}`),

  getMeeting: (id: number) => request<MeetingDetail>(`/meetings/${id}`),

  createMeeting: (payload: MeetingCreatePayload) =>
    request<MeetingDetail>("/meetings", { method: "POST", body: JSON.stringify(payload) }),

  updateMeeting: (id: number, payload: MeetingUpdatePayload) =>
    request<MeetingDetail>(`/meetings/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  deleteMeeting: (id: number) => request<void>(`/meetings/${id}`, { method: "DELETE" }),

  uploadTranscript: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<MeetingDetail>(`/meetings/${id}/upload-transcript`, {
      method: "POST",
      body: form,
    });
  },

  getTranscript: (id: number, params: { q?: string; insight?: string; speaker_id?: number } = {}) =>
    request<Transcript>(`/meetings/${id}/transcript${query(params)}`),

  updateSentence: (meetingId: number, sentenceId: number, text: string) =>
    request<Sentence>(`/meetings/${meetingId}/sentences/${sentenceId}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),

  getSummary: (id: number) => request<Summary>(`/meetings/${id}/summary`),

  regenerateSummary: (id: number) =>
    request<Summary>(`/meetings/${id}/summary/regenerate`, { method: "POST" }),

  listActionItems: (meetingId: number) =>
    request<ActionItem[]>(`/meetings/${meetingId}/action-items`),

  createActionItem: (
    meetingId: number,
    payload: { text: string; assignee_participant_id?: number | null; due_date?: string | null },
  ) =>
    request<ActionItem>(`/meetings/${meetingId}/action-items`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateActionItem: (
    id: number,
    payload: {
      text?: string;
      status?: "open" | "completed";
      assignee_participant_id?: number | null;
      due_date?: string | null;
    },
  ) => request<ActionItem>(`/action-items/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  deleteActionItem: (id: number) => request<void>(`/action-items/${id}`, { method: "DELETE" }),

  search: (q: string, limit = 20) => request<SearchResponse>(`/search${query({ q, limit })}`),
};
