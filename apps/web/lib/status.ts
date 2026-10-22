export type CheckState = "loading" | "ok" | "degraded" | "error";

export interface ServiceStatus {
  readonly label: string;
  readonly state: CheckState;
  readonly detail: string;
}

export interface HealthPayload {
  status?: string;
  service?: string;
  version?: string;
  environment?: string;
  database?: string;
  wallet_provider?: string;
}

export const CHECK_LABELS: Record<CheckState, string> = {
  loading: "Comprobando",
  ok: "Operativo",
  degraded: "Degradado",
  error: "Error",
};

export const LOADING_STATUS: readonly ServiceStatus[] = [
  { label: "API", state: "loading", detail: "Comprobando el backend…" },
  { label: "Base de datos", state: "loading", detail: "Comprobando PostgreSQL…" },
];

export function classifyLiveness(
  reachable: boolean,
  payload: HealthPayload | null,
): ServiceStatus {
  if (!reachable) {
    return { label: "API", state: "error", detail: "El backend no responde" };
  }
  if (payload?.status !== "ok") {
    return { label: "API", state: "degraded", detail: "Respuesta inesperada del backend" };
  }
  const service = payload.service ?? "API";
  const version = payload.version ? `v${payload.version}` : "";
  const environment = payload.environment ? `· ${payload.environment}` : "";
  return {
    label: "API",
    state: "ok",
    detail: [service, version, environment].join(" ").trim(),
  };
}

export function classifyReadiness(
  reachable: boolean,
  payload: HealthPayload | null,
): ServiceStatus {
  if (!reachable) {
    return { label: "Base de datos", state: "error", detail: "El backend no responde" };
  }
  if (payload?.status === "ready") {
    return { label: "Base de datos", state: "ok", detail: "PostgreSQL accesible" };
  }
  if (payload?.database === "unavailable") {
    return { label: "Base de datos", state: "degraded", detail: "PostgreSQL no responde" };
  }
  return {
    label: "Base de datos",
    state: "degraded",
    detail: "Respuesta inesperada del backend",
  };
}

/**
 * El proveedor de Wallet nunca puede presentarse como «tarjeta emitida» si es
 * el simulado: §17.2 exige rotularlo (ADR-0002).
 */
export function walletLabel(provider: string | undefined): string {
  if (!provider) return "No informado";
  if (provider === "simulated") return "Simulado (sin credenciales reales)";
  return provider;
}
