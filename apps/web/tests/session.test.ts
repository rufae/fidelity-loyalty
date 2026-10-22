import { describe, expect, it } from "vitest";

import { canManageMerchant, canOperateMerchant, isPlatformAdmin } from "../lib/session";

describe("permisos de interfaz (§8.2: solo ocultan botones, el backend decide)", () => {
  it("reconoce a la administración de plataforma", () => {
    expect(isPlatformAdmin({ platform_role: "owner" } as never)).toBe(true);
    expect(isPlatformAdmin({ platform_role: "admin" } as never)).toBe(true);
    expect(isPlatformAdmin({ platform_role: null } as never)).toBe(false);
  });

  it("solo owner y admin gestionan un comercio", () => {
    expect(canManageMerchant("owner")).toBe(true);
    expect(canManageMerchant("admin")).toBe(true);
    expect(canManageMerchant("staff")).toBe(false);
    expect(canManageMerchant("viewer")).toBe(false);
  });

  it("staff puede operar (sellos y canjes) pero no administrar", () => {
    expect(canOperateMerchant("staff")).toBe(true);
    expect(canManageMerchant("staff")).toBe(false);
  });
});
