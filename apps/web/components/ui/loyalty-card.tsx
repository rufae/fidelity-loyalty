/**
 * La pieza firma del producto: la tarjeta de fidelización.
 *
 * Es el mismo objeto visual en la portada (ejemplo), en la vista previa del
 * editor y en la tarjeta real del cliente. Los sellos y la próxima recompensa
 * se derivan SIEMPRE de los datos que recibe: este componente no inventa
 * progreso ni saldo.
 */
import type { ReactNode } from "react";

import { StampRow } from "@/components/ui/primitives";
import { stampSlots } from "@/lib/ui";

export interface LoyaltyRewardPreview {
  name: string;
  stamps_required: number;
  earned?: boolean;
}

type Variant = "hero" | "card" | "preview";

function initials(name: string): string {
  const words = name
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 2);
  const chosen = (words.length ? words : name.trim().split(/\s+/)).slice(0, 2);
  return chosen.map((word) => word[0]?.toUpperCase() ?? "").join("") || "LF";
}

/** Próxima recompensa real a partir de los sellos actuales. */
export function nextReward(
  stamps: number,
  rewards: LoyaltyRewardPreview[],
): { reward: LoyaltyRewardPreview | null; remaining: number } {
  const sorted = [...rewards].sort((a, b) => a.stamps_required - b.stamps_required);
  const pending = sorted.find((reward) => reward.stamps_required > stamps && !reward.earned);
  if (!pending) return { reward: null, remaining: 0 };
  return { reward: pending, remaining: pending.stamps_required - stamps };
}

export function LoyaltyCard({
  merchantName,
  programName,
  stamps,
  rewards = [],
  holderName,
  variant = "card",
  floating = false,
  className = "",
  stampsTestId,
  children,
}: {
  merchantName: string;
  programName: string;
  stamps: number;
  rewards?: LoyaltyRewardPreview[];
  holderName?: string | null;
  variant?: Variant;
  /** Identificador de prueba para el saldo (la tarjeta real lo usa). */
  stampsTestId?: string;
  /** Flotación lenta; solo decorativa (portada). Respeta reduced-motion. */
  floating?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const { reward, remaining } = nextReward(stamps, rewards);
  const { slots, filled } = stampSlots(stamps, reward?.stamps_required ?? null);
  const compact = variant === "preview";
  const hero = variant === "hero";
  const maxReward = rewards.reduce((max, item) => Math.max(max, item.stamps_required), 0);

  return (
    <article
      aria-label={`Tarjeta de fidelización de ${merchantName}`}
      className={`mesh-brand grain relative isolate overflow-hidden rounded-[26px] text-white shadow-lift ${
        floating ? "animate-float" : ""
      } ${hero ? "min-h-[360px]" : ""} ${className}`}
    >
      {/* Luz y profundidad: una tarjeta física, no un rectángulo plano. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute -right-16 -top-20 size-56 rounded-full border border-white/15" />
        <div className="absolute -right-8 -top-12 size-40 rounded-full border border-white/10" />
        <div className="absolute -bottom-24 -left-16 size-64 rounded-full bg-white/[0.05] blur-2xl" />
        <div className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-white/50 to-transparent" />
      </div>

      <div
        className={`relative flex h-full flex-col ${
          compact ? "gap-3 p-4 sm:p-5" : "gap-5 p-5 sm:p-6 lg:p-7"
        }`}
      >
        {/* Cabecera: comercio + tipo de tarjeta */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              aria-hidden="true"
              className={`flex shrink-0 items-center justify-center rounded-xl border border-white/25 bg-white/15 font-bold tracking-tight text-white backdrop-blur-sm ${
                compact ? "size-8 text-[11px]" : "size-10 text-sm"
              }`}
            >
              {initials(merchantName)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-white/70">
                {merchantName}
              </p>
              <p
                className={`truncate font-semibold leading-tight text-white ${
                  compact ? "text-[13px]" : "text-sm"
                }`}
              >
                {programName}
              </p>
            </div>
          </div>
          {!compact && (
            <span className="shrink-0 rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-white/85 backdrop-blur-sm">
              Tarjeta de sellos
            </span>
          )}
        </div>

        {/* Saldo real */}
        <div className="mt-auto">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/65">
                Sellos acumulados
              </p>
              <p className="mt-1 flex items-baseline gap-2">
                <span
                  data-testid={stampsTestId}
                  className={`tnum font-bold leading-none tracking-[-0.04em] text-white ${
                    compact ? "text-[38px]" : hero ? "text-[64px]" : "text-[52px]"
                  }`}
                >
                  {stamps}
                </span>
                <span className={`font-medium text-white/70 ${compact ? "text-xs" : "text-sm"}`}>
                  {stamps === 1 ? "sello" : "sellos"}
                </span>
              </p>
            </div>
            {maxReward > 0 && (
              <p className="pb-1 text-right text-[11px] leading-snug text-white/70">
                <span className="block font-semibold text-white/90">
                  {Math.min(stamps, maxReward)} / {maxReward}
                </span>
                hasta la última recompensa
              </p>
            )}
          </div>

          <div className={compact ? "mt-3" : "mt-4"}>
            <StampRow slots={slots} filled={filled} compact={compact} variant="dark" />
          </div>
        </div>

        {/* Próxima recompensa o titular */}
        <div className="mt-auto">
          <div className="rule-dots mb-3 text-white" />
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/55">
                {reward ? "Próxima recompensa" : "Recompensas"}
              </p>
              <p className={`truncate font-semibold text-white ${compact ? "text-xs" : "text-sm"}`}>
                {reward
                  ? `${reward.name} · faltan ${remaining}`
                  : rewards.length
                    ? "Todas las recompensas disponibles"
                    : "Define recompensas en tu programa"}
              </p>
            </div>
            <div className="min-w-0 text-right">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/55">
                Titular
              </p>
              <p className={`truncate font-medium text-white/90 ${compact ? "text-xs" : "text-sm"}`}>
                {holderName?.trim() || "Cliente del programa"}
              </p>
            </div>
          </div>
        </div>

        {children}
      </div>
    </article>
  );
}
