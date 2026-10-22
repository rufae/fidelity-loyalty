import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, formatNumber, sellos, stampSlots } from "../lib/ui";

describe("formatNumber: cifras con separador editorial", () => {
  it("agrupa los miles al estilo español", () => {
    expect(formatNumber(12480)).toBe("12.480");
  });

  it("no inventa decimales para valores enteros", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(7)).toBe("7");
  });

  it("un valor no numérico no pinta NaN en pantalla", () => {
    expect(formatNumber(Number.NaN)).toBe("—");
  });
});

describe("stampSlots: progreso derivado solo de datos reales", () => {
  it("marca los sellos conseguidos sin exceder los huecos", () => {
    const { slots, filled } = stampSlots(4, 10);
    expect(slots).toBe(10);
    expect(filled).toBe(4);
  });

  it("usa el umbral de la próxima recompensa como objetivo", () => {
    const { slots, filled } = stampSlots(12, 15);
    expect(slots).toBe(12); // 15 se recorta al máximo de 12 huecos
    expect(filled).toBe(12);
  });

  it("sin recompensas muestra 10 huecos como referencia visual", () => {
    expect(stampSlots(2, null)).toEqual({ slots: 10, filled: 2 });
    expect(stampSlots(2, undefined)).toEqual({ slots: 10, filled: 2 });
  });

  it("nunca muestra más sellos que huecos ni valores negativos", () => {
    expect(stampSlots(30, null).filled).toBeLessThanOrEqual(stampSlots(30, null).slots);
    expect(stampSlots(-5, 10)).toEqual({ slots: 10, filled: 0 });
  });

  it("un sello positivo siempre se refleja en el progreso", () => {
    const { slots, filled } = stampSlots(1, null);
    expect(filled).toBe(1);
    expect(slots).toBeGreaterThan(filled);
  });
});

describe("sellos: concordancia correcta en los mensajes", () => {
  it("usa singular y plural adecuados", () => {
    expect(sellos(1)).toBe("1 sello");
    expect(sellos(0)).toBe("0 sellos");
    expect(sellos(3)).toBe("3 sellos");
  });
});

describe("formatos de fecha para la interfaz", () => {
  it("formatDate devuelve fecha corta en español", () => {
    expect(formatDate("2026-10-13T10:00:00Z")).toMatch(/2026/);
  });

  it("formatDate admite ausencia de fecha sin romper", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
  });

  it("formatDateTime incluye hora local", () => {
    expect(formatDateTime("2026-10-13T10:00:00Z")).toMatch(/\d{2}:\d{2}/);
  });
});
