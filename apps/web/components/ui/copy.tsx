"use client";

/** Copiar al portapapeles con confirmación visible (§5.6). */
import { useEffect, useRef, useState } from "react";

import { IconCheck, IconCopy } from "@/components/ui/icons";

export function CopyButton({
  value,
  label = "Copiar",
  copiedLabel = "Copiado",
  size = "sm",
  tone = "ghost",
}: {
  value: string;
  label?: string;
  copiedLabel?: string;
  size?: "sm" | "md";
  tone?: "ghost" | "secondary";
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      aria-live="polite"
      className={`inline-flex items-center gap-1.5 rounded-lg font-semibold transition-colors ${
        size === "sm" ? "h-8 px-2.5 text-xs" : "h-10 px-3.5 text-sm"
      } ${
        copied
          ? "bg-ok-soft text-ok"
          : tone === "secondary"
            ? "border border-line-strong bg-surface text-ink hover:border-brand/50 hover:text-brand"
            : "text-brand hover:bg-brand-soft"
      }`}
    >
      {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
      {copied ? copiedLabel : label}
    </button>
  );
}
