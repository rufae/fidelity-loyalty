import { MemberCardAccess } from "@/components/member-card-access";

export default async function MyCardPage({
  params,
}: {
  params: Promise<{ merchantSlug: string }>;
}) {
  const { merchantSlug } = await params;
  return <MemberCardAccess merchantSlug={merchantSlug} />;
}
