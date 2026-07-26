import { notFound } from "next/navigation";

import { MeetingDetail } from "@/components/meetings/meeting-detail";

export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const meetingId = Number(id);
  // A non-numeric id can never match a row, so fail here rather than sending
  // the browser off to fetch /meetings/NaN.
  if (!Number.isInteger(meetingId) || meetingId < 1) notFound();

  return <MeetingDetail meetingId={meetingId} />;
}
