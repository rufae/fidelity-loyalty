import { MerchantShell } from "@/components/merchant-shell";
import { OperationsView } from "@/components/operations-view";

export default async function OperationsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Operaciones de mostrador" requires="operate">
      <OperationsView merchantId={id} />
    </MerchantShell>
  );
}
