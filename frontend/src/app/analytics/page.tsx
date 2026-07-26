import { BarChart3 } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Analytics — Fireflies" };

export default function AnalyticsPage() {
  return (
    <ComingSoon
      icon={BarChart3}
      title="Conversation analytics"
      description="Talk-time splits, sentiment trends, filler-word counts and team-level benchmarks. Only the workspace-level counts are built in this version — they are on the Home dashboard."
      bullets={[
        "Every sentence already stores a sentiment label and speaker attribution",
        "Talk time per speaker is derivable from the millisecond timings held on each line",
        "Meeting counts, total hours, open tasks and unique participants are live on Home",
      ]}
    />
  );
}
