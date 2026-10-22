import { MerchantShell } from "@/components/merchant-shell";
import { ProgramEditor } from "@/components/program-editor";

export default async function ProgramPage({
  params,
}: {
  params: Promise<{ id: string; programId: string }>;
}) {
  const { id, programId } = await params;
  return (
    <MerchantShell merchantId={id} title="Editor de programa">
      <ProgramEditor merchantId={id} programId={programId} />
    </MerchantShell>
  );
}
