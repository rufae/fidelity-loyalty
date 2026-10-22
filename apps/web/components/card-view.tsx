"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  CopyButton,
  IconCheck,
  IconGift,
  IconQr,
  IconWallet,
  LoadingState,
  LoyaltyCard,
  Panel,
  SectionTitle,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fidelity, type PublicCard, type WalletOptions } from "@/lib/fidelity";
import { nextReward } from "@/components/ui/loyalty-card";
import { sellos } from "@/lib/ui";

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

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const data = await fidelity.publicCard(token);
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

  return (
    <main className="mx-auto max-w-lg px-4 pb-12 pt-5 sm:px-6 sm:pt-7">
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

      {/* La tarjeta real del cliente, con sus datos confirmados por el backend. */}
      <div className="animate-in">
        <LoyaltyCard
          merchantName={card.merchant_name}
          programName={card.program_name}
          stamps={card.stamps}
          rewards={card.rewards}
          holderName={null}
          variant="card"
          stampsTestId="card-stamps"
        />
      </div>

      {/* Próximo paso real: cuánto falta para la siguiente recompensa. */}
      <div className="mt-4 flex items-start gap-3 rounded-2xl border border-line bg-surface p-4 shadow-soft">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gold-soft text-gold">
          <IconGift size={19} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">
            {next
              ? `Te faltan ${sellos(remaining)} para «${next.name}»`
              : card.rewards.length
                ? "Tienes recompensas disponibles: pídelas en caja"
                : "Sigue sumando sellos en cada visita"}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">
            {next
              ? "El personal confirma cada sello desde el mostrador. Tu saldo real es el que ves aquí."
              : "El saldo de esta tarjeta lo confirma siempre el servidor del comercio."}
          </p>
        </div>
      </div>

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
          <Alert tone="warn" title="Tarjeta web activa · Modo de demostración">
            Funciona desde el navegador. La integración con Apple Wallet y Google Wallet aún no está
            configurada: todavía no se ha emitido un pase real en ninguna de las dos.
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
              <p className="text-sm font-bold text-ink">Muéstralo en caja para acumular sellos</p>
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
                  {item.earned ? "Canjeable" : sellos(item.stamps_required)}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </main>
  );
}
