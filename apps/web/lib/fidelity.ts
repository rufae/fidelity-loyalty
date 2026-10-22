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
  status: string;
  created_at: string;
  updated_at: string;
  published_at: string | null;
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

export interface Membership {
  id: string;
  member_id: string;
  program_id: string;
  public_token: string;
  status: string;
  stamps: number;
  joined_at: string;
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
  createProgram: (merchantId: string, body: { name: string; description?: string; terms?: string }) =>
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
  memberships: (merchantId: string, q?: string) =>
    apiFetch<Membership[]>(
      `${base(merchantId)}/memberships${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
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
  earn: (merchantId: string, membershipId: string, idempotencyKey: string, quantity = 1) =>
    apiFetch<OperationResult>(`${base(merchantId)}/memberships/${membershipId}/earn`, {
      method: "POST",
      body: JSON.stringify({ quantity, idempotency_key: idempotencyKey }),
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
  exportUrl: (merchantId: string) => `${base(merchantId)}/export/members.csv`,
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
      marketing_consent?: boolean;
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
