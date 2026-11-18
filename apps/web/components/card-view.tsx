"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  Alert,
  CopyButton,
  IconCheck,
  IconGift,
  IconPlus,
  IconQr,
  IconWallet,
  LoadingState,
  LoyaltyCard,
  Panel,
  SectionTitle,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fidelity, type PublicCard, type WalletOptions } from "@/lib/fidelity";
import { formatDateTime, formatNumber, unidades } from "@/lib/ui";
import { nextReward } from "@/components/ui/loyalty-card";
import { LandingCardZone } from "@/components/landing-card-zone";
import { ArtSparkles } from "@/components/ui/art";

/** Cada cuánto se comprueba si el saldo o el estado cambiaron (ms). */
const REFRESH_MS = 10_000;

/**
 * Tarjeta web del cliente: fallback sin Wallet y consulta del saldo.
 * El saldo real siempre viene del backend; la tarjeta no es la base contable.
 *
 * Se **actualiza sola**: sondea la API cada pocos segundos (solo con la
 * pestaña visible) y refresca al volver a la pestaña, para que el cliente vea
 * el sello que le acaban de dar —o una suspensión— sin recargar la página.
 */
export function CardView({ token }: { token: string }) {
  const [card, setCard] = useState<PublicCard | null>(null);
  const [wallet, setWallet] = useState<WalletOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** Estado no operativo (suspendida/revocada): se muestra y puede revertirse. */
  const [inactive, setInactive] = useState<string | null>(null);
  /** Último saldo conocido: detecta sellos nuevos para estamparlos. */
  const previousStamps = useRef<number | null>(null);
  /** Índice del primer sello recién ganado (se limpia tras la animación). */
  const [freshFrom, setFreshFrom] = useState<number | null>(null);
  /** Recompensa recién alcanzada: celebración de una sola vez. */
  const [celebrate, setCelebrate] = useState<string | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const data = await fidelity.publicCard(token);
      // Detección de novedades: solo en transiciones (nunca en la primera
      // carga), para no celebrar lo que ya era así al abrir la página.
      const previous = previousStamps.current;
      if (previous !== null && data.stamps > previous) {
        setFreshFrom(previous);
        window.setTimeout(() => setFreshFrom(null), 2200);
        // Al cruzar el umbral la recompensa ya figura como ganada: el cruce
        // se calcula por los saldos anterior y nuevo, no por `earned`.
        const crossed = [...data.rewards]
          .sort((a, b) => a.stamps_required - b.stamps_required)
          .find(
            (reward) =>
              previous < reward.stamps_required && reward.stamps_required <= data.stamps,
          );
        if (crossed) {
          setCelebrate(crossed.name);
          window.setTimeout(() => setCelebrate(null), 7000);
        }
      }
      previousStamps.current = data.stamps;
      setCard(data);
      setInactive(null);
      setError(null);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        setError("Esta tarjeta no existe o está desactivada.");
        return;
      }
      if (caught instanceof ApiError) {
        // 409/403: suspendida, revocada o inactiva. El mensaje del backend es
        // claro y no sensible; el sondeo sigue por si se reactiva.
        // Los fallos de red (status 0) NO invalidan el estado: se conserva
        // lo último mostrado y el sondeo reintenta solo.
        if (caught.status === 0) return;
        setInactive(caught.message);
        return;
      }
      // Fallo de red: se conserva lo último mostrado y el sondeo reintenta.
    }
  }, [token]);

  useEffect(() => {
    const initial = async (): Promise<void> => {
      await refresh();
    };
    void initial();
    // Opciones reales de Wallet del proveedor configurado: si no hay
    // credenciales, la respuesta dice `simulated` y se ofrece la tarjeta web.
    void fidelity
      .walletOptions(token)
      .then(setWallet)
      .catch(() => setWallet(null));

    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, REFRESH_MS);
    const onVisibility = (): void => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh, token]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-surface-2 text-ink-faint">
          <IconWallet size={30} />
        </div>
        <h1 className="mt-4 text-xl font-bold text-ink">Tarjeta no disponible</h1>
        <p className="mt-2 text-sm text-ink-soft">{error}</p>
      </main>
    );
  }
  if (inactive) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-gold-soft text-warn">
          <IconWallet size={30} />
        </div>
        <h1 className="mt-4 text-xl font-bold text-ink">Tu tarjeta no está activa ahora mismo</h1>
        <p className="mt-2 text-sm text-ink-soft">{inactive}</p>
        <p className="mt-4 text-xs leading-relaxed text-ink-faint">
          Si crees que es un error, habla con el establecimiento. Esta página se actualizará sola
          cuando vuelva a estar activa.
        </p>
      </main>
    );
  }
  if (!card) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
        <LoadingState label="Cargando tu tarjeta…" />
      </main>
    );
  }

  const { reward: next, remaining } = nextReward(card.stamps, card.rewards);
  const hasRealWallet = Boolean(wallet && !wallet.simulated && wallet.actions.length > 0);
  /** iPhone sin Wallet real: la pantalla de inicio es la vía honrada. */
  const isIos = typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent);

  return (
    <main className="relative mx-auto max-w-lg px-4 pb-12 pt-5 sm:px-6 sm:pt-7">
      <ArtSparkles className="animate-twinkle pointer-events-none absolute -top-1 right-3 h-12 w-12 opacity-60" />
      <header className="animate-in mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-brand">
            {card.merchant_name}
          </p>
          <h1 className="mt-1 text-[24px] font-bold leading-tight tracking-[-0.02em] text-ink">
            Tu tarjeta
          </h1>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-[10px] font-semibold text-ink-soft">
          <span aria-hidden="true" className="size-1.5 animate-pulse rounded-full bg-ok" />
          Se actualiza sola
        </span>
      </header>

      {/* La tarjeta real del cliente, con sus datos confirmados por el backend.
          La inclinación 3D es cortesía del puntero: no afecta al contenido ni
          funciona en táctil ni con movimiento reducido. Los sellos que acaban
          de entrar se estampan solos, como en la tienda. */}
      <div className="animate-in">
        <LandingCardZone>
          <div className="tilt-stage" style={{ transformStyle: "preserve-3d" }}>
            <LoyaltyCard
              merchantName={card.merchant_name}
              programName={card.program_name}
              stamps={card.stamps}
              rewards={card.rewards}
              holderName={null}
              variant="card"
              stampsTestId="card-stamps"
              stampAnimateFrom={freshFrom}
              programType={card.program_type}
              branding={
                card.primary_color
                  ? {
                      primary_color: card.primary_color,
                      accent_color: card.accent_color ?? "#f7bd4b",
                      stamp_icon: card.stamp_icon ?? "cup",
                      footer_text: card.footer_text ?? null,
                      logo_url: card.logo_url ?? null,
                    }
                  : null
              }
            />
          </div>
        </LandingCardZone>
      </div>

      {/* Recompensa recién alcanzada: una sola vez, al cruzar el umbral. */}
      {celebrate && (
        <div
          role="status"
          className="animate-pop relative mt-4 overflow-hidden rounded-2xl border-2 border-gold/40 bg-gold-soft p-4"
        >
          <ArtSparkles className="animate-twinkle pointer-events-none absolute -right-1 -top-2 h-10 w-10 opacity-80" />
          <div className="flex items-start gap-3">
            <span
              aria-hidden="true"
              className="flex size-10 shrink-0 items-center justify-center rounded-full border-[#d99a1f] bg-[linear-gradient(145deg,#ffd985,#f7bd4b_55%,#eaa32a)] text-[#4a3208] shadow-[inset_0_1px_0_rgb(255_255_255/0.75),inset_0_-2px_3px_rgb(122_76_0/0.28),0_2px_5px_rgb(74_50_8/0.18)]"
            >
              <IconGift size={20} />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-gold">
                ¡Recompensa conseguida!
              </p>
              <p className="mt-0.5 text-[15px] font-bold leading-snug text-ink">
                Ya puedes pedir «{celebrate}» en caja.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sin Wallet real y en iPhone: la alternativa honrada es la pantalla
          de inicio. Detalle discreto, con las instrucciones exactas. */}
      {hasRealWallet === false && isIos && (
        <div className="mt-4 flex items-start gap-3 rounded-2xl border border-line bg-paper p-4">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
            <IconPlus size={17} />
          </span>
          <p className="text-xs leading-relaxed text-ink-soft">
            <strong className="font-semibold text-ink">Guárdala siempre a mano:</strong> toca el
            botón de compartir de Safari y elige «Añadir a pantalla de inicio». La abrirás con un
            toque, como una app.
          </p>
        </div>
      )}

      {/* Próximo paso real: cuánto falta para la siguiente recompensa. */}
      <div className="mt-4 flex items-start gap-3 rounded-2xl border border-line bg-surface p-4 shadow-soft">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gold-soft text-gold">
          <IconGift size={19} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">
            {next
              ? `Te faltan ${unidades(card.program_type, remaining)} para «${next.name}»`
              : card.rewards.length
                ? "Tienes recompensas disponibles: pídelas en caja"
                : card.program_type === "points"
                  ? "Sigue sumando puntos con cada venta"
                  : "Sigue sumando sellos en cada visita"}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">
            {next
              ? card.program_type === "points"
                ? "El personal registra cada venta desde el mostrador. Tu saldo real es el que ves aquí."
                : "El personal confirma cada sello desde el mostrador. Tu saldo real es el que ves aquí."
              : "El saldo de esta tarjeta lo confirma siempre el servidor del comercio."}
          </p>
        </div>
      </div>

      {/* Condición de caducidad del programa (§7.7): visible en la propia
          tarjeta para que nadie sorprenda con sellos que vencen. Los
          puntos por importe no caducan (§7.6). */}
      {card.stamps_expire_days != null && card.program_type !== "points" && (
        <p className="mt-2 rounded-xl border border-gold/60 bg-gold-soft px-3 py-2 text-[11px] font-semibold text-warn">
          ⏳ Tus sellos caducan a los {card.stamps_expire_days} días de obtenerse.
        </p>
      )}

      {/* Tu registro (§9.3: solo agregados, sin importes ni detalle). El
          cliente ve que el servidor recuerda sus visitas: confianza y menos
          disputas en caja. Se muestra solo cuando hay visitas. */}
      {(card.total_visits ?? 0) > 0 && (
        <p className="mt-2 text-xs text-ink-faint">
          {card.total_visits === 1
            ? "1 visita registrada en esta tarjeta."
            : `${formatNumber(card.total_visits ?? 0)} visitas registradas en esta tarjeta.`}
          {card.last_visit_at && ` Última: ${formatDateTime(card.last_visit_at)}.`}
        </p>
      )}

      {/* Wallet: solo acciones reales del proveedor; nunca falsas promesas. */}
      <section className="mt-4 space-y-2" aria-label="Opciones de Wallet">
        {hasRealWallet &&
          wallet?.actions.map((action) =>
            action.url ? (
              <a
                key={action.kind}
                href={action.url}
                className="flex h-12 items-center justify-center gap-2 rounded-2xl bg-nav text-sm font-bold text-white shadow-soft transition-colors hover:bg-nav-2"
              >
                <IconWallet size={18} />
                {action.label}
              </a>
            ) : (
              <p
                key={action.kind}
                className="flex h-12 items-center justify-center gap-2 rounded-2xl border border-line bg-surface-2 text-sm font-semibold text-ink-faint"
              >
                <IconWallet size={18} />
                {action.label}
              </p>
            ),
          )}

        {card.simulated_wallet && (
          <Alert tone="warn" title="Añadir a Wallet · No disponible de momento">
            De momento tu tarjeta vive aquí, en el navegador: funciona igual para
            acumular y canjear. Apple Wallet y Google Wallet llegarán más
            adelante; te avisará tu comercio cuando estén.
          </Alert>
        )}
      </section>

      {/* Identificación en caja: el QR real que sirve la API. */}
      <section className="mt-4 overflow-hidden rounded-3xl border border-line bg-surface shadow-soft">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex size-9 items-center justify-center rounded-xl bg-brand-soft text-brand">
              <IconQr size={18} />
            </span>
            <div>
              <p className="text-sm font-bold text-ink">
                {card.program_type === "points"
                  ? "Muéstralo en caja para acumular puntos"
                  : "Muéstralo en caja para acumular sellos"}
              </p>
              <p className="text-[11px] text-ink-faint">El personal lo escanea con su móvil</p>
            </div>
          </div>
          <IconCheck size={18} className="shrink-0 text-ok" />
        </div>
        <div className="px-5 py-6 text-center">
          {/* QR servido por la propia API (mismo origen). */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={fidelity.cardQrUrl(token)}
            alt="Código QR de tu tarjeta de fidelización"
            className="mx-auto size-52 rounded-2xl border border-line bg-white p-2.5 shadow-soft ring-8 ring-paper"
          />
          <div className="mx-auto mt-4 flex max-w-full items-center justify-center gap-2">
            <p className="tnum truncate font-mono text-[11px] text-ink-faint">{token}</p>
            <CopyButton value={token} label="Copiar código" copiedLabel="Copiado" />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-ink-faint">
            Guarda esta página en tu móvil: es tu tarjeta siempre contigo.
          </p>
        </div>
      </section>

      {card.rewards.length > 0 && (
        <Panel tone="muted" className="mt-4">
          <SectionTitle
            title="Tus recompensas"
            description="El estado lo confirma el servidor; si ya la has canjeado, aparecerá actualizado."
          />
          <ul className="space-y-2">
            {card.rewards.map((item) => (
              <li
                key={item.name}
                className={`flex items-center justify-between gap-3 rounded-xl border px-3.5 py-3 ${
                  item.earned
                    ? "border-gold/30 bg-gold-soft"
                    : "border-line bg-surface"
                }`}
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  {item.earned ? (
                    <IconCheck size={17} className="shrink-0 text-gold" />
                  ) : (
                    <IconGift size={17} className="shrink-0 text-ink-faint" />
                  )}
                  <span className="truncate text-sm font-semibold text-ink">{item.name}</span>
                </span>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${
                    item.earned ? "bg-gold text-white" : "bg-surface-2 text-ink-soft"
                  }`}
                >
                  {item.earned ? "Canjeable" : unidades(card.program_type, item.stamps_required)}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </main>
  );
}
