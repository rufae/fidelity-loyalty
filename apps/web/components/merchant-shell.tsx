"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import {
  BrandLogo,
  Button,
  IconClose,
  IconContactless,
  IconGrid,
  IconGift,
  IconMail,
  IconMenu,
  IconScan,
  IconStar,
  IconUsers,
} from "@/components/ui";
import { MerchantProvider } from "@/components/merchant-context";
import { ApiError, apiFetch } from "@/lib/api";
import {
  isPlatformAdmin,
  canManageMerchant,
  canOperateMerchant,
  type MerchantRole,
  type SessionPayload,
} from "@/lib/session";

/** Rol de la sesión en ESTE comercio, en lenguaje de negocio (no técnico). */
const ROLE_LABELS: Record<MerchantRole, string> = {
  owner: "Propietario",
  admin: "Administración",
  staff: "Personal de mostrador",
  viewer: "Solo lectura",
};

function rolLabel(role: MerchantRole | null): string {
  if (role && role in ROLE_LABELS) return ROLE_LABELS[role];
  return "Administración de plataforma";
}

/** Secciones completas: administración del comercio o plataforma. */
const MANAGER_GROUPS = [
  {
    label: "Tu día a día",
    items: [
      { href: "", label: "Resumen", icon: IconGrid },
      { href: "/operations", label: "Operaciones", icon: IconScan },
    ],
  },
  {
    label: "Tu programa",
    items: [
      { href: "/programs", label: "Programas", icon: IconGift },
      { href: "/members", label: "Clientes", icon: IconUsers },
    ],
  },
  {
    label: "En tu local",
    items: [
      { href: "/nfc", label: "NFC y QR", icon: IconContactless },
      { href: "/reviews", label: "Reseñas Google", icon: IconStar },
    ],
  },
  {
    label: "Ayuda",
    items: [{ href: "/support", label: "Soporte", icon: IconMail }],
  },
] as const;

/** El personal de mostrador solo opera tarjetas: ni configuración ni clientes. */
const STAFF_GROUPS = [
  {
    label: "Tu puesto",
    items: [{ href: "/operations", label: "Operaciones", icon: IconScan }],
  },
  {
    label: "Ayuda",
    items: [{ href: "/support", label: "Soporte", icon: IconMail }],
  },
] as const;

/** Qué necesita cada pantalla: la interfaz nunca muestra lo que la API niega. */
export type MerchantAccess = "manage" | "operate";

interface MerchantListItem {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
}

/** Inicial del comercio para el avatar: sin inventar logotipos. */
function mark(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "·";
}

/**
 * Envoltorio del panel del comercio: comprueba la sesión y el acceso a **este**
 * comercio y dibuja la navegación (sidebar en escritorio, cajón en móvil).
 *
 * La navegación es clara y cálida a propósito: el personal de un comercio no
 * debería sentir que entra en una herramienta de ingeniería. El permiso real lo
 * decide el backend en cada petición; aquí solo se evita mostrar una interfaz
 * que devolvería 404.
 */
