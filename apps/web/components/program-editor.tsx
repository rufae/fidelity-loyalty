"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import {
  Alert,
  Button,
  ConfirmDialog,
  FormField,
  IconCheck,
  IconEye,
  IconGift,
  IconPlus,
  IconSparkles,
  Input,
  LoadingState,
  LoyaltyCard,
  Panel,
  SectionTitle,
  StatusPill,
  Stepper,
  Textarea,
} from "@/components/ui";
import { useMerchant } from "@/components/merchant-context";
import { ApiError } from "@/lib/api";
import {
  PROGRAM_STATUS_LABELS,
  fidelity,
  type ProgramDetail,
  type Reward,
} from "@/lib/fidelity";
import { sellos } from "@/lib/ui";

const STATUS_TONE: Record<string, "neutral" | "ok" | "warn"> = {
  draft: "neutral",
  active: "ok",
  paused: "warn",
  archived: "neutral",
};

const EDITOR_STEPS = [
  { title: "Información", description: "Nombre y descripción" },
  { title: "Condiciones", description: "Texto y caducidad" },
  { title: "Recompensas", description: "Sellos necesarios" },
  { title: "Publicar", description: "Abrir el alta pública" },
];

/**
 * Editor del programa: nombre, descripción, condiciones versionadas,
 * recompensas y transiciones de estado con validación en backend. La vista
 * previa usa la misma tarjeta que verá el cliente, con datos reales.
 */
