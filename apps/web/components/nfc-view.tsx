"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  CopyButton,
  EmptyState,
  IconContactless,
  IconDownload,
  IconExternal,
  IconGift,
  IconPlus,
  IconPower,
  IconQr,
  IconStar,
  Input,
  LoadingState,
  Modal,
  Panel,
  SectionTitle,
  Select,
  StatusPill,
  IconWallet,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fidelity,
  type NfcStats,
  type NfcTag,
  type Program,
  type ReviewDestination,
} from "@/lib/fidelity";
import { formatNumber } from "@/lib/ui";

/**
 * Estado de los botones de creación de etiquetas (§5.1, §4.1).
 *
 * Devuelve el motivo por el que no se puede crear, o `null` si se puede.
 * Separado del componente para poder probarlo sin navegador.
 */
export function signupBlockReason(programs: Program[]): string | null {
  if (programs.length === 0) {
    return "Primero crea un programa de fidelización en la pestaña «Programas».";
  }
  return null;
}

export function reviewBlockReason(destination: ReviewDestination | null): string | null {
  if (!destination) {
    return "Primero guarda el enlace oficial de reseñas en la pestaña «Reseñas Google».";
  }
  if (destination.verification_status !== "verified") {
    return "Tu enlace está guardado pero sin verificar. Ve a «Reseñas Google», ábrelo y compruébalo para poder usar la etiqueta.";
  }
  return null;
}

type TagType = "loyalty_signup" | "google_review" | "counter" | "member_card_access";

/** URL absoluta que se imprime en el QR y se escribe en la etiqueta NFC. */
function shortUrl(tag: NfcTag): string {
  return tag.short_url ?? `/go/${tag.public_slug}`;
}

/** Etiqueta visual por tipo de etiqueta (alta, mostrador, reseñas, acceso). */
const TAG_META: Record<
  string,
  { tone: "teal" | "info" | "gold" | "brand"; badge: string; fallback: string; edge: string }
> = {
  loyalty_signup: {
    tone: "teal",
    badge: "fidelización",
    fallback: "Alta",
    edge: "before:bg-teal",
  },
  counter: {
    tone: "info",
    badge: "mostrador",
    fallback: "Mostrador",
    edge: "before:bg-info",
  },
  google_review: {
    tone: "gold",
    badge: "reseñas",
    fallback: "Reseñas",
    edge: "before:bg-gold-bright",
  },
  member_card_access: {
    tone: "brand",
    badge: "mi tarjeta",
    fallback: "Acceso a tarjetas",
    edge: "before:bg-brand",
  },
};

/** Fichas explicativas de los cuatro tipos: nunca se mezclan entre sí. */
const TYPE_GUIDE = [
  {
    type: "loyalty_signup",
    icon: IconGift,
    title: "Etiquetas de fidelización",
    text: (
      <>
        Llevan al cliente a tu <strong>página de alta</strong>: se registra, obtiene su tarjeta con
        QR y empieza a acumular sellos. Van en el mostrador o en la entrada.
      </>
    ),
    tone: "teal" as const,
    chip: "bg-teal-soft text-teal border-teal/25",
    edge: "bg-teal",
  },
  {
    type: "counter",
    icon: IconContactless,
    title: "Etiquetas de mostrador",
    text: (
      <>
        Atajo para <strong>el personal</strong>: al tocarla con su móvil se abren las operaciones con
        ese programa ya elegido. Nunca suman sellos por sí solas.
      </>
    ),
    tone: "info" as const,
    chip: "bg-info-soft text-info border-info/25",
    edge: "bg-info",
  },
  {
    type: "google_review",
    icon: IconStar,
    title: "Etiquetas de reseñas de Google",
    text: (
      <>
        Llevan al cliente a tu <strong>ficha oficial de Google</strong> para que deje una reseña si
        quiere. Van por separado: nunca se premia ni se filtra por reseñar.
      </>
    ),
    tone: "gold" as const,
    chip: "bg-gold-soft text-warn border-warn/25",
    edge: "bg-gold-bright",
  },
  {
    type: "member_card_access",
    icon: IconWallet,
    title: "Recuperar tarjeta del cliente",
    text: (
      <>
        El cliente introduce su correo y recibe un enlace de un solo uso. Solo tras verificar ese
        correo verá sus tarjetas de este comercio.
      </>
    ),
    tone: "brand" as const,
    chip: "bg-brand-soft text-brand border-brand/25",
    edge: "bg-brand",
  },
];

/**
 * Gestión de etiquetas (§5.4, §14): dos tipos **independientes**, con QR
 * imprimible, instrucciones y posibilidad de desactivar una etiqueta.
 */
