import { MerchantShell } from "@/components/merchant-shell";
import { PosterView } from "@/components/poster-view";

export default async function PosterPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Póster imprimible" requires="manage">
      <PosterView merchantId={id} />
    </MerchantShell>
  );
}
