/** Tipos y llamadas a la API de fidelización (espejo de la API real). */

import { apiFetch } from "@/lib/api";

export interface Program {
  id: string;
  merchant_id: string;
  name: string;
  slug: string;
  program_type: string;
  description: string | null;
  terms: string | null;
  terms_version: number;
  /** Versión del aviso de privacidad que acredita el alta (ADR-0006). */
  privacy_notice_version?: number;
  status: string;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  /** Caducidad opcional de sellos en días (§7.7); `null` = sin regla. */
  stamps_expire_days?: number | null;
  /** Regla del modo puntos (§7.6): puntos enteros por euro. */
  points_per_euro?: number | null;
}

export interface Reward {
  id: string;
  program_id: string;
  name: string;
  description: string | null;
  stamps_required: number;
  status: string;
}

export interface ProgramDetail extends Program {
  rewards: Reward[];
}

/** Resultado del alta en mostrador: tarjeta lista o la que ya tenía. */
export interface ManualEnrollResult {
  membership: Membership;
  created: boolean;
}

export interface Membership {
  id: string;
  member_id: string;
  program_id: string;
  public_token: string;
  status: string;
  stamps: number;
  joined_at: string;
  /** Tipo del programa (§7.1): `stamps` o `points`, para rotular la UI. */
  program_type?: string | null;
  /** Nombre del programa (promoción) al que pertenece la tarjeta. */
  program_name?: string | null;
  /** Identidad mínima del cliente para localizarlo en el mostrador (§13.5). */
  member_name?: string | null;
  member_email?: string | null;
  /** Ciclo de vida (ADR-0005): estado, motivo y fechas de supresión. */
  status_reason?: string | null;
  status_changed_at?: string | null;
  deletion_requested_at?: string | null;
  anonymized_at?: string | null;
  /** Premio al alcance (mejora «Premio listo»): derivado del backend. */
  next_reward_name?: string | null;
  next_reward_remaining?: number | null;
  reward_ready?: boolean;
}

/** Página del listado de tarjetas (§12.1): items + contadores reales. */
export interface MembershipPage {
  items: Membership[];
  total: number;
  active: number;
  suspended: number;
  /** Tarjetas con recompensa activa ya alcanzable (chip «Premio listo»). */
  ready: number;
}

export interface PublicProgram {
  /** Versión del aviso de privacidad que acepta el cliente (ADR-0006). */
  privacy_notice_version: number;
  merchant_name: string;
  merchant_slug: string;
  program_name: string;
  program_slug: string;
  program_type: string;
  description: string | null;
  terms: string | null;
  terms_version: number;
  rewards: { name: string; description: string | null; stamps_required: number }[];
  enrollment_open: boolean;
  /** Caducidad de sellos si el comercio la define: el alta la comunica
      antes de registrar al cliente (§7.7, §13.4). */
  stamps_expire_days?: number | null;
  /** Regla de puntos por euro si el programa es de puntos (§7.6). */
  points_per_euro?: number | null;
}

export interface WalletAction {
  kind: string;
  label: string;
  url: string | null;
  simulated: boolean;
}

export interface WalletOptions {
  provider: string;
  provider_status: string;
  simulated: boolean;
  actions: WalletAction[];
}

export interface PublicCard {
  merchant_name: string;
  program_name: string;
  program_type: string;
  stamps: number;
  status: string;
  rewards: { name: string; stamps_required: number; earned: boolean }[];
  wallet_options: string[];
  simulated_wallet: boolean;
  /** Caducidad de sellos si el programa la define (§7.7): la tarjeta la
      muestra junto al saldo para no prometer sellos que vencerán. */
  stamps_expire_days?: number | null;
  /** Registro propio del cliente: visitas totales y última (§9.3). */
  total_visits?: number;
  last_visit_at?: string | null;
  /** Diseño del comercio (decisión #8): presentación de la tarjeta. */
  primary_color?: string;
  accent_color?: string;
  stamp_icon?: string;
  footer_text?: string | null;
  logo_url?: string | null;
}

/** Diseño de tarjeta del comercio (§11.15): colores, icono, pie y logo. */
export interface CardBranding {
  primary_color: string;
  accent_color: string;
  stamp_icon: string;
  footer_text: string | null;
  logo_url: string | null;
}

