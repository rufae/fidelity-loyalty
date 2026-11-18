"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  Checkbox,
  ConfirmDialog,
  FormField,
  IconArrowLeft,
  IconClock,
  IconInfo,
  Input,
  LoadingState,
  Panel,
  SectionTitle,
  StatusPill,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  isSupportThreadOpen,
  newIdempotencyKey,
  support,
  supportStatusTone,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_CONTACT_LABELS,
  SUPPORT_STATUS_LABELS,
  type SupportThreadDetail,
} from "@/lib/support";
import { formatDateTime } from "@/lib/ui";

/** Hilo de conversación del comercio con soporte (Plan.md §10.1). */
export function SupportThreadDetailView({
  merchantId,
  threadId,
}: {
  merchantId: string;
  threadId: string;
}) {
  const [thread, setThread] = useState<SupportThreadDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [phone, setPhone] = useState("");
  const [availability, setAvailability] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    void support
      .thread(merchantId, threadId)
      .then((data) => {
        if (!cancelled) {
          setThread(data);
          setLoadError(null);
          void support.markRead(merchantId, threadId).catch(() => undefined);
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
  }, [merchantId, threadId]);

  useEffect(() => load(), [load]);

  // Conversación viva: si soporte responde, aparece sin recargar. Sondeo
  // discreto solo con pestaña visible (mismo patrón que la tarjeta web).
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 20_000);
    const onVisibility = (): void => {
      if (document.visibilityState === "visible") load();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [load]);

  async function sendReply(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.reply(merchantId, threadId, reply.trim(), newIdempotencyKey());
      setReply("");
      setNotice("Mensaje enviado a soporte.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el mensaje.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCallback(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await support.requestCallback(
        merchantId,
        threadId,
        {
          phone: phone.trim(),
          availability: availability.trim() || undefined,
          consent,
        },
        newIdempotencyKey(),
      );
      setPhone("");
      setAvailability("");
      setConsent(false);
      setNotice("Solicitud de llamada registrada.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo solicitar la llamada.");
    } finally {
      setBusy(false);
    }
  }

  async function closeThread() {
    setBusy(true);
    setError(null);
    try {
      await support.closeThread(merchantId, threadId);
      setConfirmClose(false);
      setNotice("Conversación cerrada.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la conversación.");
    } finally {
      setBusy(false);
    }
  }

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

  const open = isSupportThreadOpen(thread.status);
  const callback = thread.callback_request;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <Link
          href={`/merchants/${merchantId}/support`}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-brand"
        >
          <IconArrowLeft size={16} />
          Volver a soporte
        </Link>
      </div>

      <Panel className="animate-in">
        <SectionTitle
          eyebrow={SUPPORT_CATEGORY_LABELS[thread.category]}
          title={thread.subject}
          description={`Abierta el ${formatDateTime(thread.created_at)} · ${SUPPORT_CONTACT_LABELS[thread.preferred_contact]}`}
          action={
            <StatusPill tone={supportStatusTone(thread.status)}>
              {SUPPORT_STATUS_LABELS[thread.status]}
            </StatusPill>
          }
        />

        {callback && (
          <div className="mb-5 flex items-start gap-3 rounded-2xl border border-brand/25 bg-brand-soft/40 p-4">
            <IconClock size={18} className="mt-0.5 shrink-0 text-brand" />
            <div>
              <p className="text-sm font-semibold text-ink">
                {callback.status === "called"
                  ? "Llamada realizada"
                  : "Has pedido una llamada"}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                {callback.status === "called"
                  ? "El equipo de soporte ya ha contactado contigo por esta solicitud."
                  : "El equipo de soporte te llamará al número que indicaste. No mostramos el número por seguridad."}
                {callback.availability ? ` Disponibilidad: ${callback.availability}.` : ""}
              </p>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {thread.messages.map((message) => {
            const own = message.author_type === "merchant";
            return (
              <article
                key={message.id}
                className={`rounded-2xl border p-4 ${
                  own
                    ? "border-line bg-surface-2/60"
                    : "border-brand/20 bg-brand-soft/40"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {own ? "Tú" : message.author_display_name}
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
            <FormField label="Responder" required>
              {({ id, describedBy }) => (
                <Textarea
                  id={id}
                  aria-describedby={describedBy}
                  required
                  maxLength={4000}
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="Escribe tu respuesta…"
                />
              )}
            </FormField>
            <Button type="submit" loading={busy}>
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

      {open && !callback && (
        <Panel tone="warm">
          <SectionTitle
            title="¿Prefieres que te llamemos?"
            description="Deja tu número y el equipo de soporte te llamará de forma privada. La app no inicia llamadas."
            icon={<IconClock size={18} />}
          />
          <form onSubmit={submitCallback} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="Teléfono" required>
                {({ id, describedBy }) => (
                  <Input
                    id={id}
                    aria-describedby={describedBy}
                    required
                    type="tel"
                    minLength={6}
                    maxLength={32}
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="+34 600 000 000"
                  />
                )}
              </FormField>
              <FormField label="Disponibilidad" optional>
                {({ id, describedBy }) => (
                  <Input
                    id={id}
                    aria-describedby={describedBy}
                    maxLength={160}
                    value={availability}
                    onChange={(event) => setAvailability(event.target.value)}
                    placeholder="Ej.: mañanas"
                  />
                )}
              </FormField>
            </div>
            <Checkbox
              label="Acepto que me llamen a este número para atender esta solicitud."
              description="El número se guarda cifrado y solo lo ve el equipo de soporte."
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <Button type="submit" loading={busy} variant="secondary">
              Solicitar llamada
            </Button>
          </form>
        </Panel>
      )}

      {open && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-paper p-4">
          <div className="flex items-start gap-2 text-sm text-ink-soft">
            <IconInfo size={17} className="mt-0.5 shrink-0 text-brand" />
            <p>Si ya no necesitas ayuda, puedes cerrar la conversación.</p>
          </div>
          <Button variant="secondary" onClick={() => setConfirmClose(true)}>
            Cerrar conversación
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmClose}
        title="Cerrar conversación"
        message="Ya no podrás añadir mensajes a esta conversación. Si vuelve a surgir el problema, abre una nueva."
        confirmLabel="Cerrar"
        onConfirm={closeThread}
        onClose={() => setConfirmClose(false)}
        busy={busy}
      />
    </div>
  );
}
