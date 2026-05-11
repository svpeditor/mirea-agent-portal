"""Минимальный SMTP-клиент для уведомлений.

Если smtp_host не задан в env — логируем в stdout вместо реальной отправки
(удобно для dev/тестов).
"""
from __future__ import annotations

import smtplib
import ssl
import uuid
from email.message import EmailMessage

import structlog

log = structlog.get_logger()


def _build_message(
    *,
    sender: str,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def send_job_finished_email(
    *,
    user_email: str,
    user_display_name: str,
    agent_name: str,
    job_id: uuid.UUID,
    job_status: str,
    duration_s: int,
    base_url: str,
    smtp_host: str | None,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    smtp_from: str,
) -> None:
    """Шлёт письмо «job завершился». Failures не raise — только лог."""
    job_url = f"{base_url.rstrip('/')}/jobs/{job_id}"
    minutes = duration_s // 60
    seconds = duration_s % 60
    if minutes >= 1:
        dur = f"{minutes} мин {seconds} сек"
    else:
        dur = f"{seconds} сек"

    if job_status == "ready":
        subject = f"✓ {agent_name} — готово"
        verb = "успешно завершился"
    elif job_status == "failed":
        subject = f"✕ {agent_name} — ошибка"
        verb = "завершился с ошибкой"
    else:
        subject = f"{agent_name} — {job_status}"
        verb = f"завершился ({job_status})"

    text = (
        f"Привет, {user_display_name or user_email}!\n\n"
        f"Твой запуск агента «{agent_name}» {verb}. "
        f"Длительность: {dur}.\n\n"
        f"Открыть в портале: {job_url}\n\n"
        f"---\n"
        f"Известия НУГ — портал AI-агентов МИРЭА\n"
        f"Отписаться: профиль → выключить «email на завершение»"
    )
    html = (
        f'<div style="font-family:Georgia,serif;max-width:600px">'
        f'<h2 style="margin-bottom:0">{subject}</h2>'
        f'<p>Привет, {user_display_name or user_email}!</p>'
        f'<p>Твой запуск агента <b>«{agent_name}»</b> {verb}.<br>'
        f'Длительность: <code>{dur}</code>.</p>'
        f'<p><a href="{job_url}" '
        f'style="display:inline-block;padding:10px 16px;'
        f'background:#1a1a1a;color:#f6f0e0;text-decoration:none;'
        f'font-family:monospace">'
        f'Открыть в портале →</a></p>'
        f'<hr><p style="color:#888;font-size:13px">'
        f'<i>Известия НУГ</i> — портал AI-агентов МИРЭА.<br>'
        f'Отписаться: профиль → выключить «email на завершение».</p>'
        f'</div>'
    )

    msg = _build_message(sender=smtp_from, to=user_email, subject=subject, text=text, html=html)

    if not smtp_host:
        log.info("email_send_skipped_no_smtp", to=user_email, subject=subject)
        log.info("email_body_preview", text=text)
        return

    try:
        if smtp_port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=15) as s:
                if smtp_user and smtp_password:
                    s.login(smtp_user, smtp_password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                if smtp_user and smtp_password:
                    s.login(smtp_user, smtp_password)
                s.send_message(msg)
        log.info("email_sent", to=user_email, subject=subject)
    except Exception as e:  # noqa: BLE001
        log.error("email_send_failed", to=user_email, exc_info=e)
