/**
 * Separación de pantallas por tipo de usuario y rol (§8.1, §13.1).
 *
 * Comprueba en el navegador real que:
 *   - la portada `/` es pública y no enseña diagnósticos técnicos;
 *   - el diagnóstico vive en `/estado`, reservado a la plataforma;
 *   - el personal de mostrador solo ve Operaciones (ni configuración ni
 *     clientes), aunque escriba la URL a mano;
 *   - el rol de solo lectura recibe un aviso claro y ninguna sección;
 *   - la administración del comercio ve el panel completo;
 *   - la administración de plataforma entra a la lista de comercios y a
 *     `/estado`;
 *   - el backend sigue siendo el control definitivo (404 en la API directa).
 *
 * La suite siembra su propio comercio y usuarios por la API con el bootstrap
 * de desarrollo (o el `.env` rotado, vía playwright.config.ts).
 */
import { expect, request, test, type APIRequestContext } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:8100";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@fidelity.example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "contrasena-de-desarrollo-1234";
const STAFF_PASSWORD = "staff-roles-larga-1234";
const VIEWER_PASSWORD = "viewer-roles-larga-1234";

let api: APIRequestContext;
let merchantId = "";
let ownerEmail = "";
const ownerPassword = "owner-roles-larga-1234";
let staffEmail = "";
let viewerEmail = "";

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
  ownerEmail = `owner-roles-${stamp}@example.com`;
  staffEmail = `staff-roles-${stamp}@example.com`;
  viewerEmail = `viewer-roles-${stamp}@example.com`;

  const merchant = await api.post("/api/v1/platform/merchants", {
    data: {
      name: `Roles E2E ${stamp}`,
      owner_email: ownerEmail,
      owner_password: ownerPassword,
      owner_display_name: "Propietaria Roles",
    },
  });
  expect(merchant.status()).toBe(201);
  merchantId = ((await merchant.json()) as { id: string }).id;

  const staff = await api.post(`/api/v1/merchants/${merchantId}/users`, {
    data: {
      email: staffEmail,
      password: STAFF_PASSWORD,
      display_name: "Personal Roles",
      role: "staff",
    },
  });
  expect(staff.status()).toBe(201);

  const viewer = await api.post(`/api/v1/merchants/${merchantId}/users`, {
    data: {
      email: viewerEmail,
      password: VIEWER_PASSWORD,
      display_name: "Consulta Roles",
      role: "viewer",
    },
  });
  expect(viewer.status()).toBe(201);
});

test.afterAll(async () => {
  await api?.dispose();
});

test("anónimo: portada pública sin diagnósticos y rutas privadas que llevan al acceso", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Tu programa de fidelización, funcionando en minutos" }),
  ).toBeVisible();
  await expect(page.getByText("Para tu comercio")).toBeVisible();
  await expect(page.getByText("Para tus clientes")).toBeVisible();
  // La portada pública no expone el estado interno de la infraestructura.
  await expect(page.getByText("Comprobaciones")).toHaveCount(0);
  await expect(page.getByText("Proveedor de Wallet")).toHaveCount(0);

  // Panel: sin sesión se va al acceso.
  await page.goto("/merchants");
  await page.waitForURL("**/login");

  // Diagnóstico técnico: sin sesión, al acceso (nunca se muestra).
  await page.goto("/estado");
  await page.waitForURL("**/login");
  await expect(page.getByText("Comprobaciones")).toHaveCount(0);

  // Rutas directas del panel de un comercio: al acceso.
  await page.goto(`/merchants/${merchantId}/programs`);
  await page.waitForURL("**/login");

  // Las páginas de cliente (públicas) sí responden sin sesión.
  await page.goto("/my-card/comercio-inexistente");
  await expect(page.getByRole("heading", { name: "Encuentra tu tarjeta" })).toBeVisible();
});

