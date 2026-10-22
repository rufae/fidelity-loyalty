import { CardView } from "@/components/card-view";

export default async function CardPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <CardView token={token} />;
}
