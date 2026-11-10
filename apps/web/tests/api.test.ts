/**
 * El cliente de API traduce SIEMPRE los fallos a lenguaje de persona:
 * ningún cliente final debe ver "Failed to fetch", un número HTTP pelado
 * o los detalles de validación en inglés de FastAPI.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch, ApiError } from "../lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiFetch: mensajes de error para humanos", () => {
  it("el 422 de validación no muestra inglés ni jerga técnica", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            detail: [{ loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" }],
          }),
          { status: 422 },
        ),
      ),
    );

    const err = await apiFetch("/api/v1/test", { method: "POST" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toBe(
      "Alguno de los datos del formulario no es válido. Revisa los campos e inténtalo de nuevo.",
    );
  });

  it("conserve el mensaje estructurado del backend ({code, message})", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ detail: { code: "invalid_credentials", message: "Credenciales incorrectas" } }),
          { status: 401 },
        ),
      ),
    );

    const err = await apiFetch("/api/v1/test").catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("invalid_credentials");
    expect((err as ApiError).message).toBe("Credenciales incorrectas");
  });

  it("traduce los detalles por defecto de FastAPI («Not Found», «Forbidden»)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Not Found", { status: 404 })));

    const err = await apiFetch("/api/v1/test").catch((e: unknown) => e);
    expect((err as ApiError).message).toBe("No hemos encontrado lo que buscabas.");
  });

  it("una respuesta sin cuerpo útil no muestra «Error 409» pelado", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>gateway</html>", { status: 409 })));

    const err = await apiFetch("/api/v1/test", { method: "POST" }).catch((e: unknown) => e);
    expect((err as ApiError).message).toContain("Recarga la página");
  });

  it("la red caída se explica en español, con status 0", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));

    const err = await apiFetch("/api/v1/test").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(0);
    expect((err as ApiError).code).toBe("network_error");
    expect((err as ApiError).message).toContain("No hay conexión con el servidor");
  });

  it("un cuerpo 200 roto (proxy) no estalla con TypeError sin sentido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{no es json", { status: 200 })),
    );

    const err = await apiFetch("/api/v1/test").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe("bad_response");
  });
});
