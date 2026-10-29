import { MerchantShell } from "@/components/merchant-shell";
import { SupportThreadFormView } from "@/components/support-thread-form-view";

export default async function NewSupportThreadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Nueva conversación" requires="operate">
      <SupportThreadFormView merchantId={id} />
    </MerchantShell>
  );
}