export function ProgramEditor({
  merchantId,
  programId,
}: {
  merchantId: string;
  programId: string;
}) {
  const { merchantName } = useMerchant();
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [rewardName, setRewardName] = useState("");
  const [rewardStamps, setRewardStamps] = useState(10);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [busy, setBusy] = useState(false);
  const termsRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fidelity.program(merchantId, programId);
        if (!cancelled) setProgram(data);
      } catch {
        if (!cancelled) setError("No se pudo cargar el programa.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [merchantId, programId]);

  useEffect(() => load(), [load]);

  /** Ejecuta una mutación con mensaje de éxito; devuelve el error o `null`. */
  async function run(action: () => Promise<unknown>, message: string): Promise<string | null> {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await action();
      setNotice(message);
      load();
      return null;
    } catch (err) {
      const failure = err instanceof ApiError ? err.message : "Operación no completada.";
      setError(failure);
      return failure;
    } finally {
      setBusy(false);
    }
  }

  if (!program) {
    return error ? (
      <Alert tone="danger" title="No se pudo cargar el programa">
        {error}
      </Alert>
    ) : (
      <LoadingState label="Cargando programa…" />
    );
  }

  const isActive = program.status === "active";
  const canPublish = program.status === "draft" || program.status === "paused";
  const stage = program.status === "active" ? 4 : program.rewards.length > 0 ? 3 : 1;

  function publish() {
    void (async () => {
      const failure = await run(
        () => fidelity.transition(merchantId, programId, "publish"),
        "Programa publicado",
      );
      // El backend exige condiciones visibles: si faltan, señalamos el campo.
      if (failure && failure.toLowerCase().includes("condiciones")) {
        termsRef.current?.focus();
        termsRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    })();
  }

  return (
    <div className="space-y-6">
      <Stepper steps={EDITOR_STEPS} current={Math.min(stage, EDITOR_STEPS.length)} />

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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          {/* Información y condiciones */}
          <Panel className="animate-in">
            <SectionTitle
              title="Información del programa"
              description="Se guarda automáticamente al salir de cada campo."
              action={
                <StatusPill tone={STATUS_TONE[program.status] ?? "neutral"}>
                  {PROGRAM_STATUS_LABELS[program.status]}
                </StatusPill>
              }
            />
            <div className="space-y-5">
              <SaveableField
                label="Nombre del programa"
                initialValue={program.name}
                onSave={(value) => fidelity.updateProgram(merchantId, programId, { name: value })}
                savedMessage="Nombre actualizado"
              >
                {(field) => <Input {...field} defaultValue={program.name} />}
              </SaveableField>

              <SaveableField
                label="Descripción"
                optional
                hint="Una frase que explique el programa a tus clientes."
                initialValue={program.description ?? ""}
                onSave={(value) =>
                  fidelity.updateProgram(merchantId, programId, { description: value })
                }
                savedMessage="Descripción actualizada"
              >
                {(field) => (
                  <Textarea {...field} defaultValue={program.description ?? ""} rows={2} />
                )}
              </SaveableField>

              <SaveableField
                label="Condiciones visibles"
                required
                hint={`Obligatorias para publicar. Cada cambio crea una nueva versión (ahora v${program.terms_version}) y el alta recoge la versión vigente.`}
                initialValue={program.terms ?? ""}
                onSave={(value) => fidelity.updateProgram(merchantId, programId, { terms: value })}
                savedMessage="Condiciones actualizadas (nueva versión)"
              >
                {(field) => (
                  <Textarea
                    {...field}
                    defaultValue={program.terms ?? ""}
                    rows={3}
                    ref={termsRef}
                    placeholder="1 sello por visita. Canje desde 10 sellos."
                  />
                )}
              </SaveableField>

              {/* Caducidad opcional (§7.7): sin regla por defecto. Solo
                  afecta a sellos futuros y el cliente la ve antes del alta.
                  Los puntos no caducan: en modo points no se ofrece. */}
              {program.program_type !== "points" && (
                <SaveableField
                  label="Caducidad de sellos"
                  optional
                  hint="Opcional: días hasta que caduca cada sello nuevo (1–3650). Vacío = sin caducidad. Los sellos ya acumulados no cambian. El cliente verá la condición en la página de alta y en su tarjeta."
                  initialValue={
                    program.stamps_expire_days != null ? String(program.stamps_expire_days) : ""
                  }
                  savedMessage="Caducidad actualizada"
                  onSave={(value) => {
                    const trimmed = value.trim();
                    if (trimmed === "") {
                      return fidelity.updateProgram(merchantId, programId, {
                        stamps_expire_days: null,
                      });
                    }
                    const days = Number(trimmed);
                    if (!Number.isInteger(days) || days < 1 || days > 3650) {
                      return Promise.reject(new Error("Caducidad fuera de rango (1–3650 días)"));
                    }
                    return fidelity.updateProgram(merchantId, programId, {
                      stamps_expire_days: days,
                    });
                  }}
                >
                  {(field) => (
                    <Input
                      {...field}
                      type="number"
                      min={1}
                      max={3650}
                      inputMode="numeric"
                      defaultValue={program.stamps_expire_days ?? ""}
                      placeholder="Sin caducidad"
                      className="max-w-44"
                    />
                  )}
                </SaveableField>
              )}

              {/* Regla del modo puntos (§7.6): el importe lo teclea el
                  mostrador y el backend calcula con este entero. */}
              {program.program_type === "points" && (
                <SaveableField
                  label="Puntos por euro"
                  hint="Entero entre 1 y 1000. Los puntos los calcula el backend por importe de venta, redondeando hacia abajo (§7.6). El cliente verá la regla en la página de alta."
                  initialValue={
                    program.points_per_euro != null ? String(program.points_per_euro) : ""
                  }
                  savedMessage="Regla de puntos actualizada"
                  onSave={(value) => {
                    const rate = Number(value.trim());
                    if (!Number.isInteger(rate) || rate < 1 || rate > 1000) {
                      return Promise.reject(new Error("Regla fuera de rango (1–1000)"));
                    }
                    return fidelity.updateProgram(merchantId, programId, { points_per_euro: rate });
                  }}
                >
                  {(field) => (
                    <Input
                      {...field}
                      type="number"
                      min={1}
                      max={1000}
                      step={1}
                      defaultValue={program.points_per_euro ?? ""}
                      placeholder="1"
                      className="max-w-44"
                    />
                  )}
                </SaveableField>
              )}
            </div>
          </Panel>

          {/* Recompensas */}
          <Panel className="animate-in">
            <SectionTitle
              title="Recompensas"
              description="Cada recompensa marca los sellos que el cliente necesita para canjearla."
              icon={<IconGift size={18} />}
            />
            {program.rewards.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-line-strong bg-paper px-4 py-7 text-center">
                <span className="mx-auto flex size-11 items-center justify-center rounded-xl bg-gold-soft text-gold">
                  <IconGift size={21} />
                </span>
                <p className="mt-2 text-sm font-semibold text-ink">Sin recompensas todavía</p>
                <p className="text-xs text-ink-faint">
                  Añade la primera: por ejemplo, «Café gratis» a 10 sellos.
                </p>
              </div>
            ) : (
              <ul className="mb-5 space-y-2">
                {program.rewards.map((reward: Reward) => (
                  <li
                    key={reward.id}
                    className="ticket-notch flex items-center justify-between gap-3 border border-line bg-surface-2/50 py-3 pl-4 pr-3"
                  >
                    <span className="flex min-w-0 items-center gap-2.5 text-sm font-semibold text-ink">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gold-soft text-gold">
                        <IconGift size={16} />
                      </span>
                      <span className="truncate">{reward.name}</span>
                    </span>
                    <span className="shrink-0 rounded-full bg-surface px-2.5 py-1 text-xs font-bold text-warn ring-1 ring-gold/25">
                      {sellos(reward.stamps_required)}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await fidelity.createReward(merchantId, programId, {
                    name: rewardName,
                    stamps_required: rewardStamps,
                  });
                  setRewardName("");
                  setRewardStamps(10);
                }, "Recompensa creada");
              }}
              className="space-y-3 rounded-2xl bg-paper p-4"
            >
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-ink-faint">
                Nueva recompensa
              </p>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <FormField label="Nombre" required className="min-w-0 flex-1">
                  {({ id, describedBy }) => (
                    <Input
                      id={id}
                      aria-describedby={describedBy}
                      required
                      value={rewardName}
                      onChange={(e) => setRewardName(e.target.value)}
                      placeholder="Café gratis"
                    />
                  )}
                </FormField>
                <FormField label="Sellos" required>
                  {({ id, describedBy }) => (
                    <Input
                      id={id}
                      aria-describedby={describedBy}
                      type="number"
                      min={1}
                      max={100}
                      required
                      value={rewardStamps}
                      onChange={(e) => setRewardStamps(Number(e.target.value))}
                      className="w-24"
                    />
                  )}
                </FormField>
                <Button
                  type="submit"
                  variant="secondary"
                  icon={<IconPlus size={17} />}
                  className="shrink-0"
                >
                  Añadir recompensa
                </Button>
              </div>
            </form>
          </Panel>

          {/* Publicación */}
          <Panel tone="muted" className="animate-in">
            <SectionTitle
              title="Publicación"
              description={
                canPublish
                  ? "Al publicar, el programa acepta altas nuevas en su página pública."
                  : isActive
                    ? "El programa está aceptando altas. Puedes pausarlo si necesitas frenar temporalmente."
                    : "Programa archivado: ya no acepta altas ni aparece en la página pública."
              }
            />
            {canPublish && !program.terms && (
              <div className="mb-4">
                <Alert tone="warn" title="Faltan las condiciones visibles">
                  Escribe las condiciones del programa en el campo de arriba antes de publicarlo:
                  tus clientes las aceptan al darse de alta.
                </Alert>
              </div>
            )}
            <div className="flex flex-wrap gap-2.5">
              {canPublish && (
                <Button onClick={publish} loading={busy} icon={<IconSparkles size={17} />}>
                  Publicar
                </Button>
              )}
              {isActive && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void run(
                      () => fidelity.transition(merchantId, programId, "pause"),
                      "Programa pausado",
                    )
                  }
                >
                  Pausar
                </Button>
              )}
              {program.status !== "archived" && (
                <Button variant="danger" disabled={busy} onClick={() => setConfirmArchive(true)}>
                  Archivar
                </Button>
              )}
            </div>
          </Panel>
        </div>

        {/* Vista previa real: la misma tarjeta que verá el cliente. */}
        <aside className="space-y-4 lg:sticky lg:top-6 lg:h-fit">
          <div>
            <p className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.13em] text-ink-faint">
              <IconEye size={14} />
              Vista previa para tus clientes
            </p>
            <LoyaltyCard
              merchantName={merchantName || "Tu comercio"}
              programName={program.name || "Sin nombre"}
              stamps={0}
              rewards={program.rewards}
              holderName="Así la verá el cliente"
              variant="card"
              programType={program.program_type}
            />
            <p className="mt-2 text-[11px] leading-relaxed text-ink-faint">
              El saldo empieza en 0 al darse de alta. Esta vista usa solo los datos reales del
              programa.
            </p>
          </div>

          {program.description && (
            <Panel tone="muted">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                Descripción
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ink">{program.description}</p>
            </Panel>
          )}

          {program.terms && (
            <Panel tone="muted">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                Condiciones visibles · v{program.terms_version}
              </p>
              <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-ink-soft">
                {program.terms}
              </p>
            </Panel>
          )}

          {program.stamps_expire_days != null && program.program_type !== "points" && (
            <p className="rounded-xl border border-line bg-gold-soft px-3 py-2 text-[11px] font-semibold text-warn">
              Los sellos caducan a los {program.stamps_expire_days} días de obtenerse · El cliente
              verá esta condición en el alta y en su tarjeta.
            </p>
          )}

          {program.program_type === "points" && (
            <p className="rounded-xl border border-line bg-gold-soft px-3 py-2 text-[11px] font-semibold text-warn">
              {program.points_per_euro ?? "—"} {program.points_per_euro === 1 ? "punto" : "puntos"}{" "}
              por euro gastado · el cliente verá la regla en la página de alta.
            </p>
          )}

          <p className="rounded-xl border border-line bg-surface p-3 text-[11px] leading-relaxed text-ink-faint">
            Así verá el cliente su programa en la página de alta. Las condiciones mostradas son las
            de la versión vigente.
          </p>
        </aside>
      </div>

      <ConfirmDialog
        open={confirmArchive}
        title="¿Archivar este programa?"
        message="El programa dejará de aceptar altas nuevas y no aparecerá en la página pública. Los clientes y sus sellos se conservan, y la operación queda registrada en el historial."
        confirmLabel="Archivar programa"
        busy={busy}
        onClose={() => setConfirmArchive(false)}
        onConfirm={() => {
          setConfirmArchive(false);
          void run(
            () => fidelity.transition(merchantId, programId, "archive"),
            "Programa archivado",
          );
        }}
      />
    </div>
  );
}

