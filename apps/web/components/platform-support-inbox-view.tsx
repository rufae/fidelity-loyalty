"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  EmptyState,
  FormField,
  IconMail,
  Input,
  LinkButton,
  LoadingState,
  PageHeader,
  Panel,
  Select,
  StatusPill,
} from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { isPlatformAdmin, type SessionPayload } from "@/lib/session";
import {
  support,
  supportStatusTone,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_STATUS_LABELS,
  type SupportStatus,
  type SupportThreadPage,
} from "@/lib/support";
import { formatDateTime } from "@/lib/ui";

/**
 * Buzón de soporte de la plataforma: conversaciones de todos los comercios.
 * Solo `platform_owner`/`platform_admin`; cualquier otra sesión vuelve a la
 * portada. El teléfono de llamada aparece solo dentro del detalle.
 */
export function PlatformSupportInboxView() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [page, setPage] = useState<SupportThreadPage | null>(null);
  const [status, setStatus] = useState<SupportStatus | "">("");
  const [q, setQ] = useState("");
  const [qText, setQText] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);

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
      .platformThreads({ status: status || undefined, q: q || undefined })
      .then((rows) => {
        if (!cancelled) {
          setPage(rows);
          setLoadError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof ApiError ? err.message : "No se pudieron cargar las conversaciones.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [allowed, status, q]);

  useEffect(() => load(), [load]);

  if (!allowed) return <LoadingState label="Comprobando acceso…" />;

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert tone="danger" title="No se pudo cargar el buzón">
          {loadError}
        </Alert>
        <Button onClick={load}>Volver a intentar</Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Administración de plataforma"
        title="Soporte"
        description="Conversaciones de los comercios que contratan LocalAI Fidelity."
        actions={<LinkButton href="/merchants" variant="secondary">Volver a comercios</LinkButton>}
      />

      <Panel className="animate-in">
        <form
          className="grid grid-cols-1 gap-3 sm:grid-cols-[200px_1fr_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            setQ(qText.trim());
          }}
        >
          <FormField label="Estado">
            {({ id }) => (
              <Select
                id={id}
                value={status}
                onChange={(event) => setStatus(event.target.value as SupportStatus | "")}
              >
                <option value="">Todos</option>
                {(Object.keys(SUPPORT_STATUS_LABELS) as SupportStatus[]).map((value) => (
                  <option key={value} value={value}>
                    {SUPPORT_STATUS_LABELS[value]}
                  </option>
                ))}
              </Select>
            )}
          </FormField>
          <FormField label="Buscar">
            {({ id }) => (
              <Input
                id={id}
                value={qText}
                onChange={(event) => setQText(event.target.value)}
                placeholder="Asunto o comercio"
              />
            )}
          </FormField>
          <div className="flex items-end">
            <Button type="submit" variant="secondary">
              Buscar
            </Button>
          </div>
        </form>
      </Panel>

      {!page ? (
        <LoadingState label="Cargando conversaciones…" />
      ) : page.items.length === 0 ? (
        <EmptyState
          illustration="card"
          title="No hay conversaciones con estos filtros"
          description="Cuando un comercio abra soporte, aparecerá aquí."
        />
      ) : (
        <Panel padded={false}>
          <ul>
            {page.items.map((thread) => (
              <li key={thread.id} className="border-b border-line last:border-b-0">
                <Link
                  href={`/platform/support/${thread.id}`}
                  className="flex flex-wrap items-start justify-between gap-3 px-5 py-4 transition-colors hover:bg-surface-2/50"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {thread.unread_for_viewer > 0 && (
                        <span className="rounded-full bg-brand px-2 py-0.5 text-[11px] font-bold text-white">
                          {thread.unread_for_viewer}
                        </span>
                      )}
                      <p className="truncate font-semibold text-ink">{thread.subject}</p>
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                      <Badge tone="brand">{thread.merchant_name ?? "Comercio"}</Badge>
                      <Badge tone="neutral">{SUPPORT_CATEGORY_LABELS[thread.category]}</Badge>
                      <span>{formatDateTime(thread.last_message_at)}</span>
                      {thread.has_callback_request && <Badge tone="info">Pide llamada</Badge>}
                    </div>
                  </div>
                  <StatusPill tone={supportStatusTone(thread.status)}>
                    {SUPPORT_STATUS_LABELS[thread.status]}
                  </StatusPill>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <div className="flex items-start gap-3 rounded-2xl border border-line bg-paper p-4 text-sm text-ink-soft">
        <IconMail size={18} className="mt-0.5 shrink-0 text-brand" />
        <p>
          Los datos de contacto del comercio solo aparecen dentro de cada conversación. No se
          incluyen en listados ni en las notificaciones.
        </p>
      </div>
    </div>
  );
}
