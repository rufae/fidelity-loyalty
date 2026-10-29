/**
 * Soporte B2B en navegador (Plan.md §18): conversación del comercio y buzón
 * de plataforma, sin exponer datos personales del propietario.
 */
import { expect, request, test, type APIRequestContext } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:8100";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@fidelity.example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "contrasena-de-desarrollo-1234";

let api: APIRequestContext;
let merchantId = "";
let ownerEmail = "";
const ownerPassword = "owner-soporte-larga-1234";

test.describe.configure({ mode: "serial" });

async function loginUi(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/login");
  await page.locator("input[type=email]").first().fill(email);
  await page.locator("input[type=password]").first().fill(password);
  await page.click('button:has-text("Entrar")');
}

test.beforeAll(async () => {
  api = await request.newContext({ baseURL: BASE });
  const login = await api.post("/api/v1/auth/login", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  expect(login.ok(), `login bootstrap → ${login.status()}`).toBeTruthy();

  const stamp = Date.now();
  ownerEmail = `owner-soporte-${stamp}@example.com`;
  const merchant = await api.post("/api/v1/platform/merchants", {
    data: {
      name: `Soporte E2E ${stamp}`,
      owner_email: ownerEmail,
      owner_password: ownerPassword,
      owner_display_name: "Propietario Soporte",
    },
  });
  expect(merchant.status()).toBe(201);
  merchantId = ((await merchant.json()) as { id: string }).id;
});

test.afterAll(async () => {
  await api?.dispose();
});

test("el comercio abre una conversación y la plataforma responde", async ({ page }) => {
  await loginUi(page, ownerEmail, ownerPassword);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));

  await page.goto(`/merchants/${merchantId}/support`);
  await expect(page.getByRole("heading", { name: "Soporte", level: 1 })).toBeVisible();
  await page.click('a:has-text("Nueva conversación")');

  await page.getByLabel("Asunto").fill("No puedo imprimir los tiques");
  await page.getByLabel("Mensaje").fill("La impresora del mostrador no responde desde esta mañana.");
  await page.click('button:has-text("Enviar a soporte")');

  await page.waitForURL(new RegExp(`/merchants/${merchantId}/support/[0-9a-f-]+$`));
  await expect(page.getByText("No puedo imprimir los tiques")).toBeVisible();
  await expect(page.getByText("Esperando a soporte")).toBeVisible();

  // El comercio no ve datos privados de la plataforma.
  await expect(page.getByText("propietario@")).toHaveCount(0);

  await loginUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.waitForURL("**/merchants");
  await page.goto("/platform/support");
  await page.click('a:has-text("No puedo imprimir los tiques")');
  await page.waitForURL(/\/platform\/support\/[0-9a-f-]+$/);
  await expect(page.getByText("Soporte E2E", { exact: false }).first()).toBeVisible();
  await page.getByLabel("Responder al comercio").fill("Lo revisamos hoy mismo.");
  await page.click('button:has-text("Enviar respuesta")');
  await expect(page.getByText("Respuesta enviada al comercio.")).toBeVisible();

  await loginUi(page, ownerEmail, ownerPassword);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));
  await page.goto(`/merchants/${merchantId}/support`);
  await page.click('a:has-text("No puedo imprimir los tiques")');
  await expect(page.getByText("Lo revisamos hoy mismo.")).toBeVisible();
  await expect(page.getByText("Esperando al comercio")).toBeVisible();
});

test("la solicitud de llamada guarda el teléfono solo para la plataforma", async ({ page }) => {
  await loginUi(page, ownerEmail, ownerPassword);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));
  await page.goto(`/merchants/${merchantId}/support`);
  await page.click('a:has-text("No puedo imprimir los tiques")');

  await page.click('button:has-text("Solicitar llamada")');
  await page.getByLabel("Teléfono").fill("+34600111222");
  await page.getByLabel("Disponibilidad").fill("Por la tarde");
  await page.getByLabel("Acepto que me llamen a este número para atender esta solicitud.").check();
  await page.click('button:has-text("Solicitar llamada")');

  await expect(page.getByText("Solicitud de llamada registrada.")).toBeVisible();
  await expect(page.getByText("Has pedido una llamada")).toBeVisible();
  await expect(page.getByText("+34600111222")).toHaveCount(0);

  await loginUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.waitForURL("**/merchants");
  await page.goto("/platform/support");
  await page.click('a:has-text("No puedo imprimir los tiques")');
  await expect(page.getByText("+34600111222")).toBeVisible();
  await expect(page.getByText("Pide llamada")).toBeVisible();
});
