"use client";

/** Contexto del comercio abierto: nombre y rol reales del usuario en él. */
import { createContext, useContext, type ReactNode } from "react";

import type { MerchantRole } from "@/lib/session";

interface MerchantContextValue {
  merchantId: string;
  merchantName: string;
  /** Rol del usuario en este comercio; `null` si es administración de plataforma. */
  role: MerchantRole | null;
  isPlatformAdmin: boolean;
}

const MerchantContext = createContext<MerchantContextValue | null>(null);

export function MerchantProvider({
  value,
  children,
}: {
  value: MerchantContextValue;
  children: ReactNode;
}) {
  return <MerchantContext.Provider value={value}>{children}</MerchantContext.Provider>;
}

export function useMerchant(): MerchantContextValue {
  const value = useContext(MerchantContext);
  if (!value) {
    throw new Error("useMerchant debe usarse dentro de MerchantShell");
  }
  return value;
}
