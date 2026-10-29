"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  BrandLogo,
  Button,
  EmptyState,
  FormField,
  IconArrowRight,
  IconClose,
  IconEye,
  IconEyeOff,
  IconMail,
  IconPlus,
  Input,
  LinkButton,
  LoadingState,
  PageHeader,
  Panel,
  SectionTitle,
  StatusPill,
} from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { isPlatformAdmin, type MerchantMembership, type SessionPayload } from "@/lib/session";

interface MerchantRow {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
}

const ROLE_LABELS: Record<string, string> = {
  owner: "Propietario",
  admin: "Administración",
  staff: "Personal",
  viewer: "Lectura",
};

/** Inicial del comercio para el avatar: sin inventar logotipos. */
function mark(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "·";
}

/**
 * Entrada al producto: comercios a los que tiene acceso la sesión.
 *
 * Para la administración de plataforma es también el alta de nuevos comercios.
 * La pantalla es deliberadamente sobria: aquí se elige dónde trabajar, no se
 * configura nada del programa.
 */
export function MerchantsView() {
  const router = useRouter();
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [merchants, setMerchants] = useState<MerchantRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [creating, setCreating] = useState(false);
  const [createdNotice, setCreatedNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const payload = await apiFetch<SessionPayload>("/api/v1/auth/me");
        const rows = await apiFetch<MerchantRow[]>("/api/v1/merchants");
        if (cancelled) return;
        setSession(payload);
        setMerchants(rows);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
          return;
        }
        setError("No se pudieron cargar los comercios.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router, reloadKey]);

  const reload = () => setReloadKey((key) => key + 1);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-5 py-12">
        <Alert tone="danger" title="No se pudo cargar la lista">
          {error}
        </Alert>
        <Button className="mt-4" variant="secondary" onClick={reload}>
          Volver a intentar
        </Button>
      </main>
    );
  }

  if (!session || merchants === null) {
    return (
      <main className="mx-auto max-w-4xl px-5 py-12">
        <LoadingState label="Cargando comercios…" />
      </main>
    );
  }

  const roles = new Map<string, MerchantMembership>(
    session.merchants.map((m) => [m.merchant_id, m]),
  );
  const admin = isPlatformAdmin(session.user);
  const activeCount = merchants.filter((merchant) => merchant.status === "active").length;

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-paper/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <Link href="/" className="min-w-0">
            <BrandLogo />
          </Link>
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="hidden truncate text-[12px] text-ink-faint sm:block">
              {session.user.email}
            </span>
            <Badge tone={admin ? "brand" : "neutral"}>
              {admin ? "Plataforma" : "Comercio"}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-10">
        <PageHeader
          eyebrow={admin ? "Administración de plataforma" : "Panel del comercio"}
          title="Comercios"
          description={
            admin
              ? "Da de alta los comercios de la plataforma y entra en su panel para gestionar su programa."
              : "Aquí aparecen los comercios a los que tienes acceso. Entra en uno para gestionar su programa."
          }
          actions={
            admin ? (
              <div className="flex flex-wrap items-center gap-2">
                <LinkButton href="/platform/support" variant="secondary" icon={<IconMail size={17} />}>
                  Soporte
                </LinkButton>
                {creating ? (
                  <Button
                    variant="secondary"
                    icon={<IconClose size={17} />}
                    onClick={() => setCreating(false)}
                  >
                    Cerrar
                  </Button>
                ) : (
                  <Button icon={<IconPlus size={17} />} onClick={() => setCreating(true)}>
                    Nuevo comercio
                  </Button>
                )}
              </div>
            ) : undefined
          }
        />

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink shadow-soft">
            {merchants.length} {merchants.length === 1 ? "comercio" : "comercios"}
          </span>
          {merchants.length > 0 && (
            <span className="rounded-full bg-ok-soft px-2.5 py-1 text-xs font-semibold text-ok">
              {activeCount} {activeCount === 1 ? "activo" : "activos"}
            </span>
          )}
          <span className="text-xs text-ink-faint">
            Conectado como <span className="font-semibold text-ink-soft">{session.user.email}</span>
          </span>
        </div>

        {createdNotice && (
          <div className="mt-5">
            <Alert tone="ok" title="Comercio dado de alta">
              {createdNotice}
            </Alert>
          </div>
        )}

        {admin && creating && (
          <div className="mt-5">
            <CreateMerchantForm
              onCreated={(name) => {
                setCreatedNotice(
                  `«${name}» ya puede iniciar sesión con el correo de su propietario.`,
                );
                setCreating(false);
                reload();
              }}
            />
          </div>
        )}

        <section className="mt-8" aria-label="Lista de comercios">
          {merchants.length === 0 ? (
            <EmptyState
              illustration="card"
              title="Todavía no hay comercios dados de alta"
              description={
                admin
                  ? "Crea el primero con el botón «Nuevo comercio»: recibirás un correo de propietario con acceso al panel."
                  : "Pide a la administración de la plataforma que te incorpore a un comercio."
              }
              action={
                admin && !creating ? (
                  <Button icon={<IconPlus size={17} />} onClick={() => setCreating(true)}>
                    Nuevo comercio
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <>
              {/* Tabla en escritorio y tablet ancha */}
              <Panel padded={false} className="hidden overflow-hidden md:block">
                <table className="w-full table-fixed border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-line bg-surface-2/60 text-[11px] uppercase tracking-[0.06em] text-ink-faint">
                      <th className="w-[46%] px-5 py-3 font-semibold">Comercio</th>
                      <th className="w-[15%] px-5 py-3 font-semibold">Estado</th>
                      <th className="w-[15%] px-5 py-3 font-semibold">Tu rol</th>
                      <th className="w-[24%] px-5 py-3 text-right font-semibold">Acceso</th>
                    </tr>
                  </thead>
                  <tbody>
                    {merchants.map((merchant) => (
                      <tr
                        key={merchant.id}
                        className="border-b border-line transition-colors last:border-b-0 hover:bg-surface-2/40"
                      >
                        <td className="px-5 py-3.5">
                          <div className="flex min-w-0 items-center gap-3">
                            <span
                              aria-hidden="true"
                              className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-xs font-bold text-white shadow-soft"
                            >
                              {mark(merchant.name)}
                            </span>
                            <div className="min-w-0">
                              <Link
                                href={`/merchants/${merchant.id}`}
                                className="group inline-flex max-w-full min-w-0 items-center gap-1.5 font-semibold text-ink hover:text-brand"
                              >
                                <span className="truncate">{merchant.name}</span>
                                <IconArrowRight
                                  size={14}
                                  className="shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-brand"
                                />
                              </Link>
                              <p
                                className="truncate font-mono text-[11px] text-ink-faint"
                                title={merchant.slug}
                              >
                                {merchant.slug}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusPill tone={merchant.status === "active" ? "ok" : "warn"}>
                            {merchant.status === "active" ? "Activo" : merchant.status}
                          </StatusPill>
                        </td>
                        <td className="px-5 py-3.5">
                          <Badge tone={roles.get(merchant.id) ? "neutral" : "brand"}>
                            {ROLE_LABELS[roles.get(merchant.id)?.role ?? ""] ??
                              (admin ? "Plataforma" : "—")}
                          </Badge>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <LinkButton
                            href={`/merchants/${merchant.id}`}
                            variant="secondary"
                            size="sm"
                          >
                            Abrir panel
                          </LinkButton>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>

              {/* Tarjetas en móvil: mismas acciones, sin tabla comprimida */}
              <ul className="grid grid-cols-1 gap-3 md:hidden">
                {merchants.map((merchant) => (
                  <li key={merchant.id} className="min-w-0">
                    <Link
                      href={`/merchants/${merchant.id}`}
                      className="group block rounded-2xl border border-line bg-surface p-4 shadow-soft transition-colors hover:border-brand/40"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          aria-hidden="true"
                          className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(145deg,#6a58e8,#4633b8)] text-sm font-bold text-white"
                        >
                          {mark(merchant.name)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-semibold text-ink group-hover:text-brand">
                            {merchant.name}
                          </p>
                          <p className="truncate font-mono text-[11px] text-ink-faint">
                            {merchant.slug}
                          </p>
                        </div>
                        <StatusPill tone={merchant.status === "active" ? "ok" : "warn"}>
                          {merchant.status === "active" ? "Activo" : merchant.status}
                        </StatusPill>
                      </div>
                      <div className="mt-3 flex items-center justify-between gap-3 border-t border-line pt-3">
                        <p className="text-xs text-ink-soft">
                          Tu rol:{" "}
                          <span className="font-semibold text-ink">
                            {ROLE_LABELS[roles.get(merchant.id)?.role ?? ""] ??
                              (admin ? "Plataforma" : "—")}
                          </span>
                        </p>
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-brand">
                          Abrir panel
                          <IconArrowRight size={13} />
                        </span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

function CreateMerchantForm({ onCreated }: { onCreated: (name: string) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiFetch<MerchantRow>("/api/v1/platform/merchants", {
        method: "POST",
        body: JSON.stringify({ name, owner_email: email, owner_password: password }),
      });
      onCreated(name);
      setName("");
      setEmail("");
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el comercio.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel tone="warm" className="animate-in">
      <SectionTitle
        title="Nuevo comercio"
        description="Crea el comercio y la cuenta de su propietario: será quien configure el programa y las etiquetas."
        icon={<IconPlus size={18} />}
      />
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Nombre del comercio" required hint="Ej.: Cafetería Norte">
            {({ id, describedBy }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Cafetería Norte"
              />
            )}
          </FormField>
          <FormField label="Email del propietario" required hint="Servirá para iniciar sesión">
            {({ id, describedBy }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="propietario@negocio.com"
              />
            )}
          </FormField>
        </div>

        <FormField
          label="Contraseña del propietario"
          required
          hint="Mínimo 12 caracteres. Compártela con el propietario de forma segura."
        >
          {({ id, describedBy }) => (
            <div className="relative">
              <Input
                id={id}
                aria-describedby={describedBy}
                required
                type={showPassword ? "text" : "password"}
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-12"
                placeholder="Mínimo 12 caracteres"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={showPassword}
                className="absolute right-1.5 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
              >
                {showPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
              </button>
            </div>
          )}
        </FormField>

        {error && (
          <Alert tone="danger" title="No se pudo crear el comercio">
            {error}
          </Alert>
        )}

        <Button type="submit" loading={loading} icon={<IconPlus size={17} />}>
          {loading ? "Creando…" : "Dar de alta"}
        </Button>
      </form>
    </Panel>
  );
}
