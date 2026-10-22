/** Utilidades puras de presentación (sin DOM): probables en vitest. */

/**
 * Deriva los huecos de sellos a mostrar a partir de datos **reales**:
 * la marca se muestra hasta el umbral de la próxima recompensa (máximo 12
 * huecos para no saturar). Sin recompensas, se muestran 10 huecos. Nunca se
 * inventa un progreso: `filled` siempre es `stamps` recortado a `slots`.
 */
export function stampSlots(stamps: number, target?: number | null): { slots: number; filled: number } {
  const safeStamps = Math.max(0, Math.floor(stamps));
  const slots =
    target && target > 0 ? Math.min(12, Math.max(1, Math.floor(target))) : Math.min(12, Math.max(6, safeStamps, 10));
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

/** «1 sello» / «3 sellos»: concordancia correcta en los mensajes. */
export function sellos(n: number): string {
  return `${n} ${n === 1 ? "sello" : "sellos"}`;
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
