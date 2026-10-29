"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  FormField,
  IconArrowLeft,
  IconCheck,
  IconClock,
  IconMail,
  IconRefresh,
  Input,
  LoadingState,
  Panel,
  SectionTitle,
  Select,
  StatusPill,
  Textarea,
} from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { isPlatformAdmin, type SessionPayload } from "@/lib/session";
import {
  newIdempotencyKey,
  support,
  supportStatusTone,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_CONTACT_LABELS,
  SUPPORT_STATUS_LABELS,
  type SupportStatus,
  type SupportThreadDetail,
} from "@/lib/support";
import { formatDateTime } from "@/lib/ui";

const CHANNEL_LABELS: Record<string, string> = {
  email_platform: "Email",
  email_merchant: "Email al comercio",
  ntfy: "ntfy",
  telegram: "Telegram",
};

/**
 * Detalle de conversación para la plataforma: respuesta, estado, prioridad,
 * solicitud de llamada y reintentos de aviso (Plan.md §10.2).
 */
export function PlatformSupportThreadDetailView({ threadId }: { threadId: string }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [thread, setThread] = useState<SupportThreadDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmCalled, setConfirmCalled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void apiFetch<SessionPayload>("/api/v1/auth/me")
      .then((payload) => {
        if (cancelled) return;
        if (isPlatformAdmin(payload.user)) setAllowed(true);
        else router.replace("/");
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  const load = useCallback(() => {
    if (!allowed) return () => undefined;
    let cancelled = false;
    void support
      .platformThread(threadId)
      .then((data) => {
        if (!cancelled) {
          setThread(data);
          setLoadError(null);
          void support.platformMarkRead(threadId).catch(() => undefined);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof ApiError ? err.message : "No se pudo cargar la conversación.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [allowed, threadId]);

  useEffect(() => load(), [load]);

  async function sendReply(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.platformReply(threadId, reply.trim(), newIdempotencyKey());
      setReply("");
      setNotice("Respuesta enviada al comercio.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar la respuesta.");
    } finally {
      setBusy(false);
    }
  }

  async function updateThread(body: { status?: SupportStatus; priority?: "normal" | "high" }) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.platformUpdate(threadId, body);
      setNotice("Conversación actualizada.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar.");
    } finally {
      setBusy(false);
    }
  }

  async function markCalled() {
    if (!thread?.callback_request) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.platformMarkCalled(threadId, thread.callback_request.id, notes.trim() || undefined);
      setConfirmCalled(false);
      setNotes("");
      setNotice("Llamada marcada como realizada.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo marcar la llamada.");
    } finally {
      setBusy(false);
    }
  }

  async function retry(notificationId: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.retryNotification(notificationId);
      setNotice("Aviso reintentado.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo reintentar el aviso.");
    } finally {
      setBusy(false);
    }
  }

  if (!allowed) return <LoadingState label="Comprobando acceso…" />;

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert tone="danger" title="No se pudo cargar">
          {loadError}
        </Alert>
        <Button onClick={load}>Volver a intentar</Button>
      </div>
    );
  }

  if (!thread) return <LoadingState label="Cargando conversación…" />;

  const callback = thread.callback_request;
  const open = thread.status !== "closed";

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <Link
          href="/platform/support"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-brand"
        >
          <IconArrowLeft size={16} />
          Volver al buzón
        </Link>
      </div>

      <Panel className="animate-in">
        <SectionTitle
          eyebrow={`${thread.merchant_name ?? "Comercio"} · ${SUPPORT_CATEGORY_LABELS[thread.category]}`}
          title={thread.subject}
          description={`Abierta por ${thread.created_by_display_name} el ${formatDateTime(thread.created_at)} · ${SUPPORT_CONTACT_LABELS[thread.preferred_contact]}`}
          action={
            <StatusPill tone={supportStatusTone(thread.status)}>
              {SUPPORT_STATUS_LABELS[thread.status]}
            </StatusPill>
          }
        />

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <Badge tone="brand">{thread.merchant_name ?? "Comercio"}</Badge>
          <Badge tone="neutral">{thread.created_by_display_name}</Badge>
          <Badge tone={thread.priority === "high" ? "warn" : "neutral"}>
            {thread.priority === "high" ? "Prioridad alta" : "Prioridad normal"}
          </Badge>
          {callback && <Badge tone="info">Pide llamada</Badge>}
        </div>

        {callback && (
          <div className="mb-5 rounded-2xl border border-brand/25 bg-brand-soft/40 p-4">
            <div className="flex items-start gap-3">
              <IconClock size={18} className="mt-0.5 shrink-0 text-brand" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">
                  {callback.status === "called" ? "Llamada realizada" : "Solicitud de llamada"}
                </p>
                <p className="mt-1 text-sm text-ink-soft">
                  Teléfono: <span className="font-mono">{callback.phone ?? "No disponible"}</span>
                  {callback.availability ? ` · Disponibilidad: ${callback.availability}` : ""}
                </p>
                {callback.status !== "called" && (
                  <div className="mt-3 space-y-2">
                    <FormField label="Nota interna" optional>
                      {({ id, describedBy }) => (
                        <Input
                          id={id}
                          aria-describedby={describedBy}
                          value={notes}
                          maxLength={255}
                          onChange={(event) => setNotes(event.target.value)}
                          placeholder="Ej.: llamada realizada, hablar por la tarde"
                        />
                      )}
                    </FormField>
                    <Button
                      variant="secondary"
                      onClick={() => setConfirmCalled(true)}
                      icon={<IconCheck size={17} />}
                    >
                      Marcar llamada realizada
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {thread.messages.map((message) => {
            const merchant = message.author_type === "merchant";
            return (
              <article
                key={message.id}
                className={`rounded-2xl border p-4 ${
                  merchant ? "border-line bg-surface-2/60" : "border-brand/20 bg-brand-soft/40"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {merchant ? thread.created_by_display_name : "Soporte"}
                  </p>
                  <p className="text-xs text-ink-faint">{formatDateTime(message.created_at)}</p>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">
                  {message.body}
                </p>
              </article>
            );
          })}
        </div>

        {open && (
          <form onSubmit={sendReply} className="mt-5 space-y-3">
            <FormField label="Responder al comercio" required>
              {({ id, describedBy }) => (
                <Textarea
                  id={id}
                  aria-describedby={describedBy}
                  required
                  maxLength={4000}
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="Escribe la respuesta…"
                />
              )}
            </FormField>
            <Button type="submit" loading={busy} icon={<IconMail size={17} />}>
              Enviar respuesta
            </Button>
          </form>
        )}

        {error && (
          <div className="mt-4">
            <Alert tone="danger" title="No se pudo completar">
              {error}
            </Alert>
          </div>
        )}
        {notice && (
          <div className="mt-4">
            <Alert tone="ok" title="Hecho">
              {notice}
            </Alert>
          </div>
        )}
      </Panel>

      <Panel>
        <SectionTitle
          title="Gestión de la conversación"
          description="Cambia el estado o la prioridad. Los cambios quedan auditados."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Estado">
            {({ id }) => (
              <Select
                id={id}
                value={thread.status}
                onChange={(event) => void updateThread({ status: event.target.value as SupportStatus })}
              >
                {(Object.keys(SUPPORT_STATUS_LABELS) as SupportStatus[]).map((value) => (
                  <option key={value} value={value}>
                    {SUPPORT_STATUS_LABELS[value]}
                  </option>
                ))}
              </Select>
            )}
          </FormField>
          <FormField label="Prioridad">
            {({ id }) => (
              <Select
                id={id}
                value={thread.priority}
                onChange={(event) =>
                  void updateThread({ priority: event.target.value as "normal" | "high" })
                }
              >
                <option value="normal">Normal</option>
                <option value="high">Alta</option>
              </Select>
            )}
          </FormField>
        </div>
      </Panel>

      {thread.notifications.length > 0 && (
        <Panel>
          <SectionTitle
            title="Avisos"
            description="Estado del envío de email, ntfy y Telegram para esta conversación."
          />
          <ul className="divide-y divide-line">
            {thread.notifications.map((notification) => (
              <li
                key={notification.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div>
                  <p className="text-sm font-semibold text-ink">
                    {CHANNEL_LABELS[notification.channel] ?? notification.channel}
                  </p>
                  <p className="text-xs text-ink-faint">
                    {notification.status === "succeeded" && notification.sent_at
                      ? `Enviado ${formatDateTime(notification.sent_at)}`
                      : `${notification.attempts} intentos${notification.error_code ? ` · ${notification.error_code}` : ""}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill
                    tone={
                      notification.status === "succeeded"
                        ? "ok"
                        : notification.status === "failed"
                          ? "danger"
                          : "warn"
                    }
                  >
                    {notification.status}
                  </StatusPill>
                  {notification.status !== "succeeded" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void retry(notification.id)}
                      icon={<IconRefresh size={15} />}
                    >
                      Reintentar
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <ConfirmDialog
        open={confirmCalled}
        title="Marcar llamada como realizada"
        message="Se registrará que el equipo ya ha contactado con el comercio por esta solicitud."
        confirmLabel="Marcar realizada"
        onConfirm={markCalled}
        onClose={() => setConfirmCalled(false)}
        busy={busy}
      />
    </div>
  );
}
