/** Componentes base del sistema visual: cálidos, claros y accesibles. */
import Link from "next/link";
import type { ReactNode } from "react";

import { CountUp } from "@/components/ui/count-up";
import {
  BrandMark,
  IconAlert,
  IconCheck,
  IconInfo,
} from "@/components/ui/icons";
import { shade } from "@/lib/ui";

/* ------------------------------------------------------------------ marca */

export function BrandLogo({
  compact = false,
  tone = "default",
}: {
  compact?: boolean;
  tone?: "default" | "inverse";
}) {
  const inverse = tone === "inverse";
  return (
    <span className="inline-flex items-center gap-2.5">
      <BrandMark size={compact ? 28 : 34} />
      <span className="leading-tight">
        <span
          className={`block text-[13px] font-bold tracking-tight ${inverse ? "text-white" : "text-ink"}`}
        >
          LocalAI Fidelity
        </span>
        {!compact && (
          <span className={`block text-[11px] ${inverse ? "text-white/65" : "text-ink-faint"}`}>
            Fidelización y reseñas
          </span>
        )}
      </span>
    </span>
  );
}

/* ---------------------------------------------------------------- botones */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "dark" | "warm";
type ButtonSize = "sm" | "md" | "lg";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand text-white shadow-[0_1px_2px_rgb(28_25_41/0.22),0_10px_24px_-10px_rgb(91_72_214/0.7)] hover:bg-brand-strong hover:shadow-[0_2px_6px_rgb(28_25_41/0.24),0_16px_32px_-12px_rgb(91_72_214/0.75)] active:translate-y-px disabled:bg-brand/45 disabled:shadow-none",
  secondary:
    "border border-line-strong bg-surface text-ink shadow-[var(--shadow-inset),0_1px_2px_rgb(62_47_30/0.05)] hover:border-brand/40 hover:text-brand active:translate-y-px",
  ghost: "text-ink-soft hover:bg-surface-2 hover:text-ink",
  danger: "border border-danger/25 bg-danger-soft text-danger hover:bg-danger/15",
  dark: "bg-nav text-white hover:bg-nav-2 active:translate-y-px",
  warm: "bg-gold-bright text-[#4a3208] shadow-[0_1px_2px_rgb(74_50_8/0.2),0_10px_24px_-10px_rgb(247_189_75/0.8)] hover:bg-[#ffca63] active:translate-y-px",
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm gap-1.5",
  md: "h-11 px-4 text-sm gap-2",
  lg: "h-12 px-5 text-[15px] gap-2",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  children: ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center whitespace-nowrap rounded-xl font-semibold transition-[background-color,border-color,box-shadow,transform,color] duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-60 ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  variant = "primary",
  size = "md",
  icon,
  children,
  className = "",
  external = false,
  ariaLabel,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  external?: boolean;
  ariaLabel?: string;
}) {
  const classes = `inline-flex items-center justify-center whitespace-nowrap rounded-xl font-semibold transition-[background-color,border-color,box-shadow,transform,color] duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`;
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className={classes}
        aria-label={ariaLabel}
      >
        {icon}
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={classes} aria-label={ariaLabel}>
      {icon}
      {children}
    </Link>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block size-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      role="status"
      aria-label="Cargando"
    />
  );
}

/* ------------------------------------------------------------- superficies */

export type PanelTone = "surface" | "muted" | "warm" | "brand" | "ink";

const PANEL_TONES: Record<PanelTone, string> = {
  surface: "border-line bg-surface shadow-soft",
  muted: "border-line bg-paper shadow-soft",
  warm: "border-sand-strong bg-sand shadow-soft",
  brand: "border-brand/20 bg-brand-soft shadow-soft",
  ink: "border-white/10 bg-nav text-white shadow-lift",
};

export function Panel({
  children,
  className = "",
  padded = true,
  tone = "surface",
  as: Element = "section",
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
  tone?: PanelTone;
  as?: "section" | "div" | "article" | "aside";
}) {
  return (
    <Element
      className={`rounded-2xl border ${PANEL_TONES[tone]} ${padded ? "p-5 sm:p-6" : ""} ${className}`}
    >
      {children}
    </Element>
  );
}