export function NfcView({ merchantId }: { merchantId: string }) {
  const [tags, setTags] = useState<NfcTag[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [destination, setDestination] = useState<ReviewDestination | null>(null);
  const [stats, setStats] = useState<NfcStats | null>(null);
  const [programId, setProgramId] = useState("");
  const [label, setLabel] = useState("");
  const [tagType, setTagType] = useState<TagType>("loyalty_signup");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [qrTag, setQrTag] = useState<NfcTag | null>(null);
  const [toggleTag, setToggleTag] = useState<NfcTag | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [tagRows, programRows, statsData, destinationData] = await Promise.all([
          fidelity.tags(merchantId),
          fidelity.programs(merchantId),
          fidelity.nfcStats(merchantId),
          fidelity.reviewDestination(merchantId),
        ]);
        if (cancelled) return;
        setTags(tagRows);
        setPrograms(programRows);
        setStats(statsData);
        setDestination(destinationData);
        setProgramId((current) => current || programRows[0]?.id || "");
      } catch {
        if (!cancelled) setError("No se pudieron cargar las etiquetas.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  const signupReason = signupBlockReason(programs);
  const reviewReason = reviewBlockReason(destination);
  // Las etiquetas de alta y de mostrador comparten requisito: un programa.
  const blockReason =
    tagType === "google_review"
      ? reviewReason
      : tagType === "member_card_access"
        ? null
        : signupReason;

  if (loading) {
    return <LoadingState label="Cargando etiquetas…" />;
  }

  async function createTag() {
    setError(null);
    setNotice(null);
    setCreating(true);
    try {
      if (tagType === "loyalty_signup") {
        await fidelity.createTag(merchantId, {
          tag_type: "loyalty_signup",
          label: label || "Mostrador",
          program_id: programId,
        });
        setNotice("Etiqueta de alta creada. Descarga el QR o escribe la URL en tu etiqueta NFC.");
      } else if (tagType === "counter") {
        await fidelity.createTag(merchantId, {
          tag_type: "counter",
          label: label || "Atajo de caja",
          program_id: programId,
        });
        setNotice(
          "Etiqueta de mostrador creada. El personal la toca con su móvil para abrir las operaciones con este programa ya elegido; nunca suma sellos por sí sola.",
        );
      } else if (tagType === "member_card_access") {
        await fidelity.createTag(merchantId, {
          tag_type: "member_card_access",
          label: label || "Recuperar tarjeta",
        });
        setNotice(
          "Etiqueta creada. El cliente introduce su correo y recibe un enlace temporal; la etiqueta no contiene datos ni códigos de tarjetas.",
        );
      } else {
        await fidelity.createTag(merchantId, {
          tag_type: "google_review",
          label: label || "Zona de caja",
        });
        setNotice("Etiqueta de reseñas creada. Recuerda: solo redirige con el enlace verificado.");
      }
      setLabel("");
      load();
    } catch (err) {
      setError(friendlyTagError(err));
    } finally {
      setCreating(false);
    }
  }

  async function toggle(tag: NfcTag) {
    setError(null);
    try {
      await fidelity.updateTag(merchantId, tag.id, {
        status: tag.status === "active" ? "disabled" : "active",
      });
      load();
    } catch (err) {
      setError(friendlyTagError(err, "No se pudo actualizar la etiqueta."));
    }
  }

  const verified = destination?.verification_status === "verified";
  const secondaryStats = stats
    ? [
        { label: "Clics en alta", value: stats.loyalty_signup_clicks },
        { label: "Usos de mostrador", value: stats.counter_clicks },
        { label: "Accesos a mi tarjeta", value: stats.member_card_access_clicks },
        { label: "Clics en reseñas", value: stats.review_link_clicks },
        { label: "Etiquetas activas", value: stats.tags_active },
      ]
    : [];

  return (
    <div className="space-y-6">
      {error && (
        <Alert tone="danger" title="No se pudo completar">
          {error}
        </Alert>
      )}
      {notice && (
        <Alert tone="ok" title="Hecho">
          {notice}
        </Alert>
      )}

      {/* Uso real: un dato principal y el resto en segundo plano. */}
      {stats && (
        <Panel className="animate-in">
          <SectionTitle
            title="Uso de tus etiquetas"
            description="Aperturas y clics registrados desde que creaste cada etiqueta."
            icon={<IconContactless size={18} />}
          />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr] lg:items-center">
            <div className="mesh-ink grain relative overflow-hidden rounded-2xl p-5 text-white shadow-soft">
              <span
                aria-hidden="true"
                className="absolute -right-8 -top-10 size-28 rounded-full border border-white/15"
              />
              <p className="relative text-[11px] font-semibold uppercase tracking-[0.13em] text-white/60">
                Total de clics
              </p>
              <p className="tnum relative mt-1.5 text-[42px] font-bold leading-none tracking-[-0.03em]">
                {formatNumber(stats.total_clicks)}
              </p>
              <p className="relative mt-1 text-[11px] text-white/55">
                suma de todos los tipos de etiqueta
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              {secondaryStats.map((item) => (
                <div key={item.label} className="min-w-0">
                  <dt className="text-[12px] leading-snug text-ink-soft">{item.label}</dt>
                  <dd className="tnum mt-0.5 text-xl font-bold leading-none text-ink">
                    {formatNumber(item.value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="rule-dots my-4 text-ink-faint" />
          <p className="text-[11px] leading-relaxed text-ink-faint">
            Los clics de reseñas son <strong className="text-ink-soft">visitas al enlace</strong>,
            no reseñas publicadas ni valoraciones.
          </p>
        </Panel>
      )}

      {/* Los tipos de etiqueta, claramente distintos (§5.1, ADR-0008) */}
      <section aria-label="Tipos de etiqueta" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {TYPE_GUIDE.map(({ type, icon: Icon, title, text, chip, edge }) => (
          <article
            key={type}
            className="relative overflow-hidden rounded-2xl border border-line bg-surface p-4 shadow-soft sm:p-5"
          >
            <span
              aria-hidden="true"
              className={`absolute inset-y-4 left-0 w-[3px] rounded-r-full ${edge}`}
            />
            <div className="flex items-start gap-3">
              <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl border ${chip}`}>
                <Icon size={19} />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-bold leading-snug text-ink">{title}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">{text}</p>
              </div>
            </div>
          </article>
        ))}
      </section>

      {/* Estado del enlace de reseñas: es lo que bloquea la etiqueta de reseñas. */}
      <div
        className={`rounded-2xl border p-4 text-sm ${
          verified
            ? "border-ok/25 bg-ok-soft/60"
            : "border-warn/25 bg-gold-soft/60"
        }`}
      >
        {verified ? (
          <p className="flex flex-wrap items-center gap-2">
            <StatusPill tone="ok">Enlace comprobado por el comercio</StatusPill>
            <span className="text-ink-soft">
              Comprobado el{" "}
              {destination?.verified_at &&
                new Date(destination.verified_at).toLocaleDateString("es-ES")}
              . La etiqueta de reseñas lleva a tu ficha oficial.
            </span>
            <Link href={`/merchants/${merchantId}/reviews`} className="font-semibold text-brand underline underline-offset-2">
              Cambiarlo
            </Link>
          </p>
        ) : (
          <p className="flex flex-wrap items-center gap-2">
            <StatusPill tone="warn">Sin verificar</StatusPill>
            <span className="text-ink-soft">
              {destination
                ? "Tu enlace de reseñas está guardado pero SIN verificar: la etiqueta no redirigirá hasta que lo verifiques."
                : "Todavía no has guardado el enlace de reseñas de tu negocio."}
            </span>
            <Link href={`/merchants/${merchantId}/reviews`} className="font-semibold text-brand underline underline-offset-2">
              Ir a «Reseñas Google»
            </Link>
          </p>
        )}
      </div>

      {/* Nueva etiqueta: selector de tipo + requisitos visibles */}
      <Panel>
        <SectionTitle
          title="Nueva etiqueta"
          description="Elige el tipo, dale un nombre para reconocerla y crea la etiqueta."
          icon={<IconPlus size={18} />}
        />

        <div
          role="radiogroup"
          aria-label="Tipo de etiqueta"
          className="grid grid-cols-1 gap-2.5 sm:grid-cols-2"
        >
          {(
            [
              {
                type: "loyalty_signup" as const,
                title: "Alta de fidelización",
                text: "Abre tu página de alta de clientes.",
                icon: <IconGift size={18} />,
                tone: "teal",
              },
              {
                type: "counter" as const,
                title: "Mostrador (para el personal)",
                text: "El personal la toca y abre las operaciones de este programa.",
                icon: <IconContactless size={18} />,
                tone: "info",
              },
              {
                type: "google_review" as const,
                title: "Reseñas de Google",
                text: "Abre tu ficha oficial de reseñas.",
                icon: <IconStar size={18} />,
                tone: "gold",
              },
              {
                type: "member_card_access" as const,
                title: "Recuperar mi tarjeta (para clientes)",
                text: "Abre el acceso por correo a las tarjetas propias de este comercio.",
                icon: <IconWallet size={18} />,
                tone: "brand",
              },
            ]
          ).map((option) => {
            const selected = tagType === option.type;
            return (
              <button
                key={option.type}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setTagType(option.type)}
                className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition-colors ${
                  selected
                    ? "border-brand bg-brand-soft/60 ring-2 ring-brand/25"
                    : "border-line bg-surface hover:border-brand/40"
                }`}
              >
                <span
                  className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                    option.tone === "teal"
                      ? "bg-teal-soft text-teal"
                      : option.tone === "info"
                        ? "bg-info-soft text-info"
                        : option.tone === "brand"
                          ? "bg-brand-soft text-brand"
                          : "bg-gold-soft text-warn"
                  }`}
                >
                  {option.icon}
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] font-bold leading-snug text-ink">
                    {option.title}
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-ink-soft">
                    {option.text}
                  </span>
                </span>
                <span
                  aria-hidden="true"
                  className={`ml-auto mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border-2 ${
                    selected ? "border-brand bg-brand" : "border-line-strong bg-surface"
                  }`}
                >
                  {selected && <span className="size-1.5 rounded-full bg-white" />}
                </span>
              </button>
            );
          })}
        </div>

        <div className="mt-4 space-y-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1">
              <label htmlFor="tag-label" className="text-sm font-semibold text-ink">
                Nombre de la etiqueta{" "}
                <span className="font-normal text-ink-faint">(opcional)</span>
              </label>
              <Input
                id="tag-label"
                className="mt-1.5"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="Junto a la caja"
              />
            </div>

            {(tagType === "loyalty_signup" || tagType === "counter") && (
              <div className="min-w-0 sm:w-56">
                <label htmlFor="tag-program" className="text-sm font-semibold text-ink">
                  Programa
                </label>
                <Select
                  id="tag-program"
                  className="mt-1.5"
                  value={programId}
                  onChange={(e) => setProgramId(e.target.value)}
                  disabled={programs.length === 0}
                >
                  {programs.length === 0 && <option value="">Sin programas todavía</option>}
                  {programs.map((program) => (
                    <option key={program.id} value={program.id}>
                      {program.name}
                    </option>
                  ))}
                </Select>
              </div>
            )}

            <Button
              onClick={() => void createTag()}
              loading={creating}
              disabled={Boolean(blockReason)}
              icon={<IconPlus size={17} />}
              className="shrink-0"
            >
              {tagType === "loyalty_signup"
                ? "Crear etiqueta de alta"
                : tagType === "counter"
                  ? "Crear etiqueta de mostrador"
                  : tagType === "member_card_access"
                    ? "Crear etiqueta para recuperar tarjetas"
                    : "Crear etiqueta de reseñas"}
            </Button>
          </div>
          <p className="text-xs text-ink-faint">
            Ejemplos de nombre: «Junto a la caja», «Entrada», «Vitrina».
          </p>
        </div>

        {blockReason && (
          <div className="mt-3">
            <Alert tone="warn" title="Todavía no puedes crear esta etiqueta">
              {blockReason}
            </Alert>
          </div>
        )}

        {/* Guía de instalación (§14.3): la app no escribe la etiqueta física. */}
        <ol className="mt-5 grid grid-cols-1 gap-3 border-t border-line pt-5 sm:grid-cols-3">
          {[
            "Crea la etiqueta aquí y descarga su QR.",
            "Imprime el QR o escribe la URL corta en tu etiqueta NFC (NDEF URI) con una app compatible.",
            "Pruébala con un iPhone y un Android antes de dejarla fija.",
          ].map((step, index) => (
            <li
              key={step}
              className="rounded-xl bg-surface-2/70 p-3.5 text-xs leading-relaxed text-ink-soft"
            >
              <span className="mb-1.5 flex size-6 items-center justify-center rounded-full bg-brand text-[11px] font-bold text-white">
                {index + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs leading-relaxed text-ink-faint">
          La plataforma no escribe automáticamente las etiquetas NFC físicas: te da la URL y el QR
          para programarlas tú y probarlas antes de instalarlas.
        </p>
      </Panel>

      {/* Listado de etiquetas */}
      {tags.length === 0 ? (
        <EmptyState
          illustration="tag"
          title="No hay etiquetas todavía"
          description="Crea la primera con el formulario de arriba y descarga su QR para imprimirlo o programar tu etiqueta NFC."
        />
      ) : (
        <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {tags.map((tag) => {
            const meta = TAG_META[tag.tag_type];
            return (
              <li
                key={tag.id}
                className={`relative overflow-hidden rounded-2xl border bg-surface p-4 pl-5 shadow-soft transition-colors sm:p-5 sm:pl-6 ${
                  tag.status === "active" ? "border-line" : "border-line opacity-80"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`absolute inset-y-4 left-0 w-[3px] rounded-r-full ${
                    meta?.tone === "teal"
                      ? "bg-teal"
                      : meta?.tone === "info"
                        ? "bg-info"
                        : meta?.tone === "brand"
                          ? "bg-brand"
                          : "bg-gold-bright"
                  }`}
                />
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="flex min-w-0 flex-wrap items-center gap-2 font-bold text-ink">
                    <span className="truncate">
                      {tag.label ?? (meta?.fallback ?? "Etiqueta")}
                    </span>
                    <Badge tone={meta?.tone ?? "neutral"}>{meta?.badge ?? tag.tag_type}</Badge>
                  </p>
                  {tag.status !== "active" && <StatusPill tone="neutral">Desactivada</StatusPill>}
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate rounded-lg bg-surface-2 px-2.5 py-1.5 font-mono text-[11px] text-ink">
                    {shortUrl(tag)}
                  </code>
                  <CopyButton value={shortUrl(tag)} label="Copiar" />
                </div>
                <p className="mt-1.5 flex items-start gap-1 text-[11px] text-ink-faint">
                  <IconExternal size={12} className="mt-0.5 shrink-0" />
                  <span className="break-all">{tag.destination_url}</span>
                </p>

                <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<IconQr size={15} />}
                    onClick={() => setQrTag(tag)}
                  >
                    Ver QR
                  </Button>
                  {tag.status === "active" ? (
                    <Button variant="danger" size="sm" onClick={() => setToggleTag(tag)}>
                      Desactivar
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={<IconPower size={15} />}
                      onClick={() => void toggle(tag)}
                    >
                      Reactivar
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-xs leading-relaxed text-ink-faint">
        Instrucciones: descarga el QR para imprimir, o escribe la URL corta en tu etiqueta NFC
        (NDEF URI). Prueba la etiqueta con un iPhone y un Android antes de dejarla fija.
      </p>

      {/* Vista previa del QR */}
      <Modal
        open={qrTag !== null}
        onClose={() => setQrTag(null)}
        title={`QR de «${qrTag?.label ?? "etiqueta"}»`}
        footer={
          qrTag && (
            <a
              href={fidelity.tagQrUrl(merchantId, qrTag.id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-strong"
            >
              <IconDownload size={17} />
              Descargar SVG
            </a>
          )
        }
      >
        {qrTag && (
          <div className="space-y-4">
            {/* QR servido por la API (SVG, mismo origen). */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fidelity.tagQrUrl(merchantId, qrTag.id)}
              alt={`Código QR de la etiqueta ${qrTag.label ?? ""}`}
              className="mx-auto w-60 rounded-2xl border border-line bg-white p-3 shadow-soft"
            />
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                URL para tu etiqueta NFC
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                <code className="flex-1 break-all rounded-lg bg-surface-2 px-2.5 py-2 font-mono text-[11px] text-ink">
                  {shortUrl(qrTag)}
                </code>
                <CopyButton value={shortUrl(qrTag)} label="Copiar" />
              </div>
            </div>
            <p className="text-xs leading-relaxed text-ink-faint">
              Programa esta URL en la etiqueta NFC (NDEF URI) con una app compatible y pruébala con
              un iPhone y un Android antes de instalarla. Si la etiqueta se pierde o se usa mal,
              puedes desactivarla desde esta pantalla.
            </p>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={toggleTag !== null}
        title="¿Desactivar esta etiqueta?"
        message="La URL dejará de redirigir y mostrará una página de etiqueta desactivada. Puedes reactivarla cuando quieras."
        confirmLabel="Desactivar etiqueta"
        onClose={() => setToggleTag(null)}
        onConfirm={() => {
          const tag = toggleTag;
          setToggleTag(null);
          if (tag) void toggle(tag);
        }}
      />
    </div>
  );
}

/** Traduce los errores del backend a algo que una persona entienda. */
function friendlyTagError(err: unknown, fallback = "No se pudo crear la etiqueta."): string {
  if (err instanceof ApiError) {
    if (err.code === "review_destination_required") {
      return "Guarda y verifica primero el enlace de reseñas en la pestaña «Reseñas Google».";
    }
    if (err.code === "program_required") {
      return "Esta etiqueta necesita un programa: créalo antes en «Programas».";
    }
    if (err.code === "not_found") {
      return "No se ha encontrado el programa seleccionado. Recarga la página.";
    }
    if (err.status === 422) {
      return "Revisa los datos del formulario: algún campo no es válido.";
    }
    return err.message;
  }
  return fallback;
}
