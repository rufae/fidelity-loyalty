"use client";

/** Recuperación de contraseña de personal (§8.3, P0-2).

Dos pasos en una misma ruta: sin `?token=` se pide el correo; con `?token=`
se define la nueva contraseña (enlace de un solo uso, 30 minutos). La
respuesta de la solicitud es idéntica exista o no el email (§8.2): nunca
decimos "esa cuenta existe".
 */
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { BrandLogo, Button, FormField, IconArrowLeft, Input, Alert } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";

function ResetFlow() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  return token ? <ConfirmForm token={token} /> : <RequestForm />;
}

function RequestForm() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/api/v1/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch {
      setError("No se pudo procesar la solicitud. Inténtalo de nuevo en un momento.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="space-y-4 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Revisa tu correo</h1>
        <p className="text-sm leading-relaxed text-ink-soft">
          Si tu cuenta existe, te acabamos de enviar un enlace para elegir una
          contraseña nueva. Caduca en 30 minutos y solo vale una vez. Si no te
          llega, mira en «correo no deseado».
        </p>
        <Link
          href="/login"
          className="inline-flex min-h-11 items-center rounded-xl bg-ink px-4 text-sm font-semibold text-paper transition-colors hover:bg-nav"
        >
          Volver a entrar
        </Link>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Recuperar acceso</h1>
        <p className="text-sm leading-relaxed text-ink-soft">
          Escribe el correo de tu cuenta y te enviamos un enlace para elegir una
          contraseña nueva.
        </p>
      </div>
      <FormField label="Correo de la cuenta" required>
        {({ id, describedBy }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@correo.com"
          />
        )}
      </FormField>
      {error && (
        <Alert tone="danger" title="No se pudo enviar">
          {error}
        </Alert>
      )}
      <Button type="submit" size="lg" loading={busy} className="w-full">
        {busy ? "Enviando…" : "Enviar enlace"}
      </Button>
      <p className="text-center text-xs text-ink-faint">
        <Link href="/login" className="font-semibold hover:text-ink">
          Volver a entrar
        </Link>
      </p>
    </form>
  );
}

function ConfirmForm({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== repeat) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }
    setBusy(true);
    try {
      await apiFetch("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 400
            ? "El enlace no es válido o ha caducado. Pide otro desde «Recuperar acceso»."
            : err.message,
        );
      } else {
        setError("No se pudo cambiar la contraseña. Inténtalo de nuevo.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="space-y-4 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Contraseña cambiada</h1>
        <p className="text-sm leading-relaxed text-ink-soft">
          Ya puedes entrar con tu nueva contraseña. Por seguridad, se han
          cerrado todas las sesiones abiertas de tu cuenta.
        </p>
        <Link
          href="/login"
          className="inline-flex min-h-11 items-center rounded-xl bg-ink px-4 text-sm font-semibold text-paper transition-colors hover:bg-nav"
        >
          Entrar al panel
        </Link>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Elige tu nueva contraseña</h1>
        <p className="text-sm leading-relaxed text-ink-soft">
          Mínimo 10 caracteres. Al guardarla se cierran todas las sesiones
          abiertas de tu cuenta.
        </p>
      </div>
      <FormField label="Nueva contraseña" required>
        {({ id, describedBy }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            type="password"
            required
            minLength={10}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        )}
      </FormField>
      <FormField label="Repite la nueva contraseña" required>
        {({ id, describedBy }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            type="password"
            required
            minLength={10}
            autoComplete="new-password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
          />
        )}
      </FormField>
      {error && (
        <Alert tone="danger" title="No se pudo cambiar">
          {error}
        </Alert>
      )}
      <Button type="submit" size="lg" loading={busy} className="w-full">
        {busy ? "Guardando…" : "Guardar contraseña"}
      </Button>
    </form>
  );
}

export function ResetView() {
  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b border-line/80 px-5 py-4 sm:px-8">
        <div className="mx-auto flex w-full max-w-md items-center justify-between">
          <Link href="/" className="transition-opacity hover:opacity-80" aria-label="Inicio">
            <BrandLogo />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft transition-colors hover:text-ink"
          >
            <IconArrowLeft size={14} />
            Entrar
          </Link>
        </div>
      </header>
      <div className="flex flex-1 items-center justify-center px-5 py-12">
        <div className="w-full max-w-[400px]">
          <Suspense fallback={null}>
            <ResetFlow />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
