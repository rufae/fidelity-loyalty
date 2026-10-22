"use client";

/**
 * Escáner QR con la cámara del móvil para el mostrador (tasks2 §8).
 *
 * - El permiso de cámara se pide **solo** al pulsar el botón (§8.3).
 * - La decodificación ocurre en el navegador: `BarcodeDetector` cuando existe
 *   y ZXing (MIT) como respaldo (iOS Safari no expone BarcodeDetector).
 * - No se suben imágenes ni vídeo a ningún servidor (§8.3).
 * - La cámara se detiene al cerrar, al escanear y al desmontar.
 * - El campo manual sigue siendo el mecanismo fiable de respaldo.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { Button, IconClose, IconScan, Modal } from "@/components/ui";

type Detector = {
  detect(video: HTMLVideoElement): Promise<Array<{ rawValue: string }>>;
};
type DetectorCtor = new (options: { formats: string[] }) => Detector;

type ScanState =
  | "closed"
  | "requesting"
  | "scanning"
  | "denied"
  | "insecure"
  | "unsupported"
  | "error";

const MESSAGES: Record<Exclude<ScanState, "closed">, string> = {
  requesting: "Pide permiso de cámara… concédelo para escanear el QR de la tarjeta.",
  scanning: "Apunta al QR de la tarjeta del cliente. La lectura es automática.",
  denied:
    "Sin permiso de cámara. Toca el candado (o el icono del sitio) de la barra de direcciones, permite la cámara y vuelve a intentarlo.",
  insecure:
    "Este navegador no permite la cámara en esta página: debe abrirse por HTTPS.",
  unsupported: "Este navegador no permite escanear con la cámara. Escribe o pega el código a mano.",
  error: "No se pudo usar la cámara (¿está ocupada por otra aplicación?). Usa el código manual.",
};

export function QrScanner({ onScan }: { onScan: (text: string) => void }) {
  const [state, setState] = useState<ScanState>("closed");
  const videoRef = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<(() => void) | null>(null);
  const lastValueRef = useRef<{ value: string; at: number }>({ value: "", at: 0 });

  const stop = useCallback(() => {
    stopRef.current?.();
    stopRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setState("closed");
  }, []);

  useEffect(() => () => stopRef.current?.(), []);

  const handleValue = useCallback(
    (value: string) => {
      const now = Date.now();
      // Evita reprocesar el mismo QR en cada frame (§8.3).
      if (lastValueRef.current.value === value && now - lastValueRef.current.at < 3000) return;
      lastValueRef.current = { value, at: now };
      stop();
      onScan(value);
    },
    [onScan, stop],
  );

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) {
      // Sin contexto seguro (HTTPS) o sin API de cámara no hay nada que pedir.
      setState("insecure");
      return;
    }
    setState("requesting");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
      });
    } catch (error) {
      const name = (error as { name?: string }).name;
      setState(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "error");
      return;
    }

    const video = videoRef.current;
    if (!video) {
      stream.getTracks().forEach((track) => track.stop());
      setState("error");
      return;
    }
    video.srcObject = stream;
    // La reproducción no debe bloquear el estado: algunos navegadores dejan
    // `play()` pendiente con streams sin pistas reales.
    void video.play().catch(() => undefined);
    setState("scanning");

    const detectorCtor = (
      window as unknown as { BarcodeDetector?: DetectorCtor }
    ).BarcodeDetector;
    if (detectorCtor) {
      const detector = new detectorCtor({ formats: ["qr_code"] });
      const timer = window.setInterval(() => {
        void detector
          .detect(video)
          .then((codes) => {
            const value = codes[0]?.rawValue;
            if (value) handleValue(value);
          })
          .catch(() => undefined);
      }, 300);
      stopRef.current = () => {
        window.clearInterval(timer);
        stream.getTracks().forEach((track) => track.stop());
      };
      return;
    }

    // Respaldo con ZXing (licencia MIT) para navegadores sin BarcodeDetector.
    try {
      const { BrowserQRCodeReader } = await import("@zxing/browser");
      const reader = new BrowserQRCodeReader();
      const controls = await reader.decodeFromStream(stream, video, (result) => {
        if (result) handleValue(result.getText());
      });
      stopRef.current = () => {
        controls.stop();
        stream.getTracks().forEach((track) => track.stop());
      };
    } catch {
      stream.getTracks().forEach((track) => track.stop());
      setState("unsupported");
    }
  }

  return (
    <>
      <Button variant="secondary" size="lg" icon={<IconScan size={18} />} onClick={() => void start()}>
        Escanear QR
      </Button>

      <Modal
        open={state !== "closed"}
        onClose={stop}
        title="Escanear la tarjeta del cliente"
        footer={
          <>
            {(state === "denied" || state === "error") && (
              <Button
                variant="primary"
                onClick={() => void start()}
                icon={<IconScan size={16} />}
              >
                Reintentar cámara
              </Button>
            )}
            <Button variant="secondary" onClick={stop} icon={<IconClose size={16} />}>
              Usar el código manual
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <video
            ref={videoRef}
            playsInline
            muted
            className={`w-full rounded-2xl bg-nav ${state === "scanning" ? "block" : "hidden"}`}
          />
          <p
            className={`text-sm ${
              state === "denied" ||
              state === "error" ||
              state === "unsupported" ||
              state === "insecure"
                ? "font-semibold text-danger"
                : "text-ink-soft"
            }`}
            aria-live="polite"
          >
            {state === "closed" ? "" : MESSAGES[state]}
          </p>
        </div>
      </Modal>
    </>
  );
}
