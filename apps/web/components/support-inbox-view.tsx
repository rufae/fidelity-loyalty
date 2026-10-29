"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  EmptyState,
  IconMail,
  IconPlus,
  LinkButton,
  LoadingState,
  PageHeader,
  Panel,
  StatusPill,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  support,
  supportStatusTone,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_STATUS_LABELS,
  type SupportThreadPage,
} from "@/lib/support";
import { formatDateTime } from "@/lib/ui";

/** Lista de conversaciones de soporte del comercio (Plan.md §10.1). */
export function SupportInboxView({ merchantId }: { merchantId: string }) {
  const [page, setPage] = useState<SupportThreadPage | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void support
      .threads(merchantId)
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
  }, [merchantId]);

  useEffect(() => load(), [load]);

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert tone="danger" title="No se pudo cargar el soporte">
          {loadError}
        </Alert>
        <Button onClick={load}>Volver a intentar</Button>
      </div>
    );
  }

  if (!page) return <LoadingState label="Cargando conversaciones…" />;

  const openCount = page.items.filter((thread) => thread.status !== "closed").length;
  const unread = page.items.reduce((sum, thread) => sum + thread.unread_for_viewer, 0);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Ayuda"
        title="Soporte"
        description="Escribe al equipo de LocalAI Fidelity. Tus conversaciones son privadas de este comercio."
        actions={
          <LinkButton href={`/merchants/${merchantId}/support/new`} icon={<IconPlus size={17} />}>
            Nueva conversación
          </LinkButton>
        }
      />

      <div className="flex flex-wrap gap-2">
        <span className="rounded-xl border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink shadow-soft">
          {page.total} {page.total === 1 ? "conversación" : "conversaciones"}
        </span>
        {openCount > 0 && (
          <span className="rounded-full bg-warn-soft px-2.5 py-1 text-xs font-semibold text-warn">
            {openCount} abiertas
          </span>
        )}
        {unread > 0 && (
          <span className="rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold text-brand">
            {unread} sin leer
          </span>
        )}
      </div>

      {page.items.length === 0 ? (
        <EmptyState
          illustration="card"
          title="Todavía no has contactado con soporte"
          description="Si tienes una duda del programa, una incidencia técnica o necesitas ayuda con el material, abre una conversación."
          action={
            <LinkButton href={`/merchants/${merchantId}/support/new`} icon={<IconPlus size={17} />}>
              Nueva conversación
            </LinkButton>
          }
        />
      ) : (
        <Panel padded={false}>
          <ul>
            {page.items.map((thread) => (
              <li key={thread.id} className="border-b border-line last:border-b-0">
                <Link
                  href={`/merchants/${merchantId}/support/${thread.id}`}
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
                      <Badge tone="neutral">{SUPPORT_CATEGORY_LABELS[thread.category]}</Badge>
                      <span>Última actividad: {formatDateTime(thread.last_message_at)}</span>
                      {thread.has_callback_request && (
                        <Badge tone="info">Pide llamada</Badge>
                      )}
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
          El equipo de soporte responde desde el panel. Si necesitas una llamada, puedes pedirla
          en la conversación y te contactaremos por el número que nos indiques, sin exponer
          nuestros datos personales.
        </p>
      </div>
    </div>
  );
}
