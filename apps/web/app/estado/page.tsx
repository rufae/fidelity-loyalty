import { StatusGate } from "@/components/status-gate";

/** Diagnóstico técnico: solo para operadores autorizados (ver `StatusGate`). */
export default function StatusPage() {
  return <StatusGate />;
}
