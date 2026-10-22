/** Tipos y permisos de la sesión (espejo del backend, §8 — el permiso real se decide allí). */

export type MerchantRole = "owner" | "admin" | "staff" | "viewer";

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  platform_role: string | null;
  last_login_at: string | null;
}

export interface MerchantMembership {
  merchant_id: string;
  merchant_name: string;
  merchant_slug: string;
  merchant_status: string;
  role: MerchantRole;
}

export interface SessionPayload {
  user: SessionUser;
  merchants: MerchantMembership[];
}

/**
 * La interfaz usa estos permisos solo para **ocultar** botones: el backend
 * vuelve a comprobarlo en cada petición (§8.2). Ocultar un botón no es un
 * control de acceso.
 */
export function isPlatformAdmin(user: SessionUser): boolean {
  return user.platform_role === "owner" || user.platform_role === "admin";
}

export function canManageMerchant(role: MerchantRole): boolean {
  return role === "owner" || role === "admin";
}

export function canOperateMerchant(role: MerchantRole): boolean {
  return role === "owner" || role === "admin" || role === "staff";
}
