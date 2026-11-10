"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Alert,
  Button,
  FormField,
  IconArrowRight,
  IconLock,
  IconMail,
  Input,
  LoyaltyCard,
} from "@/components/ui";
import { ArtSparkles } from "@/components/ui/art";
import { ApiError } from "@/lib/api";
import { fidelity } from "@/lib/fidelity";

export function MemberCardAccess({ merchantSlug }: { merchantSlug: string }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await fidelity.requestCardAccess(merchantSlug, email);
      setSent(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo solicitar el enlace. Inténtalo de nuevo más tarde.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 py-10 sm:px-6">
      <section className="animate-in overflow-hidden rounded-3xl border border-line bg-surface shadow-lift">
        <div className="relative border-b border-line bg-paper px-6 py-7 text-center sm:px-8">
          <ArtSparkles className="pointer-events-none absolute right-5 top-4 h-10 w-10 opacity-70" />
          <span className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-brand-soft text-brand shadow-soft">
            <IconMail size={26} />
          </span>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.15em] text-ink-faint">
            Acceso privado
          </p>
          <h1 className="mt-1 text-[26px] font-bold tracking-[-0.02em] text-ink">
            Encuentra tu tarjeta
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-ink-soft">
            Escribe el correo que usaste al registrarte. Te enviaremos un enlace personal de un solo
            uso para ver tus tarjetas de este comercio.
          </p>
        </div>

        <div className="px-6 py-6 sm:px-8">
          {sent ? (
            <Alert tone="info" title="Comprueba tu correo">
              Si hay una tarjeta asociada a ese correo, recibirás un enlace seguro. Revisa también la
              carpeta de correo no deseado.
            </Alert>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <FormField label="Correo electrónico" required hint="No mostraremos si está registrado.">
                {({ id, describedBy }) => (
                  <Input
                    id={id}
                    aria-describedby={describedBy}
                    autoComplete="email"
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="tu@email.com"
                  />
                )}
              </FormField>
              {error && <Alert tone="danger">{error}</Alert>}
              <Button type="submit" size="lg" loading={busy} className="w-full">
                Enviarme un enlace seguro
              </Button>
            </form>
          )}
          <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-ink-faint">
            <IconLock size={15} className="mt-0.5 shrink-0" />
            <span>
              La etiqueta NFC es compartida: nunca contiene ni revela la tarjeta de otra persona.
            </span>
          </p>
        </div>
      </section>
    </main>
  );
}

