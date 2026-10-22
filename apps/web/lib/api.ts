/** Cliente mínimo de la API: mismo origen, cookie de sesión incluida (§10.5). */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface ErrorBody {
  detail?: { code?: string; message?: string } | string;
  error?: { code?: string; message?: string };
}

function extractError(status: number, body: ErrorBody | null): ApiError {
  const detail = body?.detail;
  if (detail && typeof detail === "object") {
    return new ApiError(status, detail.code ?? "error", detail.message ?? "Error");
  }
  if (typeof detail === "string") {
    return new ApiError(status, "error", detail);
  }
  if (body?.error) {
    return new ApiError(status, body.error.code ?? "error", body.error.message ?? "Error");
  }
  return new ApiError(status, "error", `Error ${status}`);
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isMutating = init?.method !== undefined && init.method !== "GET";
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: {
      ...(isMutating ? { "content-type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let body: ErrorBody | null = null;
    try {
      body = (await response.json()) as ErrorBody;
    } catch {
      body = null;
    }
    throw extractError(response.status, body);
  }
  return (await response.json()) as T;
}
