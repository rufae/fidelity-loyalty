"use client";

import { useCallback, useRef, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

/**
 * Zona interactiva de la portada: la tarjeta del héroe inclina en 3D
 * siguiendo al puntero (vía `--tilt-x/--tilt-y`) y un destello violeta muy
 * tenue comparte su centro con el cursor (vía `--glow-x/--glow-y`).
 *
 * Decorativo y de cortesía:
 *  - No toca el contenido: solo fija custom properties en un contenedor.
 *  - En pantallas táctiles y con `prefers-reduced-motion` no actúa
 *    (el CSS igualmente lo anula para el transform).
 *  - Al salir del escenario vuelve a su posición de reposo.
 */
export function LandingCardZone({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const element = ref.current;
    if (!element) return;
    if (
      window.matchMedia("(pointer: coarse)").matches ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }
    const rect = element.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    element.style.setProperty("--tilt-x", `${(-y * 4.5).toFixed(2)}deg`);
    element.style.setProperty("--tilt-y", `${(x * 6.5).toFixed(2)}deg`);
    element.style.setProperty("--glow-x", `${(x * 100 + 50).toFixed(1)}%`);
    element.style.setProperty("--glow-y", `${(y * 100 + 50).toFixed(1)}%`);
  }, []);

  const onLeave = useCallback(() => {
    const element = ref.current;
    if (!element) return;
    element.style.setProperty("--tilt-x", "0deg");
    element.style.setProperty("--tilt-y", "0deg");
  }, []);

  return (
    <div
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      className={`tilt-zone relative ${className}`}
    >
      <div
        aria-hidden="true"
        className="stage-sheen pointer-events-none absolute -inset-6 rounded-[48px]"
      />
      {children}
    </div>
  );
}
