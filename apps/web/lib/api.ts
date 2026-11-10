/** Cliente mínimo de la API: mismo origen, cookie de sesión incluida (§10.5). */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface ErrorBody {
  detail?: { code?: string; message?: string } | Array<{ loc?: unknown; msg?: string }> | string;
  error?: { code?: string; message?: string };
}

/** Mensajes de reserva para respuestas sin cuerpo útil (p. ej. un proxy). */
const FALLBACK_MESSAGES: Record<number, string> = {
  400: "La petición no es válida. Revisa los datos e inténtalo de nuevo.",
  401: "Tu sesión ha caducado. Vuelve a entrar para continuar.",
  403: "No tienes permiso para esta acción.",
  404: "No hemos encontrado lo que buscabas.",
  409: "La operación choca con el estado actual. Recarga la página e inténtalo de nuevo.",
  429: "Demasiadas peticiones. Espera unos segundos e inténtalo de nuevo.",
  500: "Ha pasado algo inesperado en el servidor. Inténtalo de nuevo.",
};

/** Textos de detalle que FastAPI responde por defecto, en inglés. */
const DEFAULT_DETAIL_MESSAGES: Record<string, string> = {
  "Not Found": FALLBACK_MESSAGES[404],
  "Method Not Allowed": "La acción no está disponible por esta vía.",
  Forbidden: FALLBACK_MESSAGES[403],
  Unauthorized: FALLBACK_MESSAGES[401],
  "Internal Server Error": FALLBACK_MESSAGES[500],
};

function extractError(status: number, body: ErrorBody | null): ApiError {
  const detail = body?.detail;
  if (detail && typeof detail === "object") {
    if (Array.isArray(detail)) {
      // 422 de validación de FastAPI: nunca en inglés ni con jerga técnica.
      return new ApiError(
        status,
        "validation_error",
        "Alguno de los datos del formulario no es válido. Revisa los campos e inténtalo de nuevo.",
      );
    }
    return new ApiError(status, detail.code ?? "error", detail.message ?? "Error");
  }
  if (typeof detail === "string") {
    const translated = DEFAULT_DETAIL_MESSAGES[detail];
    if (translated) return new ApiError(status, "error", translated);
    return new ApiError(status, "error", detail);
  }
  if (body?.error) {
    return new ApiError(status, body.error.code ?? "error", body.error.message ?? "Error");
  }
  return new ApiError(
    status,
    "error",
    FALLBACK_MESSAGES[status] ?? "No se pudo completar la operación. Inténtalo de nuevo.",
  );
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isMutating = init?.method !== undefined && init.method !== "GET";
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      headers: {
        ...(isMutating ? { "content-type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch (caught) {
    // Red caída, DNS, servidor detenido: siempre en lenguaje de persona, no
    // el "Failed to fetch" crudo del navegador (varias pantallas lo muestran
    // tal cual).
    throw new ApiError(
      0,
      "network_error",
      "No hay conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.",
      { cause: caught instanceof Error ? caught : undefined },
    );
  }

  if (!response.ok) {
    let body: ErrorBody | null = null;
    try {
      body = (await response.json()) as ErrorBody;
    } catch {
      body = null;
    }
    throw extractError(response.status, body);
  }
  try {
    return (await response.json()) as T;
  } catch (caught) {
    // Respuesta 200 con cuerpo roto (proxy intermedio): no estafar a la
    // pantalla llamadora con un TypeError sin sentido.
    throw new ApiError(
      response.status,
      "bad_response",
      "No se pudo leer la respuesta del servidor. Inténtalo de nuevo.",
      { cause: caught instanceof Error ? caught : undefined },
    );
  }
}