/**
 * Campo con guardado al salir del foco y estado visible:
 * «Guardando…» / «Guardado» / «No se pudo guardar». No envía si no ha cambiado.
 */
interface FieldRenderProps {
  id: string;
  "aria-describedby": string | undefined;
  onBlur: (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
}

function SaveableField({
  label,
  hint,
  required,
  optional,
  initialValue,
  savedMessage,
  onSave,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  optional?: boolean;
  initialValue: string;
  savedMessage: string;
  onSave: (value: string) => Promise<unknown>;
  children: (field: FieldRenderProps) => ReactNode;
}) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function handleBlur(event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const value = event.target.value;
    if (value === initialValue) return;
    setState("saving");
    setMessage(null);
    try {
      await onSave(value);
      setState("saved");
      setMessage(savedMessage);
    } catch {
      setState("error");
      setMessage("No se pudo guardar: revisa el valor e inténtalo de nuevo.");
    }
  }

  return (
    <FormField label={label} hint={hint} required={required} optional={optional}>
      {({ id, describedBy }) => (
        <div>
          {children({ id, "aria-describedby": describedBy, onBlur: handleBlur })}
          <p
            aria-live="polite"
            className={`mt-1.5 flex items-center gap-1.5 text-xs font-medium ${
              state === "error"
                ? "text-danger"
                : state === "saved"
                  ? "text-ok"
                  : state === "saving"
                    ? "text-ink-soft"
                    : "text-transparent"
            }`}
          >
            {state === "saved" && <IconCheck size={13} />}
            {state === "saving" ? "Guardando…" : (message ?? "\u00a0")}
          </p>
        </div>
      )}
    </FormField>
  );
}
