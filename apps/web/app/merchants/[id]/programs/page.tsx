import { MerchantShell } from "@/components/merchant-shell";
import { ProgramsView } from "@/components/programs-view";

export default async function ProgramsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Programas de fidelización" requires="manage">
      <ProgramsView merchantId={id} />
    </MerchantShell>
  );
}
