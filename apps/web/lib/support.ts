/** Tipos y llamadas al módulo de soporte B2B (Plan.md §9). */

import { apiFetch } from "@/lib/api";

export type SupportCategory = "technical" | "billing" | "program" | "nfc" | "wallet" | "other";
export type SupportStatus =
  | "open"
  | "waiting_platform"
  | "waiting_merchant"
  | "resolved"
  | "closed";
export type SupportContactPreference = "in_app" | "email" | "phone";
export type SupportCallbackStatus = "requested" | "called" | "cancelled";
export type SupportNotificationStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "retrying"
  | "failed"
  | "cancelled";

export interface SupportMessage {
  id: string;
  thread_id: string;
  author_type: "merchant" | "platform";
  author_user_id: string | null;
  author_display_name: string;
  body: string;
  created_at: string;
  read_by_merchant_at: string | null;
  read_by_platform_at: string | null;
}

export interface SupportCallbackRequest {
  id: string;
  status: SupportCallbackStatus;
  availability: string | null;
  requested_at: string;
  handled_at: string | null;
  /** Solo lo devuelve el buzón de plataforma; nunca al comercio. */
  phone: string | null;
}

export interface SupportNotification {
  id: string;
  channel: "email_platform" | "email_merchant" | "ntfy" | "telegram";
  status: SupportNotificationStatus;
  attempts: number;
  manual_retries: number;
  next_attempt_at: string | null;
  error_code: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface SupportThread {
  id: string;
  merchant_id: string;
  merchant_name: string | null;
  created_by_user_id: string;
  created_by_display_name: string;
  subject: string;
  category: SupportCategory;
  status: SupportStatus;
  priority: "normal" | "high";
  preferred_contact: SupportContactPreference;
  last_message_at: string;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  unread_for_viewer: number;
  has_callback_request: boolean;
}

export interface SupportThreadDetail extends SupportThread {
  messages: SupportMessage[];
  callback_request: SupportCallbackRequest | null;
  notifications: SupportNotification[];
}

export interface SupportThreadPage {
  items: SupportThread[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateSupportThreadInput {
  subject: string;
  category: SupportCategory;
  body: string;
  preferred_contact: SupportContactPreference;
  callback_phone?: string;
  callback_availability?: string;
  callback_consent?: boolean;
}

const merchantBase = (merchantId: string) => `/api/v1/merchants/${merchantId}/support`;

function idempotencyHeaders(key?: string): HeadersInit {
  return key ? { "Idempotency-Key": key } : {};
}

/** Clave idempotente por operación: reintentar no duplica mensajes. */
export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const support = {
  threads: (
    merchantId: string,
    params?: { status?: SupportStatus; q?: string; limit?: number; offset?: number },
  ) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.q) search.set("q", params.q);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    const query = search.toString();
    return apiFetch<SupportThreadPage>(
      `${merchantBase(merchantId)}${query ? `?${query}` : ""}`,
    );
  },
  thread: (merchantId: string, threadId: string) =>
    apiFetch<SupportThreadDetail>(`${merchantBase(merchantId)}/${threadId}`),
  createThread: (merchantId: string, body: CreateSupportThreadInput, key?: string) =>
    apiFetch<SupportThreadDetail>(merchantBase(merchantId), {
      method: "POST",
      headers: idempotencyHeaders(key),
      body: JSON.stringify(body),
    }),
  reply: (merchantId: string, threadId: string, body: string, key?: string) =>
    apiFetch<SupportMessage>(`${merchantBase(merchantId)}/${threadId}/messages`, {
      method: "POST",
      headers: idempotencyHeaders(key),
      body: JSON.stringify({ body }),
    }),
  requestCallback: (
    merchantId: string,
    threadId: string,
    body: { phone: string; availability?: string; consent: boolean },
    key?: string,
  ) =>
    apiFetch<SupportCallbackRequest>(
      `${merchantBase(merchantId)}/${threadId}/callback-requests`,
      {
        method: "POST",
        headers: idempotencyHeaders(key),
        body: JSON.stringify(body),
      },
    ),
  closeThread: (merchantId: string, threadId: string) =>
    apiFetch<SupportThread>(`${merchantBase(merchantId)}/${threadId}/close`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  markRead: (merchantId: string, threadId: string) =>
    apiFetch<{ count: number }>(`${merchantBase(merchantId)}/${threadId}/read`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  unreadCount: (merchantId: string) =>
    apiFetch<{ count: number }>(`${merchantBase(merchantId)}/unread-count`),

  /** Tema ntfy del comercio: suscripción de avisos push (Plan.md §11.3). */
  notificationTopic: (merchantId: string) =>
    apiFetch<{ topic: string; server_url: string | null }>(
      `${merchantBase(merchantId)}/notification-topic`,
    ),

  platformThreads: (params?: {
    status?: SupportStatus;
    merchant_id?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.merchant_id) search.set("merchant_id", params.merchant_id);
    if (params?.q) search.set("q", params.q);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    const query = search.toString();
    return apiFetch<SupportThreadPage>(
      `/api/v1/platform/support/threads${query ? `?${query}` : ""}`,
    );
  },
  platformThread: (threadId: string) =>
    apiFetch<SupportThreadDetail>(`/api/v1/platform/support/threads/${threadId}`),
  platformReply: (threadId: string, body: string, key?: string) =>
    apiFetch<SupportMessage>(`/api/v1/platform/support/threads/${threadId}/messages`, {
      method: "POST",
      headers: idempotencyHeaders(key),
      body: JSON.stringify({ body }),
    }),
  platformUpdate: (threadId: string, body: { status?: SupportStatus; priority?: "normal" | "high" }) =>
    apiFetch<SupportThread>(`/api/v1/platform/support/threads/${threadId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  platformMarkCalled: (threadId: string, requestId: string, notes?: string) =>
    apiFetch<SupportCallbackRequest>(
      `/api/v1/platform/support/threads/${threadId}/callback-requests/${requestId}/mark-called${
        notes ? `?notes=${encodeURIComponent(notes)}` : ""
      }`,
      { method: "POST", body: JSON.stringify({}) },
    ),
  platformMarkRead: (threadId: string) =>
    apiFetch<{ count: number }>(`/api/v1/platform/support/threads/${threadId}/read`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  platformUnreadCount: () =>
    apiFetch<{ count: number }>("/api/v1/platform/support/unread-count"),
  retryNotification: (notificationId: string) =>
    apiFetch<SupportNotification>(
      `/api/v1/platform/support/notifications/${notificationId}/retry`,
      { method: "POST", body: JSON.stringify({}) },
    ),
};

export const SUPPORT_CATEGORY_LABELS: Record<SupportCategory, string> = {
  technical: "Técnico",
  billing: "Facturación",
  program: "Programa",
  nfc: "NFC y QR",
  wallet: "Wallet",
  other: "Otro",
};

export const SUPPORT_STATUS_LABELS: Record<SupportStatus, string> = {
  open: "Abierta",
  waiting_platform: "Esperando a soporte",
  waiting_merchant: "Esperando al comercio",
  resolved: "Resuelta",
  closed: "Cerrada",
};

export const SUPPORT_CONTACT_LABELS: Record<SupportContactPreference, string> = {
  in_app: "Por el panel",
  email: "Por email",
  phone: "Por teléfono",
};

export function supportStatusTone(
  status: SupportStatus,
): "ok" | "warn" | "neutral" | "danger" | "info" {
  if (status === "resolved") return "ok";
  if (status === "waiting_platform") return "warn";
  if (status === "closed") return "neutral";
  return "info";
}

export function isSupportThreadOpen(status: SupportStatus): boolean {
  return status !== "closed" && status !== "resolved";
}

export function supportExcerpt(body: string, limit = 120): string {
  const clean = body.replace(/\s+/g, " ").trim();
  return clean.length <= limit ? clean : `${clean.slice(0, limit - 1).trimEnd()}…`;
}
