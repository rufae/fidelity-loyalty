"use client";

/**
 * Estudio de diseño de tarjeta (decisión de compra #8, §13.3).
 *
 * El comercio personaliza **su** tarjeta: logotipo, colores, icono de los
 * sellos y pie de tarjeta. La vista previa usa el mismo componente que la
 * tarjeta real del cliente (LoyaltyCard): lo que se ve aquí es lo que se
 * publica, sin maquetas paralelas. Nada de esto toca saldos ni reglas.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { useMerchant } from "@/components/merchant-context";
import {
  Alert,
  Button,
  LoadingState,
  Panel,
  SectionTitle,
} from "@/components/ui";
import { LoyaltyCard } from "@/components/ui/loyalty-card";
import { ApiError } from "@/lib/api";
import { fidelity, type CardBranding } from "@/lib/fidelity";
import { shade } from "@/lib/ui";

const STAMP_ICONS: { value: string; label: string }[] = [
  { value: "cup", label: "Taza" },
  { value: "heart", label: "Corazón" },
  { value: "star", label: "Estrella" },
  { value: "leaf", label: "Hoja" },
  { value: "spark", label: "Destello" },
];

/** Los mismos trazos que estampa StampRow (12×12), para el selector. */
const GLYPHS: Record<string, string> = {
  cup: "M3 4.5h5.5v2.7a2.75 2.75 0 0 1-5.5 0Z M8.5 5.2h.8a1.3 1.3 0 0 1 0 2.6h-.8 M2.5 10.5h6.5",
  heart: "M6 10C6 10 2 7.6 2 4.9 2 3.3 3.3 2.4 4.4 2.4c.8 0 1.4.5 1.6 1.1.2-.6.8-1.1 1.6-1.1 1.1 0 2.4.9 2.4 2.5C10 7.6 6 10 6 10Z",
  star: "M6 2l1.2 2.4 2.6.4-1.9 1.9.4 2.6L6 8.1 3.7 9.3l.4-2.6L2.2 4.8l2.6-.4L6 2Z",
  leaf: "M9.5 2.5C5 3 2.5 5.5 2.5 9.5c4 0 6.5-2.5 7-7Z M3.5 8.5C5 6.5 6.5 5 8.5 3.5",
  spark: "M6 1.5 7 5l3.5 1L7 7l-1 3.5L5 7 1.5 6 5 5 6 1.5Z",
};

const PRESETS: { name: string; primary: string; accent: string; icon: string }[] = [
  { name: "Cafetería", primary: "#5b48d6", accent: "#f7bd4b", icon: "cup" },
  { name: "Verde fresco", primary: "#1e8e5a", accent: "#ffd166", icon: "leaf" },
  { name: "Cálido", primary: "#b4531f", accent: "#ffd166", icon: "heart" },
  { name: "Nocturno", primary: "#1f2a56", accent: "#7dd3fc", icon: "star" },
  { name: "Floristería", primary: "#9d2f63", accent: "#fce7f3", icon: "heart" },
  { name: "Panadería", primary: "#8a5a12", accent: "#fde68a", icon: "spark" },
];

