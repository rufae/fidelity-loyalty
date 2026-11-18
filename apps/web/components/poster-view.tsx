"use client";

/**
 * Póster imprimible para el mostrador (§14.2, mejora de compra #8).
 *
 * Dos bloques con identidad **clara y separada** —«Añade tu tarjeta» y
 * «Comparte tu experiencia»— para que nadie confunda los dos recorridos
 * (§5.1). El material de reseñas es neutro: sin incentivos, sin pedir
 * estrellas y sin prometer nada a cambio (§4.2, §4.3).
 *
 * La impresión va por el navegador del comercio («Imprimir» o «Guardar
 * como PDF»): el póster solo lleva el logo, el nombre y los dos QR
 * públicos. Nunca datos de clientes. Si falta material (QR de alta o
 * reseñas verificadas) se avisa aquí y el hueco queda indicado en la
 * hoja para no imprimir un QR que no existe.
 */
import { useEffect, useState } from "react";

import { useMerchant } from "@/components/merchant-context";
import {
  Alert,
  Button,
  IconArrowRight,
  IconDownload,
  LinkButton,
  LoadingState,
} from "@/components/ui";
import {
  fidelity,
  type CardBranding,
  type NfcTag,
  type ReviewDestination,
} from "@/lib/fidelity";

export function PosterView({ merchantId }: { merchantId: string }) {
  const { merchantName } = useMerchant();
  const [branding, setBranding] = useState<CardBranding | null>(null);
  const [tags, setTags] = useState<NfcTag[] | null>(null);
  /** `undefined` = cargando; `null` = el comercio aún no configuró reseñas. */
  const [destination, setDestination] = useState<ReviewDestination | null | undefined>(
    undefined,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fidelity.branding(merchantId),
      fidelity.tags(merchantId),
      fidelity.reviewDestination(merchantId),
    ])
      .then(([brand, tagList, reviewDestination]) => {
        if (cancelled) return;
        setBranding(brand);
        setTags(tagList);
        setDestination(reviewDestination);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo preparar el póster. Comprueba tu conexión.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  if (error) {
    return (
      <Alert tone="danger" title="No se pudo cargar el póster">
        {error}
      </Alert>
    );
  }
  if (!branding || tags === null || destination === undefined) {
    return <LoadingState label="Preparando el póster…" />;
  }

  const signupTag =
    tags.find((tag) => tag.tag_type === "loyalty_signup" && tag.status === "active") ?? null;
  const reviewTag =
    tags.find((tag) => tag.tag_type === "google_review" && tag.status === "active") ?? null;
  const reviewsVerified = destination?.verification_status === "verified";

  const missing: string[] = [];
  if (!signupTag) missing.push("el QR de alta de tarjeta");
  if (!reviewsVerified) missing.push("el enlace de reseñas verificado");
  else if (!reviewTag) missing.push("el QR de reseñas");

  return (
    <div className="space-y-5">
      {/* Controles: nunca se imprimen (§14.2). */}
      <div
        data-print="hide"
        className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-line bg-paper p-4"
      >
        <p className="max-w-xl text-sm leading-relaxed text-ink-soft">
          Hoja A4 para el mostrador con los dos recorridos <strong>por separado</strong>: nadie
          confundirá la tarjeta con la reseña. Imprímela o guárdala como PDF desde tu navegador.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => window.print()}
            icon={<IconDownload size={17} />}
          >
            Imprimir o guardar PDF
          </Button>
          <LinkButton
            href={`/merchants/${merchantId}/nfc`}
            variant="secondary"
            icon={<IconArrowRight size={16} />}
          >
            NFC y QR
          </LinkButton>
        </div>
      </div>

      {missing.length > 0 && (
        <div data-print="hide">
          <Alert tone="warn" title="Falta material para el póster">
            Antes de imprimir, configura {missing.join(" y ")} en la sección NFC y QR. La hoja lo
            indica con un aviso para que no salga un QR vacío.
          </Alert>
        </div>
      )}

      {/* Hoja imprimible: en pantalla se ve como papel; al imprimir ocupa
          la página entera (ver `@media print` en globals.css). */}
      <article
        className="poster-sheet mx-auto w-full max-w-[794px] rounded-3xl border border-line bg-white p-7 shadow-soft sm:p-9"
        aria-label="Póster imprimible del comercio"
      >
        <header
          className="flex items-center gap-4 border-b-2 pb-5"
          style={{ borderColor: branding.primary_color }}
        >
          {branding.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={branding.logo_url}
              alt={`Logotipo de ${merchantName}`}
              className="size-16 shrink-0 rounded-2xl object-cover"
            />
          ) : (
            <span
              aria-hidden="true"
              className="flex size-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-black text-white"
              style={{ backgroundColor: branding.primary_color }}
            >
              {(merchantName.trim()[0] ?? "·").toUpperCase()}
            </span>
          )}
          <div className="min-w-0">
            <h2 className="truncate text-2xl font-black tracking-tight text-ink sm:text-3xl">
              {merchantName}
            </h2>
            <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-ink-faint">
              Toca o escanea con tu móvil
            </p>
          </div>
        </header>

        <div className="mt-6 grid grid-cols-1 gap-6 print:grid-cols-2">
          {/* Bloque A · fidelización (§5.1, §14.2). */}
          <section
            className="flex flex-col items-center rounded-3xl border-2 p-5 text-center"
            style={{ borderColor: branding.primary_color }}
          >
            <span
              className="rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-white"
              style={{ backgroundColor: branding.primary_color }}
            >
              Fidelización
            </span>
            <h3 className="mt-3 text-xl font-black tracking-tight text-ink">Añade tu tarjeta</h3>
            {signupTag ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={fidelity.tagQrUrl(merchantId, signupTag.id)}
                alt="Código QR para crear tu tarjeta de fidelización"
                className="mt-4 w-48 bg-white p-2 sm:w-56"
              />
            ) : (
              <p className="mt-4 rounded-2xl border border-dashed border-line-strong bg-surface px-4 py-8 text-xs font-semibold text-ink-faint">
                QR de alta sin crear · vélo en NFC y QR
              </p>
            )}
            <p className="mt-4 max-w-[34ch] text-sm leading-relaxed text-ink-soft">
              Crea tu tarjeta digital y acumula un sello en cada visita. Después puedes añadirla a
              tu móvil.
            </p>
          </section>

          {/* Bloque B · reseñas (§4.3: solo texto neutral, sin incentivos). */}
          <section className="flex flex-col items-center rounded-3xl border-2 border-dashed border-line-strong bg-surface/50 p-5 text-center">
            <span className="rounded-full bg-ink px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-white">
              Reseñas de Google
            </span>
            <h3 className="mt-3 text-xl font-black tracking-tight text-ink">
              ¿Quieres compartir tu experiencia?
            </h3>
            {reviewTag && reviewsVerified ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={fidelity.tagQrUrl(merchantId, reviewTag.id)}
                alt="Código QR para dejar una reseña en Google"
                className="mt-4 w-48 bg-white p-2 sm:w-56"
              />
            ) : (
              <p className="mt-4 rounded-2xl border border-dashed border-line-strong bg-white px-4 py-8 text-xs font-semibold text-ink-faint">
                {reviewsVerified
                  ? "QR de reseñas sin crear · vélo en NFC y QR"
                  : "Enlace de reseñas sin verificar · en Reseñas Google"}
              </p>
            )}
            <p className="mt-4 max-w-[34ch] text-sm leading-relaxed text-ink-soft">
              Puedes dejar una reseña aquí. Es voluntario y no está vinculado a ningún premio ni
              descuento.
            </p>
          </section>
        </div>

        {branding.footer_text && (
          <p className="mt-6 border-t border-line pt-4 text-center text-xs font-semibold text-ink-faint">
            {branding.footer_text}
          </p>
        )}
      </article>
    </div>
  );
}
