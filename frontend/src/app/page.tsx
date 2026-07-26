"use client";

import { CheckSquare, Clock, Notebook, Radio, Users } from "lucide-react";
import Link from "next/link";

import { MeetingRow } from "@/components/meetings/meeting-row";
import { TagBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MeetingRowSkeleton, Skeleton } from "@/components/ui/skeleton";
import { useAnalytics, useMe, useMeetings } from "@/hooks/use-api";

function StatTile({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: typeof Clock;
  label: string;
  value: string;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg bg-white p-4 ring-1 ring-grey-200">
      <div className="flex items-center gap-2 text-[12px] font-medium text-grey-500">
        <Icon className="h-3.5 w-3.5 text-grey-400" />
        {label}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-16" />
      ) : (
        <p className="mt-1 font-display text-2xl font-semibold text-grey-900 tabular-nums">
          {value}
        </p>
      )}
    </div>
  );
}

export default function HomePage() {
  const { data: user } = useMe();
  const { data: analytics, isPending: analyticsPending } = useAnalytics();
  const { data: recent, isPending: recentPending } = useMeetings({ page_size: 5, sort: "recent" });

  // One decimal place of hours, from seconds: /3600 then rounded to 0.1.
  const hours = analytics ? Math.round(analytics.total_duration_seconds / 360) / 10 : 0;
  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-grey-900">
          {firstName ? `Welcome back, ${firstName}` : "Welcome back"}
        </h1>
        <p className="mt-0.5 text-[13px] text-grey-500">
          Here is what Fred captured across your workspace.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          icon={Notebook}
          label="Meetings"
          value={String(analytics?.total_meetings ?? 0)}
          loading={analyticsPending}
        />
        <StatTile icon={Clock} label="Hours captured" value={`${hours}h`} loading={analyticsPending} />
        <StatTile
          icon={CheckSquare}
          label="Open action items"
          value={String(analytics?.open_action_items ?? 0)}
          loading={analyticsPending}
        />
        <StatTile
          icon={Users}
          label="People"
          value={String(analytics?.unique_participants ?? 0)}
          loading={analyticsPending}
        />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_280px]">
        <section className="overflow-hidden rounded-lg bg-white ring-1 ring-grey-200">
          <div className="flex items-center justify-between border-b border-grey-100 px-5 py-3">
            <h2 className="text-[13px] font-semibold text-grey-900">Recent meetings</h2>
            <Link
              href="/meetings"
              className="text-[12px] font-medium text-brand-700 hover:text-brand-800"
            >
              View all
            </Link>
          </div>
          {recentPending
            ? Array.from({ length: 4 }).map((_, index) => <MeetingRowSkeleton key={index} />)
            : recent?.items.map((meeting) => <MeetingRow key={meeting.id} meeting={meeting} />)}
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg bg-white p-4 ring-1 ring-grey-200">
            <h2 className="text-[13px] font-semibold text-grey-900">Top topics</h2>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {analyticsPending ? (
                <Skeleton className="h-5 w-full" />
              ) : (
                analytics?.top_tags.map((tag) => (
                  <TagBadge
                    key={tag.name}
                    tag={{ id: 0, name: `${tag.name} · ${tag.count}`, color: tag.color }}
                  />
                ))
              )}
            </div>
          </div>

          {/* One of the mocked surfaces the brief allows — shown rather than
              hidden, because a live-capture panel is part of Fireflies' home. */}
          <div className="rounded-lg bg-white p-4 ring-1 ring-grey-200">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-grey-400" />
              <h2 className="text-[13px] font-semibold text-grey-900">Live capture</h2>
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-grey-500">
              Fred can join Zoom, Google Meet and Teams calls to record and transcribe them live.
              Not available in this build.
            </p>
            <Button variant="secondary" size="sm" className="mt-3 w-full" disabled>
              Connect a calendar
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
}
