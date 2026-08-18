from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ipost.agents.canvas import generate_still
from ipost.agents.schemas import JobType, PlanOutput
from ipost.agents.templates import REEL_STILL_BRIEF, STILL_BRIEF, THEME_GUIDANCE, apply_reel_hashtags
from ipost.brand import load_brand_kit
from ipost.config_store import load_brand_ref_file
from ipost.settings import Settings


@dataclass
class CreatorResult:
    still_path: str
    video_path: str
    caption: str


def _style_ref_bytes(settings: Settings, topic: str) -> list[bytes]:
    kit = load_brand_kit(settings)
    images: list[bytes] = []
    for ref in kit.refs_for_topic(topic):
        loaded = load_brand_ref_file(ref.id, settings)
        if loaded:
            images.append(loaded[0])
    return images


def _still_prompt(
    plan: PlanOutput,
    job_type: JobType,
    notes: list[str],
    must_fix: str | None = None,
    *,
    has_refs: bool = False,
) -> str:
    theme = plan.topic.strip() or "hope"
    guidance = THEME_GUIDANCE.get(
        theme,
        "Find the strongest emotional and visual metaphor. Avoid the obvious religious stock image.",
    )
    look_notes = ""
    if notes:
        look_notes = (
            "\nLook notes from the brand kit (match this world, do not copy a layout):\n"
            + "\n".join(f"- {note}" for note in notes)
        )
    if has_refs:
        look_notes += (
            "\nAttached images are style references for light, palette, and atmosphere. "
            "Do not copy their composition, faces, or on-image text.\n"
        )
    fix = f"\nHonor this correction: {must_fix.strip()}\n" if must_fix and must_fix.strip() else ""
    phrase = plan.on_image_text.strip()
    visual = plan.visual_prompt.strip() or "A private human moment connected to this theme."
    brief = REEL_STILL_BRIEF if job_type == "REEL" else STILL_BRIEF
    return brief.format(
        theme=theme,
        theme_guidance=guidance,
        visual=visual,
        phrase=phrase or "Um pensamento curto em português.",
        look_notes=look_notes,
        must_fix=fix,
    )


def _materialize_still(
    settings: Settings,
    *,
    job_id: str,
    job_type: JobType,
    plan: PlanOutput,
    work_dir: Path,
    must_fix: str | None = None,
) -> Path:
    kit = load_brand_kit(settings)
    notes = [ref.note.strip() for ref in kit.refs_for_topic(plan.topic) if ref.note.strip()]
    references = _style_ref_bytes(settings, plan.topic)
    still = work_dir / f"{job_id}-still.jpg"
    generate_still(
        settings,
        _still_prompt(plan, job_type, notes, must_fix, has_refs=bool(references)),
        still,
        stamp_logo=job_type == "STORY",
        references=references,
    )
    return still


async def run_creator(
    settings: Settings,
    *,
    job_id: str,
    job_type: JobType,
    date: str,
    plan: PlanOutput,
    work_dir: Path,
    audio_id: str | None,
    attempt: int,
    max_attempts: int,
    must_fix: str | None,
) -> CreatorResult:
    still = _materialize_still(
        settings,
        job_id=job_id,
        job_type=job_type,
        plan=plan,
        work_dir=work_dir,
        must_fix=must_fix,
    )
    caption = apply_reel_hashtags(plan.caption) if job_type == "REEL" else ""
    return CreatorResult(still_path=str(still), video_path="", caption=caption)
