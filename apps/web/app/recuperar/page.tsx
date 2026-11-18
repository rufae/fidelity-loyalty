import type { Metadata } from "next";

import { ResetView } from "@/components/password-reset-view";

export const metadata: Metadata = {
  title: "Recuperar acceso · LocalAI Fidelity",
  robots: { index: false },
};

export default function PasswordResetPage() {
  return <ResetView />;
}
