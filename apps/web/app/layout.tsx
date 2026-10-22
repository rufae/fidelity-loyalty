import localFont from "next/font/local";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

/**
 * Inter variable, autopdetectada (sin red en build ni terceros en la CSP).
 * Es la tipografía de facto de los SaaS profesionales: excelente legibilidad
 * en pantallas pequeñas, dígitos tabulares y rango completo de pesos.
 */
const inter = localFont({
  src: [
    { path: "./fonts/InterVariable.woff2", style: "normal", weight: "100 900" },
    { path: "./fonts/InterVariable-Italic.woff2", style: "italic", weight: "100 900" },
  ],
  display: "swap",
  variable: "--font-inter",
  fallback: ["system-ui", "sans-serif"],
});

export const metadata: Metadata = {
  title: "LocalAI Fidelity",
  description:
    "Plataforma de fidelización digital: tarjetas Apple/Google Wallet, puntos y sellos, etiquetas NFC/QR y enlaces de reseñas",
};

export const viewport: Viewport = {
  themeColor: "#6c5ce7",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={inter.variable}>
      <body className="min-h-screen bg-canvas font-sans text-ink antialiased">
        {/* Degradado único de la marca: varias instancias del logo lo comparten
            y sigue disponible aunque la primera esté dentro de un panel oculto. */}
        <svg
          width="0"
          height="0"
          aria-hidden="true"
          focusable="false"
          className="absolute"
        >
          <defs>
            <linearGradient
              id="lm-brand"
              x1="6"
              y1="4"
              x2="42"
              y2="44"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor="#6C5CE7" />
              <stop offset="0.55" stopColor="#4D8DFF" />
              <stop offset="1" stopColor="#16B8A6" />
            </linearGradient>
          </defs>
        </svg>
        {children}
      </body>
    </html>
  );
}
