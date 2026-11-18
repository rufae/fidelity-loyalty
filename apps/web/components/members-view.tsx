"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  CopyButton,
  CountUp,
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
  Modal,
  Panel,
} from "@/components/ui";
import { useMerchant } from "@/components/merchant-context";
import { ApiError } from "@/lib/api";
import {
  fidelity,
  newIdempotencyKey,
  type Membership,
  type MembershipPage,
} from "@/lib/fidelity";
import { canManageMerchant, canOperateMerchant } from "@/lib/session";
import { formatDate, sellos, unidades } from "@/lib/ui";

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

/** Tamaño de página del listado (§12.1): el backend limita, aquí solo se
    calcula el rango visible de la paginación. */
const PAGE_SIZE = 25;

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
  /** Contadores reales de la cabecera: llegan con la página (§12.1), nunca
      se calculan sobre lo que hay pintado en pantalla. */
  const [counts, setCounts] = useState<MembershipPage | null>(null);
  /** Página visible (0-based): el backend pagina, la UI solo navega. */
  const [pageIndex, setPageIndex] = useState(0);
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
  /** Ajuste de saldo (§7.3): diálogo con cantidad con signo y motivo. */
  const [adjustRow, setAdjustRow] = useState<Membership | null>(null);
  /** Filtro «Premio listo»: solo clientes con recompensa canjeable ya. */
  const [readyOnly, setReadyOnly] = useState(false);
  /** Edición de datos del cliente (decisión de compra #9). */
  const [editRow, setEditRow] = useState<Membership | null>(null);
  const [busy, setBusy] = useState(false);

  const canManage = platformAdmin || (role !== null && canManageMerchant(role));
  /** Operar sellos: mismo rol que la consola de Operaciones (§8.1). */
  const canOperate = platformAdmin || (role !== null && canOperateMerchant(role));
  /** Alta «+1 sello» en curso: una fila cada vez, con feedback propio. */
  const [stampingId, setStampingId] = useState<string | null>(null);

  const load = useCallback(
    (search?: string) => {
      let cancelled = false;
      void fidelity
        .memberships(merchantId, {
          q: search?.trim() || undefined,
          ready: readyOnly,
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        })
        .then((page) => {
          if (cancelled) return;
          setMemberships(page.items);
          setCounts(page);
          setLoadError(null);
        })
        .catch(() => {
          if (!cancelled) setLoadError("No se pudieron cargar las tarjetas.");
        });
      return () => {
        cancelled = true;
      };
    },
    [merchantId, readyOnly, pageIndex],
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

  /** Ajuste manual de saldo (§7.3): solo administración, con motivo
      obligatorio y trazado. El saldo mostrado se actualiza con lo que
      confirma el backend, nunca con una suma en local. */
  async function applyAdjust(row: Membership, delta: number, reason: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await fidelity.adjust(merchantId, row.id, delta, reason.trim());
      setMemberships((rows) =>
        (rows ?? []).map((item) =>
          item.id === row.id ? { ...item, stamps: result.stamps } : item,
        ),
      );
      setNotice(
        `Ajuste registrado (${delta > 0 ? "+" : ""}${delta}): ${row.member_name ?? "el cliente"} lleva ${unidades(row.program_type, result.stamps)}. El movimiento queda en el historial.`,
      );
      // Reconcilia con el servidor: «Premio listo» y contadores los
      // recalcula el backend, nunca la suma local.
      load(q);
      setAdjustRow(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo aplicar el ajuste. Comprueba el saldo antes de repetirlo.",
      );
      setAdjustRow(null);
    } finally {
      setBusy(false);
    }
  }

  /** Edición de datos mínimos del cliente (decisión de compra #9).
      El backend audita; si el correo cambia queda sin verificar (ADR-0006). */
  async function applyEdit(
    row: Membership,
    changes: { display_name?: string; email?: string },
  ) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await fidelity.updateMembership(merchantId, row.id, changes);
      setMemberships((rows) =>
        (rows ?? []).map((item) =>
          item.id === row.id
            ? {
                ...item,
                member_name: updated.member_name ?? item.member_name,
                member_email: updated.member_email ?? item.member_email,
              }
            : item,
        ),
      );
      setNotice("Datos del cliente actualizados.");
      setEditRow(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar la edición.",
      );
      setEditRow(null);
    } finally {
      setBusy(false);
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

  /** «+1 sello» de un toque (§7.5): la misma operación autorizada y
      auditada que la consola de Operaciones, desde la ficha del cliente.
      El saldo mostrado se actualiza con lo que confirma el backend. */
  async function quickStamp(row: Membership) {
    setStampingId(row.id);
    setError(null);
    setNotice(null);
    try {
      const result = await fidelity.earn(merchantId, row.id, newIdempotencyKey("earn"));
      setMemberships((rows) =>
        (rows ?? []).map((item) =>
          item.id === row.id ? { ...item, stamps: result.stamps } : item,
        ),
      );
      setNotice(
        result.already_applied
          ? `La operación ya estaba registrada (no se ha duplicado): ${row.member_name ?? "el cliente"} tiene ${sellos(result.stamps)}.`
          : `Visita registrada: ${row.member_name ?? "el cliente"} lleva ${sellos(result.stamps)}.`,
      );
      // El backend recalcula «Premio listo»: se reconcilia la página.
      load(q);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo registrar la visita. Comprueba el saldo antes de repetirla.",
      );
    } finally {
      setStampingId(null);
    }
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

  if (memberships.length === 0 && !q && !readyOnly && (counts?.total ?? 0) === 0) {
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

  // Contadores de cabecera: valores reales de la base de datos para el
  // filtro activo; la paginación no recorta lo que se muestra aquí.
  const totalCount = counts?.total ?? memberships.length;
  const activeCount = counts?.active ?? 0;
  const suspendedCount = counts?.suspended ?? 0;
  const readyCount = counts?.ready ?? 0;
  // El filtro «Premio listo» lo aplica el backend: en cliente solo se pinta
  // la página devuelta (nada de recortes locales sobre una página parcial).
  const visibleRows = memberships;
  const pageStart = pageIndex * PAGE_SIZE;
  const pageEnd = Math.min(pageStart + memberships.length, totalCount);
  const hasPages = totalCount > PAGE_SIZE;

  return (
    <div className="stagger space-y-4">
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
              {totalCount} {totalCount === 1 ? "tarjeta" : "tarjetas"}
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
            <button
              type="button"
              onClick={() => {
                // El filtro viaja al backend: cambiarlo vuelve a la página 1.
                setReadyOnly((value) => !value);
                setPageIndex(0);
              }}
              aria-pressed={readyOnly}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                readyOnly
                  ? "bg-gold text-[#4a3208] shadow-[0_1px_3px_rgb(74_50_8/0.25)]"
                  : "bg-gold-soft text-warn hover:bg-gold/25"
              }`}
            >
              ⭐ Premio listo ({readyCount})
            </button>
          </div>
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              setQ(qText.trim());
              setPageIndex(0);
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
                  setPageIndex(0);
                }}
              >
                Limpiar
              </Button>
            )}
          </form>
        </div>

        {visibleRows.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-semibold text-ink">
              {q
                ? `Sin resultados para «${q}»`
                : readyOnly
                  ? "Ningún cliente tiene premio listo todavía."
                  : "No hay tarjetas en esta página."}
            </p>
            <p className="mt-1 text-xs text-ink-faint">
              {q
                ? "Prueba con otro nombre o correo, o limpia la búsqueda."
                : readyOnly
                  ? "Cuando alguien reúna los sellos, aparecerá aquí con la insignia dorada."
                  : "Vuelve a la página anterior."}
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
                    <th className="w-16 px-4 py-3 font-semibold">Saldo</th>
                    <th className="w-28 px-4 py-3 font-semibold">Estado</th>
                    <th className="w-28 px-4 py-3 font-semibold">Alta</th>
                    {canManage && (
                      <th className="w-[152px] px-4 py-3 text-right font-semibold">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => (
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
                        <div className="flex flex-col items-start gap-1">
                          <div className="flex items-center gap-2">
                            <span className="tnum text-lg font-bold text-ink">{row.stamps}</span>
                            {/* «+1 sello» solo en modo sellos: en modo
                                puntos la venta se registra con importe
                                desde Operaciones (§7.6). */}
                            {canOperate &&
                              row.status === "active" &&
                              row.program_type !== "points" && (
                                <QuickStampButton
                                  busy={stampingId === row.id}
                                  name={row.member_name}
                                  onClick={() => void quickStamp(row)}
                                />
                              )}
                          </div>
                          <RewardHint row={row} />
                        </div>
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
                            onAdjust={() => setAdjustRow(row)}
                            onEdit={() => setEditRow(row)}
                          />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Fichas en pantallas medianas y móvil: nada se corta. */}
            <ul className="stagger grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:hidden">
              {visibleRows.map((row) => (
                <li key={row.id} className="min-w-0 rounded-2xl border border-line bg-surface p-4 transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-soft">
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
                        <div className="flex items-center gap-2">
                          <p className="tnum text-2xl font-bold text-ink">
                            <CountUp value={row.stamps} />{" "}
                            <span className="text-xs font-medium text-ink-faint">
                              {row.program_type === "points"
                                ? row.stamps === 1
                                  ? "punto"
                                  : "puntos"
                                : row.stamps === 1
                                  ? "sello"
                                  : "sellos"}
                            </span>
                          </p>
                          {canOperate &&
                            row.status === "active" &&
                            row.program_type !== "points" && (
                              <QuickStampButton
                                busy={stampingId === row.id}
                                name={row.member_name}
                                onClick={() => void quickStamp(row)}
                              />
                            )}
                        </div>
                        <p className="text-[11px] text-ink-faint">Alta: {formatDate(row.joined_at)}</p>
                      </div>
                      <RewardHint row={row} />
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
                            onAdjust={() => setAdjustRow(row)}
                            onEdit={() => setEditRow(row)}
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

        {/* Paginación del servidor: rango visible real y control estable
            aunque lleguen altas nuevas mientras se navega (§12.1). */}
        {hasPages && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
            <p className="text-xs text-ink-faint">
              Mostrando {pageStart + 1}–{pageEnd} de {totalCount} tarjetas
            </p>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={pageIndex === 0}
                onClick={() => setPageIndex((value) => Math.max(0, value - 1))}
              >
                Anterior
              </Button>
              <span className="tnum text-xs text-ink-faint" aria-live="polite">
                Página {pageIndex + 1} de {Math.max(1, Math.ceil(totalCount / PAGE_SIZE))}
              </span>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={pageEnd >= totalCount}
                onClick={() => setPageIndex((value) => value + 1)}
              >
                Siguiente
              </Button>
            </div>
          </div>
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

      {adjustRow && (
        <AdjustDialog
          row={adjustRow}
          busy={busy}
          onClose={() => setAdjustRow(null)}
          onConfirm={(delta, reason) => void applyAdjust(adjustRow, delta, reason)}
        />
      )}

      {editRow && (
        <EditDialog
          row={editRow}
          busy={busy}
          onClose={() => setEditRow(null)}
          onConfirm={(changes) => void applyEdit(editRow, changes)}
        />
      )}
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

/** «+1» de un toque: registra la visita desde la ficha. La operación es la
    misma que la consola (autorizada, idempotente y auditada); el backend
    confirma el saldo. Solo en tarjetas activas y con rol de operador. */
/** Insignia «Premio listo» / hint de sellos que faltan (mejora de compra #1/#3).

    El dato lo calcula el backend a partir del ledger y del catálogo activo:
    aquí solo se rotula. Cuando el cliente puede canjear YA, la insignia
    dorada invita al empleado a ofrecer el premio en el momento. */
function RewardHint({ row }: { row: Membership }) {
  if (row.status !== "active") return null;
  if (row.reward_ready) {
    return (
      <span className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-gold px-2.5 py-1 text-[11px] font-bold text-[#4a3208] shadow-[0_1px_3px_rgb(74_50_8/0.25)]">
        ⭐ Premio listo{row.next_reward_name ? ` · ${row.next_reward_name}` : ""}
      </span>
    );
  }
  if (row.next_reward_remaining !== null && row.next_reward_remaining !== undefined) {
    return (
      <span className="mt-1 text-[11px] font-medium text-ink-faint">
        {row.next_reward_name
          ? `${row.next_reward_name}: faltan ${unidades(row.program_type, row.next_reward_remaining)}`
          : `Faltan ${unidades(row.program_type, row.next_reward_remaining)}`}
      </span>
    );
  }
  return null;
}

function QuickStampButton({
  busy,
  name,
  onClick,
}: {
  busy: boolean;
  name: string | null | undefined;
  onClick: () => void;
}) {
  return (
    <Button
      size="sm"
      variant="secondary"
      loading={busy}
      onClick={onClick}
      aria-label={`Registrar visita de ${name || "el cliente"} (+1 sello)`}
      title="Registrar visita (+1 sello)"
      className="h-8 px-2.5"
    >
      +1
    </Button>
  );
}

function ActionsCell({
  row,
  onAction,
  onAdjust,
  onEdit,
}: {
  row: Membership;
  onAction: (action: LifecycleAction) => void;
  onAdjust: () => void;
  onEdit: () => void;
}) {
  const primary: { action: LifecycleAction; label: string } | null =
    row.status === "active"
      ? { action: "suspend", label: "Suspender" }
      : row.status === "suspended"
        ? { action: "reactivate", label: "Reactivar" }
        : null;
  const secondary: {
    action: LifecycleAction | "adjust";
    label: string;
    danger?: boolean;
  }[] = [];
  if (row.status === "active" || row.status === "suspended") {
    secondary.push({ action: "adjust", label: "Ajustar saldo" });
    secondary.push({ action: "revoke", label: "Revocar tarjeta", danger: true });
    secondary.push({ action: "anonymize", label: "Eliminar cliente", danger: true });
  } else if (row.status === "revoked" || row.status === "deletion_pending") {
    secondary.push({ action: "anonymize", label: "Eliminar cliente", danger: true });
  }

  if (!primary && secondary.length === 0) {
    // Cliente anonimizado: sus datos ya no existen y no se pueden editar.
    return <span className="text-xs text-ink-faint">—</span>;
  }

  return (
    <div className="flex items-center justify-end gap-1.5">
      {primary && (
        <Button size="sm" variant="secondary" onClick={onEdit}>
          Editar datos
        </Button>
      )}
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
            {secondary.map((item) => (
              <button
                key={item.action}
                type="button"
                onClick={(event) => {
                  const wrapper = event.currentTarget.closest("details");
                  wrapper?.removeAttribute("open");
                  if (item.action === "adjust") onAdjust();
                  else onAction(item.action);
                }}
                className={`block w-full rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors ${
                  item.danger
                    ? "text-danger hover:bg-danger-soft"
                    : "text-ink hover:bg-surface-2"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

/** Edición de datos mínimos del cliente (decisión de compra #9, §9.3):
    solo nombre y correo. Cambiar el correo lo deja sin verificar y el
    backend lo audita: el aviso aparece antes de guardar. */
function EditDialog({
  row,
  busy,
  onClose,
  onConfirm,
}: {
  row: Membership;
  busy: boolean;
  onClose: () => void;
  onConfirm: (changes: { display_name?: string; email?: string }) => void;
}) {
  const [name, setName] = useState(row.member_name ?? "");
  const [email, setEmail] = useState(row.member_email ?? "");
  const emailChanged = email.trim() !== (row.member_email ?? "");

  return (
    <Modal open onClose={onClose} title={`Editar cliente · ${row.member_name || "cliente"}`}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          const changes: { display_name?: string; email?: string } = {};
          if (name.trim() && name.trim() !== (row.member_name ?? "")) {
            changes.display_name = name.trim();
          }
          if (emailChanged) changes.email = email.trim();
          if (Object.keys(changes).length > 0) onConfirm(changes);
          else onClose();
        }}
      >
        <label className="block text-xs font-semibold text-ink-soft">
          Nombre del cliente
          <input
            required
            minLength={2}
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded-xl border border-line-strong bg-paper px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
          />
        </label>
        <label className="block text-xs font-semibold text-ink-soft">
          Correo
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-xl border border-line-strong bg-paper px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
          />
        </label>
        {emailChanged && (
          <p className="rounded-xl border border-warn/30 bg-gold-soft px-4 py-2.5 text-xs leading-relaxed text-warn">
            Al cambiar el correo, la nueva dirección queda sin verificar: habrá
            que verificarla de nuevo antes de usar funciones que la exijan.
          </p>
        )}
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy} disabled={busy}>
            Guardar cambios
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Ajuste de saldo con motivo (§7.3): la cantidad puede ser negativa
    (corregir un error) pero nunca deja la tarjeta en negativo; el backend
    lo rechaza y el motivo queda en el ledger y en la auditoría. */
function AdjustDialog({
  row,
  busy,
  onClose,
  onConfirm,
}: {
  row: Membership;
  busy: boolean;
  onClose: () => void;
  onConfirm: (delta: number, reason: string) => void;
}) {
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  const parsed = Number.parseInt(delta, 10);
  const valid =
    Number.isInteger(parsed) &&
    parsed !== 0 &&
    parsed >= -50 &&
    parsed <= 50 &&
    reason.trim().length >= 3;

  return (
    <Modal
      open
      onClose={onClose}
      title={`Ajustar saldo · ${row.member_name || "cliente"}`}
    >
      <p className="text-[13px] leading-relaxed">
        Cambia el saldo en <strong className="text-ink">±50 sellos</strong> como máximo. El
        motivo queda registrado con tu usuario en el historial: es la corrección trazable del
        §7.3, no un número editable a mano.
      </p>
      <form
        className="mt-4 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (valid) onConfirm(parsed, reason.trim());
        }}
      >
        <label className="block text-xs font-semibold text-ink-soft">
          Cantidad (negativa para restar)
          <input
            type="number"
            required
            step={1}
            min={-50}
            max={50}
            value={delta}
            onChange={(event) => setDelta(event.target.value)}
            placeholder="+3 o -2"
            className="mt-1 w-full rounded-xl border border-line-strong bg-paper px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
          />
          <span className="mt-1 block text-[11px] font-normal text-ink-faint">
            Saldo actual: {unidades(row.program_type, row.stamps)}
          </span>
        </label>
        <label className="block text-xs font-semibold text-ink-soft">
          Motivo (obligatorio)
          <textarea
            required
            rows={3}
            minLength={3}
            maxLength={255}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Ej.: Se registró una visita dos veces por error."
            className="mt-1 w-full resize-y rounded-xl border border-line-strong bg-paper px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
          />
        </label>
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy} disabled={!valid || busy}>
            Aplicar ajuste
          </Button>
        </div>
      </form>
    </Modal>
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
