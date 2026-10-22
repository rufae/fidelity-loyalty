import { MerchantShell } from "@/components/merchant-shell";
import { NfcView } from "@/components/nfc-view";

export default async function NfcPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <MerchantShell merchantId={id} title="Etiquetas NFC y QR" requires="manage">
      <NfcView merchantId={id} />
    </MerchantShell>
  );
}
