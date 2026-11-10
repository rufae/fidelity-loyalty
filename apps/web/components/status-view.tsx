"use client";

import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  BrandLogo,
  IconCheck,
  IconGift,
  IconContactless,
  IconScan,
  IconStar,
  IconWallet,
  LinkButton,
  Panel,
  SectionTitle,
  StatusPill,
  IconAlert,
  IconInfo,
} from "@/components/ui";
import {
  CHECK_LABELS,
  LOADING_STATUS,
  classifyLiveness,
  classifyReadiness,
  walletLabel,
  type HealthPayload,
  type ServiceStatus,
} from "@/lib/status";

async function fetchPayload(url: string): Promise<{ reachable: boolean; payload: HealthPayload | null }> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok && response.status !== 503) {
      return { reachable: true, payload: null };
    }
    const payload = (await response.json()) as HealthPayload;
    return { reachable: true, payload };
  } catch {
    return { reachable: false, payload: null };
  }
}

const PILL_TONE = {
  loading: "neutral",
  ok: "ok",
  degraded: "warn",
  error: "danger",
} as const;

/**
 * Pantalla de estado (§7.1): comprueba los servicios reales y comunica el
 * estado con palabra + color. El proveedor simulado nunca aparece como
 * «Operativo»: se rotula «Modo de demostración» (§17.2).
 */
