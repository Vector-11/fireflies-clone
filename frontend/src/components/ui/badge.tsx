import * as React from "react";

import { cn } from "@/lib/utils";
import { tagClasses } from "@/lib/format";
import type { Tag } from "@/lib/types";

export function Badge({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        "bg-grey-50 text-grey-600 ring-grey-200",
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

/** A topic tag. The colour comes from the database so it is stable everywhere. */
export function TagBadge({ tag, onClick }: { tag: Tag; onClick?: () => void }) {
  const content = (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        tagClasses(tag.color),
      )}
    >
      {tag.name}
    </span>
  );

  if (!onClick) return content;
  return (
    <button type="button" onClick={onClick} className="cursor-pointer">
      {content}
    </button>
  );
}
