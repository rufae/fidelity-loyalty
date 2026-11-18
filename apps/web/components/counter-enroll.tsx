"use client";

/**
 * Alta en mostrador (§13.5): el personal crea la tarjeta en el local con
 * datos mínimos y el cliente se va con ella funcionando.
 *
 * - Email **opcional** (minimización §9.3): sin correo la tarjeta se
 *   recupera por su enlace/código; con correo queda sin verificar y solo
 *   sirve para identificar al cliente.
 * - El consentimiento de condiciones y aviso de privacidad lo marca el
 *   personal **delante del cliente**; las versiones las fija el backend.
 * - La tarjeta nace activa: si el cliente ya tenía una en ese programa, la
 *   API devuelve la suya en lugar de duplicar (idempotencia de mostrador).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Checkbox,
  CopyButton,
  IconCheck,
  IconPlus,
  Input,
  LinkButton,
  Panel,
  SectionTitle,
  Select,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fidelity, type ManualEnrollResult, type Membership, type Program } from "@/lib/fidelity";

export function CounterEnroll({
  merchantId,
  preferredProgramId,
  onUseCard,
  focusSignal = 0,
}: {
  merchantId: string;
  /** Programa de la etiqueta de mostrador (?program=), si hay. */
  preferredProgramId: string | null;
  onUseCard?: (membership: Membership) => void;
  /** Al incrementarse (atajo «N»): trae el panel a la vista y enfoca el nombre. */
  focusSignal?: number;
}) {
  const [programs, setPrograms] = useState<Program[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [programId, setProgramId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ManualEnrollResult | null>(null);

  const nameRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(() => {
    let cancelled = false;
    void fidelity
      .programs(merchantId)
      .then((rows) => {
        if (cancelled) return;
        const active = rows.filter((program) => program.status === "active");
        setPrograms(active);
        setLoadError(null);
        const preferred = preferredProgramId
          ? active.find((program) => program.id === preferredProgramId)
          : undefined;
        if (preferred) setProgramId(preferred.id);
        else if (active.length === 1) setProgramId(active[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setLoadError("No se pudieron cargar los programas activos.");
      });
    return () => {
      cancelled = true;
    };
  }, [merchantId, preferredProgramId]);

  useEffect(() => load(), [load]);

  // Atajo «N» (escritorio): el panel viene a la vista y el foco va al nombre,
  // listo para teclear el primer cliente. Tras el alta, «otro cliente» ya
  // enfoca por sí solo (reset).
  useEffect(() => {
    if (focusSignal === 0) return;
    if (result) reset();
    requestAnimationFrame(() => {
      nameRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
      nameRef.current?.focus();
    });
  }, [focusSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const selected = programs?.find((program) => program.id === programId) ?? null;

  function reset() {
    setResult(null);
    setName("");
    setEmail("");
    setAccepted(false);
    setError(null);
    // Listo para el siguiente cliente: el foco vuelve al nombre.
    requestAnimationFrame(() => nameRef.current?.focus());
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const data = await fidelity.manualEnroll(merchantId, {
        program_id: selected.id,
        display_name: name.trim(),
        email: email.trim() || undefined,
        accepted_terms_version: selected.terms_version,
        privacy_notice_version: selected.privacy_notice_version ?? 1,
      });
      setResult(data);
      setName("");
      setEmail("");
      setAccepted(false);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo completar el alta. Inténtalo de nuevo.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <Alert tone="warn" title="Alta en mostrador no disponible">
        {loadError}
      </Alert>
    );
  }
  if (!programs) return null;
  if (programs.length === 0) {
    return (
      <Panel className="animate-in">
        <SectionTitle
          title="Alta en mostrador"
          description="Cuando tengas un programa activo podrás dar de alta a tus clientes aquí mismo, sin QR ni correo."
          icon={<IconPlus size={18} />}
        />
      </Panel>
    );
  }

  return (
    <Panel className="animate-in">
      <SectionTitle
        title="Dar de alta a un cliente nuevo"
        description="Nombre y, si quiere, su correo. La tarjeta queda activa al instante y puede empezar a sumar hoy."
        icon={<IconPlus size={18} />}
      />

      {result ? (
        <div className="animate-pop space-y-3" role="status">
          <div className="flex items-start gap-3 rounded-2xl border-2 border-ok/25 bg-ok-soft p-4">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-ok text-white">
              <IconCheck size={20} />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ok">
                {result.created ? "Tarjeta creada y activa" : "Este cliente ya tenía tarjeta"}
              </p>
              <p className="mt-0.5 text-[15px] font-bold leading-snug text-ink">
                {result.created
                  ? `La tarjeta de ${result.membership.member_name ?? "tu cliente"} ya funciona en «${result.membership.program_name ?? "el programa"}».`
                  : `Esta es su tarjeta de «${result.membership.program_name ?? "el programa"}».`}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-paper p-4">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              Código de la tarjeta
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <code className="tnum min-w-0 flex-1 truncate rounded-lg border border-line bg-surface px-3 py-2 font-mono text-[12px] text-ink">
                {result.membership.public_token}
              </code>
              <CopyButton value={result.membership.public_token} label="Copiar código" />
              <LinkButton
                href={`/card/${result.membership.public_token}`}
                variant="secondary"
                external
              >
                Abrir la tarjeta
              </LinkButton>
            </div>
            <p className="mt-2.5 text-xs leading-relaxed text-ink-faint">
              {result.membership.member_email
                ? "El correo queda registrado sin verificar: la tarjeta se usa con su enlace o código. Para sumar sellos hoy, no hace falta esperar a ningún correo."
                : "Sin correo registrado: la tarjeta se recupera con este enlace o código, que solo muestra el establecimiento."}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {onUseCard && (
              <Button
                variant="secondary"
                onClick={() => {
                  const card = result.membership;
                  reset();
                  onUseCard(card);
                }}
              >
                Añadir el primer sello ahora
              </Button>
            )}
            <Button variant="secondary" onClick={reset}>
              Dar de alta a otro cliente
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3.5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="enroll-program" className="text-sm font-semibold text-ink">
                Programa
              </label>
              <Select
                id="enroll-program"
                value={programId}
                onChange={(e) => setProgramId(e.target.value)}
                required
              >
                <option value="" disabled>
                  Elige el programa…
                </option>
                {programs.map((program) => (
                  <option key={program.id} value={program.id}>
                    {program.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="enroll-name" className="text-sm font-semibold text-ink">
                Nombre del cliente
              </label>
              <Input
                id="enroll-name"
                ref={nameRef}
                required
                minLength={2}
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ana García"
                autoComplete="off"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="enroll-email" className="text-sm font-semibold text-ink">
              Correo <span className="font-normal text-ink-faint">(opcional)</span>
            </label>
            <Input
              id="enroll-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ana@ejemplo.com — solo si el cliente quiere recuperarla por correo"
              autoComplete="off"
            />
          </div>

          <Checkbox
            required
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            label="El cliente acepta las condiciones y el aviso de privacidad del programa."
            description={
              selected
                ? `Condiciones v${selected.terms_version} · aviso de privacidad v${selected.privacy_notice_version ?? 1} · aceptados en el mostrador, delante del personal.`
                : undefined
            }
          />

          {error && <Alert tone="danger">{error}</Alert>}

          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" size="lg" loading={busy} disabled={!programId || !accepted}>
              Crear tarjeta activa
            </Button>
            <Badge tone="neutral">Alta registrada en la auditoría</Badge>
          </div>
        </form>
      )}
    </Panel>
  );
}
