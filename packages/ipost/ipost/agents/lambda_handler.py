from __future__ import annotations

import asyncio
import json
from typing import Any

from ipost.agents.pipeline import generate_job, today_iso
from ipost.agents.schemas import JobType
from ipost.errors import ConfigError
from ipost.job_actions import JobActionError, finalize_generated_job, publish_story_job
from ipost.jobs import save_job, today_story
from ipost.settings import get_settings
from ipost.token_store import load_token


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "body": json.dumps(payload)}


def _generate(event: dict[str, Any]) -> dict[str, Any]:
    job_type: JobType = event.get("type", "STORY")
    if job_type != "STORY":
        return _response(400, {"error": "Only Story generate is available in Phase 1"})
    settings = get_settings()
    job = asyncio.run(
        generate_job(
            job_type,
            settings=settings,
            date=event.get("date"),
            forced_topic=event.get("topic"),
        )
    )
    try:
        finalize_generated_job(job, settings)
    except (JobActionError, ConfigError):
        save_job(job, settings)
    return _response(200, {"success": True, "job": job.model_dump()})


async def _publish() -> dict[str, Any]:
    settings = get_settings()
    job = today_story(today_iso(), settings)
    if job is None:
        return _response(200, {"success": True, "skipped": "no story for today"})
    if job.status != "APPROVED":
        return _response(200, {"success": True, "skipped": f"story is {job.status}"})
    token = load_token(settings)
    if token is None:
        return _response(401, {"error": "Instagram is not connected"})
    try:
        job, media_id = await publish_story_job(job, settings, token)
    except JobActionError as exc:
        return _response(400, {"error": str(exc)})
    return _response(200, {"success": True, "job": job.model_dump(), "media_id": media_id})


def lambda_handler(event: dict[str, Any], _context: object | None = None) -> dict[str, Any]:
    action = event.get("action", "generate")
    if action == "generate":
        return _generate(event)
    if action == "publish":
        return asyncio.run(_publish())
    return _response(400, {"error": f"Unsupported action: {action}"})
