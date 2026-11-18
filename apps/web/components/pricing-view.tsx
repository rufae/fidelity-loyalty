"use client";

/**
 * Página pública de precios (§22, tasks.md §1): sin sesión, datos reales.
 *
 * El catálogo lo sirve la API (la misma fuente de verdad que aplican los
 * límites del backend), así que lo que se ve aquí es lo que se cumple. El
 * movimiento es uno solo: los precios mutan al cambiar mensual/anual y las
 * tarjetas entran con un levantamiento sutil al hacer scroll. Con
 * `prefers-reduced-motion` todo queda estático (globals.css ya lo corta).
 */
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { BrandLogo, Button, IconArrowRight, IconCheck, IconLock } from "@/components/ui";
import { plans, type PublicPlan } from "@/lib/fidelity";

type Billing = "month" | "year";

/** Número que muta: el cambio de valor remonta el span y el CSS anima. */
function MorphPrice({ value, suffix }: { value: number; suffix: string }) {
  return (
    <span className="tnum inline-flex items-baseline gap-1">
      <span
        key={value}
        className="price-morph inline-block text-4xl font-bold tracking-[-0.03em] sm:text-5xl"
      >
        {value}
      </span>
      <span className="text-sm font-semibold text-ink-soft">{suffix}</span>
    </span>
  );
}

/** Levantamiento sutil al entrar en pantalla: desde visible, sin flash. */
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.remove("translate-y-2");
            entry.target.classList.add("translate-y-0");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return ref;
}

const INCLUDED_ALWAYS = [
  "Clientes ilimitados y sellos sin tope",
  "Tarjeta web sin instalar nada",
  "QR y etiquetas NFC de alta",
  "Reseñas Google neutrales, sin incentivos",
  "Soporte en español desde el panel",
];

