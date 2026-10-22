import Link from "next/link";

import { LoyaltyCard } from "@/components/ui/loyalty-card";
import { BrandLogo, LinkButton } from "@/components/ui/primitives";
import {
  IconArrowRight,
  IconCheck,
  IconContactless,
  IconGift,
  IconLock,
  IconQr,
  IconScan,
  IconSparkles,
  IconStar,
  IconUser,
  IconUsers,
  IconWallet,
} from "@/components/ui/icons";

/**
 * Portada pública: cálida y directa, como el mostrador de un buen comercio.
 *
 * Separa con claridad los dos públicos —comercios (entran al panel) y clientes
 * finales (llegan por la etiqueta NFC/QR o por el enlace de su correo)— y
 * enseña la tarjeta como objeto central. La tarjeta de muestra está rotulada
 * como ejemplo: nunca se presenta como un dato real.
 */
export function LandingView() {
  const merchantPoints = [
    { icon: IconGift, text: "Programas de sellos y recompensas, sin instalar nada." },
    { icon: IconWallet, text: "Tarjeta digital con QR y opciones de Apple/Google Wallet." },
    { icon: IconContactless, text: "Etiquetas NFC y QR de alta, de recuperación y de reseñas." },
    { icon: IconStar, text: "Enlace de reseñas de Google neutral, sin filtros ni premios." },
  ];
  const clientSteps = [
    "Acerca el móvil a la etiqueta o escanea el QR del comercio.",
    "Déjate el nombre y el correo; acepta las condiciones del programa.",
    "Confirma tu correo y guarda el enlace personal de tu tarjeta.",
    "En caja muestra el QR para sumar sellos o canjear premios.",
  ];
  const principles = [
    { icon: IconUser, text: "Sin instalar ninguna app" },
    { icon: IconLock, text: "Solo los datos necesarios" },
    { icon: IconStar, text: "Reseñas voluntarias y neutrales" },
  ];

  return (
    <main className="flex min-h-screen flex-col">
      {/* Título de página para lectores de pantalla y para el anuncio de ruta:
          distinto del titular visible, evita duplicar el texto en el DOM. */}
      <h1 className="sr-only">LocalAI Fidelity · Fidelización y reseñas para negocios locales</h1>
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-5 py-5 sm:px-8">
        <BrandLogo />
        <div className="flex items-center gap-2">
          <a
            href="#clientes"
            className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink sm:inline-flex"
          >
            Cómo funciona
          </a>
          <LinkButton
            href="/login"
            variant="secondary"
            size="sm"
            icon={<IconLock size={15} />}
            ariaLabel="Acceso comercios"
          >
            <span className="sm:hidden">Acceso</span>
            <span className="hidden sm:inline">Acceso comercios</span>
          </LinkButton>
        </div>
      </header>

      {/* Héroe: la tarjeta es la protagonista, no una rejilla de ventajas. */}
      <section className="relative mx-auto w-full max-w-6xl px-5 pb-10 pt-6 sm:px-8 sm:pb-16 sm:pt-10">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <div className="animate-in">
            <p className="inline-flex items-center gap-2 rounded-full border border-brand/15 bg-brand-soft/70 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.13em] text-brand">
              <span aria-hidden="true" className="size-1.5 rounded-full bg-brand" />
              Fidelización y reseñas para negocios de barrio
            </p>
            <h1 className="mt-5 text-[38px] font-bold leading-[1.04] tracking-[-0.03em] text-ink sm:text-[52px]">
              Tu programa de fidelización, funcionando en minutos
            </h1>
            <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-ink-soft sm:text-[17px]">
              Tarjetas digitales con sellos y premios, altas por etiqueta NFC o QR y un acceso
              independiente para que tus clientes lleguen a tus reseñas de Google cuando quieran,
              sin filtros ni incentivos.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <LinkButton href="/login" size="lg" icon={<IconArrowRight size={17} />}>
                Acceder al panel
              </LinkButton>
              <a
                href="#clientes"
                className="inline-flex h-12 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-ink-soft transition-colors hover:text-brand"
              >
                Ver el recorrido del cliente
                <span aria-hidden="true">↓</span>
              </a>
            </div>

            <ul className="mt-8 flex flex-wrap gap-x-5 gap-y-2.5">
              {principles.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-2 text-[13px] font-medium text-ink-soft">
                  <span className="flex size-6 items-center justify-center rounded-full bg-surface-2 text-ink-soft">
                    <Icon size={13} />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
          </div>

          {/* Composición: tarjeta real del sistema, rotulada como ejemplo. */}
          <div className="relative mx-auto w-full max-w-md lg:max-w-none">
            <div
              aria-hidden="true"
              className="absolute inset-x-6 top-6 h-[86%] rotate-[3.5deg] rounded-[26px] border border-line-strong bg-sand shadow-soft"
            />
            <div
              aria-hidden="true"
              className="absolute inset-x-3 top-3 h-[93%] rotate-[1.5deg] rounded-[26px] border border-line bg-paper shadow-soft"
            />
            <div className="relative">
              <LoyaltyCard
                merchantName="Café La Esquina"
                programName="Club de sellos"
                stamps={7}
                holderName="Ejemplo de tarjeta"
                rewards={[
                  { name: "Café gratis", stamps_required: 8 },
                  { name: "Desayuno completo", stamps_required: 12 },
                ]}
                variant="hero"
                floating
              />
              <span className="absolute -top-3 right-4 rounded-full border border-line bg-surface px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-ink-soft shadow-soft">
                Ejemplo
              </span>
            </div>

            {/* Pequeño ticket de recompensa: refuerza el concepto sin datos falsos. */}
            <div className="absolute -bottom-7 -left-3 hidden w-52 -rotate-3 sm:block">
              <div className="ticket-notch rounded-xl border border-gold/25 bg-gold-soft px-4 py-3 shadow-soft">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-gold">
                  Próxima recompensa
                </p>
                <p className="mt-1 text-sm font-bold text-ink">Café gratis</p>
                <p className="text-[11px] text-ink-soft">A un sello de conseguirlo</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Franja de principios: hechos del producto, no métricas inventadas. */}
      <section className="border-y border-line bg-paper/70">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 px-5 py-6 sm:grid-cols-3 sm:px-8">
          {[
            {
              icon: IconQr,
              title: "La tarjeta, siempre a mano",
              text: "En el navegador, en el correo o en Wallet cuando el emisor está configurado.",
            },
            {
              icon: IconScan,
              title: "Mostrador en dos toques",
              text: "El personal escanea el QR, suma el sello y ve el saldo confirmado por el servidor.",
            },
            {
              icon: IconSparkles,
              title: "Cada operación, trazable",
              text: "Sellos y canjes quedan en un libro auditable: nada se edita a mano por detrás.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex items-start gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-surface text-brand shadow-soft">
                <Icon size={17} />
              </span>
              <div>
                <p className="text-[13px] font-bold text-ink">{title}</p>
                <p className="mt-0.5 text-[12px] leading-relaxed text-ink-soft">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dos públicos, dos recorridos. */}
      <section className="mx-auto w-full max-w-6xl flex-1 px-5 py-12 sm:px-8 sm:py-16">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.05fr_0.95fr]">
          <article className="relative flex flex-col overflow-hidden rounded-3xl border border-line bg-surface p-6 shadow-soft sm:p-8">
            <span
              aria-hidden="true"
              className="absolute right-0 top-0 h-24 w-24 rounded-bl-[64px] bg-brand-soft"
            />
            <span className="relative flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-brand">
              <IconGift size={24} />
            </span>
            <h2 className="relative mt-5 text-[24px] font-bold tracking-tight text-ink">
              Para tu comercio
            </h2>
            <p className="relative mt-1.5 max-w-md text-sm leading-relaxed text-ink-soft">
              Configura el programa, opera en el mostrador y sigue las cifras reales de tu negocio.
              Sin hojas de cálculo y sin desarrollos a medida.
            </p>
            <ul className="relative mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {merchantPoints.map(({ icon: Icon, text }) => (
                <li
                  key={text}
                  className="flex items-start gap-2.5 rounded-xl border border-line bg-paper p-3 text-[13px] leading-snug text-ink"
                >
                  <Icon size={16} className="mt-0.5 shrink-0 text-brand" />
                  <span>{text}</span>
                </li>
              ))}
            </ul>
            <div className="relative mt-auto flex flex-wrap items-center gap-3 pt-7">
              <LinkButton href="/login" size="lg" icon={<IconArrowRight size={17} />}>
                Acceder al panel
              </LinkButton>
              <span className="text-xs leading-snug text-ink-faint">
                El acceso lo entrega la administración de la plataforma.
              </span>
            </div>
          </article>

          <article
            id="clientes"
            className="relative flex scroll-mt-6 flex-col overflow-hidden rounded-3xl border border-line bg-paper p-6 shadow-soft sm:p-8"
          >
            <span className="flex size-12 items-center justify-center rounded-2xl bg-teal-soft text-teal">
              <IconScan size={24} />
            </span>
            <h2 className="mt-5 text-[24px] font-bold tracking-tight text-ink">
              Para tus clientes
            </h2>
            <p className="mt-1.5 max-w-md text-sm leading-relaxed text-ink-soft">
              No instalan ninguna app: su tarjeta vive en el navegador y llega a su correo.
            </p>
            <ol className="mt-6 space-y-0">
              {clientSteps.map((text, index) => (
                <li key={text} className="relative flex gap-3 pb-4 last:pb-0">
                  {index < clientSteps.length - 1 && (
                    <span
                      aria-hidden="true"
                      className="absolute left-[13px] top-7 h-[calc(100%-20px)] w-px bg-line-strong"
                    />
                  )}
                  <span className="relative flex size-7 shrink-0 items-center justify-center rounded-full border border-teal/25 bg-surface text-[11px] font-bold text-teal">
                    {index + 1}
                  </span>
                  <span className="pt-1 text-[13px] leading-snug text-ink">{text}</span>
                </li>
              ))}
            </ol>
            <p className="mt-5 flex items-start gap-2 rounded-xl border border-line bg-surface p-3 text-xs leading-relaxed text-ink-soft">
              <IconUsers size={15} className="mt-0.5 shrink-0 text-teal" />
              <span>
                ¿Perdiste el enlace de tu tarjeta? Pide en el comercio la etiqueta «Recuperar mi
                tarjeta»: te enviaremos un enlace personal a tu correo.
              </span>
            </p>
          </article>
        </div>

        {/* Compromiso de reseñas: visible, breve y sin letra pequeña. */}
        <div className="mt-6 flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gold-soft text-gold">
              <IconStar size={19} />
            </span>
            <div>
              <p className="text-sm font-bold text-ink">Reseñas de Google, siempre voluntarias</p>
              <p className="mt-0.5 max-w-2xl text-[13px] leading-relaxed text-ink-soft">
                La plataforma no premia, filtra ni condiciona las opiniones de nadie. Solo facilita
                el enlace oficial del comercio.
              </p>
            </div>
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] font-medium text-ink-soft">
            {["Sin filtros", "Sin incentivos", "Sin automatizar reseñas"].map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <IconCheck size={13} className="text-ok" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="border-t border-line bg-paper">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-xs text-ink-faint sm:px-8">
          <span>LocalAI Fidelity · fidelización digital para negocios locales</span>
          <span className="flex items-center gap-3">
            <Link href="/login" className="font-semibold text-ink-soft hover:text-brand">
              Acceso comercios
            </Link>
            <span aria-hidden="true">·</span>
            <span>Acceso reservado al personal autorizado</span>
          </span>
        </div>
      </footer>
    </main>
  );
}
