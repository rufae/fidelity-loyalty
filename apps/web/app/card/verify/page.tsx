import { EmailActionView } from "@/components/member-card-access";

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string; m?: string }>;
}) {
  const { token = "", m = "" } = await searchParams;
  return <EmailActionView token={token} merchantSlug={m} action="verify" />;
}
