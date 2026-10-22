# Inter — tipografía autopdetectada

- **Origen:** <https://rsms.me/inter/> (The Inter Project Authors).
- **Licencia:** SIL Open Font License 1.1 — ver [`OFL.txt`](./OFL.txt).
- **Archivos:** `InterVariable.woff2` y `InterVariable-Italic.woff2`, tipografía
  variable con rango de peso 100–900 (una sola familia para toda la interfaz).

Se cargan con `next/font/local` desde `app/layout.tsx`: el build no necesita
red, la CSP se mantiene en `font-src 'self'` y no hay dependencias de terceros
en tiempo de ejecución. Si actualizas los `.woff2`, conserva junto a ellos la
licencia OFL y este texto de procedencia.
