"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  Alert,
  BrandLogo,
  Button,
  FormField,
  IconArrowLeft,
  IconEye,
  IconEyeOff,
  IconGift,
  IconLock,
  IconScan,
  IconStar,
  Input,
  LoyaltyCard,
} from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { isPlatformAdmin, type SessionPayload } from "@/lib/session";
import { ArtSparkles } from "@/components/ui/art";

export function LoginView() {
  const router = useRouter();
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
      const payload = await apiFetch<SessionPayload>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      // Cada usuario va directo a su pantalla: la administración de plataforma
      // a la lista de comercios; el equipo de un comercio, a su panel.
      if (!isPlatformAdmin(payload.user) && payload.merchants.length === 1) {
        router.push(`/merchants/${payload.merchants[0].merchant_id}`);
      } else {
        router.push("/merchants");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Demasiados intentos. Espera un momento y vuelve a probar.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Credenciales incorrectas.");
      } else {
        setError("No se pudo iniciar sesión. Inténtalo de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen lg:grid lg:grid-cols-[1.02fr_0.98fr]">
      {/* Bloque de marca: la tarjeta como bienvenida, siempre rotulada como ejemplo. */}
      <aside className="mesh-brand grain relative hidden flex-col justify-between overflow-hidden p-10 text-white lg:flex xl:p-14">
        <div
          aria-hidden="true"
          className="animate-drift pointer-events-none absolute -right-24 -top-24 size-80 rounded-full border border-white/15"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-32 -left-20 size-96 rounded-full border border-white/10"
        />
        <ArtSparkles className="pointer-events-none absolute right-8 top-8 h-14 w-14 opacity-80" />

        <div className="relative flex items-center justify-between">
          <BrandLogo tone="inverse" />
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-white/70 transition-colors hover:text-white"
          >
            <IconArrowLeft size={14} />
            Portada
          </Link>
        </div>

        <div className="relative my-10 max-w-md space-y-7">
          <div>
            <h2 className="text-[34px] font-bold leading-[1.1] tracking-[-0.02em]">
              Tu programa de sellos, funcionando en un minuto.
            </h2>
            <p className="mt-3 text-[15px] leading-relaxed text-white/75">
              El mostrador, la tarjeta del cliente y las cifras reales del negocio, en el mismo
              lugar.
            </p>
          </div>

          <div className="relative">
            <LoyaltyCard
              merchantName="Café La Esquina"
              programName="Club de sellos"
              stamps={7}
              holderName="Tu clienta, en su móvil"
              rewards={[
                { name: "Café gratis", stamps_required: 8 },
                { name: "Desayuno completo", stamps_required: 12 },
              ]}
              variant="card"
            />
            <span className="absolute -top-2.5 right-4 rounded-full border border-white/25 bg-white/15 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-white backdrop-blur">
              Ejemplo
            </span>
          </div>

          <ul className="space-y-3 text-sm text-white/85">
            {[
              { icon: IconGift, text: "Programas de sellos y recompensas por comercio." },
              { icon: IconScan, text: "Altas por NFC/QR y tarjeta digital con código propio." },
              { icon: IconStar, text: "Etiqueta independiente para tus reseñas de Google." },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/12 ring-1 ring-inset ring-white/10">
                  <Icon size={16} />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/60">
          Acceso para comercios y administración de la plataforma.
        </p>
      </aside>

      {/* Formulario */}
      <div className="relative flex flex-1 items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-[400px]">
          <div className="flex items-center justify-between lg:hidden">
            <BrandLogo />
            {/* Táctil ≥44px (WCAG 2.2 §2.5.8): el enlace vuelve al origen público. */}
            <Link
              href="/"
              className="-my-1 inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 text-xs font-semibold text-ink-soft hover:text-brand"
            >
              Volver
            </Link>
          </div>

          <header className="mt-10 space-y-2 lg:mt-0">
            <p className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-brand">
              <span aria-hidden="true" className="h-px w-5 bg-brand/50" />
              LocalAI Fidelity
            </p>
            <h1 className="text-[30px] font-bold leading-tight tracking-[-0.02em] text-ink">
              Acceso al panel
            </h1>
            <p className="text-sm leading-relaxed text-ink-soft">
              Comercios y administración de la plataforma de fidelización.
            </p>
          </header>

          <form
            onSubmit={onSubmit}
            className="mt-7 space-y-4 rounded-2xl border border-line bg-surface p-6 shadow-soft sm:p-7"
          >
            <FormField label="Email" required>
              {({ id, describedBy }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  type="email"
                  required
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tu@negocio.com"
                />
              )}
            </FormField>

            <FormField label="Contraseña" required>
              {({ id, describedBy }) => (
                <div className="relative">
                  <Input
                    id={id}
                    aria-describedby={describedBy}
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pr-12"
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
              <Alert tone="danger" title="No se pudo entrar">
                {error}
              </Alert>
            )}

            <Button type="submit" size="lg" loading={loading} className="w-full">
              {loading ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-ink-faint">
            <IconLock size={15} className="mt-0.5 shrink-0 text-ink-soft" />
            <span>
              Solo entra el personal autorizado. Tu sesión es privada y puedes cerrarla cuando
              quieras desde el panel.
            </span>
          </p>

          <p className="mt-4 rounded-xl border border-line bg-paper p-3 text-xs leading-relaxed text-ink-soft">
            <strong className="font-semibold text-ink">¿Eres cliente?</strong> No necesitas cuenta:
            tu tarjeta llega a tu correo y se abre desde el enlace personal o desde la etiqueta
            «Recuperar mi tarjeta» de tu comercio.
          </p>
        </div>
      </div>
    </main>
  );
}
