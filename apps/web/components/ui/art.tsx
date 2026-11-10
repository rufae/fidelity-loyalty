/**
 * Ilustraciones propias del producto (§10.4): SVG inline, paleta de marca y
 * trazo redondeado. Sin imágenes externas ni dependencias nuevas.
 *
 * Dos reglas al dibujar aquí:
 *  1. `aria-hidden` siempre: acompañan texto real, nunca lo sustituyen.
 *  2. `currentColor` no se usa: la paleta es la del tema, pero pintada en la
 *     propia pieza para que cada escena impone su composición de color.
 */

type SizeProps = { className?: string };

const common = "pointer-events-none select-none";

export function ArtStorefront({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 160 120"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Cielo */}
      <circle cx="132" cy="22" r="11" fill="#f7bd4b" />
      <path d="M146 30c6 0 10 4 10 9s-4 9-10 9" stroke="#f7bd4b" strokeWidth="3" strokeLinecap="round" opacity="0.5" />
      {/* Fachada */}
      <path d="M18 108h124" stroke="#1c1929" strokeWidth="3" strokeLinecap="round" />
      <rect x="26" y="46" width="108" height="60" rx="6" fill="#fbf9f5" stroke="#1c1929" strokeWidth="3" />
      {/* Toldo */}
      <path d="M18 46h124l-10-18a6 6 0 0 0-5.6-4H33.6A6 6 0 0 0 28 28l-10 18z" fill="#5b48d6" />
      <path d="M34 30l-4 32M56 30l-6 32M80 30v32M104 30l6 32M126 30l4 32" stroke="rgba(255,255,255,0.45)" strokeWidth="3" strokeLinecap="round" />
      <path d="M24 52h112" stroke="rgba(91,72,214,0.5)" strokeWidth="3" strokeLinecap="round" />
      {/* Puerta y ventana */}
      <rect x="34" y="62" width="30" height="44" rx="4" fill="#f1ece3" stroke="#1c1929" strokeWidth="3" />
      <circle cx="58" cy="84" r="2.5" fill="#1c1929" />
      <rect x="78" y="62" width="44" height="30" rx="4" fill="#ddf5f0" stroke="#1c1929" strokeWidth="3" />
      <path d="M84 88h32" stroke="#1c1929" strokeWidth="3" strokeLinecap="round" />
      {/* Banderines */}
      <path d="M22 10h116" stroke="#1c1929" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M28 10l-4 9 8 0zM46 10l-4 9 8 0zM64 10l-4 9 8 0zM96 10l-4 9 8 0zM114 10l-4 9 8 0z" fill="#f7bd4b" stroke="#1c1929" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

export function ArtCoffeeCup({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 120 120"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Vapor */}
      <path d="M46 34c0-8 10-8 10-16M62 30c0-8 10-8 10-16" stroke="#c25e22" strokeWidth="3.5" strokeLinecap="round" opacity="0.75" />
      {/* Taza */}
      <path d="M32 52h48l-5 38a8 8 0 0 1-8 7H45a8 8 0 0 1-8-7l-5-38z" fill="#fbf9f5" stroke="#1c1929" strokeWidth="3" strokeLinejoin="round" />
      <path d="M32 62h48l-1.5 12a4 4 0 0 1-4 3.5H37.5a4 4 0 0 1-4-3.5L32 62z" fill="#8b5e3c" opacity="0.25" />
      <path d="M80 58h6a10 10 0 0 1 0 20h-4" stroke="#1c1929" strokeWidth="3" strokeLinecap="round" />
      {/* Platito */}
      <path d="M26 104h64" stroke="#1c1929" strokeWidth="3" strokeLinecap="round" />
      {/* Corazón de agradecimiento */}
      <path
        d="M96 32c0-5 4-8 9-7 4 1 6 5 4 9-1 3-7 9-9 11-2-2-8-8-9-11-2-4 0-8 4-9 2-0.8 1 7 1 7z"
        fill="#d9544a"
        transform="translate(-2 -6) scale(0.9)"
      />
    </svg>
  );
}

export function ArtNfcTap({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 140 120"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Móvil acercándose a la etiqueta */}
      <rect x="18" y="30" width="42" height="72" rx="8" fill="#1c1929" />
      <rect x="22" y="34" width="34" height="64" rx="5" fill="#eeebfd" />
      <circle cx="39" cy="88" r="2.5" fill="#eeebfd" opacity="0.8" />
      {/* Etiqueta redonda */}
      <circle cx="100" cy="66" r="26" fill="#fdf2d7" stroke="#1c1929" strokeWidth="3" />
      <path d="M92 56a14 14 0 0 1 16 0M96 62a9 9 0 0 1 8 0" stroke="#a56a12" strokeWidth="3" strokeLinecap="round" />
      <circle cx="100" cy="70" r="3" fill="#a56a12" />
      {/* Ondas NFC */}
      <path d="M88 34a34 34 0 0 1 24 0M96 42a22 22 0 0 1 8 0" stroke="#0e8a78" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* Chispas */}
      <path d="M70 20l3 6 6 1-4.5 4.5 1 6.5-5.5-3-5.5 3 1-6.5L61 27l6-1 3-6z" fill="#f7bd4b" transform="scale(0.9)" />
    </svg>
  );
}

export function ArtQrScan({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 140 120"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Tarjeta apoyada */}
      <rect x="16" y="24" width="60" height="78" rx="10" fill="#fbf9f5" stroke="#1c1929" strokeWidth="3" />
      <rect x="24" y="34" width="26" height="26" rx="4" fill="#1c1929" />
      <rect x="31" y="41" width="12" height="12" rx="2" fill="#fbf9f5" />
      <circle cx="86" cy="40" r="5" fill="#0e8a78" />
      <path d="M28 76h36M28 84h22" stroke="rgba(28,25,41,0.35)" strokeWidth="4" strokeLinecap="round" />
      {/* Móvil escaneando, en ángulo sobre la tarjeta */}
      <g transform="rotate(12 96 78)">
        <rect x="72" y="46" width="46" height="74" rx="9" fill="#1c1929" />
        <rect x="76" y="50" width="38" height="66" rx="6" fill="#f1ece3" />
        <rect x="84" y="60" width="22" height="22" rx="3" fill="none" stroke="#5b48d6" strokeWidth="2.6" />
        <path d="M88 66v-4h4M102 66v-4h-4M88 80v4h4M102 80v4h-4" stroke="#5b48d6" strokeWidth="2.4" strokeLinecap="round" />
      </g>
      {/* Chispa de confirmación */}
      <path d="M104 24l3 6 6 1-4.5 4.5 1 6.5-5.5-3-5.5 3 1-6.5L95 31l6-1 3-6z" fill="#f7bd4b" />
    </svg>
  );
}

export function ArtRewards({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 120 120"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Estrella grande con rayos */}
      <path
        d="M60 18l11 22 24 3-18 17 5 24-22-12-22 12 5-24-18-17 24-3 11-22z"
        fill="#fdf2d7"
        stroke="#a56a12"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path d="M18 34c-5 2-9 5-12 9M102 34c5 2 9 5 12 9M10 84c4 2 8 3 12 3M110 84c-4 2-8 3-12 3" stroke="#f7bd4b" strokeWidth="3" strokeLinecap="round" opacity="0.8" />
      {/* Corazón flotante */}
      <path
        d="M24 58c0-4 3-6 6-5 3 0.8 4 3.6 3 6.5-0.8 2-4.4 6.4-5.6 8-1.2-1.6-4.8-6-5.6-8-1-2.9 0.4-5.7 2.2-6.5z"
        fill="#d9544a"
      />
      {/* Pasos de confeti */}
      <path d="M78 20c4-2 9-2 13 1M26 22c-4-2-9-2-13 1" stroke="#5b48d6" strokeWidth="2.6" strokeLinecap="round" opacity="0.6" />
    </svg>
  );
}

/** Swoosh decorativo, a mano alzada, para subrayar una palabra clave. */
export function ArtUnderline({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 220 22"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      preserveAspectRatio="none"
      focusable="false"
    >
      <path
        d="M6 15c46-11 112-13 208-7"
        stroke="#f7bd4b"
        strokeWidth="8"
        strokeLinecap="round"
        opacity="0.85"
      />
      <path
        d="M12 20c40-8 96-10 196-5"
        stroke="#a56a12"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.75"
      />
    </svg>
  );
}

/** Chispas pequeñas para acompañar un titular. */
export function ArtSparkles({ className = "" }: SizeProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      className={`${common} ${className}`}
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M14 22l3.5 7L25 32.5l-7.5 3.5L14 44l-3.5-8L3 32.5l7.5-3.5L14 22z" fill="#f7bd4b" opacity="0.9" />
      <path d="M44 12l2.5 5 5 2.5-5 2.5L44 27l-2.5-5-5-2.5 5-2.5L44 12z" fill="#5b48d6" opacity="0.6" />
      <path d="M50 44l2 4 4 2-4 2-2 4-2-4-4-2 4-2 2-4z" fill="#0e8a78" opacity="0.55" />
    </svg>
  );
}
