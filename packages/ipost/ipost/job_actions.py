from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import os

import httpx

from ipost.agents.schemas import JobRecord, TimelineStep
from ipost.config_store import get_track, list_topics, upsert_topic, upsert_track
from ipost.instagram import InstagramError, publish_reel, publish_story
from ipost.jobs import save_job
from ipost.agents.templates import apply_reel_hashtags
from ipost.mux import MuxError, mux_still_with_audio
from ipost.notify import notify_publish_failed
from ipost.settings import Settings
from ipost.storage import StorageError, download_private_bytes, upload_file
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


def persist_incomplete_generate(job: JobRecord, settings: Settings, error: str) -> JobRecord:
    has_file = bool(job.still_path) and Path(job.still_path).is_file()
    if not job.still_url and not has_file and not job.still_path.startswith("http"):
        job.status = "FAILED"
    job.must_fix = error
    return save_job(job, settings)


def finalize_generated_job(job: JobRecord, settings: Settings) -> JobRecord:
    attach_public_still(job, settings)
    if job.type == "REEL":
        if not job.audio_id:
            raise JobActionError("Upload and tag an audio file for this topic before generating a Reel.")
        attach_reel_audio(job, job.audio_id, settings)
    mark_topic_used(job.topic, job.date, settings)
    return save_job(job, settings)


def _job_work_dir(settings: Settings, job_id: str) -> Path:
    ephemeral = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("FLY_APP_NAME")
    root = Path("/tmp") if ephemeral else settings.token_file.parent
    path = root / "jobs" / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def attach_public_video(job: JobRecord, settings: Settings) -> JobRecord:
    if job.video_path.startswith("http"):
        job.video_url = job.video_path
        return job
    path = Path(job.video_path) if job.video_path else None
    if path is None or not path.is_file():
        if job.video_url:
            return job
        raise JobActionError("Job has no reel to upload")
    try:
        job.video_url = upload_file(settings, f"jobs/{job.id}/reel.mp4", path, "video/mp4")
    except StorageError as exc:
        raise JobActionError(str(exc)) from exc
    return job


def _still_file(job: JobRecord, work_dir: Path) -> Path:
    local = Path(job.still_path) if job.still_path else None
    if local and local.is_file():
        return local
    dest = work_dir / f"{job.id}-still.jpg"
    if job.still_url:
        response = httpx.get(job.still_url, timeout=60, follow_redirects=True)
        if response.status_code >= 400:
            raise JobActionError("Could not download the still to mux")
        dest.write_bytes(response.content)
        return dest
    raise JobActionError("Job has no still to mux")


def attach_reel_audio(job: JobRecord, track_id: str, settings: Settings) -> JobRecord:
    if job.type != "REEL":
        raise JobActionError("Audio is for Reels only")
    if job.status in ("PUBLISHED", "SKIPPED", "REJECTED"):
        raise JobActionError(f"Job is {job.status}")
    attach_public_still(job, settings)
    track = get_track(track_id, settings)
    if track is None:
        raise JobActionError("Track not found")
    if not track.path:
        raise JobActionError("Upload an audio file for this track first")
    audio_bytes = download_private_bytes(settings, track.path)
    if not audio_bytes:
        raise JobActionError("Track file is missing from storage")
    work = _job_work_dir(settings, job.id)
    suffix = Path(track.path).suffix or ".mp3"
    audio_path = work / f"{track.id}{suffix}"
    audio_path.write_bytes(audio_bytes)
    still = _still_file(job, work)
    video = work / f"{job.id}-reel.mp4"
    try:
        mux_still_with_audio(still, audio_path, video)
    except MuxError as exc:
        raise JobActionError(str(exc)) from exc
    job.audio_id = track.id
    job.video_path = str(video)
    job.video_url = ""
    attach_public_video(job, settings)
    track.last_used = job.date
    upsert_track(track, settings)
    job.timeline.append(TimelineStep(label="Audio", sub=track.title, kind="neutral"))
    return save_job(job, settings)


async def publish_story_job(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> tuple[JobRecord, str]:
    if job.type != "STORY":
        raise JobActionError("Not a Story")
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
        notify_publish_failed(job, settings, str(exc))
        raise JobActionError(str(exc)) from exc
    job.ig_media_id = media_id
    job.status = "PUBLISHED"
    job.must_fix = None
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")
    job.timeline.append(TimelineStep(label="Published", sub=now, kind="current"))
    return save_job(job, settings), media_id


async def publish_reel_job(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> tuple[JobRecord, str]:
    if job.type != "REEL":
        raise JobActionError("Not a Reel")
    if job.status in ("PUBLISHED", "SKIPPED", "REJECTED"):
        raise JobActionError(f"Job is {job.status}")
    if not job.video_url:
        if job.video_path:
            attach_public_video(job, settings)
    if not job.video_url:
        raise JobActionError("Reel has no video to publish")
    job.caption = apply_reel_hashtags(job.caption)
    job.status = "PUBLISHING"
    save_job(job, settings)
    try:
        media_id = await publish_reel(settings, token, job.video_url, job.caption)
    except InstagramError as exc:
        job.status = "FAILED"
        job.must_fix = str(exc)
        save_job(job, settings)
        notify_publish_failed(job, settings, str(exc))
        raise JobActionError(str(exc)) from exc
    job.ig_media_id = media_id
    job.status = "PUBLISHED"
    job.must_fix = None
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")
    job.timeline.append(TimelineStep(label="Published", sub=now, kind="current"))
    return save_job(job, settings), media_id


async def publish_media_job(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> tuple[JobRecord, str]:
    if job.type == "REEL":
        return await publish_reel_job(job, settings, token)
    return await publish_story_job(job, settings, token)


def set_terminal_status(job: JobRecord, status: str, settings: Settings) -> JobRecord:
    if status not in ("REJECTED", "SKIPPED"):
        raise JobActionError("Unsupported status")
    if job.status in ("PUBLISHED", "SKIPPED", "REJECTED"):
        raise JobActionError(f"Job is {job.status}")
    job.status = status
    return save_job(job, settings)