/** Bloque de marca con malla cálida: héroes, cabeceras de tarjeta. */
export function BrandPanel({
  children,
  className = "",
  tone = "brand",
}: {
  children: ReactNode;
  className?: string;
  tone?: "brand" | "ink";
}) {
  return (
    <section
      className={`grain relative overflow-hidden rounded-3xl text-white shadow-lift ${
        tone === "brand" ? "mesh-brand" : "mesh-ink"
      } ${className}`}
    >
      <div aria-hidden="true" className="animate-drift absolute inset-0 opacity-70">
        <div className="absolute -right-24 -top-28 size-80 rounded-full bg-white/[0.07]" />
        <div className="absolute -bottom-40 -left-20 size-96 rounded-full bg-white/[0.05]" />
      </div>
      <div className="relative">{children}</div>
    </section>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 space-y-2">
        {eyebrow && (
          <p className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-brand">
            <span aria-hidden="true" className="h-px w-5 bg-brand/50" />
            {eyebrow}
          </p>
        )}
        <h1 className="text-[26px] font-bold leading-[1.15] tracking-[-0.02em] text-ink sm:text-[32px]">
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-sm leading-relaxed text-ink-soft sm:text-[15px]">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function SectionTitle({
  title,
  description,
  action,
  icon,
  eyebrow,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          {eyebrow && (
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-faint">
              {eyebrow}
            </p>
          )}
          <h2 className="text-base font-bold tracking-tight text-ink">{title}</h2>
          {description && (
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink-soft">{description}</p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/* --------------------------------------------------------------- etiquetas */

export type Tone = "neutral" | "brand" | "ok" | "warn" | "danger" | "info" | "gold" | "teal";

const TONES: Record<Tone, string> = {
  neutral: "bg-surface-2 text-ink-soft ring-line-strong",
  brand: "bg-brand-soft text-brand ring-brand/20",
  ok: "bg-ok-soft text-ok ring-ok/20",
  warn: "bg-warn-soft text-warn ring-warn/20",
  danger: "bg-danger-soft text-danger ring-danger/20",
  info: "bg-info-soft text-info ring-info/20",
  gold: "bg-gold-soft text-warn ring-warn/20",
  teal: "bg-teal-soft text-teal ring-teal/20",
};

export function Badge({
  tone = "neutral",
  icon,
  children,
  className = "",
}: {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${TONES[tone]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}

/** Píldora de estado: el estado SIEMPRE va con palabra, nunca solo color. */
export function StatusPill({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return (
    <Badge tone={tone} icon={<span className="size-1.5 rounded-full bg-current" />}>
      {children}
    </Badge>
  );
}

/* ------------------------------------------------------------------ avisos */

const ALERT_TONES: Record<NonNullable<Tone>, string> = {
  ...TONES,
  neutral: "bg-surface-2 text-ink-soft ring-line-strong",
};

export function Alert({
  tone = "info",
  title,
  children,
  actions,
}: {
  tone?: "info" | "ok" | "warn" | "danger" | "brand";
  title?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  const icon =
    tone === "danger" ? (
      <IconAlert size={18} />
    ) : tone === "ok" || tone === "brand" ? (
      <IconCheck size={18} />
    ) : (
      <IconInfo size={18} />
    );
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      aria-live={tone === "danger" ? "assertive" : "polite"}
      className={`flex items-start gap-3 rounded-xl p-4 text-sm ring-1 ring-inset ${ALERT_TONES[tone]}`}
    >
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "mt-0.5 leading-relaxed" : "leading-relaxed"}>{children}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ------------------------------------------------- estados de cada pantalla */

export function LoadingState({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <p className="flex items-center gap-2 text-sm text-ink-faint">
        <Spinner className="text-brand" />
        {label}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-28 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

/** Variantes de ilustración de estado vacío: SVG propio, sin imágenes. */
function EmptyIllustration({ kind }: { kind: "card" | "scan" | "users" | "star" | "tag" }) {
  const common = "h-20 w-24";
  if (kind === "scan") {
    return (
      <svg viewBox="0 0 96 80" className={common} fill="none" aria-hidden="true">
        <rect x="18" y="12" width="60" height="56" rx="12" fill="#eeebfd" />
        <path d="M32 30v-6a4 4 0 0 1 4-4h6M64 30v-6a4 4 0 0 0-4-4h-6M32 50v6a4 4 0 0 0 4 4h6M64 50v6a4 4 0 0 1-4 4h-6" stroke="#5b48d6" strokeWidth="2.4" strokeLinecap="round" />
        <path d="M32 40h32" stroke="#5b48d6" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="70" cy="52" r="10" fill="#f7bd4b" />
        <path d="m66 52 2.6 2.6L74 49.5" stroke="#4a3208" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (kind === "users") {
    return (
      <svg viewBox="0 0 96 80" className={common} fill="none" aria-hidden="true">
        <circle cx="38" cy="30" r="11" fill="#eeebfd" stroke="#5b48d6" strokeWidth="2.2" />
        <path d="M19 62c2-10 9-15 19-15s17 5 19 15" stroke="#5b48d6" strokeWidth="2.2" strokeLinecap="round" />
        <circle cx="65" cy="35" r="8" fill="#fdeee1" stroke="#c25e22" strokeWidth="2" />
        <path d="M56 60c1.4-7 5.5-11 11-11 4 0 7 1.6 9 5" stroke="#c25e22" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  if (kind === "star") {
    return (
      <svg viewBox="0 0 96 80" className={common} fill="none" aria-hidden="true">
        <path d="M48 14l6.5 13.4L69 29.5 59 39.3l2.4 14.2L48 46.8l-13.4 6.7L37 39.3 27 29.5l14.5-2.1z" fill="#fdf2d7" stroke="#a56a12" strokeWidth="2.2" strokeLinejoin="round" />
        <path d="M24 58h48" stroke="#d7cdbd" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
    );
  }
  if (kind === "tag") {
    return (
      <svg viewBox="0 0 96 80" className={common} fill="none" aria-hidden="true">
        <path d="M51 14h20a8 8 0 0 1 8 8v20a6 6 0 0 1-1.7 4.2L55 68.4a6 6 0 0 1-8.5 0L25.6 47.5a6 6 0 0 1 0-8.5l20.2-23.3A6 6 0 0 1 51 14z" fill="#ddf5f0" stroke="#0e8a78" strokeWidth="2.2" />
        <circle cx="66" cy="29" r="5" fill="#0e8a78" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 96 80" className={common} fill="none" aria-hidden="true">
      <rect x="12" y="22" width="64" height="42" rx="10" fill="#eeebfd" stroke="#5b48d6" strokeWidth="2.2" />
      <path d="M12 34h64" stroke="#5b48d6" strokeWidth="2.2" />
      <circle cx="67" cy="51" r="3.4" fill="#f7bd4b" />
      <path d="M23 27h14" stroke="#8b7cf6" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  illustration,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  illustration?: "card" | "scan" | "users" | "star" | "tag";
}) {
  return (
    <div className="animate-in relative overflow-hidden rounded-3xl border border-dashed border-line-strong bg-paper/80 px-6 py-10 text-center">
      <div className="relative mx-auto flex w-fit items-center justify-center">
        {icon ? (
          <span className="flex size-16 items-center justify-center rounded-2xl bg-brand-soft text-brand">
            {icon}
          </span>
        ) : (
          <EmptyIllustration kind={illustration ?? "card"} />
        )}
      </div>
      <h3 className="mt-4 text-base font-bold tracking-tight text-ink">{title}</h3>
      {description && (
        <p className="mx-auto mt-1.5 max-w-md text-sm leading-relaxed text-ink-soft">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Alert tone="danger" title="No se pudo completar la operación">
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 font-semibold text-danger underline underline-offset-2"
        >
          Volver a intentar
        </button>
      )}
    </Alert>
  );
}

/* ------------------------------------------------------- tarjetas de datos */

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "brand",
}: {
  label: string;
  value: number | string;
  hint?: string;
  icon?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface p-4 shadow-soft transition-[border-color,box-shadow,transform] duration-300 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-lift">
      {/* Filo de color: identifica la métrica sin llenar la tarjeta de color. */}
      <span
        aria-hidden="true"
        className={`absolute inset-x-0 top-0 h-[3px] rounded-t-2xl ${
          tone === "brand"
            ? "bg-brand/60"
            : tone === "info"
              ? "bg-info/60"
              : tone === "gold"
                ? "bg-gold-bright"
                : tone === "teal"
                  ? "bg-teal/60"
                  : tone === "warn"
                    ? "bg-warn/60"
                    : "bg-line-strong"
        }`}
      />
      <div className="flex items-start justify-between gap-2">
        <p className="min-h-9 text-[12px] font-semibold uppercase leading-snug tracking-[0.06em] text-ink-faint">
          {label}
        </p>
        {icon && (
          <span className={`flex size-9 items-center justify-center rounded-xl ${TONES[tone]}`}>
            {icon}
          </span>
        )}
      </div>
      <p className="tnum mt-auto pt-2 text-[32px] font-bold leading-none tracking-tight text-ink">
        {typeof value === "number" ? <CountUp value={value} /> : value}
      </p>
      {hint && <p className="mt-2 text-[11px] leading-snug text-ink-faint">{hint}</p>}
    </div>
  );
}

/** Fila de sellos derivada SIEMPRE de datos reales: nada inventado.
 *
 *  Con `animated`, los sellos ya puestos se estampan uno a uno al entrar
 *  (portada): un `seal-pop` desplazado por sello. Estático en el resto de
 *  usos y anulado por `prefers-reduced-motion` (regla global).
 */
export function StampRow({
  slots,
  filled,
  compact = false,
  variant = "light",
  animated = false,
  animateFrom = null,
  accentColor = null,
  icon = null,
}: {
  slots: number;
  filled: number;
  compact?: boolean;
  variant?: "light" | "dark";
  animated?: boolean;
  /**
   * Índice desde el que los sellos recién ganados se estampan con animación
   * (tarjeta del cliente: solo los nuevos, no toda la fila).
   */
  animateFrom?: number | null;
  /**
   * Color de acento del comercio (decisión #8): sustituye al dorado por
   * defecto en los sellos puestos. Nulo = aspecto clásico.
   */
  accentColor?: string | null;
  /** Icono del sello del comercio: cup | heart | star | leaf | spark. */
  icon?: string | null;
}) {
  const size = compact ? "size-5" : "size-8";
  const empty =
    variant === "dark"
      ? "border-white/35 bg-white/[0.08] shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]"
      : "border-line-strong bg-surface-2 shadow-[inset_0_1px_2px_rgb(62_47_30/0.06)]";
  // Filas equilibradas de como mucho 5 sellos (10 → 5+5, 8 → 4+4, 7 → 4+3).
  const columns =
    slots <= 5 ? Math.max(slots, 1) : Math.ceil(slots / Math.ceil(slots / 5));
  const filledStyle = accentColor
    ? {
        background: `linear-gradient(145deg, ${shade(accentColor, 26)}, ${accentColor} 55%, ${shade(accentColor, -14)})`,
        borderColor: shade(accentColor, -32),
        boxShadow: `inset 0 1px 0 rgb(255 255 255 / 0.6), inset 0 -2px 3px ${shade(accentColor, -45)}, 0 2px 5px rgb(74 50 8 / 0.18)`,
      }
    : undefined;
  /** Aspecto clásico dorado cuando el comercio no ha definido acento. */
  const filledClass =
    "animate-seal border-[#d99a1f] bg-[linear-gradient(145deg,#ffd985,#f7bd4b_55%,#eaa32a)] shadow-[inset_0_1px_0_rgb(255_255_255/0.75),inset_0_-2px_3px_rgb(122_76_0/0.28),0_2px_5px_rgb(74_50_8/0.18)]";
  const glyphColor = accentColor ? shade(accentColor, -62) : "#6b4500";
  return (
    <div
      className="grid justify-start gap-1.5"
      style={{ gridTemplateColumns: `repeat(${columns}, auto)` }}
      aria-hidden="true"
    >
      {Array.from({ length: slots }, (_, index) => {
        const on = index < filled;
        // Recién ganado: estampado con retardo corto y escalonado.
        const fresh = animateFrom !== null && on && index >= animateFrom;
        const delay = fresh ? `${(index - (animateFrom ?? 0)) * 140}ms` : animated && on ? `${640 + index * 90}ms` : undefined;
        return (
          <span
            key={index}
            style={delay ? { animationDelay: delay, ...(on ? filledStyle : undefined) } : on ? filledStyle : undefined}
            className={`${size} relative flex items-center justify-center rounded-full border-2 transition-colors ${
              on
                ? accentColor
                  ? "animate-seal"
                  : filledClass
                : empty
            }`}
          >

            {on && (
              <svg viewBox="0 0 12 12" className="size-3.5" fill="none" style={{ color: glyphColor }}>
                <path
                  d={STAMP_GLYPHS[icon && icon in STAMP_GLYPHS ? icon : "check"]}
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </span>
        );
      })}
    </div>
  );
}

/** Glifos de sello del catálogo de diseño (decisión #8). Trazo de 12×12. */
const STAMP_GLYPHS: Record<string, string> = {
  check: "m2.5 6.2 2.3 2.3 4.7-4.8",
  cup: "M3 4.5h5.5v2.7a2.75 2.75 0 0 1-5.5 0Z M8.5 5.2h.8a1.3 1.3 0 0 1 0 2.6h-.8 M2.5 10.5h6.5",
  heart: "M6 10C6 10 2 7.6 2 4.9 2 3.3 3.3 2.4 4.4 2.4c.8 0 1.4.5 1.6 1.1.2-.6.8-1.1 1.6-1.1 1.1 0 2.4.9 2.4 2.5C10 7.6 6 10 6 10Z",
  star: "M6 2l1.2 2.4 2.6.4-1.9 1.9.4 2.6L6 8.1 3.7 9.3l.4-2.6L2.2 4.8l2.6-.4L6 2Z",
  leaf: "M9.5 2.5C5 3 2.5 5.5 2.5 9.5c4 0 6.5-2.5 7-7Z M3.5 8.5C5 6.5 6.5 5 8.5 3.5",
  spark: "M6 1.5 7 5l3.5 1L7 7l-1 3.5L5 7 1.5 6 5 5 6 1.5Z",
};
