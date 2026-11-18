"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Alert,
  BrandPanel,
  Button,
  ErrorState,
  IconAlert,
  IconArrowRight,
  IconCheck,
  IconContactless,
  IconDownload,
  IconExternal,
  IconGift,
  IconScan,
  IconSparkles,
  IconUsers,
  IconWallet,
  LinkButton,
  LoadingState,
  Panel,
  SectionTitle,
  StatCard,
} from "@/components/ui";
import { useMerchant } from "@/components/merchant-context";
import { ApiError } from "@/lib/api";
import {
  fidelity,
  type DashboardOnboarding,
  type DashboardSummary,
  type DashboardToday,
  type LoyaltySeries,
  type WalletJob,
} from "@/lib/fidelity";
import { ArtSparkles } from "@/components/ui/art";
import { canManageMerchant } from "@/lib/session";
import { formatDate, formatNumber } from "@/lib/ui";

/**
 * Resumen real del comercio: todas las cifras vienen de la base de datos.
 * La jerarquía importa: primero la comunidad de clientes, después el detalle
 * operativo. Nada de ocho tarjetas blancas idénticas.
 */
/** Checkpoint de puesta en marcha (mejora de onboarding, §13.2).

 Cuatro puertas hasta el primer sello; cada una enlaza a la pantalla que
    la resuelve. El panel se oculta solo en cuanto `completed` es verdadero:
    un comercio en marcha no quiere un checklist mirándole. */
const ONBOARDING_STEPS: {
  key: "program_ready" | "store_ready" | "qr_ready" | "first_member";
  title: string;
  description: string;
  action: string;
  href: string;
}[] = [
  {
    key: "program_ready",
    title: "Publica tu programa",
    description: "Un programa activo con al menos una recompensa para canjear.",
    action: "Programas",
    href: "/programs",
  },
  {
    key: "store_ready",
    title: "Registra tu tienda",
    description: "Da de alta el local del comercio (para el servicio por ubicación).",
    action: "Tiendas",
    href: "/stores",
  },
  {
    key: "qr_ready",
    title: "Prepara el QR de alta",
    description: "Una etiqueta NFC/QR en el mostrador para que el cliente se dé de alta.",
    action: "NFC y QR",
    href: "/nfc",
  },
  {
    key: "first_member",
    title: "Da de alta al primer cliente",
    description: "Escanea el QR o pásalo por el mostrador: ya tendrá su tarjeta.",
    action: "Clientes",
    href: "/members",
  },
];
/** Gráfica de tendencia (§13.2): operaciones diarias del comercio.
 *
 * SVG puro sin dependencias: una línea por tipo de movimiento (sellos dados
 * en brand, canjes en gold) sobre los días del periodo, huecos incluidos a
 * cero para que la forma sea honesta. `prefers-reduced-motion` no la anima:
 * entra estática con el resto del panel.
 */
const TREND_PERIODS = [
  { days: 7, label: "7 días" },
  { days: 30, label: "30 días" },
  { days: 90, label: "90 días" },
] as const;

