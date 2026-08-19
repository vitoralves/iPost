from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from ipost.agents.pipeline import generate_job, today_iso
from ipost.agents.schemas import JobType
from ipost.agents.canvas import StillError
from ipost.errors import ConfigError
from ipost.insights import InsightsError, sync_insights
from ipost.job_actions import (
    JobActionError,
    finalize_generated_job,
    persist_incomplete_generate,
    publish_media_job,
)
from ipost.jobs import get_job, today_job
from ipost.notify import (
    notify,
    notify_generate_failed,
    notify_needs_review,
    notify_publish_skipped,
    notify_scheduler_error,
)
from ipost.runs import record_run
from ipost.settings import get_settings
from ipost.token_store import load_token

_BUSY = frozenset({"GENERATING", "CRITIQUE", "REGENERATING", "PUBLISHING"})
_KEEP = frozenset({"APPROVED", "NEEDS_REVIEW", "PUBLISHED"})


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "body": json.dumps(payload)}


def _generate(event: dict[str, Any]) -> dict[str, Any]:
    job_type: JobType = event.get("type", "STORY")
    if job_type not in ("STORY", "REEL"):
        return _response(400, {"error": "type must be STORY or REEL"})
    settings = get_settings()
    day = event.get("date") or today_iso()
    existing = today_job(day, job_type, settings)
    if existing is not None and existing.status in _KEEP | _BUSY:
        label = "story" if job_type == "STORY" else "reel"
        reason = f"today's {label} is already {existing.status}"
        if existing.status == "NEEDS_REVIEW":
            notify(
                settings,
                subject=f"iPost: {job_type} generate skipped",
                body=f"{reason}. Review it in the dashboard.\n",
            )
        return _response(
            200,
            {"success": True, "skipped": reason, "job": existing.model_dump()},
        )
    job = None
    existing_id = event.get("job_id")
    if existing_id:
        job = get_job(existing_id, settings)
    try:
        job = asyncio.run(
            generate_job(
                job_type,
                settings=settings,
                date=event.get("date"),
                forced_topic=event.get("topic"),
                existing=job,
            )
        )
        job = finalize_generated_job(job, settings)
    except (StillError, ConfigError, JobActionError) as exc:
        if job is not None:
            persist_incomplete_generate(job, settings, str(exc))
            notify_generate_failed(job, settings, str(exc))
        else:
            notify_generate_failed(None, settings, str(exc))
        return _response(503, {"error": str(exc), "job": job.model_dump() if job else None})
    if job.status == "NEEDS_REVIEW":
        notify_needs_review(job, settings)
    return _response(200, {"success": True, "job": job.model_dump()})


async def _publish(event: dict[str, Any]) -> dict[str, Any]:
    job_type: JobType = event.get("type", "STORY")
    settings = get_settings()
    job = today_job(today_iso(), job_type, settings)
    label = "story" if job_type == "STORY" else "reel"
    if job is None:
        reason = f"no {label} for today"
        notify_publish_skipped(settings, job_type, reason)
        return _response(200, {"success": True, "skipped": reason})
    if job.status != "APPROVED":
        reason = f"{label} is {job.status}"
        notify_publish_skipped(settings, job_type, reason)
        return _response(200, {"success": True, "skipped": reason, "job": job.model_dump()})
    token = load_token(settings)
    if token is None:
        notify(settings, subject="iPost: publish skipped", body="Instagram is not connected.")
        return _response(401, {"error": "Instagram is not connected"})
    try:
        job, media_id = await publish_media_job(job, settings, token)
    except JobActionError as exc:
        return _response(400, {"error": str(exc), "job": job.model_dump()})
    return _response(200, {"success": True, "job": job.model_dump(), "media_id": media_id})


async def _insights() -> dict[str, Any]:
    settings = get_settings()
    token = load_token(settings)
    if token is None:
        notify(settings, subject="iPost: insights skipped", body="Instagram is not connected.")
        return _response(401, {"error": "Instagram is not connected"})
    try:
        result = await sync_insights(settings, token)
    except InsightsError as exc:
        notify(settings, subject="iPost: insights skipped", body=str(exc))
        return _response(400, {"error": str(exc)})
    return _response(200, {"success": True, **result})


def _parse_body(result: dict[str, Any]) -> dict[str, Any]:
    raw = result.get("body") or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _outcome(result: dict[str, Any]) -> tuple[str, str, str | None]:
    code = int(result.get("statusCode") or 500)
    body = _parse_body(result)
    job = body.get("job")
    job_id = job.get("id") if isinstance(job, dict) else None
    if code >= 400:
        return "error", str(body.get("error") or f"HTTP {code}"), job_id
    if body.get("skipped"):
        return "skipped", str(body["skipped"]), job_id
    return "ok", "", job_id


def lambda_handler(event: dict[str, Any], context: object | None = None) -> dict[str, Any]:
    action = event.get("action", "generate")
    job_type = event.get("type")
    started = time.perf_counter()
    memory_mb = int(os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE") or "0")
    request_id = getattr(context, "aws_request_id", None) if context is not None else None
    result: dict[str, Any]
    try:
        if action == "generate":
            result = _generate(event)
        elif action == "publish":
            result = asyncio.run(_publish(event))
        elif action == "insights":
            result = asyncio.run(_insights())
        else:
            result = _response(400, {"error": f"Unsupported action: {action}"})
    except Exception as exc:
        settings = get_settings()
        notify_scheduler_error(settings, action, str(exc))
        result = _response(500, {"error": str(exc)})
    duration_ms = int((time.perf_counter() - started) * 1000)
    status, message, job_id = _outcome(result)
    record_run(
        action=action,
        status=status,
        settings=get_settings(),
        source="lambda",
        job_type=job_type if isinstance(job_type, str) else None,
        job_id=job_id,
        message=message,
        duration_ms=duration_ms,
        memory_mb=memory_mb,
        request_id=request_id if isinstance(request_id, str) else None,
    )
    return result
