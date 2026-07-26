import { Sparkles } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "AskFred — Fireflies" };

export default function AskFredPage() {
  return (
    <ComingSoon
      icon={Sparkles}
      title="AskFred"
      description="Ask questions about a meeting in natural language and get an answer grounded in the transcript. This build generates its summaries with a deterministic on-server algorithm rather than a language model, so conversational Q&A is out of scope."
      bullets={[
        "Summaries, chapters and action items are already generated — see any meeting's Overview panel",
        "The summariser sits behind a one-method interface, so a model-backed implementation is a drop-in replacement",
        "Full-text search across every transcript is live today under Search",
      ]}
    />
  );
}
