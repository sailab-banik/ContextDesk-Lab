import type { Metadata } from "next";

import { ReplayView } from "@/components/analytics/replay-view";

export const metadata: Metadata = { title: "Replay" };

export default async function ReplayPage({ params }: PageProps<"/analytics/[requestId]">) {
  const { requestId } = await params;
  return <ReplayView requestId={requestId} />;
}
