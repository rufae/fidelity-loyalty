import type { NextConfig } from "next";

// URL interna del backend. En docker-compose se inyecta `http://api:8101`;
// en local (npm run dev) se usa `http://localhost:8101`.
const apiUrl = process.env.API_URL ?? "http://localhost:8101";

// Cabeceras de seguridad de las páginas (AGENTS.md §16.7). La API añade las
// suyas en `app/main.py`; aquí se cubre el HTML que sirve Next. La CSP no
// permite ningún origen externo: la aplicación no carga CDNs ni fuentes
// remotas. `script-src 'unsafe-inline'` es necesario porque Next inyecta en
// línea el arranque de la hidratación; una CSP con nonces exige render
// dinámico y queda pendiente para la FASE 12 (docs/SECURITY.md).
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  {
    key: "Permissions-Policy",
    // `camera=(self)`: la página de operaciones escanea el QR del cliente con
    // la cámara del propio dispositivo (§8.3). Con `camera=()` el navegador
    // deniega sin preguntar. Micrófono y geolocalización siguen desactivados.
    value: "camera=(self), microphone=(), geolocation=()",
  },
  {
    key: "Content-Security-Policy",
    value:
      "default-src 'self'; base-uri 'self'; object-src 'none'; " +
      "frame-ancestors 'none'; form-action 'self'; " +
      "img-src 'self' data:; font-src 'self' data:; " +
      "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; " +
      "connect-src 'self'; manifest-src 'self'",
  },
];

const nextConfig: NextConfig = {
  // El navegador solo habla con el origen del frontend: la API se proxifica
  // aquí (el frontend nunca accede a la BD ni contiene secretos, §10.5).
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` },
      // Ruta corta de las etiquetas NFC/QR (§12.8): el público la llama a
      // través del dominio de la web, que la proxifica al backend.
      { source: "/go/:slug", destination: `${apiUrl}/go/:slug` },
      { source: "/health", destination: `${apiUrl}/health` },
      { source: "/ready", destination: `${apiUrl}/ready` },
    ];
  },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