function TrendChart({ merchantId }: { merchantId: string }) {
  const [period, setPeriod] = useState<7 | 30 | 90>(30);
  const [series, setSeries] = useState<LoyaltySeries | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fidelity
      .dashboardLoyalty(merchantId, period)
      .then((data) => {
        if (!cancelled) {
          setSeries(data);
          setError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId, period]);

  // Días completos del periodo (UTC, igual que los guarda el ledger), con
  // huecos a cero: la gráfica no inventa picos donde solo faltan datos.
  const byDayEarn = new Map<string, number>();
  const byDayRedeem = new Map<string, number>();
  if (series) {
    for (const point of series.series) {
      if (point.transaction_type === "earn") byDayEarn.set(point.day, point.count);
      else if (point.transaction_type === "redeem") byDayRedeem.set(point.day, point.count);
    }
  }
  const days: { day: string; earn: number; redeem: number }[] = [];
  const today = new Date();
  for (let i = period - 1; i >= 0; i -= 1) {
    const d = new Date(today.getTime() - i * 86_400_000);
    const key = d.toISOString().slice(0, 10);
    days.push({ day: key, earn: byDayEarn.get(key) ?? 0, redeem: byDayRedeem.get(key) ?? 0 });
  }
  const totalEarn = days.reduce((acc, d) => acc + d.earn, 0);
  const totalRedeem = days.reduce((acc, d) => acc + d.redeem, 0);
  const max = Math.max(1, ...days.map((d) => d.earn));

  const W = 640;
  const H = 170;
  const PAD_L = 6;
  const PAD_B = 4;
  const stepX = (W - PAD_L * 2) / Math.max(1, days.length - 1);
  const x = (i: number) => PAD_L + i * stepX;
  const y = (v: number) => H - PAD_B - (v / max) * (H - 18);
  const line = (key: "earn" | "redeem") =>
    days.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(" ");
  const area = `${line("earn")} L${x(days.length - 1).toFixed(1)},${H - PAD_B} L${PAD_L},${H - PAD_B} Z`;

  return (
    <Panel className="animate-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
            Movimientos del programa
          </p>
          <p className="mt-1 text-sm text-ink-soft">
            Sellos dados y canjes por día · cifras del ledger
          </p>
        </div>
        <div
          className="flex rounded-xl border border-line bg-surface-2 p-0.5"
          role="group"
          aria-label="Periodo de la gráfica"
        >
          {TREND_PERIODS.map((option) => (
            <button
              key={option.days}
              type="button"
              onClick={() => setPeriod(option.days)}
              aria-pressed={period === option.days}
              className={`min-h-8 rounded-[10px] px-3 text-xs font-bold transition-colors ${
                period === option.days
                  ? "bg-surface text-ink shadow-soft"
                  : "text-ink-faint hover:text-ink"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-5">
        <span className="flex items-center gap-2 text-xs font-semibold text-ink">
          <span aria-hidden="true" className="h-0.5 w-4 rounded-full bg-brand" />
          Sellos dados <span className="tnum text-ink-soft">{formatNumber(totalEarn)}</span>
        </span>
        <span className="flex items-center gap-2 text-xs font-semibold text-ink">
          <span aria-hidden="true" className="h-0.5 w-4 rounded-full bg-gold-bright" />
          Canjes <span className="tnum text-ink-soft">{formatNumber(totalRedeem)}</span>
        </span>
      </div>

      {error ? (
        <p className="mt-5 rounded-xl border border-warn/30 bg-gold-soft px-4 py-2.5 text-xs text-warn">
          No se pudo cargar la gráfica. El resto de cifras sigue disponible.
        </p>
      ) : !series ? (
        <div className="mt-5 h-[170px] animate-pulse rounded-xl bg-surface-2" aria-hidden />
      ) : (
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Operaciones de los últimos ${period} días: ${formatNumber(totalEarn)} sellos dados y ${formatNumber(totalRedeem)} canjes.`}
          className="mt-4 h-auto w-full"
        >
          {[0.25, 0.5, 0.75].map((fraction) => (
            <line
              key={fraction}
              x1={PAD_L}
              x2={W - PAD_L}
              y1={y(max * fraction)}
              y2={y(max * fraction)}
              stroke="currentColor"
              className="text-line"
              strokeDasharray="3 5"
              strokeWidth="1"
            />
          ))}
          <path d={area} fill="var(--color-brand)" opacity="0.09" />
          <path
            d={line("earn")}
            fill="none"
            stroke="var(--color-brand)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={line("redeem")}
            fill="none"
            stroke="var(--color-gold-bright)"
            strokeWidth="2"
            strokeDasharray="1 0"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
      <p className="mt-3 text-[11px] text-ink-faint">
        {days.length > 0 && (
          <>
            Del {formatDate(days[0].day)} al {formatDate(days[days.length - 1].day)} · los días sin
            operaciones aparecen en cero.
          </>
        )}
      </p>
    </Panel>
  );
}

export function MerchantDashboard() {
  const { merchantId, merchantName, role, isPlatformAdmin: platformAdmin } = useMerchant();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  /** Cierre de turno: lo que ha pasado HOY (zona horaria del comercio). */
  const [today, setToday] = useState<DashboardToday | null>(null);
  /** Checklist de puesta en marcha: se oculta al completarse. */
  const [onboarding, setOnboarding] = useState<DashboardOnboarding | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** Distingue la primera carga (puede mostrar error) del sondeo posterior. */
  const summaryLoaded = useRef(false);

  const load = useCallback(() => {
    let cancelled = false;
    const fetchSummary = async (): Promise<void> => {
      try {
        const [data, todayData, onboardingData] = await Promise.all([
          fidelity.dashboard(merchantId),
          fidelity.dashboardToday(merchantId),
          fidelity.dashboardOnboarding(merchantId),
        ]);
        if (cancelled) return;
        setSummary(data);
        setToday(todayData);
        setOnboarding(onboardingData);
        setError(null);
      } catch {
        // En sondeo periódico no se desmonta el resumen por un fallo de red:
        // se conserva lo último y el siguiente ciclo reintenta.
        if (!cancelled && !summaryLoaded.current) {
          setError("No se pudo cargar el resumen del comercio.");
        }
      }
    };
    void fetchSummary();
    // Panel en pantalla durante el servicio: las métricas envejecen si no
    // se refrescan (mismo patrón que Clientes). Solo con pestaña visible.
    summaryLoaded.current = true;
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void fetchSummary();
    }, 30_000);
    const onVisibility = (): void => {
      if (document.visibilityState === "visible") void fetchSummary();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  // La exportación contiene datos de contacto: solo para quien gestiona.
  const canManage = platformAdmin || (role !== null && canManageMerchant(role));
  const canExport = canManage;

  if (error && !summary) {
    return <ErrorState message={error} onRetry={() => load()} />;
  }
  if (!summary) {
    return <LoadingState label="Cargando los indicadores reales…" />;
  }

  const activeShare =
    summary.members_total > 0
      ? Math.round((summary.memberships_active / summary.members_total) * 100)
      : 0;

  const secondary = [
    {
      label: "Sellos canjeados",
      value: summary.stamps_redeemed,
      icon: <IconScan size={16} />,
      hint: "sellos gastados en premios",
      attention: false,
    },
    {
      label: "Pases Wallet",
      value: summary.wallet_passes,
      icon: <IconWallet size={16} />,
      hint: "Wallet no está disponible de momento",
      attention: false,
    },
    {
      label: "Errores de Wallet",
      value: summary.wallet_errors,
      icon: <IconAlert size={16} />,
      hint: "trabajos pendientes de reintentar",
      attention: summary.wallet_errors > 0,
    },
    {
      label: "Clics en el enlace de reseñas",
      value: summary.review_link_clicks,
      icon: <IconExternal size={16} />,
      hint: "visitas al enlace, no reseñas publicadas",
      attention: false,
    },
  ];

  return (
    <div className="stagger space-y-7">
      {/* Bienvenida con una acción útil de verdad: operar en el mostrador. */}
      <BrandPanel className="animate-in p-6 sm:p-8" tone="brand">
        <ArtSparkles className="animate-twinkle pointer-events-none absolute right-6 top-5 hidden h-12 w-12 opacity-70 md:block" />
        <div className="grid grid-cols-1 items-center gap-7 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-white/65">
              Resumen
            </p>
            <h2 className="mt-3 text-[28px] font-bold leading-[1.1] tracking-[-0.02em] text-balance sm:text-[34px]">
              {merchantName}
            </h2>
            <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-white/80 sm:text-[15px]">
              Configura el programa, opera en el mostrador y prepara las etiquetas de tu
              establecimiento.
            </p>
            <span className="mt-3 inline-block rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-[11px] font-semibold text-white/90">
              Cifras reales de tu base de datos
            </span>
            <div className="mt-6 flex flex-wrap gap-2.5">
              <LinkButton
                href={`/merchants/${merchantId}/operations`}
                variant="secondary"
                size="lg"
                icon={<IconScan size={18} />}
                className="border-transparent bg-white text-brand hover:bg-white"
              >
                Registrar en mostrador
              </LinkButton>
              <LinkButton
                href={`/merchants/${merchantId}/nfc`}
                variant="secondary"
                size="lg"
                icon={<IconContactless size={18} />}
                className="border-white/25 bg-white/10 text-white hover:bg-white/20"
              >
                Etiquetas NFC y QR
              </LinkButton>
            </div>
          </div>

          {/* Acceso rápido al mostrador: el gesto más frecuente del día. */}
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-sm sm:p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/60">
              En el mostrador
            </p>
            <p className="mt-1.5 text-lg font-bold leading-tight">Un cliente enseña su QR</p>
            <p className="mt-1 text-[13px] leading-relaxed text-white/70">
              Busca su tarjeta, suma un sello o canjea una recompensa. El saldo lo confirma el
              servidor al instante.
            </p>
            <Link
              href={`/merchants/${merchantId}/operations`}
              className="mt-4 flex h-11 items-center justify-between gap-2 rounded-xl bg-white px-3.5 text-sm font-bold text-brand transition-transform hover:-translate-y-0.5"
            >
              Abrir operaciones
              <IconArrowRight size={17} />
            </Link>
          </div>
        </div>
      </BrandPanel>

      {/* Puesta en marcha (mejora de onboarding, §13.2): cuatro puertas
          hasta el primer sello; se oculta en cuanto están todas cerradas
          para no estorbar a un comercio ya en marcha. */}
      {onboarding && !onboarding.completed && (
        <Panel className="animate-in">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Puesta en marcha
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                {ONBOARDING_STEPS.filter((step) => onboarding[step.key]).length} de{" "}
                {ONBOARDING_STEPS.length} listos · del programa al primer cliente
              </p>
            </div>
            <span className="rounded-full bg-gold-soft px-2.5 py-1 text-[11px] font-bold text-warn">
              {ONBOARDING_STEPS.filter((step) => onboarding[step.key]).length}/
              {ONBOARDING_STEPS.length}
            </span>
          </div>
          <ol className="mt-4 space-y-2">
            {ONBOARDING_STEPS.map((step, index) => {
              const done = onboarding[step.key];
              return (
                <li
                  key={step.key}
                  className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 ${
                    done ? "border-ok/40 bg-ok-soft/40" : "border-line bg-paper"
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      aria-hidden="true"
                      className={`flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        done
                          ? "bg-ok-soft text-ok"
                          : "border border-line-strong bg-surface text-ink-faint"
                      }`}
                    >
                      {done ? <IconCheck size={15} /> : index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink">
                        {step.title}
                        {done && <span className="sr-only"> (hecho)</span>}
                      </p>
                      {!done && (
                        <p className="mt-0.5 text-xs leading-relaxed text-ink-faint">
                          {step.description}
                        </p>
                      )}
                    </div>
                  </div>
                  {!done && (
                    <LinkButton
                      href={`/merchants/${merchantId}${step.href}`}
                      size="sm"
                      variant="secondary"
                      icon={<IconArrowRight size={15} />}
                    >
                      {step.action}
                    </LinkButton>
                  )}
                </li>
              );
            })}
          </ol>
        </Panel>
      )}

      {/* Cierre de turno (§13.2): lo que ha pasado HOY, en la zona horaria
          del comercio. Cifras del día, siempre desde la base de datos. */}
      {today && (
        <Panel className="animate-in">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Hoy en el local
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                Cierre del día {today.local_date} · hora local del comercio
              </p>
            </div>
            <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-bold text-brand">
              turno de hoy
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-line bg-paper px-4 py-3">
              <dt className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Altas
              </dt>
              <dd className="tnum mt-1 text-2xl font-bold text-ink">
                {formatNumber(today.enrolled_today)}
              </dd>
            </div>
            <div className="rounded-xl border border-line bg-paper px-4 py-3">
              <dt className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Sellos dados
              </dt>
              <dd className="tnum mt-1 text-2xl font-bold text-ink">
                {formatNumber(today.stamps_today)}
              </dd>
            </div>
            <div className="rounded-xl border border-line bg-paper px-4 py-3">
              <dt className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Sellos canjeados
              </dt>
              <dd className="tnum mt-1 text-2xl font-bold text-ink">
                {formatNumber(today.redeemed_stamps_today)}
              </dd>
            </div>
            <div className="rounded-xl border border-line bg-paper px-4 py-3">
              <dt className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                Recompensas servidas
              </dt>
              <dd className="tnum mt-1 text-2xl font-bold text-ink">
                {formatNumber(today.redemptions_today)}
              </dd>
            </div>
          </dl>
        </Panel>
      )}

      {/* Tendencia (§13.2): la forma de los últimos días, siempre del ledger. */}
      <TrendChart merchantId={merchantId} />

      {/* Comunidad primero; el resto de métricas en segundo plano. */}
      <section aria-label="Indicadores principales" className="space-y-3">
        <SectionTitle
          title="Tu programa de un vistazo"
          description="Clientes, tarjetas y movimientos acumulados de siempre."
          action={
            <Link
              href={`/merchants/${merchantId}/members`}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-semibold text-brand transition-colors hover:bg-brand-soft"
            >
              Ver clientes
              <IconArrowRight size={15} />
            </Link>
          }
        />
        <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Métrica principal: comunidad y proporción de tarjetas activas. */}
          <div className="relative overflow-hidden rounded-2xl border border-brand/15 bg-[linear-gradient(140deg,#f4f1ff_0%,#ffffff_60%)] p-5 shadow-soft sm:col-span-2">
            <span
              aria-hidden="true"
              className="absolute -right-8 -top-10 size-32 rounded-full bg-brand/[0.07]"
            />
            <div className="relative flex items-start justify-between gap-3">
              <div>
                <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-faint">
                  Clientes registrados
                </p>
                <p className="tnum mt-2 text-[40px] font-bold leading-none tracking-[-0.03em] text-ink">
                  {formatNumber(summary.members_total)}
                </p>
              </div>
              <span className="flex size-10 items-center justify-center rounded-xl bg-brand text-white shadow-soft">
                <IconUsers size={19} />
              </span>
            </div>
            <div className="relative mt-5">
              <div className="flex items-baseline justify-between gap-3 text-[12px]">
                <span className="font-semibold text-ink">
                  {formatNumber(summary.memberships_active)} tarjetas activas
                </span>
                <span className="tnum text-ink-faint">
                  {summary.members_total > 0 ? `${activeShare}% del total` : "sin altas todavía"}
                </span>
              </div>
              <div
                role="img"
                aria-label={`${activeShare}% de las tarjetas están activas`}
                className="mt-2 h-2 overflow-hidden rounded-full bg-brand/10"
              >
                <div
                  className="h-full rounded-full bg-brand transition-[width] duration-500"
                  style={{ width: `${activeShare}%` }}
                />
              </div>
              <Link
                href={`/merchants/${merchantId}/members`}
                className="mt-3 inline-flex items-center gap-1 text-[12px] font-semibold text-brand hover:underline"
              >
                Gestionar clientes
                <IconArrowRight size={13} />
              </Link>
            </div>
          </div>

          <StatCard
            label="Sellos concedidos"
            value={summary.stamps_granted}
            hint="acumulados en toda la historia"
            icon={<IconSparkles size={17} />}
            tone="gold"
          />
          <StatCard
            label="Recompensas canjeadas"
            value={summary.redemptions}
            hint="canjes confirmados por el servidor"
            icon={<IconGift size={17} />}
            tone="teal"
          />
        </div>
      </section>

      {/* Detalle operativo sin repetir tarjetas: una lista legible. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.45fr_0.55fr]">
        <Panel className="animate-in">
          <SectionTitle
            title="Detalle operativo"
            description="Sincronización con Wallet, canjes y visitas al enlace de reseñas."
            icon={<IconWallet size={18} />}
          />
          <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            {secondary.map((item) => (
              <div key={item.label} className="flex items-start gap-3">
                <span
                  className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${
                    item.attention ? "bg-warn-soft text-warn" : "bg-surface-2 text-ink-soft"
                  }`}
                >
                  {item.icon}
                </span>
                <div className="min-w-0">
                  <dt className="text-[12px] text-ink-soft">{item.label}</dt>
                  <dd className="tnum mt-0.5 text-xl font-bold leading-none text-ink">
                    {formatNumber(item.value)}
                  </dd>
                  <p
                    className={`mt-1 text-[11px] leading-snug ${
                      item.attention ? "font-semibold text-warn" : "text-ink-faint"
                    }`}
                  >
                    {item.hint}
                  </p>
                </div>
              </div>
            ))}
          </dl>
          <p className="rule-dots my-4 text-ink-faint" />
          <p className="text-[11px] leading-relaxed text-ink-faint">
            Los indicadores se recalculan con los datos reales del comercio. Los clics de reseñas
            cuentan <strong className="font-semibold text-ink-soft">visitas al enlace</strong>:
            nunca reseñas publicadas ni valoraciones.
          </p>
        </Panel>

        <Panel tone="muted" className="animate-in flex flex-col">
          <SectionTitle title="Atajos" icon={<IconArrowRight size={18} />} />
          <nav className="flex flex-col gap-1.5" aria-label="Atajos del panel">
            <Link
              href={`/merchants/${merchantId}/programs`}
              className="flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface"
            >
              <span className="flex items-center gap-2.5">
                <IconGift size={16} className="text-brand" />
                Programa y recompensas
              </span>
              <IconArrowRight size={14} className="text-ink-faint" />
            </Link>
            <Link
              href={`/merchants/${merchantId}/reviews`}
              className="flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface"
            >
              <span className="flex items-center gap-2.5">
                <IconExternal size={16} className="text-gold" />
                Enlace de reseñas
              </span>
              <IconArrowRight size={14} className="text-ink-faint" />
            </Link>
            {canExport && (
              <a
                href={fidelity.exportUrl(merchantId)}
                className="flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface"
              >
                <span className="flex items-center gap-2.5">
                  <IconDownload size={16} className="text-ink-soft" />
                  Exportar clientes (CSV)
                </span>
                <IconArrowRight size={14} className="text-ink-faint" />
              </a>
            )}
            {canExport && (
              <a
                href={fidelity.exportTransactionsUrl(merchantId)}
                className="flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface"
              >
                <span className="flex items-center gap-2.5">
                  <IconDownload size={16} className="text-ink-soft" />
                  Exportar movimientos (CSV)
                </span>
                <IconArrowRight size={14} className="text-ink-faint" />
              </a>
            )}
            <Link
              href={`/merchants/${merchantId}/nfc`}
              className="flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface"
            >
              <span className="flex items-center gap-2.5">
                <IconContactless size={16} className="text-teal" />
                Etiquetas del local
              </span>
              <IconArrowRight size={14} className="text-ink-faint" />
            </Link>
          </nav>
        </Panel>
      </div>

      {/* Trabajo de Wallet al descubierto (§15): visible, explicable y
          reintenable. Los fallos de sincronización no tocan el ledger. */}
      {canManage && summary.wallet_errors > 0 && (
        <WalletJobs merchantId={merchantId} onChanged={() => load()} />
      )}
    </div>
  );
}

const WALLET_JOB_LABELS: Record<string, string> = {
  "wallet.issue": "Emitir pase Wallet",
  "wallet.update": "Actualizar pase Wallet",
};

const WALLET_JOB_STATUS: Record<string, string> = {
  queued: "En cola",
  running: "En proceso",
  retrying: "Reintentando",
  failed: "Fallido",
  partial: "Terminado a medias",
  succeeded: "Completado",
};

const WALLET_ERROR_LABELS: Record<string, string> = {
  wallet_provider_not_configured: "Proveedor sin configurar",
  wallet_issue_failed: "El proveedor rechazó la operación",
  wallet_update_failed: "El proveedor no actualizó el pase",
  wallet_update_pending: "Actualización pendiente del proveedor",
};

/**
 * Trabajos de Wallet pendientes o fallidos, con reintento manual (§15, §18.2).
 * Solo aparece cuando hay algo pendiente; el reintento conserva la
 * idempotencia del trabajo: nunca duplica pases ni toca el ledger.
 */
function WalletJobs({
  merchantId,
  onChanged,
}: {
  merchantId: string;
  onChanged: () => void;
}) {
  const [jobs, setJobs] = useState<WalletJob[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyJob, setBusyJob] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; message: string } | null>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void fidelity
      .walletJobs(merchantId)
      .then((rows) => {
        if (cancelled) return;
        // Solo pendiente o fallido: completados y cancelados no estorban.
        setJobs(rows.filter((job) => job.status !== "succeeded" && job.status !== "cancelled"));
        setLoadError(null);
      })
      .catch(() => {
        if (!cancelled) setLoadError("No se pudieron cargar los trabajos.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  async function retry(job: WalletJob) {
    setBusyJob(job.id);
    setRowError(null);
    try {
      const updated = await fidelity.retryWalletJob(merchantId, job.id);
      setJobs((current) =>
        current
          ?.map((row) => (row.id === updated.id ? updated : row))
          .filter((row) => row.status !== "succeeded" && row.status !== "cancelled") ?? null,
      );
      onChanged();
    } catch (err) {
      setRowError({
        id: job.id,
        message:
          err instanceof ApiError ? err.message : "No se pudo reintentar ahora mismo.",
      });
    } finally {
      setBusyJob(null);
    }
  }

  if (loadError) {
    return (
      <section aria-label="Trabajos de Wallet pendientes" className="animate-in">
        <Alert tone="warn" title="No se pudieron ver los trabajos de Wallet">
          {loadError}{" "}
          <button
            type="button"
            onClick={() => load()}
            className="font-semibold text-brand underline underline-offset-2"
          >
            Volver a intentar
          </button>
        </Alert>
      </section>
    );
  }
  // Carga en curso o nada pendiente: sin ruido (el recuento del resumen avisa).
  if (!jobs || jobs.length === 0) return null;

  return (
    <section
      aria-label="Trabajos de Wallet pendientes o fallidos"
      className="animate-in rounded-2xl border border-warn/25 bg-warn-soft/50 p-5"
    >
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-warn text-white">
          <IconAlert size={18} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-bold text-ink">
            {jobs.length === 1 ? "Un trabajo de Wallet pendiente" : `${jobs.length} trabajos de Wallet pendientes`}
          </p>
          <p className="mt-0.5 text-[12px] leading-relaxed text-ink-soft">
            La <strong className="font-semibold text-ink">sincronización</strong> fallida{" "}
            <strong className="font-semibold text-ink">no afecta al saldo</strong>: los puntos y
            sellos ya quedaron registrados. Puedes reintentar cuando quieras.
          </p>
        </div>
      </div>
      <ul className="mt-3.5 space-y-2">
        {jobs.map((job) => (
          <li key={job.id} className="rounded-xl border border-line bg-surface p-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">
                  {WALLET_JOB_LABELS[job.job_type] ?? job.job_type}{" "}
                  <span className="text-xs font-medium text-ink-faint">
                    · {formatDate(job.created_at)}
                  </span>
                </p>
                <p className="mt-0.5 text-[11px] text-ink-faint">
                  <span className={job.status === "failed" ? "font-semibold text-warn" : ""}>
                    {WALLET_JOB_STATUS[job.status] ?? job.status}
                  </span>{" "}
                  · intento {job.attempts}
                  {job.error_code && (
                    <> · {WALLET_ERROR_LABELS[job.error_code] ?? job.error_code}</>
                  )}
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                loading={busyJob === job.id}
                onClick={() => void retry(job)}
              >
                Reintentar
              </Button>
            </div>
            {rowError?.id === job.id && (
              <p className="mt-2 rounded-lg bg-danger-soft px-2.5 py-1.5 text-[11px] font-semibold text-danger">
                {rowError.message}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
