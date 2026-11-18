import { MerchantShell } from "@/components/merchant-shell";
import { StoresView } from "@/components/stores-view";

export default async function StoresPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Tiendas" requires="manage">
      <StoresView merchantId={id} />
    </MerchantShell>
  );
}
