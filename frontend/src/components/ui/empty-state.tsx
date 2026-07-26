import type { LucideIcon } from "lucide-react";
import type * as React from "react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 ring-1 ring-brand-100">
        <Icon className="h-5 w-5 text-brand-600" />
      </div>
      <h3 className="text-sm font-semibold text-grey-900">{title}</h3>
      <p className="mt-1 max-w-sm text-[13px] text-grey-500">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
