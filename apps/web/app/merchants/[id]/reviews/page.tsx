import { MerchantShell } from "@/components/merchant-shell";
import { ReviewsView } from "@/components/reviews-view";

export default async function ReviewsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Reseñas de Google" requires="manage">
      <ReviewsView merchantId={id} />
    </MerchantShell>
  );
}
