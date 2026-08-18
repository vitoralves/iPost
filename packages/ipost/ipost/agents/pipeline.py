from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from uuid import uuid4

from ipost.agents.canvas import StillError
from ipost.agents.creator import run_creator
from ipost.agents.critic import run_critic
from ipost.agents.planner import run_planner
from ipost.agents.schemas import JobRecord, JobType, Slot, TimelineStep, TopicSlug
from ipost.agents.templates import apply_reel_hashtags
from ipost.agents.topic import pick_audio, pick_topic
from ipost.config_store import list_topics
from ipost.errors import ConfigError
from ipost.insights import performance_note, track_play_scores
from ipost.jobs import list_jobs
from ipost.settings import Settings, get_settings


def today_iso() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def _today() -> str:
    return today_iso()


def _slot(job_type: JobType) -> tuple[Slot, str]:
    if job_type == "STORY":
        return "morning", "06:00"
    return "evening", "19:00"


def _work_dir(settings: Settings, job_id: str) -> Path:
    ephemeral = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("FLY_APP_NAME")
    root = Path("/tmp") if ephemeral else settings.token_file.parent
    path = root / "jobs" / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reel_audio_id(topic_slug: str, settings: Settings) -> str:
    match = next((item for item in list_topics(settings) if item.slug == topic_slug), None)
    if match is None:
        raise ConfigError("Add an enabled topic before generating.")
    plays = track_play_scores(list_jobs(settings))
    track = pick_audio(match, plays=plays)
    if track is None:
        raise ConfigError("Upload and tag an audio file for this topic before generating a Reel.")
    return track.id


async def generate_job(
    job_type: JobType,
    *,
    settings: Settings | None = None,
    date: str | None = None,
    forced_topic: TopicSlug | None = None,
) -> JobRecord:
    settings = settings or get_settings()
    day = date or _today()
    slot, publish_at = _slot(job_type)
    topic = pick_topic(job_type=job_type).model_copy()
    if forced_topic:
        topic.slug = forced_topic
    audience = performance_note(list_jobs(settings), day)
    job_id = f"{job_type.lower()}-{day}-{uuid4().hex[:8]}"
    work_dir = _work_dir(settings, job_id)
    job = JobRecord(
        id=job_id,
        type=job_type,
        slot=slot,
        date=day,
        publish_at=publish_at,
        topic=topic.slug,
        status="GENERATING",
        audio_id=None,
        max_attempts=settings.max_attempts,
        timeline=[TimelineStep(label="Generate", sub="start", kind="neutral")],
    )
    must_fix: str | None = None
    plan = await run_planner(
        settings,
        job_type=job_type,
        date=day,
        topics=[topic.slug],
        forced_topic=topic.slug,
        must_fix=must_fix,
        performance_note=audience,
    )
    job.topic = plan.topic
    job.hook = plan.hook
    job.visual_prompt = plan.visual_prompt
    job.caption = apply_reel_hashtags(plan.caption) if job_type == "REEL" else ""
    if job_type == "REEL":
        job.audio_id = _reel_audio_id(plan.topic, settings)

    for attempt in range(1, settings.max_attempts + 1):
        job.attempt = attempt
        job.status = "GENERATING" if attempt == 1 else "REGENERATING"
        artifact = await run_creator(
            settings,
            job_id=job_id,
            job_type=job_type,
            date=day,
            plan=plan,
            work_dir=work_dir,
            audio_id=job.audio_id,
            attempt=attempt,
            max_attempts=settings.max_attempts,
            must_fix=must_fix,
        )
        job.still_path = artifact.still_path
        job.video_path = artifact.video_path
        if job_type == "REEL":
            job.caption = apply_reel_hashtags(artifact.caption or job.caption)
        if not artifact.still_path or not Path(artifact.still_path).is_file():
            raise StillError("Still was not written")
        job.status = "CRITIQUE"
        critique = await run_critic(
            settings,
            job_type=job_type,
            plan=plan,
            still_path=artifact.still_path,
            caption=job.caption,
            attempt=attempt,
            max_attempts=settings.max_attempts,
        )
        job.score = critique.score
        job.must_fix = critique.must_fix
        job.subscores = critique.subscores
        kind = "bad" if critique.score < settings.critic_pass_score else "neutral"
        job.timeline.append(
            TimelineStep(label="Critique", sub=f"{critique.score:.1f} / 10", kind=kind)
        )
        passed = critique.score >= settings.critic_pass_score and not critique.hard_fail
        if passed:
            job.status = "APPROVED"
            job.timeline.append(
                TimelineStep(label="Approved", sub=f"{critique.score:.1f} / 10", kind="current")
            )
            return job
        must_fix = critique.must_fix
        if attempt < settings.max_attempts:
            job.timeline.append(
                TimelineStep(label="Regenerate", sub=f"Attempt {attempt + 1}", kind="neutral")
            )
            plan = await run_planner(
                settings,
                job_type=job_type,
                date=day,
                topics=[topic.slug],
                forced_topic=plan.topic,
                must_fix=must_fix,
                performance_note=audience,
            )
            job.topic = plan.topic
            job.caption = apply_reel_hashtags(plan.caption) if job_type == "REEL" else ""
            if job_type == "REEL":
                job.audio_id = _reel_audio_id(plan.topic, settings)

    job.status = "NEEDS_REVIEW"
    job.timeline.append(
        TimelineStep(label="Needs review", sub=f"{job.score:.1f} / 10", kind="current")
    )
    return job
