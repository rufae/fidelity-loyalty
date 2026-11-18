import Link from "next/link";
import type { CSSProperties } from "react";

import { LandingCardZone } from "@/components/landing-card-zone";
import { LoyaltyCard } from "@/components/ui/loyalty-card";
import { BrandLogo, LinkButton } from "@/components/ui/primitives";
import { ArtCoffeeCup, ArtNfcTap, ArtSparkles, ArtStorefront, ArtUnderline } from "@/components/ui/art";
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
  IconUsers,
  IconWallet,
} from "@/components/ui/icons";

/**
 * Portada pública: cálida y directa, como el mostrador de un buen comercio.
 *
 * El mundo es el mismo («papel cálido»: papel, violeta de marca, tinta,
 * ilustración a mano) llevado a plena potencia para la primera impresión:
 *
 *  - El héroe respira en una aurora propia (halos borrosos de los colores
 *    de la marca) detrás de la tipografía y de la tarjeta.
 *  - La tarjeta es un espécimen vivo: inclina 3D tras el puntero, los
 *    sellos se estampan al entrar, anillos NFC la rodean y la taza humea.
 *  - El cierre hace pico en tinta (mesh de marca) para que el recorrido
 *    tenga compás y no sea un llano de tarjetas.
 *
 * Separa con claridad los dos públicos —comercios y clientes— y enseña la
 * tarjeta como objeto central. La tarjeta de muestra está rotulada como
 * ejemplo: nunca se presenta como un dato real.
 */
