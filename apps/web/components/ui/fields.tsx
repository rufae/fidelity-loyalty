/** Campos de formulario compartidos: etiquetas visibles y errores cercanos. */
import { useId, type ReactNode } from "react";

const FIELD_CLASSES =
  "w-full rounded-xl border border-line-strong bg-surface px-3.5 text-[15px] text-ink shadow-[inset_0_1px_2px_rgb(62_47_30/0.04)] transition-[border-color,box-shadow] placeholder:text-ink-faint hover:border-ink-faint/60 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-faint aria-[invalid=true]:border-danger aria-[invalid=true]:ring-danger/10";

export function FormField({
  label,
  hint,
  error,
  required,
  optional,
  children,
  className = "",
}: {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  optional?: boolean;
  children: (props: { id: string; describedBy: string | undefined }) => ReactNode;
  className?: string;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`space-y-1.5 ${className}`}>
      <label htmlFor={id} className="flex items-baseline gap-2 text-sm font-semibold text-ink">
        {label}
        {optional && <span className="text-xs font-normal text-ink-faint">(opcional)</span>}
        {required && <span className="text-xs font-normal text-danger">*</span>}
      </label>
      {hint && (
        <p id={hintId} className="text-xs leading-relaxed text-ink-faint">
          {hint}
        </p>
      )}
      {children({ id, describedBy })}
      {error && (
        <p id={errorId} role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function Input({ className = "", ...props }: React.ComponentProps<"input">) {
  return <input {...props} className={`${FIELD_CLASSES} h-11 ${className}`} />;
}

export function Textarea({ className = "", ...props }: React.ComponentProps<"textarea">) {
  return <textarea {...props} className={`${FIELD_CLASSES} min-h-24 py-3 ${className}`} />;
}

export function Select({ className = "", ...props }: React.ComponentProps<"select">) {
  return <select {...props} className={`${FIELD_CLASSES} h-11 ${className}`} />;
}

export function Checkbox({
  label,
  description,
  ...props
}: { label: ReactNode; description?: ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-surface p-3.5 transition-colors hover:border-brand/40 has-[:checked]:border-brand/50 has-[:checked]:bg-brand-soft/40"
    >
      <input
        {...props}
        id={id}
        type="checkbox"
        className="mt-0.5 size-[18px] shrink-0 cursor-pointer rounded-[5px] border-line-strong accent-[#5b48d6]"
      />
      <span className="text-sm leading-snug text-ink">
        {label}
        {description && <span className="mt-0.5 block text-xs text-ink-faint">{description}</span>}
      </span>
    </label>
  );
}
