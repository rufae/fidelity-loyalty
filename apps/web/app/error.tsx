"use client";

import { useEffect } from "react";

import { Button, IconAlert } from "@/components/ui";

/**
 * Límite de error de la aplicación: cualquier fallo inesperado de renderizado
 * de cliente cae aquí, en el mundo cálido y en castellano, nunca en la
 * pantalla genérica de Next. No expone stack, código ni detalles técnicos.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // El detalle técnico va al log de consola (diagnóstico), no a la interfaz.
  useEffect(() => {
    console.error("Error de interfaz:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16 text-center">
      <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-warn-soft text-warn">
        <IconAlert size={30} />
      </div>
      <h1 className="mt-4 text-2xl font-bold tracking-tight text-ink">Algo ha ido mal</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        No se pudo terminar de cargar esta pantalla. Tus datos están guardados en el servidor:
        prueba de nuevo y, si vuelve a ocurrir, recarga la página.
      </p>
      <div className="mt-6 flex justify-center">
        <Button size="lg" onClick={reset}>
          Probar de nuevo
        </Button>
      </div>
    </main>
  );
}
