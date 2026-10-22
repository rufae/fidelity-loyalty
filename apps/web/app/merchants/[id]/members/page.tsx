import { MerchantShell } from "@/components/merchant-shell";
import { MembersView } from "@/components/members-view";

export default async function MembersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Clientes y tarjetas" requires="manage">
      <MembersView merchantId={id} />
    </MerchantShell>
  );
}
