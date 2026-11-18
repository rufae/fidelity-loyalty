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
import { shade, stampSlots } from "@/lib/ui";
import type { CardBranding } from "@/lib/fidelity";

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
  animateStamps = false,
  stampAnimateFrom = null,
  className = "",
  stampsTestId,
  children,
  branding = null,
  programType = null,
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
  /** Estampado escalonado de los sellos al entrar; solo portada. */
  animateStamps?: boolean;
  /** Índice desde el que los sellos nuevos se estampan (tarjeta real). */
  stampAnimateFrom?: number | null;
  className?: string;
  children?: ReactNode;
  /** Diseño del comercio (decisión #8): colores, icono, logo y pie.
      Sin branding usa el aspecto clásico dorado. */
  branding?: CardBranding | null;
  /** Tipo de programa (§7.1): rota la etiqueta entre «sellos» y «puntos». */
  programType?: string | null;
}) {
  const { reward, remaining } = nextReward(stamps, rewards);
  const { slots, filled } = stampSlots(stamps, reward?.stamps_required ?? null);
  const compact = variant === "preview";
  const hero = variant === "hero";
  const maxReward = rewards.reduce((max, item) => Math.max(max, item.stamps_required), 0);
  const isPoints = programType === "points";

  const accent = branding?.accent_color ?? null;
  const hasBranding = branding !== null;

  return (
    <article
      aria-label={`Tarjeta de fidelización de ${merchantName}`}
      className={`grain relative isolate overflow-hidden rounded-[26px] text-white shadow-lift ${
        floating ? "animate-float" : ""
      } ${hero ? "min-h-[360px]" : ""} ${className}`}
      style={
        hasBranding
          ? {
              background: `linear-gradient(150deg, ${branding.primary_color} 0%, ${shade(branding.primary_color, -24)} 100%)`,
            }
          : undefined
      }
    >
      {!hasBranding && <div className="mesh-brand absolute inset-0" aria-hidden="true" />}
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
            {hasBranding && branding.logo_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={branding.logo_url}
                alt=""
                aria-hidden="true"
                className={`shrink-0 rounded-xl border border-white/25 bg-white/15 object-contain backdrop-blur-sm ${
                  compact ? "size-8 p-1" : "size-10 p-1.5"
                }`}
              />
            ) : (
              <span
                aria-hidden="true"
                className={`flex shrink-0 items-center justify-center rounded-xl border border-white/25 bg-white/15 font-bold tracking-tight text-white backdrop-blur-sm ${
                  compact ? "size-8 text-[11px]" : "size-10 text-sm"
                }`}
              >
                {initials(merchantName)}
              </span>
            )}
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
            <span
              className="shrink-0 rounded-full border bg-white/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] backdrop-blur-sm"
              style={
                accent
                  ? { borderColor: shade(accent, 10), color: shade(accent, 35) }
                  : { borderColor: "rgb(255 255 255 / 0.2)", color: "rgb(255 255 255 / 0.85)" }
              }
            >
              {isPoints ? "Tarjeta de puntos" : "Tarjeta de sellos"}
            </span>
          )}
        </div>

        {/* Saldo real */}
        <div className="mt-auto">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/65">
                {isPoints ? "Puntos acumulados" : "Sellos acumulados"}
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
                  {isPoints
                    ? stamps === 1
                      ? "punto"
                      : "puntos"
                    : stamps === 1
                      ? "sello"
                      : "sellos"}
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
            <StampRow
              slots={slots}
              filled={filled}
              compact={compact}
              variant="dark"
              animated={animateStamps}
              animateFrom={stampAnimateFrom}
              accentColor={accent}
              icon={branding?.stamp_icon ?? null}
            />
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

        {branding?.footer_text?.trim() ? (
          <p className="border-t border-white/15 pt-2.5 text-center text-[10px] leading-snug text-white/70">
            {branding.footer_text}
          </p>
        ) : null}

        {children}
      </div>
    </article>
  );
}