/** Formulario de solicitud de alta: la plataforma crea el comercio (§22). */
function LeadForm({
  planCode,
  planNames,
}: {
  planCode: string;
  planNames: Record<string, string>;
}) {
  const [business, setBusiness] = useState("");
  const [contact, setContact] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [plan, setPlan] = useState(planCode);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLDivElement | null>(null);

  // El plan lo cambia un CTA externo (`?plan=plus` → botón de la tarjeta):
  // ajuste durante el render (patrón oficial de estado derivado de props).
  const [lastPlanCode, setLastPlanCode] = useState(planCode);
  if (planCode !== lastPlanCode) {
    setLastPlanCode(planCode);
    setPlan(planCode);
  }

  useEffect(() => {
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setState("busy");
    try {
      await plans.requestOnboarding({
        business_name: business.trim(),
        contact_name: contact.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        plan,
        message: message.trim() || undefined,
      });
      setState("sent");
    } catch {
      setState("idle");
      setError("No se pudo enviar la solicitud. Escríbenos a nuestro correo de soporte.");
    }
  }

  return (
    <div
      ref={formRef}
      className="mx-auto mt-14 max-w-2xl scroll-mt-24 rounded-3xl border border-line bg-surface p-7 shadow-soft"
    >
      {state === "sent" ? (
        <div className="space-y-3 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-ok-soft text-ok">
            <IconCheck size={22} />
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink">Solicitud recibida</h2>
          <p className="text-sm leading-relaxed text-ink-soft">
            Te escribimos en breve a <strong className="text-ink">{email.trim()}</strong> para
            abrir tu comercio y darte el acceso. Nada de pagos ni configuración de
            tu parte hasta que esté todo listo.
          </p>
        </div>
      ) : (
        <>
          <h2 className="text-xl font-bold tracking-tight text-ink">Solicita tu alta</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-soft">
            Cuéntanos qué negocio es y te abrimos el comercio con el plan
            elegido. Nosotros preparamos todo; tú no configuras nada.
          </p>
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-xs font-semibold text-ink-soft">
                Nombre del negocio
                <input
                  required
                  minLength={2}
                  maxLength={160}
                  value={business}
                  onChange={(e) => setBusiness(e.target.value)}
                  placeholder="Cafetería Norte"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
              <label className="block text-xs font-semibold text-ink-soft">
                Tu nombre
                <input
                  required
                  minLength={2}
                  maxLength={120}
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder="Marta"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
              <label className="block text-xs font-semibold text-ink-soft">
                Tu correo
                <input
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tu@correo.com"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
              <label className="block text-xs font-semibold text-ink-soft">
                Teléfono (opcional)
                <input
                  type="tel"
                  maxLength={30}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="600 123 456"
                  className="mt-1 w-full rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-xs font-semibold text-ink-soft">
                Plan que te interesa
                <select
                  value={plan}
                  onChange={(e) => setPlan(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                >
                  {Object.entries(planNames).map(([code, name]) => (
                    <option key={code} value={code}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="block text-xs font-semibold text-ink-soft">
              ¿Algo más? (opcional)
              <textarea
                rows={3}
                maxLength={1000}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tengo dos locales y quiero los dos en el mismo programa…"
                className="mt-1 w-full resize-y rounded-xl border border-line-strong bg-canvas px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
              />
            </label>
            {error && (
              <p className="rounded-xl border border-warn/30 bg-gold-soft px-4 py-2.5 text-xs text-warn">
                {error}
              </p>
            )}
            <Button type="submit" size="lg" loading={state === "busy"} className="w-full">
              Enviar solicitud
            </Button>
            <p className="text-xs leading-relaxed text-ink-faint">
              Solo usamos estos datos para abrirte el comercio y contactarte.
              Nada de publicidad: sin alta no hay tratamiento.
            </p>
          </form>
        </>
      )}
    </div>
  );
}

export function PricingView() {
  const [billing, setBilling] = useState<Billing>("month");
  const [catalog, setCatalog] = useState<PublicPlan[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [leadPlan, setLeadPlan] = useState<string | null>(null);
  const cardsRef = useReveal<HTMLDivElement>();

  useEffect(() => {
    let cancelled = false;
    plans
      .public()
      .then((rows) => {
        if (!cancelled) setCatalog(rows);
      })
      .catch(() => {
        // La página no se queda vacía: si la API falla, se informa con la
        // vía de contacto (§13.6: estados de error reales).
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="flex min-h-screen flex-col">
      {/* Cabecera: mismo vidrio cálido que la landing, continuidad visual. */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-canvas/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <Link
            href="/"
            className="transition-opacity hover:opacity-80"
            aria-label="Volver al inicio"
          >
            <BrandLogo />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-paper shadow-soft transition-[background-color,transform] hover:bg-nav hover:translate-y-[-1px]"
          >
            <IconLock size={15} />
            Acceso comercios
          </Link>
        </div>
      </header>

      {/* Hero: el titular lleva su propio peso, sin etiquetas encima. */}
      <section className="relative overflow-hidden px-5 pb-4 pt-16 sm:px-8 sm:pt-24">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 right-[-10%] size-[420px] rounded-full bg-brand-soft opacity-60 blur-3xl"
        />
        <div className="relative mx-auto max-w-3xl text-center">
          <h1 className="text-balance text-4xl font-bold leading-[1.08] tracking-[-0.035em] text-ink sm:text-6xl">
            Un precio por lo que
            <br />
            tu negocio necesita.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-pretty text-lg leading-relaxed text-ink-soft">
            Pagas por tiendas y programas en vivo. Los clientes, los sellos y
            los canjes nunca tienen límite: más éxito no cuesta más.
          </p>
        </div>

        {/* Conmutador de facturación: el gesto que mueve los precios. */}
        <div className="relative mx-auto mt-10 flex w-fit items-center gap-1 rounded-2xl border border-line bg-surface p-1 shadow-soft">
          {(
            [
              ["month", "Mensual"],
              ["year", "Anual · 2 meses gratis"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setBilling(key)}
              aria-pressed={billing === key}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-[background-color,color] duration-200 ${
                billing === key
                  ? "bg-ink text-paper shadow-[0_2px_5px_rgb(62_47_30/0.14)]"
                  : "text-ink-soft hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Tarjetas: una destacada, las demás serenas; asimetría real. */}
      <section
        aria-label="Planes y precios"
        className="mx-auto w-full max-w-6xl px-5 pb-8 pt-10 sm:px-8"
      >
        {loadError && (
          <p className="mx-auto max-w-xl rounded-2xl border border-warn/30 bg-gold-soft px-5 py-4 text-center text-sm leading-relaxed text-warn">
            Ahora mismo no podemos cargar los precios. Inténtalo de nuevo en un
            momento o escríbenos desde{" "}
            <Link href="/login" className="font-semibold underline underline-offset-2">
              tu acceso de comercio
            </Link>
            .
          </p>
        )}

        <div
          ref={cardsRef}
          className="grid translate-y-2 gap-5 transition-transform duration-700 ease-out lg:grid-cols-[1fr_1.15fr_1fr] lg:items-center"
        >
          {(catalog ?? []).map((plan) => {
            const featured = plan.code === "plus";
            const monthly =
              billing === "month" ? plan.price_month_eur : plan.price_year_eur;
            return (
              <article
                key={plan.code}
                className={`relative rounded-3xl p-7 transition-transform duration-500 ease-out ${
                  featured
                    ? "border border-brand/25 bg-brand-soft shadow-lift lg:-my-4 lg:py-11"
                    : "border border-line bg-surface shadow-soft"
                }`}
              >
                {featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand px-3 py-1 text-[11px] font-bold text-white shadow-soft">
                    El más elegido
                  </span>
                )}
                <h2 className="text-xl font-bold tracking-tight text-ink">{plan.name}</h2>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{plan.tagline}</p>

                <p className="mt-6">
                  <MorphPrice
                    value={monthly}
                    suffix={billing === "month" ? "€/mes" : "€/mes · anual"}
                  />
                </p>

                <dl className="mt-6 space-y-3 border-t border-line pt-5">
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-sm text-ink-soft">Tiendas</dt>
                    <dd className="tnum text-sm font-bold text-ink">
                      {plan.max_locations}
                    </dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-sm text-ink-soft">Programas en vivo</dt>
                    <dd className="tnum text-sm font-bold text-ink">
                      {plan.max_active_programs}
                    </dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-sm text-ink-soft">Empleados</dt>
                    <dd className="tnum text-sm font-bold text-ink">{plan.max_staff}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-sm text-ink-soft">Clientes</dt>
                    <dd className="text-sm font-bold text-ink">Ilimitados</dd>
                  </div>
                </dl>

                <button
                  type="button"
                  onClick={() => setLeadPlan(plan.code)}
                  className={`mt-7 flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold shadow-soft transition-[background-color,transform] hover:translate-y-[-1px] ${
                    featured
                      ? "bg-brand text-white hover:bg-brand-strong"
                      : "bg-ink text-paper hover:bg-nav"
                  }`}
                >
                  Empezar con {plan.name}
                  <IconArrowRight size={16} />
                </button>
              </article>
            );
          })}
        </div>

        {!catalog && !loadError && (
          <div className="mt-2 grid gap-5 lg:grid-cols-[1fr_1.15fr_1fr]" aria-hidden>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={`h-72 animate-pulse rounded-3xl border border-line bg-surface ${
                  i === 1 ? "lg:-my-4" : ""
                }`}
                style={{ animationDelay: `${i * 120}ms` }}
              />
            ))}
          </div>
        )}

        {leadPlan && catalog && (
          <LeadForm
            planCode={leadPlan}
            planNames={Object.fromEntries(catalog.map((p) => [p.code, p.name]))}
          />
        )}

        {/* Lo que todos los planes incluyen: una lista, no más tarjetas. */}
        <div className="mx-auto mt-14 max-w-3xl">
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            En todos los planes, siempre
          </h2>
          <ul className="mt-5 grid gap-3 sm:grid-cols-2">
            {INCLUDED_ALWAYS.map((item) => (
              <li key={item} className="flex items-start gap-2.5">
                <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-ok-soft text-ok">
                  <IconCheck size={13} />
                </span>
                <span className="text-sm leading-relaxed text-ink-soft">{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-xs leading-relaxed text-ink-faint">
            Precios en euros, IVA no incluido. Puedes cambiar de plan cuando
            quieras: tus programas, clientes y datos se conservan tal cual. Sin
            permanencia.
          </p>
        </div>
      </section>

      <footer className="mt-auto border-t border-line/70 px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <BrandLogo />
          <p className="text-xs text-ink-faint">
            Fidelización y reseñas para comercios · Datos al margen, RGPD
          </p>
        </div>
      </footer>
    </main>
  );
}
