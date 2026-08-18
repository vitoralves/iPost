from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ipost.agents.schemas import JobRecord, TimelineStep
from ipost.config_store import list_topics, upsert_topic
from ipost.instagram import InstagramError, publish_story
from ipost.jobs import save_job
from ipost.settings import Settings
from ipost.storage import StorageError, upload_file
from ipost.token_store import InstagramToken


class JobActionError(RuntimeError):
    pass


def attach_public_still(job: JobRecord, settings: Settings) -> JobRecord:
    if job.still_url:
        return job
    if job.still_path.startswith("http"):
        job.still_url = job.still_path
        return job
    path = Path(job.still_path) if job.still_path else None
    if path is None or not path.is_file():
        raise JobActionError("Job has no still to upload")
    try:
        job.still_url = upload_file(settings, f"jobs/{job.id}/still.jpg", path, "image/jpeg")
    except StorageError as exc:
        raise JobActionError(str(exc)) from exc
    return job


def mark_topic_used(slug: str, day: str, settings: Settings) -> None:
    for topic in list_topics(settings):
        if topic.slug == slug:
            topic.last_used = day
            upsert_topic(topic, settings)
            return


def finalize_generated_job(job: JobRecord, settings: Settings) -> JobRecord:
    attach_public_still(job, settings)
    mark_topic_used(job.topic, job.date, settings)
    return save_job(job, settings)


async def publish_story_job(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> tuple[JobRecord, str]:
    if job.type != "STORY":
        raise JobActionError("Only Story publish is available in Phase 1")
    if job.status in ("PUBLISHED", "SKIPPED", "REJECTED"):
        raise JobActionError(f"Job is {job.status}")
    attach_public_still(job, settings)
    if not job.still_url:
        raise JobActionError("Job has no still to publish")
    job.status = "PUBLISHING"
    save_job(job, settings)
    try:
        media_id = await publish_story(settings, token, job.still_url)
    except InstagramError as exc:
        job.status = "FAILED"
        job.must_fix = str(exc)
        save_job(job, settings)
        raise JobActionError(str(exc)) from exc
    job.status = "PUBLISHED"
    job.must_fix = None
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")
    job.timeline.append(TimelineStep(label="Published", sub=now, kind="current"))
    return save_job(job, settings), media_id


def set_terminal_status(job: JobRecord, status: str, settings: Settings) -> JobRecord:
    if status not in ("REJECTED", "SKIPPED"):
        raise JobActionError("Unsupported status")
    if job.status in ("PUBLISHED", "SKIPPED", "REJECTED"):
        raise JobActionError(f"Job is {job.status}")
    job.status = status
    return save_job(job, settings)
