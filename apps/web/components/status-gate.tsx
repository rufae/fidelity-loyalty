"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { StatusView } from "@/components/status-view";
import { BrandLogo, LoadingState } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { isPlatformAdmin, type SessionPayload } from "@/lib/session";

/**
 * Puerta del diagnóstico técnico (§13.1): `/estado` solo la ve la
 * administración de la plataforma. Sin sesión se envía al acceso; con sesión
 * de comercio se vuelve a la portada (los comercios tienen sus indicadores en
 * el panel, no el estado interno de la infraestructura).
 */
export function StatusGate() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void apiFetch<SessionPayload>("/api/v1/auth/me")
      .then((payload) => {
        if (cancelled) return;
        if (isPlatformAdmin(payload.user)) {
          setAllowed(true);
        } else {
          router.replace("/");
        }
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!allowed) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-5">
        <BrandLogo />
        <LoadingState label="Comprobando acceso de operador…" />
      </main>
    );
  }
  return <StatusView />;
}