test("staff: solo Operaciones; la URL directa a otras secciones no las muestra", async ({
  page,
}) => {
  await loginUi(page, staffEmail, STAFF_PASSWORD);
  // Con un solo comercio, el acceso va directo a su panel; el personal de
  // mostrador aterriza en Operaciones (su única pantalla).
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/operations$`));
  await expect(page.getByRole("heading", { name: "Operaciones de mostrador" })).toBeVisible();
  await expect(page.getByText("Personal de mostrador")).toBeVisible();

  // La navegación no ofrece configuración ni clientes.
  const nav = page.getByRole("navigation", { name: "Secciones del comercio" });
  await expect(nav.getByRole("link", { name: "Operaciones" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Programas" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Clientes" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "NFC y QR" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Reseñas Google" })).toHaveCount(0);

  // URL escrita a mano: se redirige sin mostrar la pantalla ajena.
  await page.goto(`/merchants/${merchantId}/programs`);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/operations$`));
  await expect(page.getByText("Programas de fidelización")).toHaveCount(0);

  await page.goto(`/merchants/${merchantId}/members`);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/operations$`));

  // El backend es el control definitivo: la API niega lo mismo (404).
  const direct = await page.request.get(`/api/v1/merchants/${merchantId}/programs`);
  expect(direct.status()).toBe(404);
  const membersList = await page.request.get(`/api/v1/merchants/${merchantId}/memberships`);
  expect(membersList.status()).toBe(404);
});

test("viewer: sin secciones operativas, con aviso claro", async ({ page }) => {
  await loginUi(page, viewerEmail, VIEWER_PASSWORD);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));
  await expect(page.getByText("Tu acceso es de solo lectura")).toBeVisible();

  const nav = page.getByRole("navigation", { name: "Secciones del comercio" });
  await expect(nav.getByRole("link")).toHaveCount(0);

  // Tampoco puede entrar a Operaciones por URL: vuelve al aviso.
  await page.goto(`/merchants/${merchantId}/operations`);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));
  await expect(page.getByText("Tu acceso es de solo lectura")).toBeVisible();
});

test("administración del comercio: panel completo (sin enlace técnico)", async ({ page }) => {
  await loginUi(page, ownerEmail, ownerPassword);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/dashboard$`));
  await expect(page.getByText("Tu programa de un vistazo")).toBeVisible();

  const nav = page.getByRole("navigation", { name: "Secciones del comercio" });
  for (const name of ["Resumen", "Operaciones", "Programas", "Clientes", "NFC y QR", "Reseñas Google"]) {
    await expect(nav.getByRole("link", { name })).toBeVisible();
  }
  // «Estado» (diagnóstico) no aparece para comercios.
  await expect(page.getByRole("link", { name: "Estado" })).toHaveCount(0);

  // Programas sí es accesible directamente para este rol.
  await page.goto(`/merchants/${merchantId}/programs`);
  await expect(page.getByRole("heading", { name: "Programas de fidelización" })).toBeVisible();

  // /estado no es para comercios: vuelve a la portada pública.
  await page.goto("/estado");
  await page.waitForURL(`${BASE}/`);
  // El anuncio de ruta (route announcer) replica el h1: el rol de título
  // selecciona solo el elemento real de la portada.
  await expect(
    page.getByRole("heading", { name: "Tu programa de fidelización, funcionando en minutos" }),
  ).toBeVisible();
});

test("plataforma: lista de comercios y diagnóstico reservado", async ({ page }) => {
  await loginUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.waitForURL("**/merchants");
  await expect(page.getByRole("heading", { name: "Comercios" })).toBeVisible();

  // El diagnóstico existe para la plataforma.
  await page.goto("/estado");
  await expect(page.getByText("Comprobaciones")).toBeVisible();
  await expect(page.getByText("Proveedor de Wallet")).toBeVisible();

  // Y puede abrir el panel de un comercio con toda la navegación.
  await page.goto(`/merchants/${merchantId}/dashboard`);
  await expect(page.getByText("Tu programa de un vistazo")).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Secciones del comercio" });
  await expect(nav.getByRole("link", { name: "Programas" })).toBeVisible();
  // El diagnóstico no aparece en la interfaz de ningún rol: se abre con la
  // URL directa /estado, reservada a la plataforma (nada de «Estado» en el menú).
  await expect(page.getByRole("link", { name: "Estado" })).toHaveCount(0);
});

test("móvil: el menú del personal respeta su rol y la portada es responsive", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  // Portada pública sin desbordes horizontales.
  await page.goto("/");
  await expect(page.getByText("Para tu comercio")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);

  // Personal de mostrador en móvil: cajón con su única sección.
  await loginUi(page, staffEmail, STAFF_PASSWORD);
  await page.waitForURL(new RegExp(`/merchants/${merchantId}/operations$`));
  await page.getByRole("button", { name: "Abrir menú" }).click();
  // Con el cajón abierto hay dos <nav> en el DOM (sidebar oculta + cajón):
  // el visible es el último.
  const drawer = page.locator("nav[aria-label='Secciones del comercio']").last();
  await expect(drawer.getByRole("link", { name: "Operaciones" })).toBeVisible();
  await expect(drawer.getByRole("link", { name: "Programas" })).toHaveCount(0);
});
