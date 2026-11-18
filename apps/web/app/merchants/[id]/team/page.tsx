import { MerchantShell } from "@/components/merchant-shell";
import { TeamView } from "@/components/team-view";

export default async function TeamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Equipo" requires="manage">
      <TeamView merchantId={id} />
    </MerchantShell>
  );
}
