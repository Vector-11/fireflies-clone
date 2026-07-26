import { Settings } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Settings — Fireflies" };

export default function SettingsPage() {
  return (
    <ComingSoon
      icon={Settings}
      title="Settings"
      description="Profile, notification preferences, meeting defaults, storage and billing. Authentication is mocked in this build — the app always runs as the seeded workspace user — so account settings have nothing to configure."
      bullets={[
        "The signed-in user, including name, email and timezone, is served from /api/v1/me",
        "Swapping the mocked user for a real session means changing one dependency function on the backend",
      ]}
    />
  );
}