export function MemberCardList({ merchantSlug }: { merchantSlug: string }) {
  const [cards, setCards] = useState<Awaited<ReturnType<typeof fidelity.myCards>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    void fidelity
      .myCards(merchantSlug)
      .then((result) => {
        if (!cancelled) setCards(result);
      })
      .catch(() => {
        if (!cancelled) setError("Tu sesión ha caducado. Solicita un nuevo enlace por correo.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantSlug]);

  async function logout() {
    setBusy(true);
    try {
      await fidelity.logoutMemberCards(merchantSlug);
      router.replace(`/my-card/${encodeURIComponent(merchantSlug)}`);
    } catch {
      setError("No se pudo cerrar la sesión. Puedes cerrar esta pestaña.");
      setBusy(false);
    }
  }

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5">
        <Alert tone="warn" title="Vuelve a verificar tu acceso">
          {error}
        </Alert>
        <a
          className="mt-4 text-center text-sm font-semibold text-brand"
          href={`/my-card/${encodeURIComponent(merchantSlug)}`}
        >
          Solicitar otro enlace
        </a>
      </main>
    );
  }

  if (!cards) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md items-center justify-center px-5">
        <p role="status" className="text-sm text-ink-soft">
          Cargando tus tarjetas…
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-8 sm:px-6 sm:py-10">
      <header className="animate-in">
        <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-brand">
          {cards[0]?.merchant_name ?? "LocalAI Fidelity"}
        </p>
        <h1 className="mt-1 text-[28px] font-bold tracking-[-0.02em] text-ink">Tus tarjetas</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
          Solo tú puedes verlas desde este enlace personal.
        </p>
      </header>

      {cards.length === 0 ? (
        <div className="mt-6">
          <Alert tone="info" title="No hay tarjetas activas">
            No encontramos tarjetas activas asociadas a este correo en este comercio.
          </Alert>
        </div>
      ) : (
        <ul className="stagger mt-6 space-y-4">
          {cards.map((card) => (
            <li key={card.token}>
              <a
                href={`/card/${encodeURIComponent(card.token)}`}
                className="group block rounded-3xl transition-transform duration-300 hover:-translate-y-0.5"
              >
                <LoyaltyCard
                  merchantName={card.merchant_name}
                  programName={card.program_name}
                  stamps={card.stamps}
                  variant="preview"
                />
                <span className="mt-2 flex items-center justify-between rounded-xl border border-line bg-surface px-4 py-3 text-sm font-semibold text-ink shadow-soft transition-colors group-hover:border-brand/40 group-hover:text-brand">
                  Abrir tarjeta y mostrar QR
                  <IconArrowRight size={16} />
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}

      <Button
        variant="ghost"
        size="sm"
        disabled={busy}
        onClick={() => void logout()}
        className="mt-6 w-full"
      >
        {busy ? "Cerrando sesión…" : "Cerrar sesión en este dispositivo"}
      </Button>

      <p className="mt-3 text-center text-[11px] leading-relaxed text-ink-faint">
        Si el enlace ha caducado, pide uno nuevo desde la etiqueta «Recuperar mi tarjeta» del
        comercio.
      </p>
    </main>
  );
}

export function EmailActionView({
  token,
  merchantSlug,
  action,
}: {
  token: string;
  merchantSlug?: string;
  action: "verify" | "access";
}) {
  const router = useRouter();
  const [state, setState] = useState<"ready" | "busy" | "error">("ready");
  const [error, setError] = useState<string | null>(null);
  /** Un enlace gastado no debe dejar sin acceso en el mismo dispositivo: si la
      sesión de 30 días sigue viva, se ofrece abrir las tarjetas directamente. */
  const [sessionActive, setSessionActive] = useState(false);

  useEffect(() => {
    if (state !== "error" || !merchantSlug) return;
    let cancelled = false;
    void fidelity
      .myCards(merchantSlug)
      .then(() => {
        if (!cancelled) setSessionActive(true);
      })
      .catch(() => {
        if (!cancelled) setSessionActive(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state, merchantSlug]);

  async function continueToCard() {
    setState("busy");
    setError(null);
    window.history.replaceState(null, "", window.location.pathname);
    try {
      const result =
        action === "verify"
          ? await fidelity.verifyMemberEmail(token)
          : await fidelity.exchangeCardAccess(token);
      router.replace(`/my-card/${encodeURIComponent(result.merchant_slug)}/cards`);
    } catch (caught) {
      setState("error");
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo validar el enlace. Solicita uno nuevo desde la etiqueta del establecimiento.",
      );
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-12 text-center sm:px-5">
      <div className="animate-in rounded-3xl border border-line bg-surface p-7 shadow-lift sm:p-8">
        <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-brand-soft text-brand">
          <IconLock size={25} />
        </div>
        <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.15em] text-ink-faint">
          Enlace personal
        </p>
        <h1 className="mt-1 text-[24px] font-bold tracking-[-0.02em] text-ink">
          {action === "verify" ? "Confirma tu correo" : "Abre tus tarjetas"}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          {action === "verify"
            ? "Confirmaremos tu correo y activaremos tu acceso. También enviaremos otro enlace para que puedas guardar tu tarjeta."
            : "Este enlace personal es de un solo uso. Al continuar, abriremos solo tus tarjetas."}
        </p>
        {error && (
          <div className="mt-4 space-y-3 text-left">
            <Alert tone="danger" title="Enlace no válido">
              {error}
            </Alert>
            <p className="text-xs leading-relaxed text-ink-faint">
              Es normal: cada enlace del correo sirve una sola vez y caduca a los 30 minutos. Tus
              tarjetas no se pierden.
            </p>
            {merchantSlug && sessionActive ? (
              <a
                href={`/my-card/${encodeURIComponent(merchantSlug)}/cards`}
                className="block rounded-xl border border-brand/30 bg-brand-soft/40 px-4 py-3 text-sm font-semibold text-brand"
              >
                Ver mis tarjetas: siguen abiertas en este dispositivo
              </a>
            ) : null}
            {merchantSlug ? (
              <a
                href={`/my-card/${encodeURIComponent(merchantSlug)}`}
                className="block px-4 py-1 text-sm font-semibold text-ink-soft underline-offset-2 hover:text-ink hover:underline"
              >
                Pedir un enlace nuevo por correo
              </a>
            ) : null}
          </div>
        )}
        <Button
          size="lg"
          loading={state === "busy"}
          onClick={() => void continueToCard()}
          className="mt-6 w-full"
        >
          {action === "verify" ? "Confirmar correo y continuar" : "Abrir mis tarjetas"}
        </Button>
      </div>
    </main>
  );
}
