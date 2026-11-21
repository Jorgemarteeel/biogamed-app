"""Deliver private activation links without persisting or logging their secrets."""
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import urlsplit
from uuid import UUID


@dataclass(frozen=True)
class Invitation:
    user_id: UUID
    email: str
    code: str
    digest: str


def send_invitations(invitations: list[Invitation], ttl_hours: int) -> set[UUID]:
    """Return recipients accepted by SMTP. Unsent accounts remain pending."""
    if not invitations:
        return set()
    sent = set()
    origin = os.getenv("BIOGAMED_PUBLIC_URL", "").rstrip("/")
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return sent
    host = os.getenv("BIOGAMED_SMTP_HOST")
    sender = os.getenv("BIOGAMED_SMTP_FROM")
    username = os.getenv("BIOGAMED_SMTP_USERNAME")
    password = os.getenv("BIOGAMED_SMTP_PASSWORD")
    security = os.getenv("BIOGAMED_SMTP_SECURITY", "starttls")
    http_local = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not (http_local or parsed.scheme == "https")
        or not parsed.hostname or parsed.username or parsed.query or parsed.fragment
        or not host or not sender or security not in {"starttls", "ssl", "none"}
        or bool(username) != bool(password) or (username and security == "none")
    ):
        return sent

    context = ssl.create_default_context()
    try:
        port = int(os.getenv("BIOGAMED_SMTP_PORT", "465" if security == "ssl" else "587"))
        connection = (smtplib.SMTP_SSL(host, port, timeout=5, context=context)
                      if security == "ssl" else smtplib.SMTP(host, port, timeout=5))
        with connection as smtp:
            if security == "starttls":
                smtp.starttls(context=context)
            if username:
                smtp.login(username, password)
            for invitation in invitations:
                mail = EmailMessage()
                mail["From"] = sender
                mail["To"] = invitation.email
                mail["Subject"] = "Activa tu cuenta de BioGaMed"
                mail.set_content(
                    f"Elige tu contraseña de BioGaMed en las próximas {ttl_hours} horas.\n\n"
                    f"{origin}/activar#code={invitation.code}\n\n"
                    "El enlace permite activar tu cuenta una sola vez."
                )
                try:
                    rejected = smtp.send_message(mail)
                except smtplib.SMTPRecipientsRefused:
                    continue
                if not rejected:
                    sent.add(invitation.user_id)
    except (smtplib.SMTPException, OSError, ValueError):
        return sent
    return sent
