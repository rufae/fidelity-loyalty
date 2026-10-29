import { MerchantShell } from "@/components/merchant-shell";
import { SupportInboxView } from "@/components/support-inbox-view";

export default async function SupportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Soporte" requires="operate">
      <SupportInboxView merchantId={id} />
    </MerchantShell>
  );
}
