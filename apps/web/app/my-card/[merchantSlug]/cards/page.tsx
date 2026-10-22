import { MemberCardList } from "@/components/member-card-access";

export default async function MyCardsPage({
  params,
}: {
  params: Promise<{ merchantSlug: string }>;
}) {
  const { merchantSlug } = await params;
  return <MemberCardList merchantSlug={merchantSlug} />;
}
