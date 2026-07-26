"use client";

import { CheckSquare, Plus, Sparkles, Trash2, User } from "lucide-react";
import * as React from "react";

import { usePlayer } from "@/components/player/player-provider";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useActionItems,
  useCreateActionItem,
  useDeleteActionItem,
  useUpdateActionItem,
} from "@/hooks/use-api";
import type { Sentence } from "@/lib/types";
import { formatTimestamp } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ActionItems({
  meetingId,
  sentences,
}: {
  meetingId: number;
  /** Used to jump the player to where a task was committed to. */
  sentences: Sentence[];
}) {
  const { seek } = usePlayer();
  const { data: items, isPending } = useActionItems(meetingId);
  const createItem = useCreateActionItem(meetingId);
  const updateItem = useUpdateActionItem(meetingId);
  const deleteItem = useDeleteActionItem(meetingId);

  const [draft, setDraft] = React.useState("");

  const startBySentenceId = React.useMemo(
    () => new Map(sentences.map((sentence) => [sentence.id, sentence.start_ms])),
    [sentences],
  );

  async function addItem(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    await createItem.mutateAsync({ text });
  }

  const open = items?.filter((item) => item.status === "open") ?? [];
  const done = items?.filter((item) => item.status === "completed") ?? [];

  return (
    <div className="rounded-lg bg-white ring-1 ring-grey-200">
      <div className="flex items-center justify-between border-b border-grey-100 px-4 py-3">
        <h2 className="flex items-center gap-2 text-[13px] font-semibold text-grey-900">
          <CheckSquare className="h-4 w-4 text-grey-400" />
          Action items
        </h2>
        {items?.length ? (
          <span className="text-[11px] text-grey-500 tabular-nums">
            {done.length}/{items.length} done
          </span>
        ) : null}
      </div>

      <div className="p-3">
        {isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-9 w-full" />
            ))}
          </div>
        ) : items && items.length > 0 ? (
          <ul className="space-y-0.5">
            {[...open, ...done].map((item) => {
              const startMs = item.sentence_id
                ? startBySentenceId.get(item.sentence_id)
                : undefined;
              const completed = item.status === "completed";

              return (
                <li key={item.id} className="group flex items-start gap-2.5 rounded-sm px-1.5 py-1.5 hover:bg-grey-25">
                  <input
                    type="checkbox"
                    checked={completed}
                    onChange={() =>
                      updateItem.mutate({
                        id: item.id,
                        status: completed ? "open" : "completed",
                      })
                    }
                    aria-label={completed ? `Reopen: ${item.text}` : `Complete: ${item.text}`}
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 cursor-pointer rounded-xs accent-brand-500"
                  />

                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-[13px] leading-snug",
                        completed ? "text-grey-400 line-through" : "text-grey-700",
                      )}
                    >
                      {item.text}
                    </p>

                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-grey-400">
                      {item.assignee ? (
                        <span className="inline-flex items-center gap-1">
                          <Avatar name={item.assignee.name} size="xs" colorKey={item.id % 8} />
                          {item.assignee.name ?? item.assignee.email}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1">
                          <User className="h-3 w-3" />
                          Unassigned
                        </span>
                      )}

                      {/* Extracted tasks link back to the exact line they came
                          from — the strongest argument that the extraction is
                          real and not decoration. */}
                      {startMs !== undefined ? (
                        <button
                          type="button"
                          onClick={() => seek(startMs)}
                          className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-800"
                        >
                          {formatTimestamp(startMs)}
                        </button>
                      ) : null}

                      {item.source === "extracted" ? (
                        <span
                          className="inline-flex items-center gap-0.5 text-grey-400"
                          title="Extracted from the transcript. Regenerating the summary rebuilds these; items you add by hand are left alone."
                        >
                          <Sparkles className="h-2.5 w-2.5" />
                          auto
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => deleteItem.mutate(item.id)}
                    aria-label={`Delete action item: ${item.text}`}
                    className="rounded-sm p-1 text-grey-300 opacity-0 transition hover:bg-danger-50 hover:text-danger-600 group-hover:opacity-100 focus:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="px-1.5 py-4 text-[13px] text-grey-500">
            No action items were found in this transcript. Add one below.
          </p>
        )}

        <form onSubmit={addItem} className="mt-2 flex gap-2 border-t border-grey-100 pt-3">
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add an action item…"
            className="h-8 text-[13px]"
          />
          <Button
            type="submit"
            variant="secondary"
            size="sm"
            disabled={!draft.trim() || createItem.isPending}
            aria-label="Add action item"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}
