import { LinkButton } from "@/components/ui/primitives";

/**
 * 404 propia de la plataforma: misma calidez, cero detalles técnicos. Los
 * enlaces de tarjetas y etiquetas NFC nunca deben ser válidos: el fallo
 * habitual es un QR antiguo o mal escrito.
 */
export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16 text-center">
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-brand">
        Página no encontrada
      </p>
      <h1 className="mt-2 text-[34px] font-bold leading-tight tracking-[-0.02em] text-ink">
        Esta página no existe
      </h1>
      <p className="mt-2.5 text-sm leading-relaxed text-ink-soft">
        El enlace no corresponde a ninguna página. Si venías de una tarjeta o de una etiqueta del
        establecimiento, pide el enlace en el propio comercio o vuelve a escanearlo.
      </p>
      <div className="mt-6 flex justify-center">
        <LinkButton href="/" variant="secondary">
          Volver a la portada
        </LinkButton>
      </div>
    </main>
  );
}
