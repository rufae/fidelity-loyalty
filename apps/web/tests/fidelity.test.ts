import { describe, expect, it } from "vitest";

import { PROGRAM_STATUS_LABELS, extractCardCode, newIdempotencyKey } from "../lib/fidelity";

describe("newIdempotencyKey (§16.4)", () => {
  it("genera claves únicas por operación", () => {
    const keys = new Set(Array.from({ length: 200 }, () => newIdempotencyKey("earn")));
    expect(keys.size).toBe(200);
  });

  it("incluye el prefijo para poder auditar el origen", () => {
    expect(newIdempotencyKey("redeem")).toMatch(/^redeem-/);
  });
});

describe("extractCardCode: el buscador acepta el código o la URL del QR", () => {
  it("devuelve el código tal cual cuando ya lo es", () => {
    expect(extractCardCode("320d7c2a19160de9")).toBe("320d7c2a19160de9");
    expect(extractCardCode("  320d7c2a19160de9  ")).toBe("320d7c2a19160de9");
  });

  it("extrae el código de la URL que imprime el QR", () => {
    expect(extractCardCode("http://localhost:8100/card/320d7c2a19160de9")).toBe(
      "320d7c2a19160de9",
    );
    expect(extractCardCode("https://fidelidad.dominio/card/320d7c2a19160de9?x=1")).toBe(
      "320d7c2a19160de9",
    );
  });

  it("no se traga separadores accidentales", () => {
    expect(extractCardCode("http://localhost:8100/card/abc/")).toBe("abc");
    expect(extractCardCode("")).toBe("");
  });
});

describe("etiquetas de estado de programa", () => {
  it("no deja estados sin traducir en la interfaz", () => {
    for (const status of ["draft", "active", "paused", "archived"]) {
      expect(PROGRAM_STATUS_LABELS[status]).toBeTruthy();
    }
  });
});
