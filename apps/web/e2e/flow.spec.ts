/**
 * E2E del recorrido comercial mínimo (tasks2 §19.4):
 *
 *   etiqueta NFC → alta con verificación de correo → tarjeta web honesta →
 *   recuperación por etiqueta compartida → mostrador (sello y canje
 *   confirmados por el backend) → suspensión que bloquea operaciones →
 *   escáner de cámara con respaldo manual.
 *
 * El correo de desarrollo va a `mailpit` (docker-compose): la suite espera el
 * mensaje real en su API local y sigue el enlace de un solo uso, igual que
 * haría el cliente. La suite siembra su propio comercio, programa, recompensa
 * y etiquetas por la API (usuario bootstrap de desarrollo) y después navega
 * la interfaz real. No usa datos de demostración ni toca otros comercios.
 */
import { expect, request, test, type APIRequestContext, type Page } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:8100";
const MAIL = process.env.E2E_MAIL_URL ?? "http://127.0.0.1:8025";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@fidelity.example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "contrasena-de-desarrollo-1234";

let api: APIRequestContext;
let mail: APIRequestContext;
let merchantId = "";
let merchantSlug = "";
let programId = "";
let programSlug = "";
let programBId = "";
let programBSlug = "";
let tagSlug = "";
let counterTagSlug = "";
let recoveryTagSlug = "";
let cardToken = "";
let clientEmail = "";
/** Tarjeta de un segundo cliente: prueba de actualización en vivo. */
let realtimeToken = "";

test.describe.configure({ mode: "serial" });

/**
 * Espera el correo `kind` (verificación o acceso) para `to` y devuelve el
 * token del enlace. El link completo se emite con `PUBLIC_BASE_URL`; aquí solo
 * se usa el token para navegar sobre el origen de `BASE` (así la suite no
 * depende de la IP pública configurada en cada entorno).
 */
