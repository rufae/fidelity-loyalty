import type { Metadata } from "next";

import { PricingView } from "@/components/pricing-view";

export const metadata: Metadata = {
  title: "Precios · LocalAI Fidelity",
  description:
    "Planes para comercios: paga por tiendas y programas en vivo. Clientes, sellos y canjes siempre ilimitados.",
};

export default function PricingPage() {
  return <PricingView />;
}
