"use client";

import { useEffect, useRef, useState } from "react";

import { formatNumber } from "@/lib/ui";

/**
 * Número que sube hasta su valor real al aparecer (y salta al nuevo valor
 * cuando cambia, p. ej. al añadir un sello).
 *
 * Decorativo y de cortesía:
 * - Con `prefers-reduced-motion` muestra el valor final sin animar.
 * - El dato mostrado es siempre el confirmado por el backend: la animación
 *   solo lo presenta, nunca lo adelanta.
 */
export function CountUp({ value, className = "" }: { value: number; className?: string }) {
  const [display, setDisplay] = useState(value);
  /** Arranca en 0 para que la primera aparición suba desde cero. */
  const previous = useRef(0);

  useEffect(() => {
    const from = previous.current;
    previous.current = value;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Sin animación (movimiento reducido o valor igual): corregir en el
    // siguiente frame — nunca con setState síncrono dentro del efecto.
    if (reduce || value === from) {
      const raf = requestAnimationFrame(() => setDisplay(value));
      return () => cancelAnimationFrame(raf);
    }

    const DURATION = 700;
    const start = performance.now();
    let raf = 0;
    const step = (now: number): void => {
      const progress = Math.min((now - start) / DURATION, 1);
      const eased = 1 - Math.pow(1 - progress, 4); // ease-out-quart
      setDisplay(Math.round(from + (value - from) * eased));
      if (progress < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <span className={className}>{formatNumber(display)}</span>;
}
