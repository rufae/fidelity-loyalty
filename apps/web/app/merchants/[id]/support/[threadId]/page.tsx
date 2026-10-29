import { MerchantShell } from "@/components/merchant-shell";
import { SupportThreadDetailView } from "@/components/support-thread-detail-view";

export default async function SupportThreadPage({
  params,
}: {
  params: Promise<{ id: string; threadId: string }>;
}) {
  const { id, threadId } = await params;
  return (
    <MerchantShell merchantId={id} title="Conversación" requires="operate">
      <SupportThreadDetailView merchantId={id} threadId={threadId} />
    </MerchantShell>
  );
}