export function MerchantShell({
  merchantId,
  title,
  requires,
  children,
}: {
  merchantId: string;
  title: string;
  /** Restringe la pantalla al rol correspondiente (el backend ya la protege). */
  requires?: MerchantAccess;
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [merchantName, setMerchantName] = useState<string>("");
  const [role, setRole] = useState<MerchantRole | null>(null);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  /** El esqueleto no puede ser un pringue eterno: si la sesión no carga, se lo explicamos. */
  const [sessionError, setSessionError] = useState<string | null>(null);
  /** Reintento del usuario: cada intento relanza la carga de sesión. */
  const [attempt, setAttempt] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  /** Cierra la sesión del panel (logout real en backend) y vuelve al acceso. */
  async function logout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Aunque falle la llamada, la sesión local sale igualmente: el backend
      // invalida la cookie cuando responda.
    }
    router.replace("/login");
  }

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      try {
        const payload = await apiFetch<SessionPayload>("/api/v1/auth/me");
        const visible =
          isPlatformAdmin(payload.user) ||
          payload.merchants.some((m) => m.merchant_id === merchantId);
        if (cancelled) return;
        setSessionError(null);
        setSession(payload);
        setAllowed(visible);
        if (!visible) {
          router.push("/merchants");
          return;
        }
        const membership = payload.merchants.find((m) => m.merchant_id === merchantId);
        setRole(membership?.role ?? null);
        if (membership) {
          setMerchantName(membership.merchant_name);
        } else {
          // Administración de plataforma sin membresía: resuelve el nombre real.
          try {
            const rows = await apiFetch<MerchantListItem[]>("/api/v1/merchants");
            if (!cancelled) {
              setMerchantName(rows.find((row) => row.id === merchantId)?.name ?? "Comercio");
            }
          } catch {
            if (!cancelled) setMerchantName("Comercio");
          }
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
          return;
        }
        // Red caída o error del servidor: mensaje claro + reintentar aquí
        // mismo, nunca un esqueleto vacío sin salida.
        setSessionError(
          err instanceof ApiError
            ? err.message
            : "No se pudo comprobar tu sesión. Inténtalo de nuevo.",
        );
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [merchantId, router, attempt]);

  // Cierra el cajón al cambiar de pantalla (ajuste de estado durante el render).
  const [prevPath, setPrevPath] = useState(pathname);
  if (prevPath !== pathname) {
    setPrevPath(pathname);
    setMenuOpen(false);
  }

  const root = `/merchants/${merchantId}`;
  const platformAdmin = session ? isPlatformAdmin(session.user) : false;

  // Guardia de interfaz: cada pantalla declara qué rol necesita; quien no lo
  // tiene es enviado a su pantalla útil (el backend sigue siendo el control).
  useEffect(() => {
    if (allowed !== true || !requires || platformAdmin) return;
    const allowedHere =
      requires === "manage"
        ? role !== null && canManageMerchant(role)
        : role !== null && canOperateMerchant(role);
    if (!allowedHere) {
      const target = role !== null && canOperateMerchant(role) ? `${root}/operations` : root;
      router.replace(target);
    }
  }, [allowed, requires, platformAdmin, role, router, root]);

  if (sessionError && allowed === null) {
    return <ShellSkeleton error={sessionError} onRetry={() => setAttempt((n) => n + 1)} />;
  }
  if (allowed !== true) {
    return <ShellSkeleton />;
  }

  const groups =
    platformAdmin || (role !== null && canManageMerchant(role))
      ? MANAGER_GROUPS
      : role !== null && canOperateMerchant(role)
        ? STAFF_GROUPS
        : [];

  const navItems = (onNavigate?: () => void) => (
    <nav className="flex flex-col gap-5" aria-label="Secciones del comercio">
      {groups.map((group) => (
        <div key={group.label} className="space-y-1">
          <p className="px-3 text-[10px] font-bold uppercase tracking-[0.15em] text-ink-faint">
            {group.label}
          </p>
          {group.items.map((item) => {
            const href = `${root}${item.href}`;
            const active = pathname === href || (item.href === "" && pathname === root);
            const Icon = item.icon;
            return (
              <Link
                key={href}
                href={href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                  active
                    ? "bg-brand-soft text-brand"
                    : "text-ink-soft hover:bg-surface hover:text-ink"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`absolute inset-y-2 left-0 w-[3px] rounded-full transition-opacity ${
                    active ? "bg-brand opacity-100" : "opacity-0 group-hover:opacity-40"
                  }`}
                />
                <Icon size={19} className={active ? "text-brand" : "text-ink-faint group-hover:text-ink-soft"} />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );

  const userFooter = (
    <div className="mt-auto space-y-3 border-t border-line pt-4">
      <div className="flex items-center gap-2.5">
        {/* Inicial del correo: avatar discreto sin datos personales nuevos. */}
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-sm font-bold text-white shadow-soft">
          {(session?.user.email ?? "?").charAt(0).toUpperCase()}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-[12px] font-semibold text-ink">
            {session?.user.email}
          </span>
          <span className="block text-[11px] text-ink-faint">{rolLabel(role)}</span>
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Link
          href="/merchants"
          className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[11px] font-semibold text-ink-soft transition-colors hover:border-brand/40 hover:text-brand"
        >
          Cambiar comercio
        </Link>
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded-lg px-2.5 py-1.5 text-[11px] font-semibold text-ink-faint transition-colors hover:bg-surface hover:text-ink"
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  );

  return (
    <MerchantProvider
      value={{
        merchantId,
        merchantName,
        role,
        isPlatformAdmin: session ? isPlatformAdmin(session.user) : false,
      }}
    >
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-brand focus:px-4 focus:py-2.5 focus:text-sm focus:font-semibold focus:text-white"
      >
        Saltar al contenido
      </a>

      <div className="min-h-screen lg:flex">
        {/* Sidebar cálida en escritorio: papel, no una franja negra genérica. */}
        <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col gap-5 border-r border-line bg-paper px-4 py-5 lg:flex">
          <Link href="/merchants" className="block px-1.5">
            <BrandLogo />
          </Link>

          <div className="rounded-2xl border border-line bg-surface p-3 shadow-soft">
            <p className="px-1 text-[10px] font-bold uppercase tracking-[0.15em] text-ink-faint">
              Comercio
            </p>
            <div className="mt-1.5 flex items-center gap-2.5">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-sm font-bold text-white">
                {mark(merchantName)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold leading-tight text-ink">
                  {merchantName || "…"}
                </span>
              </span>
            </div>
          </div>

          {navItems()}
          {userFooter}
        </aside>

        {/* Contenido */}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-canvas/90 px-4 py-3 backdrop-blur lg:hidden">
            <Link href="/merchants" className="min-w-0">
              <BrandLogo compact />
            </Link>
            <div className="flex items-center gap-2">
              {groups.some((group) => group.items.some((item) => item.href === "/operations")) && (
                <Button
                  size="sm"
                  icon={<IconScan size={17} />}
                  onClick={() => router.push(`${root}/operations`)}
                >
                  Operar
                </Button>
              )}
              <button
                type="button"
                onClick={() => setMenuOpen(true)}
                aria-label="Abrir menú"
                className="flex size-11 items-center justify-center rounded-xl border border-line-strong bg-surface text-ink shadow-soft"
              >
                <IconMenu size={20} />
              </button>
            </div>
          </header>

          {menuOpen && (
            <div className="fixed inset-0 z-40 lg:hidden">
              <div
                className="absolute inset-0 bg-ink/40 backdrop-blur-sm"
                onClick={() => setMenuOpen(false)}
              />
              <div className="animate-pop absolute inset-y-0 left-0 flex w-[292px] max-w-[86vw] flex-col gap-5 border-r border-line bg-paper p-4 shadow-lift">
                <div className="flex items-center justify-between px-1">
                  <BrandLogo compact />
                  <button
                    type="button"
                    onClick={() => setMenuOpen(false)}
                    aria-label="Cerrar menú"
                    className="flex size-10 items-center justify-center rounded-xl text-ink-soft hover:bg-surface"
                  >
                    <IconClose size={18} />
                  </button>
                </div>
                <div className="rounded-2xl border border-line bg-surface p-3">
                  <p className="px-1 text-[10px] font-bold uppercase tracking-[0.15em] text-ink-faint">
                    Comercio
                  </p>
                  <div className="mt-1.5 flex items-center gap-2.5">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-sm font-bold text-white">
                      {mark(merchantName)}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-bold leading-tight text-ink">
                        {merchantName || "…"}
                      </span>
                    </span>
                  </div>
                </div>
                {navItems(() => setMenuOpen(false))}
                {userFooter}
              </div>
            </div>
          )}

          <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
            <nav aria-label="Migas de pan" className="mb-3 flex flex-wrap items-center gap-1.5 text-xs text-ink-faint">
              <Link href="/merchants" className="transition-colors hover:text-brand">
                Comercios
              </Link>
              <span aria-hidden="true">/</span>
              <span className="max-w-[12rem] truncate text-ink-soft">{merchantName}</span>
              <span aria-hidden="true">/</span>
              <span aria-current="page" className="font-semibold text-ink">
                {title}
              </span>
            </nav>
            <h1 className="mb-6 text-[26px] font-bold tracking-[-0.02em] text-ink sm:text-[30px]">
              {title}
            </h1>
            {children}
          </main>
        </div>
      </div>
    </MerchantProvider>
  );
}

/** Skeleton de la estructura real: sin destellos de contenido privado. */
function ShellSkeleton({
  error,
  onRetry,
}: {
  error?: string;
  onRetry?: () => void;
}) {
  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-surface-2 text-ink-faint">
          <IconGrid size={26} />
        </span>
        <h1 className="mt-4 text-lg font-bold tracking-tight text-ink">
          No se pudo abrir tu panel
        </h1>
        <p role="alert" className="mt-2 text-sm leading-relaxed text-ink-soft">
          {error}
        </p>
        {onRetry && (
          <Button className="mt-5" onClick={onRetry}>
            Reintentar
          </Button>
        )}
      </main>
    );
  }
  return (
    <div className="min-h-screen lg:flex" aria-busy="true">
      <p className="sr-only" role="status">
        Comprobando acceso…
      </p>
      <aside className="hidden h-screen w-[264px] shrink-0 flex-col gap-5 border-r border-line bg-paper px-4 py-5 lg:flex">
        <div className="skeleton h-9 w-40 rounded-lg" />
        <div className="skeleton h-[74px] rounded-2xl" />
        {MANAGER_GROUPS.map((group) => (
          <div key={group.label} className="space-y-2">
            {group.items.map((item) => (
              <div key={item.label} className="skeleton h-10 rounded-xl" />
            ))}
          </div>
        ))}
      </aside>
      <div className="flex-1 px-5 py-8 sm:px-8">
        <div className="skeleton h-4 w-64 rounded-lg" />
        <div className="skeleton mt-4 h-8 w-72 rounded-xl" />
        <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      </div>
    </div>
  );
}
