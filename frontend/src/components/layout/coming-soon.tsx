import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";

/**
 * Placeholder for the surfaces the brief explicitly allows to be mocked: the
 * live-call bot, real transcription, integrations, team sharing and AskFred.
 *
 * They are still routed and still appear in the sidebar, because removing them
 * would make the navigation feel smaller than Fireflies' — the shape of the
 * product is part of what is being recreated.
 */
export function ComingSoon({
  icon: Icon,
  title,
  description,
  bullets,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  bullets?: string[];
}) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-14">
      <div className="rounded-xl bg-white p-8 ring-1 ring-grey-200">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 ring-1 ring-brand-100">
          <Icon className="h-5 w-5 text-brand-600" />
        </div>
        <div className="mt-5 flex items-center gap-2.5">
          <h1 className="text-xl font-semibold text-grey-900">{title}</h1>
          <Badge className="bg-warning-50 text-warning-700 ring-warning-100">Coming soon</Badge>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-grey-600">{description}</p>

        {bullets?.length ? (
          <ul className="mt-6 space-y-2.5 border-t border-grey-100 pt-6">
            {bullets.map((bullet) => (
              <li key={bullet} className="flex gap-2.5 text-[13px] text-grey-600">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-grey-300" />
                {bullet}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
