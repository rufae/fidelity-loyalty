import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { defineConfig } from "@playwright/test";

/**
 * E2E de navegador (tasks2 §19.4, brecha 17 del gap analysis).
 *
 * Precondición: la pila debe estar levantada (`docker compose up -d`): la web
 * en :8100 y la API proxificada por ella. La suite **siembra su propio
 * comercio** por la API con el usuario bootstrap de desarrollo y no depende
 * de datos de demostración.
 *
 * Las credenciales del bootstrap salen del `.env` local (que puede haberse
 * rotado): se cargan aquí sin dependencias extra y se exponen como
 * `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD` al entorno de las pruebas. Si no
 * hay `.env`, se usan los valores de ejemplo de desarrollo.
 */

/** Lee pares `CLAVE=valor` del `.env` de la raíz, sin imprimir nada. */
function localEnv(): Record<string, string> {
  try {
    const raw = readFileSync(resolve(__dirname, "../../.env"), "utf8");
    const values: Record<string, string> = {};
    for (const line of raw.split("\n")) {
      const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
      if (match) values[match[1]] = match[2].trim();
    }
    return values;
  } catch {
    return {};
  }
}

const env = localEnv();
if (!process.env.E2E_ADMIN_EMAIL && env.AUTH_BOOTSTRAP_EMAIL) {
  process.env.E2E_ADMIN_EMAIL = env.AUTH_BOOTSTRAP_EMAIL;
}
if (!process.env.E2E_ADMIN_PASSWORD && env.AUTH_BOOTSTRAP_PASSWORD) {
  process.env.E2E_ADMIN_PASSWORD = env.AUTH_BOOTSTRAP_PASSWORD;
}

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // Una sola pila compartida y datos de la propia suite: nada de paralelismo.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8100",
    locale: "es-ES",
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