export interface NfcTag {
  id: string;
  tag_type: string;
  public_slug: string;
  status: string;
  label: string | null;
  destination_url: string | null;
  /** URL absoluta que se imprime en el QR y se escribe en la etiqueta NFC. */
  short_url: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Normaliza lo que pega el personal en el buscador de operaciones: el código
 * de la tarjeta o la URL completa que contiene el QR (`…/card/{código}`).
 */
export function extractCardCode(input: string): string {
  const trimmed = input.trim();
  const withoutQuery = trimmed.split(/[?#]/)[0] ?? trimmed;
  const segment = withoutQuery.split("/").filter(Boolean).pop() ?? trimmed;
  return segment.trim();
}

export interface ReviewDestination {
  id: string;
  provider: string;
  review_url: string;
  verification_status: string;
  verified_at: string | null;
  updated_at: string;
}

export interface NfcStats {
  loyalty_signup_clicks: number;
  review_link_clicks: number;
  /** Usos del atajo de mostrador por el personal (ADR-0008). */
  counter_clicks: number;
  member_card_access_clicks: number;
  total_clicks: number;
  tags_active: number;
}

/** Trabajo asíncrono de Wallet (§15): estados persistidos y reintenable. */
export interface WalletJob {
  id: string;
  job_type: string;
  status: string;
  attempts: number;
  error_code: string | null;
  error_detail: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardSummary {
  members_total: number;
  memberships_active: number;
  stamps_granted: number;
  stamps_redeemed: number;
  redemptions: number;
  wallet_passes: number;
  wallet_errors: number;
  review_link_clicks: number;
}

/** Cierre de turno (§13.2): lo que ha pasado HOY en el comercio. */
export interface DashboardToday {
  local_date: string;
  enrolled_today: number;
  stamps_today: number;
  redeemed_stamps_today: number;
  redemptions_today: number;
}

/** Primeros pasos del comercio nuevo (mejora de onboarding, §13.2):
    cuatro puertas hasta el primer sello, derivadas del backend. */
export interface DashboardOnboarding {
  /** Programa publicado con al menos una recompensa activa. */
  program_ready: boolean;
  /** Al menos una tienda registrada. */
  store_ready: boolean;
  /** QR/NFC de alta activo para que el cliente se dé de alta. */
  qr_ready: boolean;
  /** Primer cliente registrado en el programa. */
  first_member: boolean;
  completed: boolean;
}

/** Serie diaria de operaciones para la gráfica de tendencia (§13.2). */
export interface LoyaltySeriesPoint {
  day: string;
  transaction_type: string;
  count: number;
}

export interface LoyaltySeries {
  period_days: number;
  series: LoyaltySeriesPoint[];
}

/** Plan contratado y su uso real (cifras del backend, §13.2). */
export interface PlanUsage {
  plan: string;
  plan_name: string;
  max_locations: number;
  locations: number;
  max_active_programs: number;
  active_programs: number;
  max_staff: number;
  staff: number;
}

/** Usuario del comercio (propietario, admin o staff, §8.1). */
export interface MerchantUser {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  created_at: string;
}

/** Tienda del comercio (§11.3). */
export interface MerchantLocation {
  id: string;
  name: string;
  address: string | null;
  status: string;
  created_at: string;
}

/** Catálogo público de planes y precios (página /precios). */
export interface PublicPlan {
  code: string;
  name: string;
  tagline: string;
  price_month_eur: number;
  price_year_eur: number;
  max_locations: number;
  max_active_programs: number;
  max_staff: number;
}

export interface TransactionRow {
  id: string;
  transaction_type: string;
  quantity: number;
  reward_id: string | null;
  reason: string | null;
  created_at: string;
}

export interface OperationResult {
  transaction_id: string;
  membership_id: string;
  transaction_type: string;
  quantity: number;
  stamps: number;
  already_applied: boolean;
}

const base = (merchantId: string) => `/api/v1/merchants/${merchantId}`;

export const fidelity = {
  programs: (merchantId: string) => apiFetch<Program[]>(`${base(merchantId)}/programs`),
  /** Plan contratado y su uso (cifras reales del backend). */
  planUsage: (merchantId: string) => apiFetch<PlanUsage>(`${base(merchantId)}/plan`),
  locations: (merchantId: string) =>
    apiFetch<MerchantLocation[]>(`${base(merchantId)}/locations`),
  createLocation: (merchantId: string, body: { name: string; address?: string }) =>
    apiFetch<MerchantLocation>(`${base(merchantId)}/locations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  setLocationStatus: (merchantId: string, locationId: string, status: "active" | "inactive") =>
    apiFetch<MerchantLocation>(`${base(merchantId)}/locations/${locationId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  /** Equipo del comercio (§12.3): el dueño crea sus empleados. */
  users: (merchantId: string) => apiFetch<MerchantUser[]>(`${base(merchantId)}/users`),
  createUser: (
    merchantId: string,
    body: { email: string; password: string; display_name: string; role: string },
  ) =>
    apiFetch<MerchantUser>(`${base(merchantId)}/users`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  setUserStatus: (merchantId: string, userId: string, status: "active" | "disabled") =>
    apiFetch<MerchantUser>(`${base(merchantId)}/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  /** Alta en mostrador (§13.5): el personal crea la tarjeta en el local. */
  manualEnroll: (
    merchantId: string,
    body: {
      program_id: string;
      display_name: string;
      email?: string;
      accepted_terms_version: number;
      privacy_notice_version: number;
    },
  ) =>
    apiFetch<ManualEnrollResult>(`${base(merchantId)}/memberships`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createProgram: (
    merchantId: string,
    body: {
      name: string;
      description?: string;
      terms?: string;
      stamps_expire_days?: number | null;
      program_type?: "stamps" | "points";
      points_per_euro?: number | null;
    },
  ) =>
    apiFetch<ProgramDetail>(`${base(merchantId)}/programs`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  program: (merchantId: string, programId: string) =>
    apiFetch<ProgramDetail>(`${base(merchantId)}/programs/${programId}`),
  updateProgram: (merchantId: string, programId: string, body: Record<string, unknown>) =>
    apiFetch<ProgramDetail>(`${base(merchantId)}/programs/${programId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  transition: (merchantId: string, programId: string, action: "publish" | "pause" | "archive") =>
    apiFetch<ProgramDetail>(`${base(merchantId)}/programs/${programId}/${action}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  createReward: (
    merchantId: string,
    programId: string,
    body: { name: string; stamps_required: number; description?: string },
  ) =>
    apiFetch<Reward>(`${base(merchantId)}/programs/${programId}/rewards`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Página de tarjetas: `q` filtra, `ready` aplica el chip «Premio listo»
      y los contadores de la cabecera llegan con la misma respuesta. */
  memberships: (
    merchantId: string,
    options?: { q?: string; ready?: boolean; limit?: number; offset?: number },
  ) => {
    const params = new URLSearchParams();
    if (options?.q) params.set("q", options.q);
    if (options?.ready) params.set("ready", "true");
    if (options?.limit) params.set("limit", String(options.limit));
    if (options?.offset) params.set("offset", String(options.offset));
    const query = params.toString();
    return apiFetch<MembershipPage>(`${base(merchantId)}/memberships${query ? `?${query}` : ""}`);
  },
  /** Búsqueda por nombre/correo del cliente para el mostrador (§13.5):
      en backend queda registrada en la auditoría. */
  searchCards: (merchantId: string, q: string) =>
    apiFetch<Membership[]>(`${base(merchantId)}/memberships/search?q=${encodeURIComponent(q)}`),
  /** Todas las tarjetas de un cliente: elige la promoción correcta en caja. */
  memberCards: (merchantId: string, memberId: string) =>
    apiFetch<Membership[]>(`${base(merchantId)}/members/${memberId}/cards`),
  lookup: (merchantId: string, token: string) =>
    apiFetch<Membership>(`${base(merchantId)}/memberships/lookup`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  /** Acumula en el mostrador: `quantity` (1–20) en modo sellos o
      `amount` (euros) en modo puntos — la cantidad de puntos la calcula
      el backend con la regla del programa (§7.6). */
  earn: (
    merchantId: string,
    membershipId: string,
    idempotencyKey: string,
    options?: { quantity?: number; amount?: number },
  ) => {
    const body =
      options?.amount != null
        ? { amount: options.amount, idempotency_key: idempotencyKey }
        : { quantity: options?.quantity ?? 1, idempotency_key: idempotencyKey };
    return apiFetch<OperationResult>(`${base(merchantId)}/memberships/${membershipId}/earn`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  /** Ajuste manual con motivo obligatorio (§7.3): solo administración. */
  adjust: (merchantId: string, membershipId: string, delta: number, reason: string) =>
    apiFetch<OperationResult>(`${base(merchantId)}/memberships/${membershipId}/adjust`, {
      method: "POST",
      body: JSON.stringify({ delta, reason }),
    }),
  redeem: (merchantId: string, membershipId: string, rewardId: string, idempotencyKey: string) =>
    apiFetch<OperationResult>(`${base(merchantId)}/memberships/${membershipId}/redeem`, {
      method: "POST",
      body: JSON.stringify({ reward_id: rewardId, idempotency_key: idempotencyKey }),
    }),
  transactions: (merchantId: string, membershipId: string) =>
    apiFetch<TransactionRow[]>(`${base(merchantId)}/memberships/${membershipId}/transactions`),
  reviewDestination: (merchantId: string) =>
    apiFetch<ReviewDestination | null>(`${base(merchantId)}/review-destination`),
  saveReviewDestination: (merchantId: string, reviewUrl: string) =>
    apiFetch<ReviewDestination>(`${base(merchantId)}/review-destination`, {
      method: "PUT",
      body: JSON.stringify({ review_url: reviewUrl }),
    }),
  verifyReviewDestination: (merchantId: string) =>
    apiFetch<ReviewDestination>(`${base(merchantId)}/review-destination/verify`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  tags: (merchantId: string) => apiFetch<NfcTag[]>(`${base(merchantId)}/nfc-tags`),
  createTag: (merchantId: string, body: { tag_type: string; label?: string; program_id?: string }) =>
    apiFetch<NfcTag>(`${base(merchantId)}/nfc-tags`, { method: "POST", body: JSON.stringify(body) }),
  updateTag: (merchantId: string, tagId: string, body: Record<string, unknown>) =>
    apiFetch<NfcTag>(`${base(merchantId)}/nfc-tags/${tagId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  tagQrUrl: (merchantId: string, tagId: string) => `${base(merchantId)}/nfc-tags/${tagId}/qr`,
  nfcStats: (merchantId: string) => apiFetch<NfcStats>(`${base(merchantId)}/nfc/stats`),
  dashboard: (merchantId: string) => apiFetch<DashboardSummary>(`${base(merchantId)}/dashboard/summary`),
  /** Cierre de turno: altas, sellos y canjes de hoy (zona del comercio). */
  dashboardToday: (merchantId: string) =>
    apiFetch<DashboardToday>(`${base(merchantId)}/dashboard/today`),
  /** Primeros pasos del comercio nuevo (checklist del Resumen). */
  dashboardOnboarding: (merchantId: string) =>
    apiFetch<DashboardOnboarding>(`${base(merchantId)}/dashboard/onboarding`),
  /** Serie diaria de operaciones del periodo (7/30/90 días). */
  dashboardLoyalty: (merchantId: string, period: 7 | 30 | 90 = 30) =>
    apiFetch<LoyaltySeries>(`${base(merchantId)}/dashboard/loyalty?period=${period}`),
  exportUrl: (merchantId: string) => `${base(merchantId)}/export/members.csv`,
  /** Diseño de tarjeta (decisión #8): lectura, cambios y logotipo. */
  branding: (merchantId: string) =>
    apiFetch<CardBranding>(`${base(merchantId)}/branding`),
  updateBranding: (merchantId: string, body: Partial<CardBranding> & { remove_logo?: boolean }) =>
    apiFetch<CardBranding>(`${base(merchantId)}/branding`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  uploadLogo: (merchantId: string, file: File) =>
    apiFetch<CardBranding>(`${base(merchantId)}/branding/logo`, {
      method: "POST",
      headers: { "Content-Type": file.type || "image/png" },
      body: file,
    }),
  removeLogo: (merchantId: string) =>
    apiFetch<CardBranding>(`${base(merchantId)}/branding/logo`, { method: "DELETE" }),
  exportTransactionsUrl: (merchantId: string) => `${base(merchantId)}/export/transactions.csv`,
  /** Altas de hoy del mostrador (puente mostrador, sin notificaciones). */
  enrollmentsToday: (merchantId: string) =>
    apiFetch<Membership[]>(`${base(merchantId)}/enrollments/today`),
  /** Edición mínima del cliente (nombre y correo); el backend audita. */
  updateMembership: (
    merchantId: string,
    membershipId: string,
    body: { display_name?: string; email?: string },
  ) =>
    apiFetch<Membership>(`${base(merchantId)}/memberships/${membershipId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  publicProgram: (merchantSlug: string, programSlug: string) =>
    apiFetch<PublicProgram>(`/api/v1/public/programs/${merchantSlug}/${programSlug}`),
  enroll: (
    merchantSlug: string,
    programSlug: string,
    body: {
      email: string;
      display_name: string;
      accepted_terms_version: number;
      privacy_notice_version: number;
      // Sin `marketing_consent`: el MVP no tiene canal de envío (§9.6) y
      // no se pide un consentimiento que nadie puede cumplir.
    },
  ) =>
    apiFetch<{ message: string }>(
      `/api/v1/public/programs/${merchantSlug}/${programSlug}/enroll`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  verifyMemberEmail: (token: string) =>
    apiFetch<{ merchant_slug: string }>("/api/v1/public/email/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  requestCardAccess: (merchantSlug: string, email: string) =>
    apiFetch<{ message: string }>(
      `/api/v1/public/card-access/request?merchant_slug=${encodeURIComponent(merchantSlug)}`,
      { method: "POST", body: JSON.stringify({ email }) },
    ),
  exchangeCardAccess: (token: string) =>
    apiFetch<{ merchant_slug: string }>("/api/v1/public/card-access", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  myCards: (merchantSlug: string) =>
    apiFetch<
      Array<{
        token: string;
        merchant_name: string;
        merchant_slug: string;
        program_id: string;
        program_name: string;
        stamps: number;
      }>
    >(`/api/v1/public/card-access/${encodeURIComponent(merchantSlug)}`),
  logoutMemberCards: (merchantSlug: string) =>
    apiFetch<{ message: string }>(
      `/api/v1/public/card-access/${encodeURIComponent(merchantSlug)}/logout`,
      { method: "POST" },
    ),
  publicCard: (token: string) => apiFetch<PublicCard>(`/api/v1/public/memberships/${token}`),
  walletOptions: (token: string) =>
    apiFetch<WalletOptions>(`/api/v1/public/memberships/${token}/wallet-options`),
  walletJobs: (merchantId: string) =>
    apiFetch<WalletJob[]>(`${base(merchantId)}/wallet/jobs`),
  retryWalletJob: (merchantId: string, jobId: string) =>
    apiFetch<WalletJob>(`${base(merchantId)}/wallet/jobs/${jobId}/retry`, { method: "POST" }),
  lifecycleAction: (
    merchantId: string,
    membershipId: string,
    action: "suspend" | "reactivate" | "revoke" | "anonymize",
    reason?: string,
  ) =>
    apiFetch<Membership>(`/api/v1/merchants/${merchantId}/memberships/${membershipId}/${action}`, {
      method: "POST",
      body: JSON.stringify(reason ? { reason } : {}),
    }),
  cardQrUrl: (token: string) => `/api/v1/public/memberships/${token}/qr`,
};

/** Catálogo de planes: público, sin sesión (página /precios, §22). */
export const plans = {
  public: () => apiFetch<PublicPlan[]>("/api/v1/public/plans"),
  /** Solicitud de alta: la plataforma crea el comercio y le da el acceso. */
  requestOnboarding: (body: {
    business_name: string;
    contact_name: string;
    email: string;
    phone?: string;
    plan: string;
    message?: string;
  }) =>
    apiFetch<{ ok: boolean }>("/api/v1/public/merchant-lead", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

/** Clave idempotente por operación: única y trazable (§16.4). */
export function newIdempotencyKey(prefix: string): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now()}-${random}`;
}

export const PROGRAM_STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  active: "Activo",
  paused: "En pausa",
  archived: "Archivado",
};
