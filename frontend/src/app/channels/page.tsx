import { Hash } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Channels — Fireflies" };

export default function ChannelsPage() {
  return (
    <ComingSoon
      icon={Hash}
      title="Channels"
      description="Group meetings into shared channels so a team sees the conversations that matter to them. Sharing and collaboration are explicitly out of scope for this build, which runs as a single user with no authentication."
      bullets={[
        "Meetings already carry many-to-many tags, which is the same shape a channel would need",
        "Filter the notebook by tag today for a single-user version of the same idea",
      ]}
    />
  );
}
