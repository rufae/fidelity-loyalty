"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  EmptyState,
  FormField,
  IconArrowRight,
  IconCheck,
  IconGift,
  IconPlus,
  Input,
  LoadingState,
  Panel,
  SectionTitle,
  StatusPill,
  Stepper,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { PROGRAM_STATUS_LABELS, fidelity, type Program } from "@/lib/fidelity";
import { formatDate } from "@/lib/ui";

const STATUS_TONE: Record<string, "neutral" | "ok" | "warn"> = {
  draft: "neutral",
  active: "ok",
  paused: "warn",
  archived: "neutral",
};

/** Guía compacta de primer uso: qué hacer y en qué orden. */
const STEPS = [
  { title: "Crea el programa", description: "Nombre y tipo de tarjeta." },
  { title: "Define recompensas", description: "Qué se consigue y con cuántos sellos." },
  { title: "Escribe las condiciones", description: "Texto visible antes del alta." },
  { title: "Publica y etiqueta", description: "Activa el alta y genera tu QR/NFC." },
];

export function ProgramsView({ merchantId }: { merchantId: string }) {
  const [programs, setPrograms] = useState<Program[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    void (async () => {
      try {
        const rows = await fidelity.programs(merchantId);
        if (!cancelled) setPrograms(rows);
      } catch {
        if (!cancelled) setError("No se pudieron cargar los programas.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => load(), [load]);

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await fidelity.createProgram(merchantId, { name });
      setName("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el programa.");
    } finally {
      setLoading(false);
    }
  }

  const currentStep =
    programs === null || programs.length === 0
      ? 0
      : programs.some((program) => program.status === "active")
        ? STEPS.length
        : 2;

  return (
    <div className="space-y-6">
      <Stepper steps={STEPS} current={currentStep} />

      {error && (
        <Alert tone="danger" title="No se pudo completar">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px] lg:items-start">
        {/* Listado: la pieza principal de la pantalla. */}
        <section aria-label="Programas del comercio" className="space-y-3">
          <SectionTitle
            title="Tus programas"
            description="Cada programa tiene sus recompensas y sus condiciones. Solo los activos abren el alta pública."
            icon={<IconGift size={18} />}
          />

          {programs === null ? (
            <LoadingState label="Cargando programas…" />
          ) : programs.length === 0 ? (
            <EmptyState
              illustration="card"
              title="Todavía no hay programas"
              description="Crea el primero con el formulario de al lado: será el programa de sellos que verán tus clientes."
            />
          ) : (
            <ul className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {programs.map((program) => {
                const isActive = program.status === "active";
                return (
                  <li key={program.id}>
                    <Link
                      href={`/merchants/${merchantId}/programs/${program.id}`}
                      className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-lift ${
                        isActive
                          ? "border-brand/20 bg-[linear-gradient(150deg,#f4f1ff_0%,#ffffff_55%)] hover:border-brand/40"
                          : "border-line bg-surface hover:border-brand/40"
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className={`absolute inset-y-4 left-0 w-[3px] rounded-r-full ${
                          isActive ? "bg-brand" : "bg-line-strong"
                        }`}
                      />
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-base font-bold text-ink group-hover:text-brand">
                            {program.name}
                          </p>
                          <p className="mt-1 text-[11px] text-ink-faint">
                            Condiciones v{program.terms_version} ·{" "}
                            <code className="font-mono">{program.slug}</code>
                          </p>
                        </div>
                        <StatusPill tone={STATUS_TONE[program.status] ?? "neutral"}>
                          {PROGRAM_STATUS_LABELS[program.status] ?? program.status}
                        </StatusPill>
                      </div>

                      <div className="mt-auto pt-5">
                        <p className="text-[11px] leading-snug text-ink-faint">
                          {program.published_at
                            ? `Publicado el ${formatDate(program.published_at)}`
                            : "Aún sin publicar"}
                        </p>
                        <span className="mt-1.5 inline-flex items-center gap-1 whitespace-nowrap text-[13px] font-semibold text-brand">
                          Abrir editor
                          <IconArrowRight
                            size={15}
                            className="transition-transform group-hover:translate-x-0.5"
                          />
                        </span>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}

          {programs !== null && programs.length > 0 && (
            <p className="flex items-start gap-2 rounded-xl bg-paper p-3 text-xs leading-relaxed text-ink-faint">
              <IconCheck size={15} className="mt-0.5 shrink-0 text-ok" />
              <span>
                El estado del programa controla si las altas están abiertas: solo los programas{" "}
                <strong className="font-semibold text-ink-soft">activos</strong> aparecen en tu
                página pública de alta.
              </span>
            </p>
          )}
        </section>

        {/* Crear: una acción pequeña, siempre a mano. */}
        <Panel tone="warm" className="lg:sticky lg:top-6">
          <SectionTitle
            title="Nuevo programa"
            description="Nace en borrador: podrás definir recompensas y condiciones antes de publicarlo."
            icon={<IconPlus size={18} />}
          />
          <form onSubmit={onCreate} className="space-y-3">
            <FormField label="Nombre del programa" required>
              {({ id, describedBy }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  required
                  minLength={2}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Club del Café"
                />
              )}
            </FormField>
            <Button
              type="submit"
              loading={loading}
              icon={<IconPlus size={17} />}
              className="w-full"
            >
              {loading ? "Creando…" : "Crear programa"}
            </Button>
          </form>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            Tipo sellos. El alta pública, el QR y Wallet se configuran después, en el editor del
            programa y en «NFC y QR».
          </p>
        </Panel>
      </div>
    </div>
  );
}
