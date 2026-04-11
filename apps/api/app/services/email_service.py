"""Email notification service."""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from threading import Thread

from app.core.config import settings

log = logging.getLogger(__name__)


def _send_in_background(subject: str, body: str, to: str) -> None:
    """Send email in a background thread to avoid blocking the API."""
    try:
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = to

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        log.info("email.sent", to=to, subject=subject)
    except Exception as exc:
        log.error("email.send_failed", error=str(exc), to=to)


def send_email(subject: str, body: str, to: str | None = None) -> None:
    """Send an email notification. Non-blocking (background thread)."""
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("email.skip_no_credentials")
        return

    recipient = to or settings.notification_email
    if not recipient:
        return

    thread = Thread(target=_send_in_background, args=(subject, body, recipient), daemon=True)
    thread.start()


def notify_new_registration(email: str, full_name: str | None) -> None:
    """Notify admin of a new user registration."""
    name = full_name or "Non renseigne"
    subject = f"[RAG Platform] Nouvelle inscription : {email}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px;">
        <h2 style="color: #1c1917;">Nouvelle inscription</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e7e5e4; color: #78716c;">Email</td>
                <td style="padding: 8px; border-bottom: 1px solid #e7e5e4; font-weight: bold;">{email}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e7e5e4; color: #78716c;">Nom</td>
                <td style="padding: 8px; border-bottom: 1px solid #e7e5e4;">{name}</td>
            </tr>
        </table>
        <p style="margin-top: 16px; font-size: 12px; color: #a8a29e;">
            RAG Platform &mdash; rag.marinenationale.cloud
        </p>
    </div>
    """
    send_email(subject, body)
