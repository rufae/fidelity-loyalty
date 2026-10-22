"use client";

import { useCallback, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  EmptyState,
  IconCheck,
  IconChevronDown,
  IconGift,
  IconScan,
  IconSearch,
  Input,
  Panel,
  SectionTitle,
  StampRow,
} from "@/components/ui";
import { QrScanner } from "@/components/qr-scanner";
import { ApiError } from "@/lib/api";
import {
  extractCardCode,
  fidelity,
  newIdempotencyKey,
  type Membership,
  type ProgramDetail,
  type TransactionRow,
} from "@/lib/fidelity";
import { formatDateTime, sellos, stampSlots } from "@/lib/ui";

const TYPE_LABELS: Record<string, string> = {
  earn: "Acumulación",
  redeem: "Canje",
  adjustment: "Ajuste",
  reversal: "Reversión",
  expiry: "Expiración",
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

function initials(name: string | null | undefined): string {
  if (!name?.trim()) return "C";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * Vista del personal: identifica la tarjeta por su código (pegado o escaneado
 * con cualquier lector de cámara), muestra saldo y permite acumular o canjear.
 *
 * La consola prioriza el gesto más frecuente —escanear y sumar— y deja la
 * búsqueda por nombre en un segundo plano accesible. Para clientes sin móvil a
 * mano, esa búsqueda **queda registrada en la auditoría** del comercio.
 */
export function OperationsView({ merchantId }: { merchantId: string }) {
  const [token, setToken] = useState("");
  const [membership, setMembership] = useState<Membership | null>(null);
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [history, setHistory] = useState<TransactionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [networkWarning, setNetworkWarning] = useState<string | null>(null);
  const [clientQuery, setClientQuery] = useState("");
  const [clientResults, setClientResults] = useState<Membership[] | null>(null);
  const [searchingClient, setSearchingClient] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  /** Tarjetas (programas) del cliente identificado: elige la promoción. */
  const [memberCards, setMemberCards] = useState<Membership[]>([]);
  /** Programa preseleccionado por la etiqueta de mostrador (?program=). */
  const [preferredProgramId] = useState<string | null>(() =>
    typeof window === "undefined"
      ? null
      : new URLSearchParams(window.location.search).get("program"),
  );
  const [programNotice, setProgramNotice] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadProgram = useCallback(
    async (programId: string) => {
      try {
        setProgram(await fidelity.program(merchantId, programId));
      } catch {
        setProgram(null);
      }
    },
    [merchantId],
  );

  const refreshHistory = useCallback(
    async (membershipId: string) => {
      try {
        setHistory(await fidelity.transactions(merchantId, membershipId));
      } catch {
        setHistory([]);
      }
    },
    [merchantId],
  );

  function clearFeedback() {
    setError(null);
    setNotice(null);
    setNetworkWarning(null);
  }

  async function lookup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await search(token);
  }

  /** Búsqueda por código o URL de tarjeta; también la usa el escáner QR. */
  async function search(code: string) {
    clearFeedback();
    setMembership(null);
    setProgram(null);
    setHistory([]);
    setMemberCards([]);
    setProgramNotice(null);
    setBusy(true);
    try {
      // Se acepta el código o la URL de la tarjeta (lo que escupe el QR).
      const found = await fidelity.lookup(merchantId, extractCardCode(code));
      // Todas las tarjetas del cliente: si está en varias promociones, el
      // mostrador elige la correcta sin escanear otro QR.
      let cards: Membership[] = [found];
      try {
        cards = await fidelity.memberCards(merchantId, found.member_id);
      } catch {
        cards = [found];
      }
      setMemberCards(cards);
      // La etiqueta de mostrador preselecciona su programa (ADR-0008).
      const preferred = preferredProgramId
        ? cards.find((card) => card.program_id === preferredProgramId)
        : undefined;
      if (preferredProgramId && !preferred) {
        setProgramNotice(
          "Este cliente no tiene tarjeta en el programa de la etiqueta que has tocado. Dale de alta con la etiqueta de inscripción o elige otro programa.",
        );
      }
      const active = preferred ?? found;
      setMembership(active);
      await loadProgram(active.program_id);
      await refreshHistory(active.id);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "No se ha encontrado ninguna tarjeta con ese código en este comercio."
          : "No se pudo consultar la tarjeta.",
      );
    } finally {
      setBusy(false);
    }
  }

  /** Cambia la promoción activa cuando el cliente está en varias. */
  async function selectProgram(card: Membership) {
    if (membership !== null && card.id === membership.id) return;
    clearFeedback();
    setProgramNotice(null);
    setMembership(card);
    await loadProgram(card.program_id);
    await refreshHistory(card.id);
  }

  /** Búsqueda por nombre/correo para clientes sin móvil a mano. */
  async function searchClient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = clientQuery.trim();
    if (q.length < 2) return;
    setSearchingClient(true);
    setClientError(null);
    try {
      setClientResults(await fidelity.searchCards(merchantId, q));
    } catch {
      setClientError("No se pudo buscar. Comprueba la conexión e inténtalo de nuevo.");
    } finally {
      setSearchingClient(false);
    }
  }

  function selectCard(row: Membership) {
    setToken(row.public_token);
    setClientResults(null);
    setClientQuery("");
    void search(row.public_token);
  }

  async function earn() {
    if (!membership) return;
    setBusy(true);
    clearFeedback();
    try {
      const result = await fidelity.earn(merchantId, membership.id, newIdempotencyKey("earn"));
      setNotice(
        result.already_applied
          ? "Esta operación ya estaba registrada (no se ha duplicado)."
          : `Sello añadido: la tarjeta tiene ${sellos(result.stamps)}.`,
      );
      setMembership({ ...membership, stamps: result.stamps });
      // El selector de programas refleja el saldo al día.
      setMemberCards((cards) =>
        cards.map((card) =>
          card.id === membership.id ? { ...card, stamps: result.stamps } : card,
        ),
      );
      await refreshHistory(membership.id);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo acumular.");
        setNetworkWarning(
          "Antes de repetir la operación, comprueba el saldo de la tarjeta: si la petición llegó al servidor, el sello ya estará registrado.",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function redeem(rewardId: string) {
    if (!membership) return;
    setBusy(true);
    clearFeedback();
    try {
      const result = await fidelity.redeem(
        merchantId,
        membership.id,
        rewardId,
        newIdempotencyKey("redeem"),
      );
      setNotice(
        `Recompensa canjeada: ${result.stamps === 1 ? "queda" : "quedan"} ${sellos(result.stamps)}.`,
      );
      setMembership({ ...membership, stamps: result.stamps });
      // El selector de programas refleja el saldo al día.
      setMemberCards((cards) =>
        cards.map((card) =>
          card.id === membership.id ? { ...card, stamps: result.stamps } : card,
        ),
      );
      await refreshHistory(membership.id);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo canjear.");
        setNetworkWarning(
          "Antes de repetir la operación, comprueba el saldo: el canje podría haberse registrado ya en el servidor.",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  const nextTarget = program?.rewards
    .map((reward) => reward.stamps_required)
    .filter((required) => membership && required > membership.stamps)
    .sort((a, b) => a - b)[0];
  const progress = membership
    ? stampSlots(membership.stamps, nextTarget ?? null)
    : { slots: 0, filled: 0 };
  const active = membership?.status === "active";

  return (
    <div className="space-y-5">
      {/* Consola de identificación: una sola entrada, botones alineados. */}
      <Panel className="animate-in">
        <SectionTitle
          title="Identifica la tarjeta"
          description="Escanea el QR del cliente o pega su código. También se acepta la URL completa que muestra el QR."
          icon={<IconScan size={18} />}
        />
        <form onSubmit={lookup} className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1 space-y-1.5">
              <label htmlFor="card-code" className="text-sm font-semibold text-ink">
                Código de la tarjeta
              </label>
              <Input
                id="card-code"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Escanea el QR o pega el código"
                className="h-12 font-mono text-[13px]"
              />
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <Button
                type="submit"
                size="lg"
                loading={busy}
                icon={<IconSearch size={18} />}
                className="flex-1 sm:flex-none"
              >
                Buscar tarjeta
              </Button>
              <QrScanner
                onScan={(text) => {
                  setToken(text);
                  void search(text);
                }}
              />
            </div>
          </div>
          <p className="text-xs leading-relaxed text-ink-faint">
            Puedes escribir el código, pegarlo o pulsar «Escanear QR» con la cámara. La cámara solo
            se activa al pulsar el botón.
          </p>
        </form>
      </Panel>

      {/* Búsqueda por nombre/correo: alternativa sin QR, en segundo plano. */}
      <details className="group rounded-2xl border border-line bg-paper shadow-soft">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
          <span className="flex min-w-0 items-center gap-2.5">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-surface text-ink-soft">
              <IconSearch size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-ink">
                ¿No tiene el móvil a mano?
              </span>
              <span className="block text-xs text-ink-faint">
                Busca al cliente por nombre o correo
              </span>
            </span>
          </span>
          <IconChevronDown
            size={18}
            className="shrink-0 text-ink-faint transition-transform duration-200 group-open:rotate-180"
          />
        </summary>
        <div className="border-t border-line px-5 py-4">
          <form onSubmit={searchClient} className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1 space-y-1.5">
                <label htmlFor="client-query" className="text-sm font-semibold text-ink">
                  Nombre o correo del cliente
                </label>
                <Input
                  id="client-query"
                  type="search"
                  value={clientQuery}
                  onChange={(e) => setClientQuery(e.target.value)}
                  placeholder="Ana / ana@ejemplo.com"
                  className="h-12"
                />
              </div>
              <Button
                type="submit"
                size="lg"
                loading={searchingClient}
                disabled={clientQuery.trim().length < 2}
                icon={<IconSearch size={18} />}
              >
                Buscar cliente
              </Button>
            </div>
            <p className="text-xs leading-relaxed text-ink-faint">
              Las búsquedas por nombre o correo quedan registradas en la auditoría del comercio.
            </p>
          </form>

          {clientError && (
            <div className="mt-3">
              <Alert tone="danger" title="Búsqueda no disponible">
                {clientError}
              </Alert>
            </div>
          )}
          {clientResults && clientResults.length === 0 && !clientError && (
            <p className="mt-3 rounded-xl bg-surface p-3 text-sm text-ink-faint">
              Sin resultados para «{clientQuery.trim()}».
            </p>
          )}
          {clientResults && clientResults.length > 0 && (
            <ul className="mt-3 space-y-2">
              {clientResults.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-3"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
                      {initials(row.member_name)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink">
                        {row.member_name || "Sin nombre"}
                      </p>
                      <p className="truncate text-xs text-ink-faint">
                        {row.program_name ? `«${row.program_name}» · ` : ""}
                        {row.member_email || "sin correo"} · {sellos(row.stamps)} ·{" "}
                        {STATUS_LABELS[row.status] ?? row.status}
                      </p>
                    </div>
                  </div>
                  <Button type="button" size="sm" onClick={() => selectCard(row)}>
                    Usar esta tarjeta
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>

      {error && (
        <Alert tone="danger" title="Operación no completada">
          <p>{error}</p>
          {networkWarning && <p className="mt-1 text-xs">{networkWarning}</p>}
        </Alert>
      )}

      {/* Confirmación del servidor: el recibo de la operación. */}
      {notice && (
        <div
          role="status"
          className="animate-in flex items-start gap-3 rounded-2xl border-2 border-ok/25 bg-ok-soft p-4"
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-ok text-white">
            <IconCheck size={22} />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ok">
              Operación registrada
            </p>
            <p className="mt-0.5 text-[15px] font-bold leading-snug text-ink">{notice}</p>
          </div>
        </div>
      )}

      {!membership && !error && (
        <EmptyState
          illustration="scan"
          title="Identifica una tarjeta para empezar"
          description="Introduce o escanea el código de la tarjeta del cliente. Verás sus sellos y las recompensas que puede canjear."
          action={
            <p className="text-xs text-ink-faint">
              Consejo: el QR de la tarjeta se encuentra en la pantalla del cliente.
            </p>
          }
        />
      )}

      {membership && (
        <Panel padded={false} className="animate-in overflow-hidden">
          {/* Identidad del cliente y estado de la tarjeta. */}
          <div className="border-b border-line bg-paper px-5 py-5 sm:px-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex min-w-0 items-start gap-3">
                <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-sm font-bold text-white shadow-soft">
                  {initials(membership.member_name)}
                </span>
                <div className="min-w-0">
                  {(membership.member_name || membership.member_email) && (
                    <p className="truncate text-sm font-semibold text-ink">
                      {membership.member_name || "Cliente"}
                      {membership.member_email && (
                        <span className="ml-2 text-xs font-normal text-ink-faint">
                          {membership.member_email}
                        </span>
                      )}
                    </p>
                  )}
                  <h2 className="text-xl font-bold tracking-tight text-ink">
                    {program?.name ?? "Programa"}
                  </h2>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">
                      Estado de la tarjeta:{" "}
                      {STATUS_LABELS[membership.status] ?? membership.status}
                    </Badge>
                    <Badge tone="brand">
                      <IconGift size={13} />
                      {program?.rewards.length ?? 0} recompensas
                    </Badge>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="tnum text-[52px] font-bold leading-none tracking-[-0.04em] text-brand">
                  {membership.stamps}
                </p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-[0.1em] text-ink-faint">
                  sellos
                </p>
              </div>
            </div>

            {programNotice && (
              <div className="mt-4">
                <Alert tone="warn" title="Programa de la etiqueta">
                  {programNotice}
                </Alert>
              </div>
            )}

            {/* Selector de promoción (ADR-0008). */}
            {memberCards.length > 1 && (
              <div className="mt-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                  Programas del cliente · elige la promoción
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {memberCards.map((card) => {
                    const current = card.id === membership.id;
                    return (
                      <button
                        key={card.id}
                        type="button"
                        aria-pressed={current}
                        onClick={() => void selectProgram(card)}
                        disabled={current}
                        className={`min-h-11 rounded-xl border px-4 text-sm font-semibold transition-colors ${
                          current
                            ? "border-brand bg-brand-soft text-brand"
                            : "border-line bg-surface text-ink-soft hover:border-brand/50"
                        }`}
                      >
                        {card.program_name ?? "Programa"} · {sellos(card.stamps)}
                        {current && " ✓"}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Progreso visual derivado de datos reales. */}
            <div className="mt-4 rounded-2xl border border-line bg-surface p-4">
              <StampRow slots={progress.slots} filled={progress.filled} />
              <p className="mt-2 text-xs text-ink-soft">
                {nextTarget
                  ? `Faltan ${sellos(nextTarget - membership.stamps)} para la próxima recompensa.`
                  : "Todos los sellos acumulados están reflejados aquí."}
              </p>
            </div>
          </div>

          <div className="px-5 py-5 sm:px-6">
            {/* Tarjeta no activa: se dice y se bloquean las acciones. */}
            {!active && (
              <p className="mb-4 rounded-xl border border-warn/30 bg-gold-soft px-4 py-3 text-sm font-semibold text-warn">
                Esta tarjeta está {STATUS_LABELS[membership.status] ?? membership.status} y no puede
                sumar sellos ni canjear recompensas.
              </p>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => void earn()}
                disabled={busy || !active}
                className="flex min-h-16 items-center justify-center gap-2.5 rounded-2xl bg-brand text-lg font-bold text-white shadow-[0_10px_24px_-12px_rgb(91_72_214/0.8)] transition-colors hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60 sm:col-span-2"
              >
                <IconCheck size={22} />
                +1 sello (visita)
              </button>

              {program?.rewards.map((reward) => {
                const enough = membership.stamps >= reward.stamps_required;
                return (
                  <button
                    key={reward.id}
                    type="button"
                    onClick={() => void redeem(reward.id)}
                    disabled={busy || !enough || !active}
                    title={enough ? `Canjear por ${reward.stamps_required} sellos` : "Sellos insuficientes"}
                    className={`flex min-h-16 flex-col items-center justify-center gap-0.5 rounded-2xl border px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${
                      enough
                        ? "border-gold/40 bg-gold-soft text-warn hover:bg-gold-soft/70"
                        : "border-line bg-surface text-ink-faint opacity-70"
                    }`}
                  >
                    <span>
                      Canjear: {reward.name} ({reward.stamps_required})
                    </span>
                    {!enough && (
                      <span className="text-[11px] font-medium">
                        Sellos insuficientes · lleva {membership.stamps} de{" "}
                        {reward.stamps_required}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Historial inmutable: línea de tiempo, no tabla apretada. */}
            {history.length > 0 && (
              <div className="mt-6">
                <SectionTitle title="Historial de movimientos" />
                <ol className="space-y-0">
                  {history.map((row, index) => (
                    <li key={row.id} className="relative flex gap-3 pb-3 last:pb-0">
                      {index < history.length - 1 && (
                        <span
                          aria-hidden="true"
                          className="absolute left-[7px] top-5 h-full w-px bg-line"
                        />
                      )}
                      <span
                        aria-hidden="true"
                        className={`relative mt-1.5 size-[15px] shrink-0 rounded-full border-2 bg-surface ${
                          row.quantity > 0 ? "border-ok" : "border-warn"
                        }`}
                      />
                      <div className="flex min-w-0 flex-1 items-baseline justify-between gap-3 rounded-lg px-1 py-0.5">
                        <span className="text-sm text-ink">
                          {TYPE_LABELS[row.transaction_type] ?? row.transaction_type}
                        </span>
                        <span className="flex items-baseline gap-3">
                          <span
                            className={`tnum text-sm font-bold ${
                              row.quantity > 0 ? "text-ok" : "text-warn"
                            }`}
                          >
                            {row.quantity > 0 ? `+${row.quantity}` : row.quantity}
                          </span>
                          <span className="text-[11px] text-ink-faint">
                            {formatDateTime(row.created_at)}
                          </span>
                        </span>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
