/** Utilidades puras de presentación (sin DOM): probables en vitest. */

/**
 * Deriva los huecos de sellos a mostrar a partir de datos **reales**:
 * la marca se muestra hasta el umbral de la próxima recompensa (máximo 12
 * huecos para no saturar). Sin recompensas, se muestran 10 huecos. Nunca se
 * inventa un progreso: `filled` siempre es `stamps` recortado a `slots`.
 */
export function stampSlots(stamps: number, target?: number | null): { slots: number; filled: number } {
  const safeStamps = Math.max(0, Math.floor(stamps));
  if (target && target > 0) {
    // Proporción real hacia el objetivo: 12 de 15 nunca puede parecer
    // «lleno» cuando debajo dice «faltan 3» (§13.2, estados honestos).
    const slots = Math.min(12, Math.max(1, Math.floor(target)));
    const filled = Math.round((Math.min(safeStamps, target) / target) * slots);
    return { slots, filled };
  }
  const slots = Math.min(12, Math.max(6, safeStamps, 10));
  return { slots, filled: Math.min(safeStamps, slots) };
}

/** Fecha corta en español para la interfaz (la BD guarda UTC). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Fecha y hora local para historiales de operaciones. */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Aclara (pct > 0) u oscurece (pct < 0) un color `#RRGGBB`.
    Usado por el diseño de tarjeta (decisión #8) para derivar bordes,
    sombras y tinta a partir del color de acento elegido por el comercio. */
export function shade(hex: string, pct: number): string {
  const n = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(n)) return hex;
  const num = parseInt(n, 16);
  const delta = Math.round((255 * pct) / 100);
  const clamp = (v: number) => Math.max(0, Math.min(255, v));
  const r = clamp((num >> 16) + delta);
  const g = clamp(((num >> 8) & 0xff) + delta);
  const b = clamp((num & 0xff) + delta);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

/** «1 sello» / «3 sellos»: concordancia correcta en los mensajes. */
export function sellos(n: number): string {
  return `${n} ${n === 1 ? "sello" : "sellos"}`;
}

/** Unidad de la tarjeta según el programa (§7.1): «sellos» en modo
    stamps, «puntos» en modo points. El saldo siempre lo confirma el
    backend; esto solo rotula lo que ya se sabe. */
export function unidades(programType: string | null | undefined, n: number): string {
  if (programType === "points") return `${n} ${n === 1 ? "punto" : "puntos"}`;
  return sellos(n);
}

/**
 * Cifras tal como las formatea una editorial: separador de miles español
 * (12.480) y sin decimales fiction. La ausencia de separador es la marca
 * inconfundible de un panel amateur.
 */
export function formatNumber(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 }).format(n);
}
