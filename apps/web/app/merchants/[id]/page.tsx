import { redirect } from "next/navigation";

export default async function MerchantHome({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/merchants/${id}/dashboard`);
}
