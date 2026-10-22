"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useMerchant } from "@/components/merchant-context";
import { MerchantDashboard } from "@/components/merchant-dashboard";
import { EmptyState, IconLock, LoadingState } from "@/components/ui";
import { canManageMerchant, canOperateMerchant } from "@/lib/session";

/**
 * Puerta del «Resumen» según el rol (§8.1):
 *
 * - Administración (o plataforma): el resumen completo.
 * - Personal de mostrador: su pantalla es Operaciones; se le lleva allí.
 * - Solo lectura: no tiene ninguna sección operativa, así que se le explica
 *   su alcance en lugar de mostrarle datos que la API le negaría.
 *
 * El backend sigue siendo el control definitivo: esto solo evita enseñar
 * pantallas que fallarían o no aportan nada.
 */
export function DashboardGate() {
  const { merchantId, role, isPlatformAdmin } = useMerchant();
  const router = useRouter();

  const manager = isPlatformAdmin || (role !== null && canManageMerchant(role));
  const staff = !manager && role !== null && canOperateMerchant(role);

  useEffect(() => {
    if (staff) router.replace(`/merchants/${merchantId}/operations`);
  }, [staff, merchantId, router]);

  if (manager) return <MerchantDashboard />;
  if (staff) {
    return <LoadingState label="Abriendo tus operaciones de mostrador…" />;
  }
  return (
    <EmptyState
      icon={<IconLock size={26} />}
      title="Tu acceso es de solo lectura"
      description="Puedes consultar la ficha del comercio, pero no operar tarjetas ni cambiar la configuración. Pide a la administración del comercio que amplíe tu rol si necesitas más acceso."
    />
  );
}
