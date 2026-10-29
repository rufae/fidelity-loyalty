"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  Alert,
  Button,
  Checkbox,
  FormField,
  IconArrowLeft,
  IconInfo,
  IconMail,
  Input,
  LinkButton,
  Panel,
  SectionTitle,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  newIdempotencyKey,
  support,
  SUPPORT_CATEGORY_LABELS,
  SUPPORT_CONTACT_LABELS,
  type CreateSupportThreadInput,
  type SupportCategory,
  type SupportContactPreference,
} from "@/lib/support";

/**
 * Nueva conversación de soporte: mensaje claro, categoría y, si se pide
 * llamada, teléfono con consentimiento explícito (Plan.md §12.3).
 */
export function SupportThreadFormView({ merchantId }: { merchantId: string }) {
  const router = useRouter();
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<SupportCategory>("technical");
  const [body, setBody] = useState("");
  const [contact, setContact] = useState<SupportContactPreference>("in_app");
  const [phone, setPhone] = useState("");
  const [availability, setAvailability] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const wantsCall = contact === "phone";

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const payload: CreateSupportThreadInput = {
        subject: subject.trim(),
        category,
        body: body.trim(),
        preferred_contact: contact,
        ...(wantsCall
          ? {
              callback_phone: phone.trim(),
              callback_availability: availability.trim() || undefined,
              callback_consent: consent,
            }
          : {}),
      };
      const thread = await support.createThread(
        merchantId,
        payload,
        newIdempotencyKey(),
      );
      router.push(`/merchants/${merchantId}/support/${thread.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo abrir la conversación.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <Link
          href={`/merchants/${merchantId}/support`}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-brand"
        >
          <IconArrowLeft size={16} />
          Volver a soporte
        </Link>
      </div>

      <Panel className="animate-in">
        <SectionTitle
          title="Nueva conversación"
          description="Cuéntanos brevemente qué necesitas. Responderemos desde el panel de soporte."
          icon={<IconMail size={18} />}
        />

        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Asunto" required hint="Una frase corta que resuma el problema">
            {({ id, describedBy }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                required
                minLength={3}
                maxLength={120}
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                placeholder="Ej.: No puedo imprimir los tiques"
              />
            )}
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Categoría" required>
              {({ id, describedBy }) => (
                <Select
                  id={id}
                  aria-describedby={describedBy}
                  value={category}
                  onChange={(event) => setCategory(event.target.value as SupportCategory)}
                >
                  {(Object.keys(SUPPORT_CATEGORY_LABELS) as SupportCategory[]).map((value) => (
                    <option key={value} value={value}>
                      {SUPPORT_CATEGORY_LABELS[value]}
                    </option>
                  ))}
                </Select>
              )}
            </FormField>

            <FormField label="¿Cómo prefieres que te contactemos?" required>
              {({ id, describedBy }) => (
                <Select
                  id={id}
                  aria-describedby={describedBy}
                  value={contact}
                  onChange={(event) =>
                    setContact(event.target.value as SupportContactPreference)
                  }
                >
                  {(Object.keys(SUPPORT_CONTACT_LABELS) as SupportContactPreference[]).map(
                    (value) => (
                      <option key={value} value={value}>
                        {SUPPORT_CONTACT_LABELS[value]}
                      </option>
                    ),
                  )}
                </Select>
              )}
            </FormField>
          </div>

          <FormField label="Mensaje" required hint="No incluyas contraseñas ni datos de tarjetas">
            {({ id, describedBy }) => (
              <Textarea
                id={id}
                aria-describedby={describedBy}
                required
                minLength={1}
                maxLength={4000}
                value={body}
                onChange={(event) => setBody(event.target.value)}
                placeholder="Describe qué ha pasado, cuándo empezó y qué has intentado."
              />
            )}
          </FormField>

          {wantsCall && (
            <div className="space-y-4 rounded-2xl border border-brand/25 bg-brand-soft/40 p-4">
              <p className="text-sm font-semibold text-ink">Solicitud de llamada</p>
              <p className="text-xs leading-relaxed text-ink-soft">
                La llamada la realiza el equipo de soporte de forma privada. La app no inicia
                llamadas ni guarda grabaciones.
              </p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Teléfono" required hint="Solo se usará para esta solicitud">
                  {({ id, describedBy }) => (
                    <Input
                      id={id}
                      aria-describedby={describedBy}
                      required
                      type="tel"
                      minLength={6}
                      maxLength={32}
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      placeholder="+34 600 000 000"
                    />
                  )}
                </FormField>
                <FormField label="Disponibilidad" optional hint="Ej.: tardes de 16:00 a 18:00">
                  {({ id, describedBy }) => (
                    <Input
                      id={id}
                      aria-describedby={describedBy}
                      maxLength={160}
                      value={availability}
                      onChange={(event) => setAvailability(event.target.value)}
                      placeholder="Cuándo te viene bien"
                    />
                  )}
                </FormField>
              </div>
              <Checkbox
                label="Acepto que me llamen a este número para atender esta solicitud."
                description="El número se guarda cifrado y solo lo ve el equipo de soporte."
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
              />
            </div>
          )}

          {error && (
            <Alert tone="danger" title="No se pudo abrir la conversación">
              {error}
            </Alert>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" loading={busy}>
              Enviar a soporte
            </Button>
            <LinkButton
              href={`/merchants/${merchantId}/support`}
              variant="secondary"
            >
              Cancelar
            </LinkButton>
          </div>
        </form>
      </Panel>

      <div className="flex items-start gap-3 rounded-2xl border border-line bg-paper p-4 text-sm text-ink-soft">
        <IconInfo size={18} className="mt-0.5 shrink-0 text-brand" />
        <p>
          Este soporte es para el comercio. Si un cliente tiene una duda de su tarjeta, atiéndelo
          desde la sección de clientes o desde tu programa.
        </p>
      </div>
    </div>
  );
}
