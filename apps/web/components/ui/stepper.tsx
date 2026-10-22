/**
 * Pasos de una configuración guiada (programa, reseñas, alta). No es un
 * adorno: marca dónde está el comercio y qué falta, con texto además de color.
 */
import { IconCheck } from "@/components/ui/icons";

export interface Step {
  title: string;
  description?: string;
}

export function Stepper({
  steps,
  current,
  className = "",
}: {
  steps: Step[];
  /** Índice 0-based del paso actual; los anteriores se muestran completados. */
  current: number;
  className?: string;
}) {
  return (
    <ol
      className={`grid gap-3 ${steps.length > 3 ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-3"} ${className}`}
      aria-label="Pasos de configuración"
    >
      {steps.map((step, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li
            key={step.title}
            aria-current={active ? "step" : undefined}
            className={`relative flex items-start gap-3 rounded-xl border p-3 transition-colors ${
              active
                ? "border-brand/30 bg-brand-soft"
                : done
                  ? "border-ok/20 bg-ok-soft/60"
                  : "border-line bg-paper"
            }`}
          >
            <span
              aria-hidden="true"
              className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ring-1 ring-inset ${
                done
                  ? "bg-ok text-white ring-ok"
                  : active
                    ? "bg-brand text-white ring-brand"
                    : "bg-surface text-ink-faint ring-line-strong"
              }`}
            >
              {done ? <IconCheck size={15} /> : index + 1}
            </span>
            <div className="min-w-0">
              <p
                className={`text-[13px] font-semibold leading-snug ${
                  active ? "text-brand" : done ? "text-ok" : "text-ink"
                }`}
              >
                {step.title}
              </p>
              {step.description && (
                <p className="mt-0.5 text-[11px] leading-snug text-ink-faint">{step.description}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
