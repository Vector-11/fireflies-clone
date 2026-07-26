import { Users } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Team — Fireflies" };

export default function TeamPage() {
  return (
    <ComingSoon
      icon={Users}
      title="Team & sharing"
      description="Invite teammates, manage roles and share meetings inside or outside the workspace. This build assumes a single signed-in user, as the brief permits, so there is no one to share with yet."
      bullets={[
        "Meetings are already owned by a user row, so multi-user is a query filter rather than a redesign",
        "Participants distinguish workspace members from external guests today",
      ]}
    />
  );
}
