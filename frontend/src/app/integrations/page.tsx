import { Plug } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Integrations — Fireflies" };

export default function IntegrationsPage() {
  return (
    <ComingSoon
      icon={Plug}
      title="Integrations"
      description="Connect Zoom, Google Meet, Teams, Slack, Salesforce, HubSpot and the rest so meetings arrive automatically and notes flow back out. Integrations are listed in the brief as a mockable surface, so nothing here is wired to a real provider."
      bullets={[
        "Meetings already store a calendar_type and a meeting_link, which is what a sync would populate",
        "Upload a .vtt or .json export from Zoom or Meet today — the parser handles both",
      ]}
    />
  );
}
