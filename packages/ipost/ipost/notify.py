from __future__ import annotations

import logging

import httpx

from ipost.agents.schemas import JobRecord
from ipost.settings import Settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def notify(settings: Settings, *, subject: str, body: str) -> None:
    email = settings.alert_email.strip()
    key = settings.resend_api_key.strip()
    if not email or not key:
        logger.warning("Alert skipped: ALERT_EMAIL or RESEND_API_KEY is unset")
        return
    try:
        response = httpx.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from,
                "to": [email],
                "subject": subject,
                "text": body,
            },
            timeout=15.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to send alert email")


def notify_needs_review(job: JobRecord, settings: Settings) -> None:
    notify(
        settings,
        subject=f"iPost: {job.type} needs review ({job.date})",
        body=(
            f"Job {job.id} scored {job.score:.1f}/10 after {job.attempt} attempts "
            f"and is waiting in the dashboard.\n\n"
            f"Topic: {job.topic}\n"
            f"Must fix: {job.must_fix or 'n/a'}\n"
        ),
    )


def notify_publish_failed(job: JobRecord, settings: Settings, error: str) -> None:
    notify(
        settings,
        subject=f"iPost: {job.type} publish failed ({job.date})",
        body=f"Job {job.id} failed to publish.\n\nError: {error}\n",
    )


def notify_generate_failed(job: JobRecord | None, settings: Settings, error: str) -> None:
    job_id = job.id if job else "unknown"
    notify(
        settings,
        subject="iPost: generate failed",
        body=f"Job {job_id} failed during generate.\n\nError: {error}\n",
    )
