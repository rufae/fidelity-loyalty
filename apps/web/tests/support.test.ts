import { describe, expect, it } from "vitest";

import {
  isSupportThreadOpen,
  newIdempotencyKey,
  supportExcerpt,
  supportStatusTone,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_CONTACT_LABELS,
  SUPPORT_STATUS_LABELS,
} from "@/lib/support";

describe("utilidades del soporte", () => {
  it("resume el mensaje limpiando espacios y recortando", () => {
    expect(supportExcerpt("  Hola   buenas\n tardes  ")).toBe("Hola buenas tardes");
    const long = "a".repeat(200);
    const excerpt = supportExcerpt(long, 20);
    expect(excerpt).toHaveLength(20);
    expect(excerpt.endsWith("…")).toBe(true);
  });

  it("considera abierta todo salvo resuelta y cerrada", () => {
    expect(isSupportThreadOpen("open")).toBe(true);
    expect(isSupportThreadOpen("waiting_platform")).toBe(true);
    expect(isSupportThreadOpen("waiting_merchant")).toBe(true);
    expect(isSupportThreadOpen("resolved")).toBe(false);
    expect(isSupportThreadOpen("closed")).toBe(false);
  });

  it("asigna tono distinto a cada estado visible", () => {
    expect(supportStatusTone("resolved")).toBe("ok");
    expect(supportStatusTone("waiting_platform")).toBe("warn");
    expect(supportStatusTone("closed")).toBe("neutral");
    expect(supportStatusTone("open")).toBe("info");
  });

  it("genera claves idempotentes distintas", () => {
    const first = newIdempotencyKey();
    const second = newIdempotencyKey();
    expect(first).not.toBe(second);
    expect(first.length).toBeGreaterThan(8);
  });

  it("tiene etiquetas para todas las categorías y contactos", () => {
    expect(Object.keys(SUPPORT_CATEGORY_LABELS)).toHaveLength(6);
    expect(Object.keys(SUPPORT_CONTACT_LABELS)).toHaveLength(3);
    expect(Object.keys(SUPPORT_STATUS_LABELS)).toHaveLength(5);
  });
});
