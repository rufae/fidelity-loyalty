"""Envío de correos transaccionales, sin registrar enlaces ni tokens.

Seguridad (§16.2): la credencial SMTP y los enlaces de un solo uso viajan
**solo cifrados**. En producción se exige TLS verificado (`SSL` o `STARTTLS`
con contexto que valida el certificado del servidor); un SMTP en claro se
rechaza aunque la configuración lo permita (defensa en profundidad frente a
un `.env` mal puesto).

Plantilla (§13.6 para correo): HTML sobrio con la identidad de la plataforma
(tarjeta blanca sobre fondo claro, cabecera navy, botón violeta), estilos
**inline** y maquetación por tablas para que se vea igual en Gmail, Outlook,
Apple Mail y clientes móviles; el texto plano lleva el mismo contenido y el
enlace completo para clientes sin HTML ni con imágenes desactivadas.
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from app.core.config import Settings
from app.domain.errors import DomainError

_TLS_MSG = "El envío de correo no está configurado. Contacta con el establecimiento."

#: Sin fuentes web (ninguna petición externa desde el correo); apila a las del sistema.
_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
#: Tokens de `globals.css`: brand #6c5ce7, navy #1a135c, surface-2 #f0f3fa.
_NAVY = "#1a135c"
_BRAND = "#6c5ce7"
_BG = "#f0f3fa"
_INK = "#172033"
_INK_SOFT = "#586174"
_INK_FAINT = "#778197"
_LINE = "#eceff7"
#: Quien cede la plataforma: el comercio manda; la plataforma firma el pie.
_PLATFORM = "LocalAI Fidelity"


def ensure_email_configured(settings: Settings) -> None:
    if not settings.email_from or not settings.email_smtp_host:
        raise DomainError(503, "email_delivery_not_configured", _TLS_MSG)


def _render_html(
    merchant_name: str,
    subject: str,
    text: str,
    action_url: str,
    cta_label: str,
    subtitle: str = "Tu programa de fidelización",
) -> str:
    """HTML de un solo bloque, sin recursos externos (los clientes lo bloquean)."""
    url = escape(action_url, quote=True)
    visible_url = escape(action_url)
    subject_h = escape(subject)
    text_h = escape(text)
    cta_h = escape(cta_label)
    merchant_h = escape(merchant_name) if merchant_name else escape(_PLATFORM)
    subtitle_h = escape(subtitle)
    preheader = escape(f"{subject} · {text[:90]}")
    font = _FONT  # atajo para no repetir la pila en cada regla

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{subject_h}</title>
<style>
  @media only screen and (max-width: 620px) {{
    .card {{ width: 100% !important; }}
    .pad {{ padding-left: 20px !important; padding-right: 20px !important; }}
    h1 {{ font-size: 21px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:{_BG};font-family:{font};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{_BG};font-family:{font};">
<tr>
<td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="card" style="width:100%;max-width:600px;background-color:#ffffff;border:1px solid {_LINE};border-radius:16px;overflow:hidden;">
  <tr>
    <td style="background-color:{_NAVY};padding:20px 32px;">
      <span style="font-family:{font};font-size:18px;font-weight:700;color:#ffffff;letter-spacing:0.01em;">{merchant_h}</span>
      <span style="display:block;margin-top:2px;font-family:{font};font-size:12px;font-weight:500;color:#b3acff;">{subtitle_h}</span>
    </td>
  </tr>
  <tr>
    <td style="height:5px;background-color:{_BRAND};font-size:0;line-height:0;">&nbsp;</td>
  </tr>
  <tr>
    <td class="pad" style="padding:32px 32px 10px;">
      <h1 style="margin:0 0 14px;font-family:{font};font-size:23px;line-height:1.3;font-weight:700;color:{_INK};">{subject_h}</h1>
      <p style="margin:0 0 26px;font-family:{font};font-size:15px;line-height:1.65;color:{_INK_SOFT};">{text_h}</p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td align="center" style="background-color:{_BRAND};border-radius:10px;">
          <a href="{url}" style="display:inline-block;padding:14px 30px;font-family:{font};font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px;">{cta_h}</a>
        </td>
      </tr>
      </table>
      <p style="margin:24px 0 0;font-family:{font};font-size:13px;line-height:1.65;color:{_INK_FAINT};">Si el botón no funciona, copia este enlace en tu navegador:<br>
      <a href="{url}" style="color:{_BRAND};text-decoration:underline;word-break:break-all;">{visible_url}</a></p>
    </td>
  </tr>
  <tr>
    <td class="pad" style="padding:22px 32px 30px;">
      <p style="margin:0;padding-top:18px;border-top:1px solid {_LINE};font-family:{font};font-size:12px;line-height:1.65;color:{_INK_FAINT};">Este enlace es personal, caduca y solo puede usarse una vez. Si no has solicitado este mensaje, ignóralo: no se ha realizado ningún cambio en tu cuenta.</p>
      <p style="margin:10px 0 0;font-family:{font};font-size:12px;color:{_INK_FAINT};">Programa cedido por <span style="font-weight:700;color:{_INK_SOFT};">{_PLATFORM}</span> · fidelización digital para comercios locales</p>
    </td>
  </tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""


def _render_text(merchant_name: str, subject: str, text: str, action_url: str) -> str:
    brand = f"{merchant_name}\n\n" if merchant_name else ""
    return (
        f"{brand}{subject}\n\n{text}\n\n"
        f"Continúa aquí:\n{action_url}\n\n"
        f"Programa cedido por {_PLATFORM}.\n"
        "Si no lo has solicitado, ignora este mensaje."
    )


def _deliver_message(settings: Settings, message: EmailMessage) -> None:
    """Entrega un mensaje ya construido por SMTP con TLS verificado."""
    ensure_email_configured(settings)
    assert settings.email_from is not None and settings.email_smtp_host is not None

    # Fail-closed: jamás credenciales ni mensajes en claro en producción, aunque
    # `EMAIL_SMTP_STARTTLS=false` hubiera colado en la configuración.
    if settings.is_production and not (settings.email_smtp_ssl or settings.email_smtp_starttls):
        raise DomainError(503, "email_delivery_not_configured", _TLS_MSG)

    try:
        if settings.email_smtp_ssl:
            with smtplib.SMTP_SSL(
                settings.email_smtp_host,
                settings.email_smtp_port,
                timeout=settings.email_smtp_timeout_seconds,
                context=ssl.create_default_context(),
            ) as smtp:
                _smtp_deliver(smtp, settings, message)
        else:
            with smtplib.SMTP(
                settings.email_smtp_host,
                settings.email_smtp_port,
                timeout=settings.email_smtp_timeout_seconds,
            ) as smtp:
                if settings.email_smtp_starttls:
                    # Contexto por defecto: valida el certificado del servidor
                    # (sin él, STARTTLS no autentica a nadie y admite MITM).
                    smtp.starttls(context=ssl.create_default_context())
                _smtp_deliver(smtp, settings, message)
    except (OSError, smtplib.SMTPException) as exc:
        raise DomainError(
            503,
            "email_delivery_failed",
            "No se pudo enviar el correo ahora. Inténtalo de nuevo más tarde.",
        ) from exc


def send_email(
    settings: Settings,
    recipient: str,
    subject: str,
    text: str,
    action_url: str,
    cta_label: str = "Abrir mi tarjeta",
    merchant_name: str = "",
) -> None:
    """Envía correo por SMTP con TLS verificado; falla explícitamente si no corresponde.

    El mensaje va en nombre del comercio (`merchant_name` en cabecera y en el
    «De» visible); la plataforma firma el pie. La dirección `From` no cambia:
    sigue siendo la configurada, que es la que autentican SPF/DKIM/DMARC.
    """
    ensure_email_configured(settings)
    assert settings.email_from is not None and settings.email_smtp_host is not None
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        formataddr((merchant_name, settings.email_from)) if merchant_name else settings.email_from
    )
    message["To"] = recipient
    message.set_content(_render_text(merchant_name, subject, text, action_url))
    message.add_alternative(
        _render_html(merchant_name, subject, text, action_url, cta_label),
        subtype="html",
    )
    _deliver_message(settings, message)


def _render_support_text(subject: str, text: str, action_url: str) -> str:
    return (
        f"Soporte LocalAI Fidelity\n\n{subject}\n\n{text}\n\n"
        f"Abrir el buzón de soporte:\n{action_url}\n\n"
        "Este es un aviso automático del servicio de soporte. "
        "Responde desde el panel para mantener la conversación."
    )


def send_support_email(
    settings: Settings,
    recipient: str,
    subject: str,
    text: str,
    action_url: str,
) -> None:
    """Correo del soporte con identidad genérica, nunca datos personales.

    Usa `SUPPORT_FROM_EMAIL` si existe; si no, `EMAIL_FROM`. El nombre visible
    es siempre «Soporte LocalAI Fidelity»: el comercio no debe conocer al
    propietario ni su correo personal (Plan.md §12.6).
    """
    sender = settings.support_from_email or settings.email_from
    delivery = settings.model_copy(update={"email_from": sender})
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("Soporte LocalAI Fidelity", sender or ""))
    message["To"] = recipient
    message.set_content(_render_support_text(subject, text, action_url))
    message.add_alternative(
        _render_html(
            "Soporte LocalAI Fidelity",
            subject,
            text,
            action_url,
            "Abrir el buzón",
            subtitle="Atención al cliente",
        ),
        subtype="html",
    )
    _deliver_message(delivery, message)


def _smtp_deliver(smtp: smtplib.SMTP, settings: Settings, message: EmailMessage) -> None:
    if settings.email_smtp_username:
        smtp.login(settings.email_smtp_username, settings.email_smtp_password or "")
    smtp.send_message(message)
