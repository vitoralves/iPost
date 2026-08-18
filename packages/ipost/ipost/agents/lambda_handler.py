from __future__ import annotations

import asyncio
import json
from typing import Any

from ipost.agents.pipeline import generate_job, today_iso
from ipost.agents.schemas import JobType
from ipost.agents.canvas import StillError
from ipost.errors import ConfigError
from ipost.job_actions import (
    JobActionError,
    finalize_generated_job,
    persist_incomplete_generate,
    publish_media_job,
)
from ipost.jobs import today_job
from ipost.notify import notify, notify_generate_failed, notify_needs_review
from ipost.settings import get_settings
from ipost.token_store import load_token


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "body": json.dumps(payload)}


def _generate(event: dict[str, Any]) -> dict[str, Any]:
    job_type: JobType = event.get("type", "STORY")
    if job_type not in ("STORY", "REEL"):
        return _response(400, {"error": "type must be STORY or REEL"})
    settings = get_settings()
    job = None
    try:
        job = asyncio.run(
            generate_job(
                job_type,
                settings=settings,
                date=event.get("date"),
                forced_topic=event.get("topic"),
            )
        )
        job = finalize_generated_job(job, settings)
    except (StillError, ConfigError, JobActionError) as exc:
        if job is not None:
            persist_incomplete_generate(job, settings, str(exc))
            notify_generate_failed(job, settings, str(exc))
        return _response(503, {"error": str(exc)})
    if job.status == "NEEDS_REVIEW":
        notify_needs_review(job, settings)
    return _response(200, {"success": True, "job": job.model_dump()})


async def _publish(event: dict[str, Any]) -> dict[str, Any]:
    job_type: JobType = event.get("type", "STORY")
    settings = get_settings()
    job = today_job(today_iso(), job_type, settings)
    label = "story" if job_type == "STORY" else "reel"
    if job is None:
        return _response(200, {"success": True, "skipped": f"no {label} for today"})
    if job.status != "APPROVED":
        return _response(200, {"success": True, "skipped": f"{label} is {job.status}"})
    token = load_token(settings)
    if token is None:
        notify(settings, subject="iPost: publish skipped", body="Instagram is not connected.")
        return _response(401, {"error": "Instagram is not connected"})
    try:
        job, media_id = await publish_media_job(job, settings, token)
    except JobActionError as exc:
        return _response(400, {"error": str(exc)})
    return _response(200, {"success": True, "job": job.model_dump(), "media_id": media_id})


def lambda_handler(event: dict[str, Any], _context: object | None = None) -> dict[str, Any]:
    action = event.get("action", "generate")
    if action == "generate":
        return _generate(event)
    if action == "publish":
        return asyncio.run(_publish(event))
    return _response(400, {"error": f"Unsupported action: {action}"})
