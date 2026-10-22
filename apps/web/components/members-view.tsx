"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  CopyButton,
  EmptyState,
  IconChevronDown,
  IconContactless,
  IconEye,
  IconEyeOff,
  IconSearch,
  IconUsers,
  Input,
  LinkButton,
  LoadingState,
  Panel,
} from "@/components/ui";
import { useMerchant } from "@/components/merchant-context";
import { ApiError } from "@/lib/api";
import { fidelity, type Membership } from "@/lib/fidelity";
import { canManageMerchant } from "@/lib/session";
import { formatDate } from "@/lib/ui";

const STATUS_TONE: Record<string, "ok" | "warn" | "neutral" | "danger" | "info"> = {
  active: "ok",
  suspended: "warn",
  revoked: "danger",
  deletion_pending: "info",
  anonymized: "neutral",
  inactive: "neutral",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  suspended: "Suspendida",
  revoked: "Revocada",
  deletion_pending: "Eliminación solicitada",
  anonymized: "Eliminada",
  inactive: "Inactiva",
  blocked: "Bloqueada",
  deleted: "Eliminada",
};

type LifecycleAction = "suspend" | "reactivate" | "revoke" | "anonymize";

function initials(name: string | null | undefined): string {
  if (!name?.trim()) return "·";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * Clientes y tarjetas del comercio:
 * - el código se muestra bajo demanda (copiable) desde la ficha del cliente;
 * - el ciclo de vida (suspender/reactivar/revocar/eliminar) se ejecuta en
 *   backend con confirmación y auditoría;
 * - «Eliminar» ejecuta la supresión en un paso y conserva el ledger
 *   seudonimizado por integridad contable.
 *
 * La tabla usa un ancho fijo y solo aparece cuando hay sitio real (xl). Antes
 * se cortaba la columna de acciones a 1280 px; ahora las acciones viven en una
 * fila propia y no se solapan con el contenido.
 */
export function MembersView({ merchantId }: { merchantId: string }) {
  const { role, isPlatformAdmin: platformAdmin } = useMerchant();
  const [memberships, setMemberships] = useState<Membership[] | null>(null);
  /** Fallo de la carga inicial: con él hay que renderizar el error antes que
      el spinner (corrección de la auditoría: antes quedaba cargando infinito). */
  const [loadError, setLoadError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  /** Lo que hay escrito en el campo; la búsqueda se aplica al enviar para no
      lanzar una consulta por cada tecla. */
  const [qText, setQText] = useState("");
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ row: Membership; action: LifecycleAction } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  const canManage = platformAdmin || (role !== null && canManageMerchant(role));

  const load = useCallback(
    (search?: string) => {
      let cancelled = false;
      void fidelity
        .memberships(merchantId, search?.trim() || undefined)
        .then((rows) => {
          if (cancelled) return;
          setMemberships(rows);
          setLoadError(null);
        })
        .catch(() => {
          if (!cancelled) setLoadError("No se pudieron cargar las tarjetas.");
        });
      return () => {
        cancelled = true;
      };
    },
    [merchantId],
  );

  useEffect(() => load(q), [load, q]);

  // Las altas y los cambios de otras cajas aparecen sin recargar: refresco
  // suave (solo con la pestaña visible) y al volver a la pestaña.
  useEffect(() => {
    const reload = (): void => {
      if (document.visibilityState === "visible") load(q);
    };
    const interval = window.setInterval(reload, 30_000);
    window.addEventListener("focus", reload);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", reload);
    };
  }, [load, q]);

  async function runAction(row: Membership, action: LifecycleAction, reason?: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await fidelity.lifecycleAction(merchantId, row.id, action, reason);
      setNotice(MESSAGES[action]);
      load(q);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la operación.");
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  }

  function toggleReveal(id: string) {
    setRevealed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (!memberships) {
    if (loadError) {
      return (
        <div className="space-y-4">
          <Alert tone="danger" title="No se pudo cargar">
            {loadError}
          </Alert>
          <Button
            onClick={() => {
              setLoadError(null);
              load(q);
            }}
          >
            Reintentar
          </Button>
        </div>
      );
    }
    return <LoadingState label="Cargando clientes…" />;
  }

  if (memberships.length === 0 && !q) {
    return (
      <EmptyState
        illustration="users"
        title="Todavía no hay clientes registrados"
        description="Coloca la etiqueta NFC o comparte la URL de alta para que tus clientes creen su tarjeta."
        action={
          <LinkButton
            href={`/merchants/${merchantId}/nfc`}
            icon={<IconContactless size={17} />}
          >
            Preparar etiquetas NFC y QR
          </LinkButton>
        }
      />
    );
  }

  const activeCount = memberships.filter((row) => row.status === "active").length;
  const suspendedCount = memberships.filter((row) => row.status === "suspended").length;

  return (
    <div className="space-y-4">
      {error && (
        <Alert tone="danger" title="No se pudo completar">
          {error}
        </Alert>
      )}
      {notice && (
        <Alert tone="ok" title="Hecho">
          {notice}
        </Alert>
      )}

      <Panel padded={false} className="overflow-visible">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-xl border border-line bg-paper px-3 py-2 text-sm font-semibold text-ink">
              <IconUsers size={16} className="text-brand" />
              {memberships.length} {memberships.length === 1 ? "tarjeta" : "tarjetas"}
            </span>
            {activeCount > 0 && (
              <span className="rounded-full bg-ok-soft px-2.5 py-1 text-xs font-semibold text-ok">
                {activeCount} activas
              </span>
            )}
            {suspendedCount > 0 && (
              <span className="rounded-full bg-warn-soft px-2.5 py-1 text-xs font-semibold text-warn">
                {suspendedCount} suspendidas
              </span>
            )}
          </div>
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              setQ(qText.trim());
            }}
          >
            <div className="relative">
              <IconSearch
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
              />
              <label className="sr-only" htmlFor="members-search">
                Buscar por nombre o correo
              </label>
              <Input
                id="members-search"
                type="search"
                value={qText}
                onChange={(event) => setQText(event.target.value)}
                placeholder="Nombre o correo"
                className="w-56 pl-9"
              />
            </div>
            <Button type="submit" size="sm" variant="secondary">
              Buscar
            </Button>
            {(q || qText) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setQText("");
                  setQ("");
                }}
              >
                Limpiar
              </Button>
            )}
          </form>
        </div>

        {memberships.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-semibold text-ink">Sin resultados para «{q}»</p>
            <p className="mt-1 text-xs text-ink-faint">
              Prueba con otro nombre o correo, o limpia la búsqueda.
            </p>
          </div>
        ) : (
          <>
            {/* Tabla en escritorio: ancho fijo, sin recortes ni scroll oculto. */}
            <div className="hidden xl:block">
              <table className="w-full table-fixed text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-surface-2/60 text-[11px] uppercase tracking-[0.06em] text-ink-faint">
                    <th className="w-[30%] px-4 py-3 font-semibold">Cliente</th>
                    <th className="w-[20%] px-4 py-3 font-semibold">Programa</th>
                    <th className="w-16 px-4 py-3 font-semibold">Sellos</th>
                    <th className="w-28 px-4 py-3 font-semibold">Estado</th>
                    <th className="w-28 px-4 py-3 font-semibold">Alta</th>
                    {canManage && (
                      <th className="w-[152px] px-4 py-3 text-right font-semibold">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {memberships.map((row) => (
                    <tr
                      key={row.id}
                      className="border-b border-line align-top last:border-b-0 hover:bg-surface-2/40"
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex items-start gap-3">
                          <span
                            aria-hidden="true"
                            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand"
                          >
                            {initials(row.member_name)}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-ink">
                              {row.member_name || "Sin nombre"}
                            </p>
                            {row.member_email && (
                              <p className="truncate text-xs text-ink-faint">{row.member_email}</p>
                            )}
                            <div className="mt-1">
                              <CodeCell
                                code={row.public_token}
                                revealed={revealed.has(row.id)}
                                onToggle={() => toggleReveal(row.id)}
                              />
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-ink-soft">
                        <span className="line-clamp-2 break-words">{row.program_name ?? "—"}</span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="tnum text-lg font-bold text-ink">{row.stamps}</span>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge tone={STATUS_TONE[row.status] ?? "neutral"}>
                          {STATUS_LABELS[row.status] ?? row.status}
                        </Badge>
                        {row.status_reason && (
                          <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-ink-faint">
                            {row.status_reason}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-ink-soft">
                        {formatDate(row.joined_at)}
                      </td>
                      {canManage && (
                        <td className="px-4 py-3.5">
                          <ActionsCell
                            row={row}
                            onAction={(action) => setConfirm({ row, action })}
                          />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Fichas en pantallas medianas y móvil: nada se corta. */}
            <ul className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:hidden">
              {memberships.map((row) => (
                <li key={row.id} className="min-w-0 rounded-2xl border border-line bg-surface p-4">
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden="true"
                      className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand"
                    >
                      {initials(row.member_name)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-ink">
                            {row.member_name || "Sin nombre"}
                          </p>
                          <p className="truncate text-xs text-ink-faint">
                            {row.program_name ? `«${row.program_name}» · ` : ""}
                            {row.member_email || "sin correo"}
                          </p>
                        </div>
                        <Badge tone={STATUS_TONE[row.status] ?? "neutral"}>
                          {STATUS_LABELS[row.status] ?? row.status}
                        </Badge>
                      </div>
                      <div className="mt-2.5 flex items-center justify-between gap-3">
                        <p className="tnum text-2xl font-bold text-ink">
                          {row.stamps}{" "}
                          <span className="text-xs font-medium text-ink-faint">sellos</span>
                        </p>
                        <p className="text-[11px] text-ink-faint">Alta: {formatDate(row.joined_at)}</p>
                      </div>
                      {row.status_reason && (
                        <p className="mt-1 text-xs text-ink-faint">{row.status_reason}</p>
                      )}
                      <div className="mt-2">
                        <CodeCell
                          code={row.public_token}
                          revealed={revealed.has(row.id)}
                          onToggle={() => toggleReveal(row.id)}
                        />
                      </div>
                      {canManage && (
                        <div className="mt-3 border-t border-line pt-3">
                          <ActionsCell
                            row={row}
                            onAction={(action) => setConfirm({ row, action })}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </Panel>

      <p className="text-[11px] leading-relaxed text-ink-faint">
        El código identifica la tarjeta; no es una cuenta de administración. Las búsquedas y los
        cambios de ciclo de vida quedan auditados.
      </p>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm ? TITLES[confirm.action] : ""}
        message={confirm ? CONSEQUENCES[confirm.action] : ""}
        confirmLabel={confirm ? CONFIRM_LABELS[confirm.action] : "Confirmar"}
        busy={busy}
        onClose={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm) void runAction(confirm.row, confirm.action);
        }}
      />
    </div>
  );
}

const MESSAGES: Record<LifecycleAction, string> = {
  suspend: "Tarjeta suspendida: ya no puede sumar ni canjear.",
  reactivate: "Tarjeta reactivada: vuelve a funcionar con normalidad.",
  revoke: "Tarjeta revocada: bloqueo permanente registrado.",
  anonymize:
    "Cliente eliminado: datos personales borrados y fuera de la lista. El historial de movimientos se conserva de forma anónima.",
};

const TITLES: Record<LifecycleAction, string> = {
  suspend: "¿Suspender esta tarjeta?",
  reactivate: "¿Reactivar esta tarjeta?",
  revoke: "¿Revocar esta tarjeta?",
  anonymize: "¿Eliminar este cliente?",
};

const CONSEQUENCES: Record<LifecycleAction, string> = {
  suspend:
    "La tarjeta deja de sumar sellos y de canjear recompensas de inmediato. Es reversible: puedes reactivarla cuando quieras.",
  reactivate: "La tarjeta vuelve a poder sumar sellos y canjear recompensas.",
  revoke:
    "Bloqueo permanente del programa (no se puede reactivar). La tarjeta Wallet que el cliente ya tenga no se borra de su móvil: Apple y Google no permiten un borrado remoto garantizado, pero dejará de servir para operar.",
  anonymize:
    "Se borran de forma irreversible el nombre y el email, y el cliente dejará de aparecer en esta lista. Los movimientos del ledger se conservan seudonimizados por obligación contable: no se puede deshacer. La tarjeta añadida a su móvil no se puede borrar a distancia (Apple y Google no lo permiten).",
};

const CONFIRM_LABELS: Record<LifecycleAction, string> = {
  suspend: "Suspender tarjeta",
  reactivate: "Reactivar tarjeta",
  revoke: "Revocar tarjeta",
  anonymize: "Eliminar cliente",
};

function ActionsCell({
  row,
  onAction,
}: {
  row: Membership;
  onAction: (action: LifecycleAction) => void;
}) {
  const primary: { action: LifecycleAction; label: string } | null =
    row.status === "active"
      ? { action: "suspend", label: "Suspender" }
      : row.status === "suspended"
        ? { action: "reactivate", label: "Reactivar" }
        : null;
  const secondary: { action: LifecycleAction; label: string; danger?: boolean }[] = [];
  if (row.status === "active" || row.status === "suspended") {
    secondary.push({ action: "revoke", label: "Revocar tarjeta", danger: true });
    secondary.push({ action: "anonymize", label: "Eliminar cliente", danger: true });
  } else if (row.status === "revoked" || row.status === "deletion_pending") {
    secondary.push({ action: "anonymize", label: "Eliminar cliente", danger: true });
  }

  if (!primary && secondary.length === 0) {
    return <span className="text-xs text-ink-faint">—</span>;
  }

  return (
    <div className="flex items-center justify-end gap-1.5">
      {primary && (
        <Button size="sm" variant="secondary" onClick={() => onAction(primary.action)}>
          {primary.label}
        </Button>
      )}
      {secondary.length > 0 && (
        <details className="group relative">
          <summary
            aria-label="Más acciones"
            className="flex h-9 cursor-pointer list-none items-center gap-1 rounded-xl px-2 text-xs font-semibold text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink [&::-webkit-details-marker]:hidden"
          >
            Más
            <IconChevronDown size={14} className="transition-transform group-open:rotate-180" />
          </summary>
          <div className="absolute right-0 z-20 mt-1 w-44 rounded-xl border border-line bg-surface p-1 shadow-lift">
            {secondary.map((action) => (
              <button
                key={action.action}
                type="button"
                onClick={(event) => {
                  const wrapper = event.currentTarget.closest("details");
                  wrapper?.removeAttribute("open");
                  onAction(action.action);
                }}
                className={`block w-full rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors ${
                  action.danger
                    ? "text-danger hover:bg-danger-soft"
                    : "text-ink hover:bg-surface-2"
                }`}
              >
                {action.label}
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function CodeCell({
  code,
  revealed,
  onToggle,
}: {
  code: string;
  revealed: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {revealed ? (
        <>
          <code className="max-w-40 truncate rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-ink">
            {code}
          </code>
          <CopyButton value={code} label="Copiar" />
          <button
            type="button"
            onClick={onToggle}
            className="inline-flex items-center gap-1 text-[10px] font-semibold text-ink-faint hover:text-ink"
          >
            <IconEyeOff size={12} />
            ocultar
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="inline-flex items-center gap-1 rounded-md px-1 py-0.5 text-[10px] font-semibold text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <IconEye size={12} />
          Ver código
        </button>
      )}
    </div>
  );
}
