"use client";

/**
 * Tiendas del comercio (§11.3) y plan contratado (tasks.md §5-§6).
 *
 * El plan manda: la API rechaza con 409 `plan_limit_reached` al superar el
 * límite de tiendas y la interfaz muestra ese mensaje tal cual es accionable.
 * Las cifras salen siempre del backend; nunca se calculan en local.
 */
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  EmptyState,
  IconPlus,
  IconStore,
  LoadingState,
  Panel,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fidelity,
  type MerchantLocation,
  type PlanUsage,
} from "@/lib/fidelity";
import { formatDate, formatNumber } from "@/lib/ui";

/** Medidor de uso del plan: barra fina con la cifra real al lado. */
function UsageMeter({ label, used, max }: { label: string; used: number; max: number }) {
  const pct = Math.min(100, max > 0 ? Math.round((used / max) * 100) : 0);
  const full = used >= max;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
          {label}
        </p>
        <p className={`tnum text-sm font-bold ${full ? "text-warn" : "text-ink"}`}>
          {formatNumber(used)} de {formatNumber(max)}
        </p>
      </div>
      <div
        className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-3"
        role="img"
        aria-label={`${label}: ${used} de ${max}`}
      >
        <div
          className={`h-full rounded-full ${full ? "bg-warn" : "bg-brand"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function StoresView({ merchantId }: { merchantId: string }) {
  const [locations, setLocations] = useState<MerchantLocation[]>([]);
  const [plan, setPlan] = useState<PlanUsage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [rows, usage] = await Promise.all([
          fidelity.locations(merchantId),
          fidelity.planUsage(merchantId),
        ]);
        if (cancelled) return;
        setLocations(rows);
        setPlan(usage);
        setError(null);
      } catch {
        if (!cancelled) setError("No se pudieron cargar las tiendas.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  async function create() {
    const trimmed = name.trim();
    if (trimmed.length < 2) return;
    setError(null);
    setNotice(null);
    setCreating(true);
    try {
      await fidelity.createLocation(merchantId, { name: trimmed });
      setName("");
      setNotice(`Tienda «${trimmed}» dada de alta.`);
      load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo crear la tienda.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(location: MerchantLocation) {
    setError(null);
    setNotice(null);
    try {
      await fidelity.setLocationStatus(
        merchantId,
        location.id,
        location.status === "active" ? "inactive" : "active",
      );
      setNotice(
        location.status === "active"
          ? `Tienda «${location.name}» desactivada.`
          : `Tienda «${location.name}» reactivada.`,
      );
      load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo cambiar el estado de la tienda.",
      );
    }
  }

  if (loading) return <LoadingState label="Cargando tiendas…" />;

  const activeLocations = locations.filter((l) => l.status === "active");
  const atLimit = plan !== null && activeLocations.length >= plan.max_locations;

  return (
    <div className="space-y-5">
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

      {plan && (
        <Panel className="animate-in">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-ink">
                Plan {plan.plan_name}
              </h2>
              <p className="mt-1 text-sm text-ink-soft">
                Los límites del plan protegen el servicio; los clientes nunca
                tienen límite.
              </p>
            </div>
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <UsageMeter
              label="Tiendas"
              used={plan.locations}
              max={plan.max_locations}
            />
            <UsageMeter
              label="Programas en vivo"
              used={plan.active_programs}
              max={plan.max_active_programs}
            />
          </div>
          {(plan.locations >= plan.max_locations ||
            plan.active_programs >= plan.max_active_programs) && (
            <p className="mt-4 rounded-xl border border-warn/30 bg-gold-soft px-4 py-2.5 text-xs leading-relaxed text-warn">
              Has llegado al límite de tu plan. Escríbenos por Soporte y
              actualizamos tu plan: se conserva todo tal cual está.
            </p>
          )}
        </Panel>
      )}

      {atLimit ? null : (
        <Panel className="animate-in">
          <h2 className="text-sm font-semibold text-ink">Nueva tienda</h2>
          <form
            className="mt-3 flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void create();
            }}
          >
            <label className="min-w-56 flex-1 text-xs font-semibold text-ink-soft">
              Nombre de la tienda
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Sede Centro"
                maxLength={120}
                className="mt-1 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
              />
            </label>
            <Button type="submit" disabled={creating || name.trim().length < 2}>
              <span className="inline-flex items-center gap-1.5">
                <IconPlus size={16} />
                {creating ? "Creando…" : "Añadir tienda"}
              </span>
            </Button>
          </form>
        </Panel>
      )}

      {locations.length === 0 ? (
        <EmptyState
          illustration="card"
          title="Sin tiendas dadas de alta"
          description="Tu comercio opera como un solo local, sin cambiar nada. Si abres otro punto, dalo de alta aquí y lo gestionas desde este mismo panel."
        />
      ) : (
        <Panel padded={false}>
          <ul>
            {locations.map((location) => (
              <li
                key={location.id}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4 last:border-b-0"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-ink-soft">
                    <IconStore size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-ink">
                      {location.name}
                    </span>
                    <span className="block text-xs text-ink-faint">
                      Alta: {formatDate(location.created_at)}
                    </span>
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
                      location.status === "active"
                        ? "bg-ok-soft text-ok"
                        : "bg-surface-2 text-ink-faint"
                    }`}
                  >
                    {location.status === "active" ? "Activa" : "Inactiva"}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void toggleStatus(location)}
                  >
                    {location.status === "active" ? "Desactivar" : "Reactivar"}
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