export function CardDesignView({ merchantId }: { merchantId: string }) {
  const { merchantName: contextName } = useMerchant();
  const merchantName = contextName || "Tu comercio";
  const [branding, setBranding] = useState<CardBranding | null>(null);
  /** Borrador en edición: se publica solo al guardar. */
  const [draft, setDraft] = useState<CardBranding | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void fidelity
      .branding(merchantId)
      .then((data) => {
        if (cancelled) return;
        setBranding(data);
        setDraft(data);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setError("No se pudo cargar el diseño actual.");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  const dirty =
    draft !== null &&
    branding !== null &&
    (draft.primary_color !== branding.primary_color ||
      draft.accent_color !== branding.accent_color ||
      draft.stamp_icon !== branding.stamp_icon ||
      (draft.footer_text ?? "") !== (branding.footer_text ?? ""));

  function patch(changes: Partial<CardBranding>) {
    setDraft((current) => (current ? { ...current, ...changes } : current));
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await fidelity.updateBranding(merchantId, {
        primary_color: draft.primary_color,
        accent_color: draft.accent_color,
        stamp_icon: draft.stamp_icon,
        footer_text: draft.footer_text ?? "",
      });
      setBranding(updated);
      setDraft(updated);
      setNotice("Diseño guardado: así verá la tarjeta tu cliente desde ahora.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el diseño.");
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    setDraft(branding);
  }

  async function uploadLogo(file: File) {
    setLogoBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (file.size > 512 * 1024) {
        throw new ApiError(413, "logo_too_large", "El logotipo supera los 512 KB. Reduce el tamaño e inténtalo de nuevo.");
      }
      const updated = await fidelity.uploadLogo(merchantId, file);
      setBranding(updated);
      setDraft(updated);
      setNotice("Logotipo actualizado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo subir el logotipo.");
    } finally {
      setLogoBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function removeLogo() {
    setLogoBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await fidelity.removeLogo(merchantId);
      setBranding(updated);
      setDraft(updated);
      setNotice("Logotipo retirado: la tarjeta vuelve a usar tus iniciales.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo retirar el logotipo.");
    } finally {
      setLogoBusy(false);
    }
  }

  if (loading) return <LoadingState label="Cargando tu diseño…" />;

  const previewBranding = draft
    ? { ...draft, logo_url: draft.logo_url }
    : null;

  return (
    <div className="space-y-5">
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

      <Panel className="animate-in">
        <SectionTitle
          title="Diseña la tarjeta que llevarán tus clientes"
          description="Logotipo, colores, icono de sellos y pie de tarjeta. La vista previa usa exactamente el mismo componente que la tarjeta real: lo que ves es lo que se publica."
        />
        <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_1fr]">
          {/* Controles */}
          <div className="space-y-6">
            <section aria-label="Logotipo">
              <h3 className="text-sm font-bold text-ink">Logotipo</h3>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                PNG o JPG, hasta 512 KB. Cuadrado funciona mejor: la tarjeta lo
                muestra en un círculo pequeño. Se sirve por una dirección
                privada y anónima: nunca expone datos del comercio.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                {draft?.logo_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={draft.logo_url}
                    alt="Logotipo actual"
                    className="size-14 rounded-xl border border-line bg-surface-2 object-contain p-1"
                  />
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void uploadLogo(file);
                  }}
                />
                <Button
                  type="button"
                  variant="secondary"
                  loading={logoBusy}
                  onClick={() => fileRef.current?.click()}
                >
                  {draft?.logo_url ? "Cambiar logotipo" : "Subir logotipo"}
                </Button>
                {draft?.logo_url && (
                  <Button type="button" variant="ghost" onClick={() => void removeLogo()}>
                    Retirar
                  </Button>
                )}
              </div>
            </section>

            <section aria-label="Colores">
              <h3 className="text-sm font-bold text-ink">Colores</h3>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                El color principal tiñe la tarjeta; el de acento, los sellos
                puestos. Elige colores con buen contraste sobre ellos: el texto
                de la tarjeta siempre es blanco.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-ink-soft">
                  Color principal
                  <span className="mt-1 flex items-center gap-2">
                    <input
                      type="color"
                      value={draft?.primary_color ?? "#5b48d6"}
                      onChange={(event) => patch({ primary_color: event.target.value })}
                      className="h-10 w-12 cursor-pointer rounded-lg border border-line bg-surface p-0.5"
                      aria-label="Elegir color principal"
                    />
                    <input
                      value={draft?.primary_color ?? ""}
                      onChange={(event) => {
                        const value = event.target.value;
                        if (/^#[0-9a-fA-F]{0,6}$/.test(value)) {
                          patch({ primary_color: value });
                        }
                      }}
                      maxLength={7}
                      className="w-full rounded-xl border border-line-strong bg-surface px-3 py-2 font-mono text-sm text-ink focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                    />
                  </span>
                </label>
                <label className="block text-xs font-semibold text-ink-soft">
                  Color de acento
                  <span className="mt-1 flex items-center gap-2">
                    <input
                      type="color"
                      value={draft?.accent_color ?? "#f7bd4b"}
                      onChange={(event) => patch({ accent_color: event.target.value })}
                      className="h-10 w-12 cursor-pointer rounded-lg border border-line bg-surface p-0.5"
                      aria-label="Elegir color de acento"
                    />
                    <input
                      value={draft?.accent_color ?? ""}
                      onChange={(event) => {
                        const value = event.target.value;
                        if (/^#[0-9a-fA-F]{0,6}$/.test(value)) {
                          patch({ accent_color: value });
                        }
                      }}
                      maxLength={7}
                      className="w-full rounded-xl border border-line-strong bg-surface px-3 py-2 font-mono text-sm text-ink focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
                    />
                  </span>
                </label>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() =>
                      patch({
                        primary_color: preset.primary,
                        accent_color: preset.accent,
                        stamp_icon: preset.icon,
                      })
                    }
                    className="flex items-center gap-2 rounded-xl border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink-soft transition-colors hover:border-brand/40 hover:text-ink"
                    title={`Aplicar paleta «${preset.name}»`}
                  >
                    <span
                      aria-hidden="true"
                      className="flex size-5 overflow-hidden rounded-full border border-line"
                    >
                      <span className="h-full w-1/2" style={{ background: preset.primary }} />
                      <span className="h-full w-1/2" style={{ background: preset.accent }} />
                    </span>
                    {preset.name}
                  </button>
                ))}
              </div>
            </section>

            <section aria-label="Icono de los sellos">
              <h3 className="text-sm font-bold text-ink">Icono de los sellos</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {STAMP_ICONS.map((option) => {
                  const selected = draft?.stamp_icon === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => patch({ stamp_icon: option.value })}
                      aria-pressed={selected}
                      className={`flex min-w-16 flex-col items-center gap-1.5 rounded-xl border px-3 py-2.5 transition-colors ${
                        selected
                          ? "border-brand bg-brand-soft"
                          : "border-line bg-surface hover:border-ink-faint/60"
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className="flex size-7 items-center justify-center rounded-full"
                        style={{
                          background: `linear-gradient(145deg, ${shade(draft?.accent_color ?? "#f7bd4b", 26)}, ${draft?.accent_color ?? "#f7bd4b"} 55%, ${shade(draft?.accent_color ?? "#f7bd4b", -14)})`,
                        }}
                      >
                        <svg viewBox="0 0 12 12" className="size-3.5" fill="none">
                          <path
                            d={GLYPHS[option.value]}
                            stroke={shade(draft?.accent_color ?? "#f7bd4b", -62)}
                            strokeWidth="1.7"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                      <span className={`text-[10px] font-bold ${selected ? "text-brand" : "text-ink-soft"}`}>
                        {option.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section aria-label="Pie de tarjeta">
              <h3 className="text-sm font-bold text-ink">Pie de tarjeta</h3>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                Una frase breve bajo los sellos: una condición, un agradecimiento
                o tu eslogan. Máximo 80 caracteres.
              </p>
              <input
                value={draft?.footer_text ?? ""}
                maxLength={80}
                onChange={(event) => patch({ footer_text: event.target.value })}
                placeholder="Café de especialidad desde 1998 · Gracias por volver"
                className="mt-2 w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
              />
              <p className="tnum mt-1 text-right text-[11px] text-ink-faint">
                {(draft?.footer_text ?? "").length}/80
              </p>
            </section>
          </div>

          {/* Vista previa en vivo: el mismo componente que la tarjeta real. */}
          <div>
            <div className="lg:sticky lg:top-24">
              <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                Vista previa en vivo · datos de ejemplo
              </p>
              <LoyaltyCard
                merchantName={merchantName}
                programName="Tu programa"
                stamps={6}
                rewards={[
                  { name: "Café gratis", stamps_required: 10 },
                  { name: "Desayuno completo", stamps_required: 12 },
                ]}
                holderName="María G."
                variant="card"
                branding={previewBranding}
              />
              <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
                Así la verá tu cliente en su móvil con 6 de 10 sellos. El saldo
                real siempre lo confirma el servidor.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-end gap-2 border-t border-line pt-4">
          {dirty && (
            <Button type="button" variant="ghost" onClick={reset}>
              Descartar cambios
            </Button>
          )}
          <Button type="button" onClick={() => void save()} loading={saving} disabled={!dirty}>
            {dirty ? "Guardar diseño" : "Sin cambios por guardar"}
          </Button>
        </div>
      </Panel>
    </div>
  );
}
