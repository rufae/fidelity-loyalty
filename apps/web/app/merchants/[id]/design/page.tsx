import { MerchantShell } from "@/components/merchant-shell";
import { CardDesignView } from "@/components/card-design-view";

export default async function CardDesignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Diseño de tarjeta" requires="manage">
      <CardDesignView merchantId={id} />
    </MerchantShell>
  );
}
