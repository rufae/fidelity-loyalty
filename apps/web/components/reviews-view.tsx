"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  FormField,
  IconCheck,
  IconExternal,
  IconInfo,
  IconLock,
  IconStar,
  Input,
  LinkButton,
  LoadingState,
  Panel,
  SectionTitle,
  StatusPill,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fidelity, type ReviewDestination } from "@/lib/fidelity";
import { formatDate } from "@/lib/ui";

/**
 * Configuración del enlace de reseñas: URL oficial, verificación manual con
 * fecha, y material separado del de fidelización.
 *
 * Este formulario **no** contiene incentivos, filtros ni opciones de
 * recompensa: están prohibidos por política y el esquema de la API los rechaza.
 */
export function ReviewsView({ merchantId }: { merchantId: string }) {
  const [destination, setDestination] = useState<ReviewDestination | null>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    void fidelity
      .reviewDestination(merchantId)
      .then((data) => {
        if (cancelled) return;
        setDestination(data);
        setUrl(data?.review_url ?? "");
        setLoaded(true);
      })
      .catch(() => {
        // Sin esto, un fallo dejaba la vista cargando infinito (auditoría).
        if (!cancelled) {
          setLoadError("No se pudo cargar la configuración de reseñas.");
          setLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const saved = await fidelity.saveReviewDestination(merchantId, url);
      setDestination(saved);
      setNotice("Enlace guardado. Ahora verifícalo para poder usar la etiqueta.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el enlace.");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const verified = await fidelity.verifyReviewDestination(merchantId);
      setDestination(verified);
      setNotice(
        "Enlace comprobado por el comercio. Ya puedes crear la etiqueta NFC/QR de reseñas.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo verificar.");
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return <LoadingState label="Cargando configuración…" />;

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert tone="danger" title="No se pudo cargar">
          {loadError}
        </Alert>
        <Button
          onClick={() => {
            setLoadError(null);
            setLoaded(false);
            load();
          }}
        >
          Reintentar
        </Button>
      </div>
    );
  }

  const verified = destination?.verification_status === "verified";
  const saved = Boolean(destination);

  const steps = [
    {
      title: "Encuentra tu ficha en Google Maps",
      text: "Busca tu negocio y copia el enlace «Escribir una reseña».",
      done: saved,
    },
    {
      title: "Pega el enlace y guárdalo",
      text: "Queda asociado a este comercio; no se puede inventar.",
      done: saved,
    },
    {
      title: "Ábrelo y comprueba que es tu negocio",
      text: "Con «Abrir y comprobar» verás la ficha oficial tal cual la verá el cliente.",
      done: saved,
    },
    {
      title: "Verifica el enlace",
      text: "Hasta verificarlo, la etiqueta de reseñas no redirige.",
      done: verified,
    },
  ];

  return (
    <div className="max-w-5xl space-y-6">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_340px] lg:items-start">
        <Panel className="animate-in">
          <SectionTitle
            title="Enlace oficial de reseñas"
            description="Facilita que tus clientes encuentren la ficha oficial de tu negocio. Pega el enlace, guárdalo y verifica que funciona."
            icon={<IconStar size={18} />}
          />

          {/* Estado de un vistazo: texto e icono, nunca solo color. */}
          <div
            className={`mb-5 flex items-start gap-3 rounded-2xl border p-4 ${
              verified
                ? "border-ok/25 bg-ok-soft"
                : saved
                  ? "border-warn/25 bg-warn-soft"
                  : "border-line bg-paper"
            }`}
          >
            <span
              className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${
                verified ? "bg-ok text-white" : saved ? "bg-gold-bright text-[#4a3208]" : "bg-surface-2 text-ink-faint"
              }`}
            >
              {verified ? <IconCheck size={22} /> : <IconStar size={22} />}
            </span>
            <div className="min-w-0">
              <StatusPill tone={verified ? "ok" : saved ? "warn" : "neutral"}>
                {verified ? "Comprobado por el comercio" : saved ? "Guardado, sin verificar" : "Sin enlace"}
              </StatusPill>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">
                {verified
                  ? `Comprobado el ${formatDate(destination?.verified_at)}. La etiqueta de reseñas ya redirige a tu ficha oficial.`
                  : saved
                    ? "Próximo paso: abre la ficha, confirma que es tu negocio y pulsa «Verificar enlace»."
                    : "Próximo paso: pega el enlace oficial de tu negocio y guárdalo."}
              </p>
            </div>
          </div>

          <form onSubmit={save} className="space-y-3">
            <FormField
              label="Enlace de reseñas de Google"
              required
              hint="Debe empezar por https:// y abrir tu ficha oficial en Google."
            >
              {({ id, describedBy }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://g.page/r/..."
                />
              )}
            </FormField>
            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" loading={busy}>
                Guardar enlace
              </Button>
              {destination && (
                <a
                  href={destination.review_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-11 items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 text-sm font-semibold text-ink transition-colors hover:border-brand/50 hover:text-brand"
                >
                  <IconExternal size={17} />
                  Abrir y comprobar
                </a>
              )}
              {saved && (
                <Button
                  onClick={() => void verify()}
                  loading={busy}
                  variant={verified ? "secondary" : "primary"}
                  icon={<IconLock size={17} />}
                >
                  {verified ? "Verificar de nuevo" : "Verificar enlace"}
                </Button>
              )}
            </div>
          </form>

          {error && (
            <div className="mt-4">
              <Alert tone="danger" title="No se pudo completar">
                {error}
              </Alert>
            </div>
          )}
          {notice && (
            <div className="mt-4">
              <Alert tone="ok" title="Hecho">
                {notice}
              </Alert>
            </div>
          )}

          {verified && (
            <div className="mt-5 border-t border-line pt-5">
              <LinkButton
                href={`/merchants/${merchantId}/nfc`}
                icon={<IconStar size={17} />}
              >
                Crear la etiqueta de reseñas
              </LinkButton>
              <p className="mt-2 text-[11px] text-ink-faint">
                La etiqueta de reseñas es independiente de la de alta al programa.
              </p>
            </div>
          )}
        </Panel>

        <aside className="space-y-4">
          <Panel tone="muted" className="animate-in">
            <p className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.13em] text-ink-faint">
              <IconInfo size={14} />
              Cómo conseguir el enlace
            </p>
            <ol className="mt-3 space-y-0">
              {steps.map((step, index) => (
                <li key={step.title} className="relative flex gap-3 pb-4 last:pb-0">
                  {index < steps.length - 1 && (
                    <span
                      aria-hidden="true"
                      className="absolute left-[11px] top-6 h-[calc(100%-16px)] w-px bg-line-strong"
                    />
                  )}
                  <span
                    className={`relative flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ring-1 ring-inset ${
                      step.done
                        ? "bg-ok text-white ring-ok"
                        : "bg-surface text-ink-faint ring-line-strong"
                    }`}
                  >
                    {step.done ? <IconCheck size={13} /> : index + 1}
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className={`text-[13px] font-semibold ${step.done ? "text-ok" : "text-ink"}`}>
                      {step.title}
                    </p>
                    <p className="mt-0.5 text-[11px] leading-snug text-ink-soft">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Panel>

          {/* Regla de política: visible, no en letra pequeña. */}
          <div className="rounded-2xl border border-brand/20 bg-brand-soft/50 p-5">
            <h3 className="flex items-center gap-2 text-sm font-bold text-brand">
              <IconInfo size={17} />
              Sobre las solicitudes de reseñas
            </h3>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
              La plataforma solo facilita que tus clientes encuentren tu página oficial: quien quiera
              dejar una reseña lo hará allí, voluntariamente.{" "}
              <strong className="text-ink">No hay incentivos por reseñar</strong>, no se filtra por
              satisfacción y las métricas cuentan{" "}
              <strong className="text-ink">clics al enlace</strong>, no reseñas publicadas.
            </p>
            <p className="mt-3 rounded-xl bg-surface p-3 text-[13px] italic text-ink">
              Texto sugerido para el material impreso: «¿Quieres compartir tu experiencia? Puedes
              dejar una reseña aquí».
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