export function StatusView() {
  const [checks, setChecks] = useState<readonly ServiceStatus[]>(LOADING_STATUS);
  const [wallet, setWallet] = useState<string>("Comprobando…");
  const [walletDemo, setWalletDemo] = useState(false);
  const [isProduction, setIsProduction] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [health, ready] = await Promise.all([fetchPayload("/health"), fetchPayload("/ready")]);
      if (cancelled) return;
      setChecks([classifyLiveness(health.reachable, health.payload), classifyReadiness(ready.reachable, ready.payload)]);
      setWallet(walletLabel(ready.payload?.wallet_provider));
      setWalletDemo(ready.payload?.wallet_provider === "simulated");
      setIsProduction(health.payload?.environment === "production");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-8 px-5 py-12 sm:px-8">
      {/* Cabecera de marca (§7.1) */}
      <header className="animate-in">
        <BrandLogo />
        <div className="relative mt-8 overflow-hidden rounded-3xl bg-gradient-to-br from-nav via-[#4a3f9f] to-sky p-8 text-white shadow-lift sm:p-10">
          <div
            aria-hidden="true"
            className="absolute -right-20 -top-24 size-80 rounded-full bg-white/[0.07]"
          />
          <div
            aria-hidden="true"
            className="absolute -bottom-32 -left-12 size-72 rounded-full bg-white/[0.05]"
          />
          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/70">
              Fidelización y reseñas para negocios de barrio
            </p>
            <h1 className="mt-3 max-w-xl text-3xl font-bold leading-tight tracking-tight text-balance sm:text-[38px]">
              Tu fidelización, lista para funcionar
            </h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-white/85">
              Programas de sellos, tarjetas digitales, recuperación segura por correo y etiquetas
              NFC/QR de alta, acceso a tarjetas y reseñas de Google. Esta pantalla sirve para
              comprobar que los servicios responden.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <LinkButton
                href="/login"
                variant="secondary"
                size="lg"
                className="border-transparent bg-white text-brand shadow-lift hover:bg-white"
              >
                Acceder al panel
              </LinkButton>
            </div>
          </div>
        </div>
      </header>

      {/* Comprobaciones reales */}
      <Panel>
        <SectionTitle
          title="Comprobaciones"
          description="Estado real de los servicios que sostienen la plataforma."
        />
        <ul className="divide-y divide-line">
          {checks.map((check) => (
            <li key={check.label} className="flex items-center justify-between gap-4 py-3.5">
              <div>
                <p className="text-sm font-semibold text-ink">{check.label}</p>
                <p className="mt-0.5 text-sm text-ink-soft">{check.detail}</p>
              </div>
              <StatusPill tone={PILL_TONE[check.state]}>{CHECK_LABELS[check.state]}</StatusPill>
            </li>
          ))}
          <li className="flex items-center justify-between gap-4 py-3.5">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                <IconWallet size={17} className="text-brand" />
                Proveedor de Wallet
              </p>
              <p className="mt-0.5 text-sm text-ink-soft">{wallet}</p>
            </div>
            {walletDemo ? (
              <Badge tone="gold" icon={<IconInfo size={13} />}>
                Modo de demostración
              </Badge>
            ) : (
              <StatusPill tone="ok">Operativo</StatusPill>
            )}
          </li>
        </ul>

        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl bg-surface-2 px-4 py-3 text-xs text-ink-soft">
          <span className="font-semibold text-ink">Leyenda:</span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-ok" /> Operativo: servicio respondiendo
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-warn" /> Degradado: responde con avisos
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-danger" /> Error: no responde
          </span>
        </div>
      </Panel>

      {walletDemo && (
        <Alert tone="warn" title="La integración con Apple Wallet y Google Wallet está en modo demostración">
          La tarjeta web y el QR funcionan de verdad; los pases nativos se emitirán cuando se
          configuren las credenciales de cada proveedor. Nunca se presenta un pase simulado como
          emitido.
        </Alert>
      )}

      {/* Estado del proyecto */}
      <Panel>
        <SectionTitle title="Estado del proyecto" description="Qué puedes usar hoy y qué falta." />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-ok-soft/60 p-5">
            <p className="flex items-center gap-2 text-sm font-bold text-ok">
              <IconCheck size={17} /> Disponible hoy
            </p>
            <ul className="mt-3 space-y-2.5 text-sm text-ink-soft">
              {[
                { icon: IconGift, text: "Programas de sellos con recompensas y condiciones versionadas." },
                { icon: IconScan, text: "Altas con verificación de correo, tarjeta con QR y operaciones de mostrador." },
                { icon: IconContactless, text: "Etiquetas NFC/QR separadas para alta, recuperación de tarjetas y reseñas." },
                { icon: IconStar, text: "Enlace de reseñas de Google verificado y analítica real." },
              ].map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-start gap-2.5">
                  <Icon size={17} className="mt-0.5 shrink-0 text-ok" />
                  {text}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl bg-warn-soft/60 p-5">
            <p className="flex items-center gap-2 text-sm font-bold text-warn">
              <IconAlert size={17} /> Pendiente
            </p>
            <ul className="mt-3 space-y-2.5 text-sm text-ink-soft">
              <li className="flex items-start gap-2.5">
                <IconWallet size={17} className="mt-0.5 shrink-0 text-warn" />
                Pases nativos de Apple y Google Wallet: faltan credenciales de los proveedores.
              </li>
              <li className="flex items-start gap-2.5">
                <IconInfo size={17} className="mt-0.5 shrink-0 text-warn" />
                Despliegue con HTTPS y dominio para uso fuera de la red local.
              </li>
            </ul>
          </div>
        </div>
        <p className="mt-4 text-xs text-ink-faint">
          Las pantallas de producto se muestran solo cuando existen de verdad. El detalle de fases
          vive en <code className="font-mono text-ink-soft">docs/IMPLEMENTATION_PLAN.md</code>.
        </p>
      </Panel>

      <footer className="text-xs text-ink-faint">
        API en <code className="font-mono text-ink-soft">:8101</code>
        {!isProduction && (
          <>
            {" "}
            · documentación OpenAPI en{" "}
            <a
              className="inline-flex min-h-11 items-center rounded-lg px-2 font-semibold text-brand underline-offset-2 hover:underline"
              href="http://localhost:8101/docs"
            >
              localhost:8101/docs
            </a>
          </>
        )}
      </footer>
    </main>
  );
}
