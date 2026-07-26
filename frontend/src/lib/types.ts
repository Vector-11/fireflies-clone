/**
 * Response types, mirroring the Pydantic schemas in `backend/app/schemas`.
 *
 * These are hand-written rather than generated. The backend publishes an
 * OpenAPI document at /openapi.json and `openapi-typescript` would generate
 * this file, which is the better answer on a long-lived codebase; for a surface
 * this size the generated output is harder to read than the source of truth it
 * mirrors, and the tests would catch a drift anyway.
 */

export interface User {
  id: number;
  name: string;
  email: string;
  job_title: string | null;
  avatar_url: string | null;
  timezone: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface Participant {
  id: number;
  email: string;
  name: string | null;
  is_fireflies_user: boolean;
}

export interface Speaker {
  id: number;
  speaker_index: number;
  name: string;
  color_key: number;
}

export interface Chapter {
  id: number;
  idx: number;
  title: string;
  gist: string | null;
  start_ms: number;
  end_ms: number;
}

export interface Summary {
  id: number;
  gist: string | null;
  short_summary: string | null;
  overview: string | null;
  bullet_gist: string | null;
  shorthand_bullet: string | null;
  notes: string | null;
  keywords: string[];
  topics_discussed: string[];
  generated_by: string;
  model: string | null;
}

export interface Sentence {
  id: number;
  idx: number;
  text: string;
  start_ms: number;
  end_ms: number;
  speaker_id: number | null;
  sentiment: "positive" | "neutral" | "negative";
  is_task: boolean;
  is_question: boolean;
  is_metric: boolean;
  is_date_time: boolean;
}

export interface Transcript {
  meeting_id: number;
  total: number;
  sentences: Sentence[];
}

export interface MeetingListItem {
  id: number;
  title: string;
  date: string;
  duration_seconds: number;
  meeting_type: string | null;
  calendar_type: string | null;
  is_live: boolean;
  participants: Participant[];
  tags: Tag[];
  gist: string | null;
  sentence_count: number;
  action_item_count: number;
  open_action_item_count: number;
}

export interface MeetingDetail {
  id: number;
  title: string;
  date: string;
  duration_seconds: number;
  organizer_email: string | null;
  meeting_link: string | null;
  calendar_type: string | null;
  meeting_type: string | null;
  audio_url: string | null;
  video_url: string | null;
  is_live: boolean;
  created_at: string;
  updated_at: string;
  owner: User;
  participants: Participant[];
  speakers: Speaker[];
  chapters: Chapter[];
  tags: Tag[];
  summary: Summary | null;
  sentence_count: number;
}

export interface ActionItem {
  id: number;
  meeting_id: number;
  text: string;
  status: "open" | "completed";
  source: "extracted" | "manual";
  due_date: string | null;
  order_index: number;
  completed_at: string | null;
  sentence_id: number | null;
  assignee: Participant | null;
}

export interface SearchHit {
  sentence_id: number;
  idx: number;
  start_ms: number;
  speaker_name: string | null;
  /** Contains <mark> tags around matches, produced by SQLite's snippet(). */
  snippet: string;
}

export interface SearchResult {
  meeting_id: number;
  title: string;
  date: string;
  duration_seconds: number;
  meeting_type: string | null;
  match_count: number;
  hits: SearchHit[];
}

export interface SearchResponse {
  query: string;
  total_meetings: number;
  /** False when the FTS5 index was unavailable and LIKE answered instead. */
  ranked: boolean;
  results: SearchResult[];
}

export interface AnalyticsOverview {
  total_meetings: number;
  meetings_this_week: number;
  total_duration_seconds: number;
  open_action_items: number;
  completed_action_items: number;
  unique_participants: number;
  top_tags: { name: string; color: string; count: number }[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type SortOption = "recent" | "oldest" | "longest" | "shortest" | "title";
export type InsightFilter = "task" | "question" | "metric" | "datetime";

export interface MeetingFilters {
  q?: string;
  participant?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  sort?: SortOption;
  page?: number;
  page_size?: number;
}
