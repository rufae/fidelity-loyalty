# ADR-0004 — Estrategia de emisor Wallet multiempresa

**Fecha:** 14/10/2026 · **Estado:** aceptado (pendiente de credenciales para producción)

## Contexto

LocalAI Fidelity es multiempresa: cada comercio quiere que su tarjeta en Apple
Wallet / Google Wallet lleve **su marca**. Apple exige un Pass Type ID por
emisor; Google organiza la emisión en clases (plantillas) y objetos por
miembro bajo un Issuer ID. Hay que decidir quién figura como emisor técnico.

## Decisión

**Emisor único de plataforma** (LocalAI Fidelity), con **una clase/plantilla por
comercio** y branding por comercio (nombre, logotipo, colores):

- Apple: un Pass Type ID de plataforma (`pass.com.localai.fidelity`) y, dentro
  del pase, los datos visibles del comercio. Si un cliente exige su propio Pass
  Type ID, se contemplará como plan con coste de configuración.
- Google: un Issuer ID de plataforma, una clase Loyalty por comercio y un
  objeto por membresía.

## Consecuencias

- El cliente ve «el negocio + el programa» en la tarjeta; el emisor técnico es
  la plataforma (así funciona hoy la mayoría de SaaS de fidelización).
- Una sola cuenta de desarrollador Apple y un solo proyecto Google Cloud: menos
  coste y menos operación.
- Riesgo: si un comercio se va, sus pases siguen firmados por la plataforma;
  se documenta en el contrato (baja = membresías revocadas y pases invalidados
  según las posibilidades de cada proveedor).
- La marca visible del comercio exige validar logotipos (tipo/tamaño) y nunca
  renderizar SVG arbitrario sin sanitizar.

## Alternativas descartadas

- **Issuer/certificado por comercio**: mejor propiedad percibida, pero implica
  cuenta de desarrollador Apple por comercio (coste, verificación, rotación de
  certificados) y onboarding inviable para un piloto.
