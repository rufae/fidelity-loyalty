"use client";

/**
 * Equipo del comercio (§12.3, decisión de compra #2): el propietario crea a
 * sus empleados. El número depende del plan contratado (`max_staff`, el
 * propietario no cuenta) y la API rechaza con 409 `plan_limit_reached` un
 * mensaje accionable que se muestra tal cual.
 *
 * La contraseña la elige el dueño aquí (o la genera el botón) y se la pasa
 * al empleado por su canal: no hay correo de invitación todavía (§9.6).
 */
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  EmptyState,
  IconPlus,
  IconUser,
  LoadingState,
  Panel,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fidelity,
  type MerchantUser,
  type PlanUsage,
} from "@/lib/fidelity";
import { formatDate } from "@/lib/ui";

/** Medidor del plan, igual que en Tiendas (una sola forma de decirlo). */
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
          {used} de {max}
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

/** Propuesta de contraseña legible: sílabas + dígito + guion, ≥12 caracteres. */
function suggestPassword(): string {
  const syllables = ["ca", "fe", "la", "te", "ra", "mi", "lo", "ne", "sa", "tu"];
  const pick = () => syllables[Math.floor(Math.random() * syllables.length)];
  return `${pick()}${pick()}${pick()}${pick()}-${Math.floor(100 + Math.random() * 900)}`;
}

const ROLE_LABELS: Record<string, string> = {
  owner: "Propietario",
  admin: "Administración",
  staff: "Mostrador",
};

const ROLE_OPTIONS = [
  { value: "staff", label: "Mostrador", hint: "Registra sellos y canjes en el mostrador." },
  {
    value: "admin",
    label: "Administración",
    hint: "Todo el panel: programas, tiendas, clientes y equipo.",
  },
];

export function TeamView({ merchantId }: { merchantId: string }) {
  const [users, setUsers] = useState<MerchantUser[]>([]);
  const [plan, setPlan] = useState<PlanUsage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("staff");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [rows, usage] = await Promise.all([
          fidelity.users(merchantId),
          fidelity.planUsage(merchantId),
        ]);
        if (cancelled) return;
        setUsers(rows);
        setPlan(usage);
        setError(null);
      } catch {
        if (!cancelled) setError("No se pudo cargar el equipo.");
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
    const trimmedEmail = email.trim();
    if (trimmedEmail.length < 5 || password.length < 12 || displayName.trim().length < 2) {
      return;
    }
    setError(null);
    setNotice(null);
    setCreating(true);
    try {
      await fidelity.createUser(merchantId, {
        email: trimmedEmail,
        password,
        display_name: displayName.trim(),
        role,
      });
      setEmail("");
      setDisplayName("");
      setPassword("");
      setNotice(`«${displayName.trim()}» ya puede entrar con el correo y la contraseña que le diste.`);
      load();
    } catch (err) {
      // Los 409 del plan llegan con un mensaje accionable: se muestra tal cual.
      setError(
        err instanceof ApiError ? err.message : "No se pudo dar de alta al empleado.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(user: MerchantUser) {
    setError(null);
    setNotice(null);
    try {
      await fidelity.setUserStatus(
        merchantId,
        user.user_id,
        user.status === "active" ? "disabled" : "active",
      );
      setNotice(
        user.status === "active"
          ? `Acceso de «${user.display_name}» desactivado.`
          : `Acceso de «${user.display_name}» reactivado.`,
      );
      load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo cambiar el estado del acceso.",
      );
    }
  }

  if (loading) return <LoadingState label="Cargando equipo…" />;

  const owner = users.find((u) => u.role === "owner");
  const staffUsers = users.filter((u) => u.role !== "owner");
  const activeStaff = staffUsers.filter((u) => u.status === "active").length;
  const atLimit = plan !== null && activeStaff >= plan.max_staff;

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
                El propietario no cuenta en el límite: son los empleados activos.
              </p>
            </div>
          </div>
          <div className="mt-5 max-w-sm">
            <UsageMeter label="Empleados" used={activeStaff} max={plan.max_staff} />
          </div>
          {atLimit && (
            <p className="mt-4 rounded-xl border border-warn/30 bg-gold-soft px-4 py-2.5 text-xs leading-relaxed text-warn">
              Has llegado al límite de empleados de tu plan. Escríbenos por
              Soporte y actualizamos tu plan: se conserva todo tal cual está.
            </p>
          )}
        </Panel>
      )}

      {!atLimit && (
        <Panel className="animate-in">
          <h2 className="text-sm font-semibold text-ink">Nuevo empleado</h2>
          <form
            className="mt-3 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void create();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-xs font-semibold text-ink-soft">
                Correo del empleado
                <input
                  type="email"
                  required
                  autoComplete="off"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="empleado@tunegocio.com"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
              <label className="block text-xs font-semibold text-ink-soft">
                Nombre con el que lo saluda el panel
                <input
                  required
                  minLength={2}
                  maxLength={120}
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Marta"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <label className="block text-xs font-semibold text-ink-soft">
                Contraseña de acceso (mínimo 12 caracteres)
                <input
                  required
                  minLength={12}
                  maxLength={256}
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 font-mono text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
              <label className="block text-xs font-semibold text-ink-soft">
                Permiso
                <select
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink transition-[border-color,box-shadow] hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setPassword(suggestPassword())}
              >
                Generar
              </Button>
            </div>
            <p className="text-xs leading-relaxed text-ink-faint">
              {ROLE_OPTIONS.find((option) => option.value === role)?.hint} Pásale
              la contraseña a tu empleado por un canal seguro (en persona o de
              tu confianza); podrá cambiarla al entrar.
            </p>
            <Button type="submit" disabled={creating || password.length < 12}>
              <span className="inline-flex items-center gap-1.5">
                <IconPlus size={16} />
                {creating ? "Creando…" : "Dar de alta empleado"}
              </span>
            </Button>
          </form>
        </Panel>
      )}

      {staffUsers.length === 0 && !owner ? (
        <EmptyState
          illustration="card"
          title="Sin cuentas todavía"
          description="Algo inesperado: tu cuenta debería aparecer aquí. Avísanos por Soporte."
        />
      ) : (
        <Panel padded={false}>
          <ul>
            {owner && (
              <li className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
                <span className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
                    <IconUser size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-ink">
                      {owner.display_name}
                    </span>
                    <span className="block text-xs text-ink-faint">{owner.email}</span>
                  </span>
                </span>
                <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-bold text-brand">
                  Propietario
                </span>
              </li>
            )}
            {staffUsers.map((user) => (
              <li
                key={user.id}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4 last:border-b-0"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-ink-soft">
                    <IconUser size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-ink">
                      {user.display_name}
                    </span>
                    <span className="block text-xs text-ink-faint">
                      {user.email} · desde {formatDate(user.created_at)}
                    </span>
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="rounded-full bg-surface-2 px-2.5 py-1 text-[11px] font-bold text-ink-soft">
                    {ROLE_LABELS[user.role] ?? user.role}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
                      user.status === "active"
                        ? "bg-ok-soft text-ok"
                        : "bg-surface-2 text-ink-faint"
                    }`}
                  >
                    {user.status === "active" ? "Activo" : "Sin acceso"}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void toggleStatus(user)}
                  >
                    {user.status === "active" ? "Desactivar" : "Reactivar"}
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
