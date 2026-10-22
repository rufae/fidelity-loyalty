"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  BrandPanel,
  ErrorState,
  IconAlert,
  IconArrowRight,
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
import { fidelity, type DashboardSummary } from "@/lib/fidelity";
import { canManageMerchant } from "@/lib/session";
import { formatNumber } from "@/lib/ui";

/**
 * Resumen real del comercio: todas las cifras vienen de la base de datos.
 * La jerarquía importa: primero la comunidad de clientes, después el detalle
 * operativo. Nada de ocho tarjetas blancas idénticas.
 */
export function MerchantDashboard() {
  const { merchantId, merchantName, role, isPlatformAdmin: platformAdmin } = useMerchant();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void fidelity
      .dashboard(merchantId)
      .then((data) => {
        if (cancelled) return;
        setSummary(data);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar el resumen del comercio.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  // La exportación contiene datos de contacto: solo para quien gestiona.
  const canExport = platformAdmin || (role !== null && canManageMerchant(role));

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
      hint: "simulados si no hay credenciales",
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
    <div className="space-y-7">
      {/* Bienvenida con una acción útil de verdad: operar en el mostrador. */}
      <BrandPanel className="animate-in p-6 sm:p-8" tone="brand">
        <div className="grid grid-cols-1 items-center gap-7 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-white/65">
                Resumen
              </p>
              <span className="rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-[11px] font-semibold text-white/90">
                Cifras reales de tu base de datos
              </span>
            </div>
            <h2 className="mt-3 text-[28px] font-bold leading-[1.1] tracking-[-0.02em] text-balance sm:text-[34px]">
              {merchantName}
            </h2>
            <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-white/80 sm:text-[15px]">
              Configura el programa, opera en el mostrador y prepara las etiquetas de tu
              establecimiento.
            </p>
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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
    </div>
  );
}
