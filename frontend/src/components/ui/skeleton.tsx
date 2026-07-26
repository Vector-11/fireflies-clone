import { cn } from "@/lib/utils";

/**
 * Loading placeholder.
 *
 * These matter more than usual here: the API is hosted on a free tier that
 * spins down after inactivity, so the first request of a session can take the
 * better part of a minute. A skeleton that matches the real layout reads as
 * "loading"; a blank page reads as "broken".
 */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-sm bg-grey-100", className)} />;
}

export function MeetingRowSkeleton() {
  return (
    <div className="flex items-center gap-4 border-b border-grey-100 px-5 py-4">
      <div className="min-w-0 flex-1 space-y-2">
        <Skeleton className="h-4 w-2/5" />
        <Skeleton className="h-3 w-3/5" />
      </div>
      <Skeleton className="h-6 w-24" />
      <Skeleton className="h-6 w-16" />
    </div>
  );
}

export function TranscriptSkeleton() {
  return (
    <div className="space-y-5 p-5">
      {Array.from({ length: 8 }).map((_, index) => (
        <div key={index} className="flex gap-3">
          <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        </div>
      ))}
    </div>
  );
}
