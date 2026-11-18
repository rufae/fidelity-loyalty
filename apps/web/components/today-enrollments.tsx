"use client";

/**
 * «Altas de hoy» en el mostrador (mejora de compra #2, «puente mostrador»
 * sin notificaciones).
 *
 * El personal ve quién se ha registrado hoy y puede darle el primer sello de
 * bienvenida al momento, en un solo toque. Nada de push: la consola sondea
 * cada 30 s como el resto de la pantalla, y una tienda con tráfico no vive
 * de avisos. Identidad mínima: nombre y tarjeta, sin correo (§9.3, §13.5).
 */
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { fidelity, newIdempotencyKey, type Membership } from "@/lib/fidelity";
import { unidades } from "@/lib/ui";
import { Button, IconCheck, IconChevronDown, IconUsers } from "@/components/ui";

/** Iniciales de identificación rápida (mismo criterio que la consola). */
function initials(name: string | null | undefined): string {
  return (name ?? "")
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 1)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("") || "•";
}

/** Cadencia del sondeo: igual que el resumen del panel. */
const POLL_MS = 30_000;

export function TodayEnrollments({
  merchantId,
  onUseCard,
  onError,
}: {
  merchantId: string;
  onUseCard: (card: Membership) => void;
  onError?: (message: string) => void;
}) {
  const [rows, setRows] = useState<Membership[] | null>(null);
  const [welcomingId, setWelcomingId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = (): void => {
      void fidelity
        .enrollmentsToday(merchantId)
        .then((data) => {
          if (active) setRows(data);
        })
        .catch(() => {
          // Fallo de red o 404 ajeno: la consola sigue operativa; se
          // reintenta en el siguiente sondeo.
        });
    };
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [merchantId]);

  /** Primer sello de bienvenida: misma operación autorizada e idempotente. */
  async function welcome(row: Membership) {
    setWelcomingId(row.id);
    try {
      const result = await fidelity.earn(merchantId, row.id, newIdempotencyKey("welcome"));
      setRows((current) =>
        (current ?? []).map((item) =>
          item.id === row.id ? { ...item, stamps: result.stamps } : item,
        ),
      );
    } catch (err) {
      onError?.(err instanceof ApiError ? err.message : "No se pudo registrar el sello.");
    } finally {
      setWelcomingId(null);
    }
  }

  if (rows === null || rows.length === 0) return null;

  return (
    <details
      open
      className="group rounded-2xl border border-line bg-paper shadow-soft"
      aria-label="Altas de hoy"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-2xl px-5 py-4 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-ok-soft text-ok">
            <IconUsers size={16} />
          </span>
          <span>
            <span className="block text-sm font-semibold text-ink">
              Altas de hoy · {rows.length} {rows.length === 1 ? "cliente" : "clientes"}
            </span>
            <span className="block text-xs text-ink-faint">
              {rows.some((row) => row.program_type !== "points")
                ? "Dale la bienvenida con el primer sello o abre su tarjeta"
                : "Abre su tarjeta o registra su primera venta en Operaciones"}
            </span>
          </span>
        </span>
        <IconChevronDown
          size={18}
          className="shrink-0 text-ink-faint transition-transform duration-200 group-open:rotate-180"
        />
      </summary>
      <ul className="space-y-2 border-t border-line px-5 py-4">
        {rows.map((row) => (
          <li
            key={row.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-3"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                aria-hidden="true"
                className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand"
              >
                {initials(row.member_name)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">
                  {row.member_name || "Cliente"}
                </p>
                <p className="truncate text-xs text-ink-faint">
                  {row.program_name ? `«${row.program_name}» · ` : ""}
                  {row.stamps === 0
                    ? row.program_type === "points"
                      ? "Sin puntos todavía"
                      : "Sin sellos todavía"
                    : unidades(row.program_type, row.stamps)}
                  {row.reward_ready && " · ⭐ Premio listo"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* El sello de bienvenida es de modo sellos: en modo
                  puntos la primera venta se registra con importe. */}
              {row.status === "active" &&
                row.stamps === 0 &&
                row.program_type !== "points" && (
                <Button
                  type="button"
                  size="sm"
                  loading={welcomingId === row.id}
                  disabled={welcomingId !== null}
                  onClick={() => void welcome(row)}
                  icon={<IconCheck size={15} />}
                >
                  Sello de bienvenida
                </Button>
              )}
              <Button type="button" size="sm" variant="secondary" onClick={() => onUseCard(row)}>
                Usar tarjeta
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </details>
  );
}
