import { EmailActionView } from "@/components/member-card-access";

export default async function CardAccessPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string; m?: string }>;
}) {
  // `m` (slug del comercio) solo orienta la guía del final muerto: el token
  // sigue siendo la única credencial, y la sesión se comprueba con cookies.
  const { token = "", m = "" } = await searchParams;
  return <EmailActionView token={token} merchantSlug={m} action="access" />;
}
