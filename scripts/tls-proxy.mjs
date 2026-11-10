/**
 * Proxy TLS de desarrollo para pruebas desde la red local (sin VPN).
 *
 * Motivo: la cámara (`getUserMedia`) solo funciona en un contexto seguro, es
 * decir sobre **HTTPS**. Este proxy termina el TLS con un certificado
 * autofirmado (SAN con la IP de LAN) y reenvía al web de Docker que ya corre
 * en `127.0.0.1:8100`. Así el web sigue escuchando solo en loopback (§16.2) y
 * lo único alcanzable desde la LAN es este proxy.
 *
 * Uso:
 *   node scripts/tls-proxy.mjs
 *   → https://192.168.1.110:8443  (el móvil avisa de certificado no confiable;
 *     aceptas una vez y la cámara funciona, porque la conexión es HTTPS)
 *
 * El navegador mostrará un aviso de certificado porque autofirmado no está en
 * la lista de confianza del móvil. Opciones:
 *   - Android/Chrome: «Advanced → Proceed» y la cámara ya funciona.
 *   - Instalar `apps/web/.certs/dev-lan-cert.pem` como certificado de
 *     usuario en el móvil → sin avisos.
 *   - iOS: Safari bloquea certificados autofirmados con más firmeza; usar
 *     Tailscale en su lugar si hace falta.
 *
 * Solo módulos nativos de Node: sin dependencias nuevas.
 */

import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const LISTEN_HOST = process.env.TLS_PROXY_HOST || "0.0.0.0";
const LISTEN_PORT = Number(process.env.TLS_PROXY_PORT || 8443);
const TARGET_HOST = process.env.TLS_PROXY_TARGET_HOST || "127.0.0.1";
const TARGET_PORT = Number(process.env.TLS_PROXY_TARGET_PORT || 8100);

const KEY_PATH = path.resolve(ROOT, process.env.TLS_KEY || "apps/web/.certs/dev-lan-key.pem");
const CERT_PATH = path.resolve(ROOT, process.env.TLS_CERT || "apps/web/.certs/dev-lan-cert.pem");

for (const file of [KEY_PATH, CERT_PATH]) {
  if (!fs.existsSync(file)) {
    console.error(
      `No existe ${file}. Genera el certificado:\n` +
        `  openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 825 \\\n` +
        `    -keyout apps/web/.certs/dev-lan-key.pem \\\n` +
        `    -out apps/web/.certs/dev-lan-cert.pem \\\n` +
        `    -subj "/CN=192.168.1.110" \\\n` +
        `    -addext "subjectAltName=IP:192.168.1.110,IP:127.0.0.1,DNS:localhost"`,
    );
    process.exit(1);
  }
}

/** Cabeceras que gestiona Node al reenviar; no deben viajar tal cual. */
const DROP_REQUEST_HEADERS = new Set(["host", "connection", "keep-alive", "proxy-connection", "upgrade"]);

function forwardHeaders(incoming) {
  const headers = {};
  for (const [key, value] of Object.entries(incoming)) {
    if (DROP_REQUEST_HEADERS.has(key.toLowerCase())) continue;
    headers[key] = value;
  }
  headers.host = `${TARGET_HOST}:${TARGET_PORT}`;
  // El origen real es HTTPS: útil para la lógica de cookies/URLs aguas abajo.
  headers["x-forwarded-proto"] = "https";
  headers["x-forwarded-host"] = incoming.host || `${LISTEN_HOST}:${LISTEN_PORT}`;
  return headers;
}

const server = https.createServer(
  { key: fs.readFileSync(KEY_PATH), cert: fs.readFileSync(CERT_PATH) },
  (req, res) => {
    const proxyReq = http.request(
      {
        host: TARGET_HOST,
        port: TARGET_PORT,
        method: req.method,
        path: req.url,
        headers: forwardHeaders(req.headers),
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode ?? 502, proxyRes.statusMessage, proxyRes.headers);
        proxyRes.pipe(res);
      },
    );
    proxyReq.on("error", () => {
      if (!res.headersSent) {
        res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
      }
      res.end("Bad Gateway: el servicio web no está disponible.");
    });
    req.pipe(proxyReq);
  },
);

// WebSocket (HMR u otros): se reenvía el intercambio de cabeceras y se tubean
// los datos en ambos sentidos.
server.on("upgrade", (req, socket, head) => {
  const proxyReq = http.request({
    host: TARGET_HOST,
    port: TARGET_PORT,
    method: req.method,
    path: req.url,
    headers: forwardHeaders(req.headers),
  });
  proxyReq.on("upgrade", (proxyRes, proxySocket, proxyHead) => {
    const lines = [`HTTP/1.1 ${proxyRes.statusCode} ${proxyRes.statusMessage}`];
    for (const [key, value] of Object.entries(proxyRes.headers)) {
      lines.push(`${key}: ${Array.isArray(value) ? value.join(", ") : value}`);
    }
    socket.write(`${lines.join("\r\n")}\r\n\r\n`);
    if (proxyHead?.length) proxySocket.write(proxyHead);
    proxySocket.pipe(socket);
    socket.pipe(proxySocket);
  });
  proxyReq.on("error", () => socket.destroy());
  if (head?.length) proxyReq.write(head);
  proxyReq.end();
});

server.listen(LISTEN_PORT, LISTEN_HOST, () => {
  console.log(`Proxy TLS de desarrollo`);
  console.log(`  https://${LISTEN_HOST}:${LISTEN_PORT}  →  http://${TARGET_HOST}:${TARGET_PORT}`);
  console.log(`  (desde la LAN: https://192.168.1.110:${LISTEN_PORT})`);
  console.log(`  El web de destino debe estar levantado: docker compose up -d web`);
});
