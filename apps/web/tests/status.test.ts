import { describe, expect, it } from "vitest";

import {
  classifyLiveness,
  classifyReadiness,
  walletLabel,
  type HealthPayload,
} from "../lib/status";

const READY: HealthPayload = {
  status: "ready",
  service: "LocalAI Fidelity API",
  version: "0.1.0",
  environment: "test",
  database: "ok",
  wallet_provider: "simulated",
};

const NOT_READY: HealthPayload = {
  status: "not_ready",
  service: "LocalAI Fidelity API",
  version: "0.1.0",
  environment: "test",
  database: "unavailable",
};

const HEALTH_OK: HealthPayload = {
  status: "ok",
  service: "LocalAI Fidelity API",
  version: "0.1.0",
  environment: "test",
};

describe("classifyLiveness", () => {
  it("marca error si el backend no responde", () => {
    const result = classifyLiveness(false, null);
    expect(result.state).toBe("error");
    expect(result.label).toBe("API");
  });

  it("marca ok con una respuesta válida", () => {
    const result = classifyLiveness(true, HEALTH_OK);
    expect(result.state).toBe("ok");
    expect(result.detail).toContain("LocalAI Fidelity API");
    expect(result.detail).toContain("v0.1.0");
  });

  it("marca degraded con una respuesta inesperada", () => {
    const result = classifyLiveness(true, { status: "wadus" });
    expect(result.state).toBe("degraded");
  });
});

describe("classifyReadiness", () => {
  it("marca ok cuando la base de datos responde", () => {
    const result = classifyReadiness(true, READY);
    expect(result.state).toBe("ok");
    expect(result.detail).toBe("PostgreSQL accesible");
  });

  it("marca degraded cuando la BD no está disponible", () => {
    const result = classifyReadiness(true, NOT_READY);
    expect(result.state).toBe("degraded");
    expect(result.detail).toBe("PostgreSQL no responde");
  });

  it("marca error si el backend no responde", () => {
    const result = classifyReadiness(false, null);
    expect(result.state).toBe("error");
  });
});

describe("walletLabel (§17.2 / ADR-0002)", () => {
  it("rotula el proveedor simulado para no confundirlo con una tarjeta real", () => {
    expect(walletLabel("simulated")).toBe("Simulado (sin credenciales reales)");
  });

  it("muestra el nombre del proveedor real cuando esté configurado", () => {
    expect(walletLabel("apple")).toBe("apple");
    expect(walletLabel("google")).toBe("google");
  });

  it("no inventa un valor si el backend no informa el proveedor", () => {
    expect(walletLabel(undefined)).toBe("No informado");
  });
});
