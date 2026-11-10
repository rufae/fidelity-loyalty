"use client";

import { useEffect, useState } from "react";

import {
  Alert,
  Button,
  Checkbox,
  FormField,
  IconCheck,
  IconGift,
  IconMail,
  Input,
  LoadingState,
} from "@/components/ui";
import { ArtCoffeeCup, ArtNfcTap, ArtRewards, ArtSparkles } from "@/components/ui/art";
import { ApiError } from "@/lib/api";
import { fidelity, type PublicProgram } from "@/lib/fidelity";
import { sellos } from "@/lib/ui";

/** Marca discreta del programa, con las iniciales del comercio. */
function MerchantMark({ name }: { name: string }) {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <span
      aria-hidden="true"
      className="flex size-11 items-center justify-center rounded-xl border border-white/25 bg-white/15 text-sm font-bold tracking-tight text-white backdrop-blur-sm"
    >
      {initials || "LF"}
    </span>
  );
}

/**
 * Página pública de alta: mobile-first, datos mínimos, condiciones visibles con
 * versión y consentimientos separados. La calidez del comercio se nota desde
 * el primer píxel, pero el formulario no pide nada que no necesite.
 */
export function EnrollView({
  merchantSlug,
  programSlug,
}: {
  merchantSlug: string;
  programSlug: string;
}) {
  const [program, setProgram] = useState<PublicProgram | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fidelity
      .publicProgram(merchantSlug, programSlug)
      .then((data) => {
        if (!cancelled) setProgram(data);
      })
      .catch(() => {
        if (!cancelled) setError("Este programa no está disponible.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantSlug, programSlug]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!program) return;
    setBusy(true);
    setError(null);
    try {
      await fidelity.enroll(merchantSlug, programSlug, {
        email,
        display_name: name,
        accepted_terms_version: program.terms_version,
        privacy_notice_version: program.privacy_notice_version,
        marketing_consent: marketing,
      });
      setConfirmationSent(true);
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "membership_already_exists"
          ? "Este email ya está registrado en el programa."
          : err instanceof ApiError
            ? err.message
            : "No se pudo completar el registro.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (error && !program) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-surface-2 text-ink-faint">
          <IconGift size={30} />
        </div>
        <h1 className="mt-4 text-xl font-bold text-ink">Programa no disponible</h1>
        <p className="mt-2 text-sm text-ink-soft">{error}</p>
      </main>
    );
  }

  if (!program) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
        <LoadingState label="Cargando el programa…" />
      </main>
    );
  }

  if (confirmationSent) {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-5 py-14">
        <div className="animate-in overflow-hidden rounded-3xl border border-line bg-surface shadow-lift">
          <div className="mesh-brand grain relative px-7 py-8 text-center text-white">
            <ArtSparkles className="pointer-events-none absolute right-5 top-4 h-10 w-10 opacity-80 sm:h-12 sm:w-12" />
            <span className="relative mx-auto flex size-16 items-center justify-center rounded-2xl border border-white/25 bg-white/15 text-white backdrop-blur-sm">
              <IconMail size={30} />
            </span>
            <h1 className="relative mt-4 text-[26px] font-bold tracking-tight">Revisa tu correo</h1>
            <p className="relative mx-auto mt-2 max-w-sm text-sm leading-relaxed text-white/80">
              Te hemos enviado un enlace para confirmar que controlas este correo. Al confirmarlo,
              activaremos tu tarjeta y te enviaremos otro enlace para guardarla y recuperarla.
            </p>
          </div>
          <div className="space-y-4 p-6">
            <ol className="space-y-3">
              {[
                "Abre el correo que te acabamos de enviar.",
                "Pulsa el enlace de confirmación.",
                "Guarda el enlace personal de tu tarjeta.",
              ].map((text, index) => (
                <li key={text} className="flex items-start gap-3 text-sm text-ink">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-ok-soft text-[11px] font-bold text-ok">
                    {index + 1}
                  </span>
                  <span className="pt-0.5 leading-snug">{text}</span>
                </li>
              ))}
            </ol>
            <p className="rounded-xl bg-surface-2 p-3 text-xs leading-relaxed text-ink-soft">
              El enlace de confirmación caduca en 30 minutos. Si no llega, revisa la carpeta de
              correo no deseado. Puedes cerrar esta pestaña.
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-12 pt-4 sm:px-6 sm:pt-6">
      {/* Héroe del programa: identidad del comercio y qué se lleva el cliente. */}
      <header className="mesh-brand grain animate-in relative overflow-hidden rounded-3xl p-6 text-white shadow-lift sm:p-7">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-12 -top-12 size-40 rounded-full border border-white/15"
        />
        <div className="relative flex items-center gap-3">
          <MerchantMark name={program.merchant_name} />
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-white/70">
              {program.merchant_name}
            </p>
            <p className="text-[11px] text-white/55">Programa de fidelización</p>
          </div>
        </div>
        <h1 className="relative mt-5 text-[30px] font-bold leading-[1.1] tracking-[-0.02em]">
          {program.program_name}
        </h1>
        {program.description && (
          <p className="relative mt-2.5 max-w-md text-sm leading-relaxed text-white/85">
            {program.description}
          </p>
        )}
        <div className="relative mt-5 flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-white/90 backdrop-blur-sm">
            Tarjeta digital gratuita
          </span>
          <span className="rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-white/90 backdrop-blur-sm">
            Sin instalar nada
          </span>
        </div>
      </header>

      {/* Cómo funciona: tres estampas ilustradas, no tres tarjetas idénticas. */}
      <section className="mt-6" aria-labelledby="como-funciona">
        <h2 id="como-funciona" className="sr-only">
          Cómo funciona
        </h2>
        <ol className="grid grid-cols-3 gap-2">
          {[ArtNfcTap, ArtCoffeeCup, ArtRewards].map((Art, index) => (
            <li key={index} className="relative overflow-hidden rounded-2xl border border-line bg-paper p-3 text-center shadow-soft">
              <Art className="mx-auto h-14 w-[74px]" />
              <p className="mt-2 text-[11px] font-semibold leading-snug text-ink">
                {["Te acercas al mostrador", "Te das de alta en un minuto", "Sumas sellos y ganas"][index]}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* Recompensas reales del programa, como tickets. */}
      {program.rewards.length > 0 && (
        <section className="mt-6" aria-labelledby="recompensas">
          <div className="mb-2.5 flex items-baseline justify-between gap-3">
            <h2 id="recompensas" className="text-sm font-bold text-ink">
              Lo que puedes conseguir
            </h2>
            <span className="text-[11px] text-ink-faint">Según los sellos del programa</span>
          </div>
          <ul className="space-y-2">
            {program.rewards.map((reward) => (
              <li
                key={reward.name}
                className="ticket-notch flex items-center justify-between gap-3 border border-line bg-surface py-3 pl-4 pr-3 shadow-soft"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-gold-soft text-gold">
                    <IconGift size={18} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-ink">
                      {reward.name}
                    </span>
                    {reward.description && (
                      <span className="block truncate text-[11px] text-ink-faint">
                        {reward.description}
                      </span>
                    )}
                  </span>
                </span>
                <span className="shrink-0 rounded-full bg-gold-soft px-3 py-1 text-xs font-bold text-gold">
                  {sellos(reward.stamps_required)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!program.enrollment_open && (
        <div className="mt-6">
          <Alert tone="warn" title="Altas temporalmente cerradas">
            Este programa no está aceptando altas en este momento.
          </Alert>
        </div>
      )}

      {/* Formulario de alta */}
      <form
        onSubmit={onSubmit}
        className="mt-6 overflow-hidden rounded-3xl border border-line bg-surface shadow-soft"
      >
        <div className="border-b border-line px-5 pb-4 pt-5 sm:px-6">
          <h2 className="text-lg font-bold tracking-tight text-ink">Únete al programa</h2>
          <p className="mt-0.5 text-[13px] leading-relaxed text-ink-soft">
            Solo necesitamos tu nombre y tu correo.
          </p>
        </div>

        <div className="space-y-4 px-5 py-5 sm:px-6">
          <FormField label="Nombre completo" required hint="Como quieres que te llamen en tienda.">
            {({ id, describedBy }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                required
                minLength={2}
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre y apellidos"
                autoComplete="name"
              />
            )}
          </FormField>

          <FormField label="Email" required hint="Para gestionar tu tarjeta cuando lo necesites.">
            {({ id, describedBy }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                autoComplete="email"
              />
            )}
          </FormField>

          {program.terms && (
            <div className="rounded-xl border border-line bg-paper p-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                Condiciones · versión {program.terms_version}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">{program.terms}</p>
            </div>
          )}

          <div className="space-y-2">
            <Checkbox
              required
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              label={`He leído y acepto las condiciones del programa (v${program.terms_version}).`}
            />

            <Checkbox
              required
              checked={privacy}
              onChange={(e) => setPrivacy(e.target.checked)}
              label={`He leído el aviso de privacidad (v${program.privacy_notice_version}).`}
              description="Tus datos (nombre y email) se usan solo para gestionar esta tarjeta."
            />

            <Checkbox
              checked={marketing}
              onChange={(e) => setMarketing(e.target.checked)}
              label="Quiero recibir novedades del establecimiento."
              description="Opcional; puedes retirarlo cuando quieras."
            />
          </div>

          {error && (
            <Alert tone="danger" title="No se pudo completar el alta">
              {error}
            </Alert>
          )}

          <Button
            type="submit"
            size="lg"
            loading={busy}
            disabled={!program.enrollment_open}
            className="w-full"
          >
            {busy ? "Enviando confirmación…" : "Quiero mi tarjeta"}
          </Button>

          <p className="flex items-start justify-center gap-1.5 text-center text-[11px] leading-relaxed text-ink-faint">
            <IconCheck size={13} className="mt-0.5 shrink-0 text-ok" />
            <span>Al confirmar tu correo recibirás tu tarjeta. Sin coste y sin instalar nada.</span>
          </p>
        </div>
      </form>

      <p className="mt-6 text-center text-xs leading-relaxed text-ink-faint">
        Tus datos se usan solo para gestionar esta tarjeta de fidelización.
      </p>
    </main>
  );
}