export function LandingView() {
  const merchantPoints = [
    { icon: IconGift, text: "Programas de sellos y recompensas, sin instalar nada." },
    { icon: IconWallet, text: "Tarjeta digital con QR; Apple/Google Wallet llegan pronto." },
    { icon: IconContactless, text: "Etiquetas NFC y QR de alta, de recuperación y de reseñas." },
    { icon: IconStar, text: "Enlace de reseñas de Google neutral, sin filtros ni premios." },
  ];
  const clientSteps = [
    "Acerca el móvil a la etiqueta o escanea el QR del comercio.",
    "Déjate el nombre y el correo; acepta las condiciones del programa.",
    "Confirma tu correo y guarda el enlace personal de tu tarjeta.",
    "En caja muestra el QR para sumar sellos o canjear premios.",
  ];

  return (
    <main className="flex min-h-screen flex-col">
      {/* Cabecera: vidrio cálido que acompaña el scroll sin ensuciar el texto. */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-canvas/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <BrandLogo />
          <div className="flex items-center gap-2">
            <a
              href="#clientes"
              className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink sm:inline-flex"
            >
              Cómo funciona
            </a>
            <a
              href="/precios"
              className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink sm:inline-flex"
            >
              Precios
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
        </div>
      </header>

      {/* Héroe: la tarjeta es la protagonista, bajo una aurora de marca. */}
      <section className="relative mx-auto w-full max-w-6xl overflow-x-clip px-5 pb-12 pt-10 sm:px-8 sm:pb-20 sm:pt-14">
        {/* Aurora: tres halos borrosos con los colores ya propios del mundo. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 overflow-hidden rounded-[36px]"
        >
          <div className="animate-drift absolute -top-28 left-[4%] size-80 rounded-full bg-brand-glow/25 blur-3xl" />
          <div className="animate-drift absolute -top-10 right-[2%] size-96 rounded-full bg-gold-bright/15 blur-3xl [animation-delay:-7s]" />
          <div className="animate-drift absolute bottom-[-10%] left-[38%] size-72 rounded-full bg-teal/10 blur-3xl [animation-delay:-4s]" />
        </div>
        <ArtSparkles className="animate-twinkle pointer-events-none absolute right-6 top-4 hidden h-14 w-14 opacity-90 sm:block lg:right-14" />
        <ArtSparkles className="animate-twinkle pointer-events-none absolute left-2 top-40 hidden h-10 w-10 -scale-x-100 opacity-60 xl:block [animation-delay:-1.7s]" />

        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <div className="animate-in">
            <h1 className="text-[40px] font-bold leading-[1.03] tracking-[-0.035em] text-ink sm:text-[54px] lg:text-[62px]">
              Tu programa de fidelización, funcionando{" "}
              <span className="relative mt-2 inline-block sm:mt-3">
                en minutos
                <ArtUnderline
                  draw
                  className="absolute -bottom-2.5 -left-1 h-3.5 w-[104%] sm:-bottom-3.5 sm:-left-2"
                />
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-ink-soft sm:text-[18px]">
              Para negocios de barrio: tarjetas digitales con sellos y premios, altas por etiqueta NFC o QR y
              un acceso independiente para que tus clientes lleguen a tus reseñas de Google cuando quieran,
              sin filtros ni incentivos.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <LinkButton href="/login" size="lg" icon={<IconArrowRight size={17} />}>
                Acceder al panel
              </LinkButton>
              <a
                href="#clientes"
                className="group inline-flex h-12 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-ink-soft transition-colors hover:text-brand"
              >
                Ver el recorrido del cliente
                <span
                  aria-hidden="true"
                  className="transition-transform duration-200 group-hover:translate-y-0.5"
                >
                  ↓
                </span>
              </a>
            </div>

            <ul className="stagger mt-10 flex flex-wrap gap-x-5 gap-y-2.5">
              {[
                { icon: IconWallet, text: "Sin instalar ninguna app" },
                { icon: IconQr, text: "Solo los datos necesarios" },
                { icon: IconStar, text: "Reseñas voluntarias y neutrales" },
              ].map(({ icon: Icon, text }) => (
                <li
                  key={text}
                  className="flex items-center gap-2.5 rounded-xl border border-line bg-surface py-2 pl-2.5 pr-3.5 text-[13px] font-semibold text-ink shadow-soft"
                >
                  <span className="flex size-6 items-center justify-center rounded-lg bg-brand-soft text-brand">
                    <Icon size={13} />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
          </div>

          {/* Espécimen vivo: inclina 3D, estampa sellos, humea y pulsa NFC. */}
          <div className="animate-in mx-auto w-full max-w-md lg:max-w-none">
            <LandingCardZone>
              {/* Anillos NFC: el gesto del producto, en bucle sutil. */}
              <span
                aria-hidden="true"
                className="nfc-ring pointer-events-none absolute -left-3 top-4 z-20 hidden size-16 rounded-full border-2 border-brand/50 sm:block"
              />
              <span
                aria-hidden="true"
                className="nfc-ring pointer-events-none absolute -left-6 top-0 z-20 hidden size-24 rounded-full border-2 border-brand/30 lg:block [animation-delay:1.4s]"
              />

              <div className="tilt-stage relative" style={{ transformStyle: "preserve-3d" }}>
                {/* Folios de papel tras la tarjeta: respiran a su compás. */}
                <div
                  aria-hidden="true"
                  className="sheet-drift absolute inset-x-6 top-6 h-[86%] rounded-[26px] border border-line-strong bg-sand shadow-soft"
                  style={{ "--sheet-rotate": "3.5deg" } as CSSProperties}
                />
                <div
                  aria-hidden="true"
                  className="sheet-drift absolute inset-x-3 top-3 h-[93%] rounded-[26px] border border-line bg-paper shadow-soft"
                  style={{ "--sheet-rotate": "1.5deg", animationDelay: "-4s" } as CSSProperties}
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
                    animateStamps
                  />
                  <span className="absolute -top-3 right-4 rounded-full border border-line bg-surface px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-ink-soft shadow-soft">
                    Ejemplo
                  </span>
                </div>
              </div>

              {/* Ticket de recompensa (la segunda del ejemplo) + taza que humea. */}
              <div className="absolute -bottom-8 -left-3 hidden w-52 sm:block lg:-bottom-7">
                <div className="ticket-notch rounded-xl border border-gold/25 bg-gold-soft px-4 py-3 shadow-soft">
                  <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-gold">
                    La recompensa final
                  </p>
                  <p className="mt-1 text-sm font-bold text-ink">Desayuno completo</p>
                  <p className="text-[11px] text-ink-soft">A cinco sellos de conseguirla</p>
                </div>
              </div>
              <ArtCoffeeCup className="pointer-events-none absolute -bottom-14 right-0 hidden h-24 w-24 opacity-95 xl:block" />
            </LandingCardZone>
          </div>
        </div>
      </section>

      {/* Franja de principios: hechos del producto, no métricas inventadas. */}
      <section className="border-y border-line bg-surface">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-px bg-line sm:grid-cols-3">
          {[
            {
              icon: IconQr,
              title: "La tarjeta, siempre a mano",
              text: "En el navegador o en el correo; en Wallet más adelante.",
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
            <div key={title} className="flex items-start gap-3 bg-surface px-5 py-6 sm:px-7">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-brand/15 bg-brand-soft text-brand">
                <Icon size={18} />
              </span>
              <div>
                <p className="text-[13.5px] font-bold text-ink">{title}</p>
                <p className="mt-1 text-[12.5px] leading-relaxed text-ink-soft">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dos públicos, dos recorridos. */}
      <section className="mx-auto w-full max-w-6xl flex-1 px-5 py-12 sm:px-8 sm:py-16">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.05fr_0.95fr]">
          <article className="relative flex flex-col overflow-hidden rounded-3xl border border-line bg-surface p-6 shadow-soft transition-[transform,box-shadow] duration-300 hover:-translate-y-1 hover:shadow-lift sm:p-8">
            <span
              aria-hidden="true"
              className="absolute right-0 top-0 h-24 w-24 rounded-bl-[64px] bg-brand-soft"
            />
            <div className="relative flex items-start justify-between gap-4">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <IconGift size={24} />
              </span>
              <ArtStorefront className="-mr-3 -mt-3 hidden h-20 w-[110px] shrink-0 lg:block" />
            </div>
            <h2 className="relative mt-5 text-[24px] font-bold tracking-tight text-ink">
              Para tu comercio
            </h2>
            <p className="relative mt-1.5 max-w-md text-sm leading-relaxed text-ink-soft">
              Configura el programa, opera en el mostrador y sigue las cifras reales de tu negocio. Sin hojas
              de cálculo y sin desarrollos a medida.
            </p>
            <ul className="relative mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {merchantPoints.map(({ icon: Icon, text }) => (
                <li
                  key={text}
                  className="flex items-start gap-2.5 rounded-xl border border-line bg-paper p-3 text-[13px] leading-snug text-ink transition-colors hover:border-line-strong"
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
            className="relative flex scroll-mt-20 flex-col overflow-hidden rounded-3xl border border-line bg-paper p-6 shadow-soft transition-[transform,box-shadow] duration-300 hover:-translate-y-1 hover:shadow-lift sm:p-8"
          >
            <div className="flex items-start justify-between gap-4">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-teal-soft text-teal">
                <IconScan size={24} />
              </span>
              <ArtNfcTap className="-mr-2 -mt-2 hidden h-20 w-[96px] shrink-0 lg:block" />
            </div>
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
                ¿Perdiste el enlace de tu tarjeta? Pide en el comercio la etiqueta «Recuperar mi tarjeta»: te
                enviaremos un enlace personal a tu correo.
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
                La plataforma no premia, filtra ni condiciona las opiniones de nadie. Solo facilita el enlace
                oficial del comercio.
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

      {/* Cierre en tinta: el pico del recorrido; la marca, grande y descansada. */}
      <section className="mx-auto w-full max-w-6xl px-5 pb-14 sm:px-8 sm:pb-20">
        <div className="mesh-brand grain relative isolate overflow-hidden rounded-3xl shadow-lift">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0">
            <div className="animate-drift absolute -right-20 -top-24 size-80 rounded-full bg-brand-glow/30 blur-3xl" />
            <div className="animate-drift absolute -bottom-28 left-[8%] size-72 rounded-full bg-gold-bright/15 blur-3xl [animation-delay:-6s]" />
          </div>
          <p
            aria-hidden="true"
            className="pointer-events-none absolute -right-4 top-0 select-none text-[180px] font-bold leading-none text-gold-bright/20 sm:-top-8 sm:text-[240px]"
          >
            LF
          </p>

          <div className="relative flex flex-col gap-8 px-6 py-10 sm:flex-row sm:items-end sm:justify-between sm:px-10 sm:py-14">
            <div className="max-w-xl">
              <h2 className="text-[28px] font-bold leading-[1.1] tracking-[-0.03em] text-white sm:text-[38px]">
                Tu programa, en la tarjeta de tus clientes
              </h2>
              <p className="mt-3 text-[15px] leading-relaxed text-white/80 sm:text-base">
                Las cifras las confirma el servidor, la tarjeta vive en el bolsillo y las reseñas, siempre
                como decida cada cliente.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link
                  href="/login"
                  className="inline-flex h-[52px] items-center gap-2 rounded-xl bg-white px-6 text-[15px] font-bold text-ink shadow-soft transition-colors duration-150 hover:bg-gold-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                >
                  Acceder al panel
                  <IconArrowRight size={17} />
                </Link>
                <span className="text-xs leading-snug text-white/65">
                  El acceso lo entrega la administración de la plataforma.
                </span>
              </div>
            </div>
            <div className="hidden shrink-0 flex-col items-start gap-3 lg:flex" aria-hidden="true">
              {/* Sello decorativo: la forma de la marca, no un dato real. */}
              <div className="flex items-center gap-3">
                {Array.from({ length: 5 }, (_, index) => (
                  <span
                    key={index}
                    className="flex size-10 items-center justify-center rounded-full border-2 border-white/60"
                    style={{ opacity: index < 4 ? 1 : 0.4 }}
                  >
                    {index < 4 && <IconCheck size={16} className="text-white" />}
                  </span>
                ))}
              </div>
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/60">
                Ejemplo de tarjeta
              </p>
            </div>
          </div>
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
