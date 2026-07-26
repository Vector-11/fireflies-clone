import { Scissors } from "lucide-react";

import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata = { title: "Soundbites — Fireflies" };

export default function SoundbitesPage() {
  return (
    <ComingSoon
      icon={Scissors}
      title="Soundbites"
      description="Clip a moment from a recording and share it as a short standalone snippet. Soundbites need real meeting audio, which this build does not have — transcripts are seeded or uploaded rather than transcribed from a recording."
      bullets={[
        "Transcript timings are stored in milliseconds, so clip boundaries would already be exact",
        "The player interface supports real media today — a meeting only needs an audio_url set",
      ]}
    />
  );
}
