import { MerchantShell } from "@/components/merchant-shell";
import { DashboardGate } from "@/components/dashboard-gate";

export default async function DashboardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Resumen">
      <DashboardGate />
    </MerchantShell>
  );
}