async function waitEmailToken(kind: "verify" | "access", to: string): Promise<string> {
  const pattern = new RegExp(`/card/${kind}\\?token=([A-Za-z0-9_-]{16,})`);
  for (let attempt = 0; attempt < 60; attempt++) {
    const list = await mail.get("/api/v1/messages?limit=25");
    if (list.ok()) {
      const body = (await list.json()) as {
        messages?: Array<{ ID: string; To?: Array<{ Address: string }> }>;
      };
      for (const message of body.messages ?? []) {
        if (!message.To?.some((entry) => entry.Address === to)) continue;
        const detail = await mail.get(`/api/v1/message/${message.ID}`);
        if (!detail.ok()) continue;
        const payload = (await detail.json()) as { Text?: string; HTML?: string };
        const found = pattern.exec(payload.Text ?? "") ?? pattern.exec(payload.HTML ?? "");
        if (found?.[1]) return found[1];
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`No llegó el correo «${kind}» a ${to}`);
}

async function loginPanel(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type=email]").first().fill(ADMIN_EMAIL);
  await page.locator("input[type=password]").first().fill(ADMIN_PASSWORD);
  await page.click('button:has-text("Entrar")');
  await page.waitForURL("**/merchants");
}

async function buscarTarjeta(page: Page): Promise<void> {
  await page.goto(`/merchants/${merchantId}/operations`);
  await page.fill("#card-code", cardToken);
  await page.click('button:has-text("Buscar tarjeta")');
}

test.beforeAll(async () => {
  api = await request.newContext({ baseURL: BASE });
  mail = await request.newContext({ baseURL: MAIL });
  const login = await api.post("/api/v1/auth/login", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  expect(login.ok(), `login de preparación → ${login.status()}`).toBeTruthy();

  const stamp = Date.now();
  const merchant = await api.post("/api/v1/platform/merchants", {
    data: {
      name: `Comercio E2E ${stamp}`,
      owner_email: `e2e-owner-${stamp}@example.com`,
      owner_password: "contrasena-e2e-larga-1234",
      owner_display_name: "Propietaria E2E",
    },
  });
  expect(merchant.status()).toBe(201);
  const merchantBody = (await merchant.json()) as { id: string; slug: string };
  merchantId = merchantBody.id;
  merchantSlug = merchantBody.slug;

  const program = await api.post(`/api/v1/merchants/${merchantId}/programs`, {
    data: {
      name: "Club E2E",
      description: "Programa creado por la suite E2E.",
      terms: "Un sello por visita. Programa de prueba automatizada.",
    },
  });
  expect(program.status()).toBe(201);
  const programBody = (await program.json()) as { id: string; slug: string };
  programId = programBody.id;
  programSlug = programBody.slug;

  const publish = await api.post(`/api/v1/merchants/${merchantId}/programs/${programId}/publish`);
  expect(publish.ok(), `publicar programa → ${publish.status()}`).toBeTruthy();

  const reward = await api.post(`/api/v1/merchants/${merchantId}/programs/${programId}/rewards`, {
    data: { name: "Café gratis E2E", stamps_required: 2 },
  });
  expect(reward.status()).toBe(201);

  const tag = await api.post(`/api/v1/merchants/${merchantId}/nfc-tags`, {
    data: { tag_type: "loyalty_signup", label: "Mostrador E2E", program_id: programId },
  });
  expect(tag.status()).toBe(201);
  tagSlug = ((await tag.json()) as { public_slug: string }).public_slug;

  // Segundo programa del mismo comercio: prueba del selector de promoción
  // cuando un cliente está en varias a la vez (ADR-0008).
  const programB = await api.post(`/api/v1/merchants/${merchantId}/programs`, {
    data: { name: "Menú E2E", terms: "Tres menús, medio menú de regalo. Prueba." },
  });
  expect(programB.status()).toBe(201);
  const programBBody = (await programB.json()) as { id: string; slug: string };
  programBId = programBBody.id;
  programBSlug = programBBody.slug;
  const publishB = await api.post(
    `/api/v1/merchants/${merchantId}/programs/${programBId}/publish`,
  );
  expect(publishB.ok()).toBeTruthy();

  // Etiqueta de mostrador del segundo programa: el caso interesante es
  // tocar «Menú», escanear una tarjeta y que la promoción activa sea Menú.
  const counter = await api.post(`/api/v1/merchants/${merchantId}/nfc-tags`, {
    data: { tag_type: "counter", label: "Caja E2E", program_id: programBId },
  });
  expect(counter.status()).toBe(201);
  counterTagSlug = ((await counter.json()) as { public_slug: string }).public_slug;

  // Segundo cliente con tarjeta propia: la prueba de actualización en vivo
  // no debe tocar las tarjetas del ciclo de vida (que se suspenden).
  const realtimeEmail = `realtime-${stamp}@example.com`;
  const realtime = await api.post(`/api/v1/public/programs/${merchantSlug}/${programSlug}/enroll`, {
    data: {
      email: realtimeEmail,
      display_name: "Cliente Realtime",
      accepted_terms_version: 1,
      privacy_notice_version: 1,
    },
  });
  expect(realtime.status()).toBe(201);

  // Alta verificada: el token llega por correo (mailpit), igual que para un
  // cliente real. La verificación crea la sesión privada de la tarjeta.
  const verifyToken = await waitEmailToken("verify", realtimeEmail);
  const verified = await api.post("/api/v1/public/email/verify", {
    data: { token: verifyToken },
  });
  expect(verified.ok(), `verificación → ${verified.status()}`).toBeTruthy();
  const realtimeCards = await api.get(`/api/v1/public/card-access/${merchantSlug}`);
  expect(realtimeCards.ok()).toBeTruthy();
  const cardList = (await realtimeCards.json()) as Array<{ token: string }>;
  expect(cardList.length).toBe(1);
  realtimeToken = cardList[0].token;
  expect(realtimeToken.length).toBeGreaterThan(8);

  // Etiqueta de recuperación compartida (NFC «recuperar mi tarjeta»): abre
  // la página neutral donde el cliente pide su enlace por correo.
  const recovery = await api.post(`/api/v1/merchants/${merchantId}/nfc-tags`, {
    data: { tag_type: "member_card_access", label: "Recuperar mi tarjeta E2E" },
  });
  expect(recovery.status()).toBe(201);
  recoveryTagSlug = ((await recovery.json()) as { public_slug: string }).public_slug;
});

test.afterAll(async () => {
  await api?.dispose();
  await mail?.dispose();
});

test.describe("alta pública desde la etiqueta NFC (móvil)", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("la etiqueta redirige al alta y el cliente obtiene su tarjeta", async ({ page }) => {
    // La URL que se imprime en la etiqueta redirige (302) a la página pública.
    const redirect = await page.request.get(`/go/${tagSlug}`, { maxRedirects: 0 });
    expect(redirect.status()).toBe(302);
    expect(redirect.headers()["location"] ?? "").toContain(`/p/${merchantSlug}/${programSlug}`);

    await page.goto(`/p/${merchantSlug}/${programSlug}`);
    await expect(page.getByText("Nombre completo")).toBeVisible();

    // Nombre completo y email son obligatorios (ADR-0006).
    const required = await page.evaluate(() => {
      const name = document.querySelector<HTMLInputElement>("input[autocomplete=name]");
      const email = document.querySelector<HTMLInputElement>("input[type=email]");
      return { name: name?.required === true, email: email?.required === true };
    });
    expect(required).toEqual({ name: true, email: true });

    clientEmail = `cliente-e2e-${Date.now()}@example.com`;
    await page.fill("input[autocomplete=name]", "Cliente E2E");
    await page.fill("input[type=email]", clientEmail);

    // Condiciones y privacidad obligatorias; marketing opcional y sin marcar (§9.4).
    const boxes = page.locator("input[type=checkbox]");
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await expect(boxes.nth(2)).not.toBeChecked();

    await page.click('button:has-text("Quiero mi tarjeta")');
    // El alta ya no entrega la tarjeta en claro: pide confirmar el correo (§9.3).
    await expect(page.getByText("Revisa tu correo")).toBeVisible();
    await expect(page.getByText(/enviado un enlace para confirmar/)).toBeVisible();

    // El cliente sigue el enlace real de su correo (uno solo, caducado en 30 min).
    const verifyToken = await waitEmailToken("verify", clientEmail);
    await page.goto(`/card/verify?token=${verifyToken}`);
    await page.getByRole("button", { name: "Confirmar correo y continuar" }).click();
    await page.waitForURL(/\/my-card\/.+\/cards$/);
    await expect(page.getByRole("heading", { name: "Tus tarjetas" })).toBeVisible();

    // Abre la tarjeta desde su lista privada.
    await page.locator('a[href*="/card/"]').first().click();
    await expect(page.getByText("Muéstralo en caja")).toBeVisible();

    // El token de la tarjeta es opaco: sin datos personales en la URL.
    const match = /\/card\/([^/?#]+)/.exec(page.url());
    expect(match).not.toBeNull();
    cardToken = match?.[1] ?? "";
    expect(cardToken).not.toContain("@");
    expect(cardToken.length).toBeGreaterThan(8);

    // Honestidad de Wallet: sin credenciales solo hay aviso de demostración.
    await expect(page.getByText("Modo de demostración").first()).toBeVisible();
    expect(await page.locator('a:has-text("Añadir a Apple Wallet")').count()).toBe(0);
    expect(await page.locator('a:has-text("Añadir a Google Wallet")').count()).toBe(0);
  });

  test("la etiqueta de recuperación abre el acceso neutral y devuelve la tarjeta", async ({
    page,
  }) => {
    // Etiqueta compartida: redirige a la página donde el cliente escribe su
    // correo. No contiene credenciales ni permite ver tarjetas ajenas (§5.2).
    const redirect = await page.request.get(`/go/${recoveryTagSlug}`, { maxRedirects: 0 });
    expect(redirect.status()).toBe(302);
    expect(redirect.headers()["location"] ?? "").toContain(`/my-card/${merchantSlug}`);

    await page.goto(`/my-card/${merchantSlug}`);
    await expect(page.getByRole("heading", { name: "Encuentra tu tarjeta" })).toBeVisible();

    await page.fill("input[type=email]", clientEmail);
    await page.click('button:has-text("Enviarme un enlace seguro")');
    await expect(page.getByText("Comprueba tu correo")).toBeVisible();

    // Enlace de acceso de un solo uso recibido por correo (cliente verificado).
    const accessToken = await waitEmailToken("access", clientEmail);
    await page.goto(`/card/access?token=${accessToken}&m=${merchantSlug}`);
    await page.getByRole("button", { name: "Abrir mis tarjetas" }).click();
    await page.waitForURL(/\/my-card\/.+\/cards$/);
    await expect(page.getByRole("heading", { name: "Tus tarjetas" })).toBeVisible();
    await expect(page.locator('a[href*="/card/"]').first()).toBeVisible();

    // Un solo uso: reutilizar el enlace no abre nada, pero guía al cliente en
    // vez de dejarlo sin salida (la sesión del dispositivo sigue viva).
    await page.goto(`/card/access?token=${accessToken}&m=${merchantSlug}`);
    await page.getByRole("button", { name: "Abrir mis tarjetas" }).click();
    await expect(page.getByText("Enlace no válido")).toBeVisible();
    await expect(page.getByRole("link", { name: "Ver mis tarjetas" })).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Pedir un enlace nuevo por correo" }),
    ).toBeVisible();
  });
});

test.describe("mostrador y ciclo de vida de la tarjeta", () => {
  test("sello y canje confirmados; la suspensión bloquea las operaciones", async ({ page }) => {
    // El mismo cliente se apunta al segundo programa (se reutiliza su email):
    // tendrá dos tarjetas y el mostrador debe elegir la promoción correcta.
    const enrollB = await page.request.post(
      `/api/v1/public/programs/${merchantSlug}/${programBSlug}/enroll`,
      {
        data: {
          email: clientEmail,
          display_name: "Cliente E2E",
          accepted_terms_version: 1,
          privacy_notice_version: 1,
        },
      },
    );
    expect(enrollB.status()).toBe(201);

    await loginPanel(page);

    // +1 sello: la confirmación la da el backend, no la interfaz.
    await buscarTarjeta(page);
    await expect(page.getByText("Estado de la tarjeta: Activa")).toBeVisible();

    // Con dos programas, aparece el selector de promoción (ADR-0008).
    await expect(page.getByRole("button", { name: /Club E2E/ })).toBeVisible();
    const chipMenu = page.getByRole("button", { name: /Menú E2E/ });
    await expect(chipMenu).toBeVisible();

    // Cambiar de promoción y volver: la activa manda en las operaciones.
    await chipMenu.click();
    await expect(page.getByRole("heading", { name: "Menú E2E" })).toBeVisible();
    await page.getByRole("button", { name: /Club E2E/ }).click();
    await expect(page.getByRole("heading", { name: "Club E2E" })).toBeVisible();

    await page.click('button:has-text("+1 sello (visita)")');
    await expect(page.getByText(/Sello añadido/)).toBeVisible();

    // Segundo sello → alcanza la recompensa y se canjea.
    await page.click('button:has-text("+1 sello (visita)")');
    await expect(page.getByText("Sello añadido: la tarjeta tiene 2 sellos.")).toBeVisible();
    await page.click('button:has-text("Canjear: Café gratis E2E (2)")');
    await expect(page.getByText(/Recompensa canjeada/)).toBeVisible();

    // Suspender desde el panel (con confirmación explícita). El cliente tiene
    // dos tarjetas: se suspende la del programa «Club E2E».
    await page.goto(`/merchants/${merchantId}/members`);
    const filaClub = page.locator("tr", { hasText: "Club E2E" }).filter({ visible: true }).first();
    await filaClub.locator('button:has-text("Suspender")').click();
    await page.locator('[role="dialog"] button:has-text("Suspender tarjeta")').click();
    await expect(page.getByText("Tarjeta suspendida")).toBeVisible();

    // La tarjeta suspendida no opera: lo dice el servidor y la UI lo refleja.
    await buscarTarjeta(page);
    await expect(page.getByText("Estado de la tarjeta: Suspendida")).toBeVisible();
    await expect(page.getByText(/no puede sumar sellos ni canjear/)).toBeVisible();
    await expect(page.locator('button:has-text("+1 sello (visita)")')).toBeDisabled();
    await expect(page.locator('button:has-text("Canjear:")').first()).toBeDisabled();
  });

  test("el escáner QR conserva siempre el código manual como respaldo", async ({ page }) => {
    // Regresión (14/10): `Permissions-Policy: camera=()` hacía que el
    // navegador denegara la cámara sin llegar a preguntar en móviles reales.
    const head = await page.request.get("/merchants");
    expect(head.headers()["permissions-policy"] ?? "").toContain("camera=(self)");

    await loginPanel(page);
    await page.goto(`/merchants/${merchantId}/operations`);

    await page.click('button:has-text("Escanear QR")');
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog.getByText("Escanear la tarjeta del cliente")).toBeVisible();
    // Sin permiso de cámara (o sin cámara) el sistema explica el motivo en
    // claro y ofrece la vía manual; nunca un estado falso de "escaneando".
    await expect(
      dialog.getByText(/permiso de cámara|escanear con la cámara|usar la cámara|Apunta al QR/),
    ).toBeVisible();

    await dialog.locator('button:has-text("Usar el código manual")').click();
    await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    await expect(page.locator("#card-code")).toBeVisible();
  });

  test("la etiqueta de mostrador preselecciona el programa correcto", async ({ page }) => {
    // La URL corta de la etiqueta redirige a operaciones con ?program= y
    // **nunca** suma sellos por sí sola (requiere personal autenticado).
    const redirect = await page.request.get(`/go/${counterTagSlug}`, { maxRedirects: 0 });
    expect(redirect.status()).toBe(302);
    expect(redirect.headers()["location"] ?? "").toContain(
      `/operations?program=${programBId}`,
    );

    await loginPanel(page);
    // El personal toca la etiqueta del «Menú»: la página sigue la redirección
    // real del tag y abre las operaciones con esa promoción preseleccionada.
    await page.goto(`/go/${counterTagSlug}`);
    await expect(page).toHaveURL(new RegExp(`/operations\\?program=${programBId}`));
    // Al escanear la tarjeta del cliente (que también está en el Club), la
    // promoción activa es la del Menú: la etiqueta manda.
    await page.fill("#card-code", cardToken);
    await page.click('button:has-text("Buscar tarjeta")');
    await expect(page.getByRole("heading", { name: "Menú E2E" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Club E2E/ })).toBeVisible();
  });

  test("la tarjeta del cliente se actualiza sin recargar (sondeo)", async ({ page }) => {
    // La página de tarjeta se abre UNA vez y queda a la vista del cliente…
    await page.goto(`/card/${realtimeToken}`);
    await expect(page.getByTestId("card-stamps")).toHaveText("0");

    // …el personal suma el sello desde caja (misma API real de Operaciones)…
    const lookup = await api.post(`/api/v1/merchants/${merchantId}/memberships/lookup`, {
      data: { token: realtimeToken },
    });
    expect(lookup.ok()).toBeTruthy();
    const membershipId = ((await lookup.json()) as { id: string }).id;
    const earn = await api.post(
      `/api/v1/merchants/${merchantId}/memberships/${membershipId}/earn`,
      { data: { quantity: 1, idempotency_key: `realtime-${Date.now()}` } },
    );
    expect(earn.status()).toBe(201);

    // …y el sello aparece en la tarjeta SIN recargar (sondeo cada 10 s).
    await expect(page.getByTestId("card-stamps")).toHaveText("1", { timeout: 20_000 });
  });
});
