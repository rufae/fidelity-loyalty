import { EnrollView } from "@/components/enroll-view";

export default async function PublicEnrollPage({
  params,
}: {
  params: Promise<{ merchant: string; program: string }>;
}) {
  const { merchant, program } = await params;
  return <EnrollView merchantSlug={merchant} programSlug={program} />;
}
