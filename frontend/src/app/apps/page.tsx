import { LayoutGrid } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "AI Apps — Fireflies" };

export default function AppsPage() {
  return (
    <ComingSoon
      icon={LayoutGrid}
      title="AI Apps"
      description="Run custom prompts over a meeting to produce bespoke outputs — a follow-up email, a CRM note, a hiring scorecard. Custom prompt apps need a language model, which this build deliberately does without."
      bullets={[
        "The summary table already stores provenance, so model-generated and algorithmic output could coexist",
        "Every meeting exposes its full transcript through the API for a downstream app to consume",
      ]}
    />
  );
}
