from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ipost.agents.canvas import generate_still
from ipost.agents.schemas import JobType, PlanOutput
from ipost.agents.templates import REEL_STILL_BRIEF, STILL_BRIEF, THEME_GUIDANCE, apply_reel_hashtags
from ipost.brand import load_brand_kit
from ipost.overlay import burn_text
from ipost.settings import Settings


@dataclass
class CreatorContext:
    settings: Settings
    job_id: str
    job_type: JobType
    plan: PlanOutput
    work_dir: Path
    audio_id: str | None = None
    still_path: str = ""
    video_path: str = ""
    caption: str = ""
    refs: list[str] = field(default_factory=list)


@dataclass
class CreatorResult:
    still_path: str
    video_path: str
    caption: str


@function_tool
async def retrieve_style_refs(wrapper: RunContextWrapper[CreatorContext]) -> str:
    from ipost.storage import StorageError, signed_private_url

    ctx = wrapper.context
    kit = load_brand_kit(ctx.settings)
    topic = ctx.plan.topic
    lines: list[str] = []
    for ref in kit.refs_for_topic(topic):
        url = ref.url
        if ref.path:
            try:
                url = signed_private_url(ctx.settings, ref.path)
            except StorageError:
                url = ref.path
        note = ref.note.strip() or "style reference"
        if url:
            lines.append(f"{note} ({url})")
        elif note:
            lines.append(note)
    ctx.refs = lines
    if not ctx.refs:
        return f"No style refs for topic {topic}"
    return f"Style refs for {topic}:\n" + "\n".join(f"- {line}" for line in ctx.refs)


@function_tool
async def generate_still_tool(wrapper: RunContextWrapper[CreatorContext], prompt: str) -> str:
    ctx = wrapper.context
    kit = load_brand_kit(ctx.settings)
    notes = [ref.note.strip() for ref in kit.refs_for_topic(ctx.plan.topic) if ref.note.strip()]
    prompt = _still_prompt(ctx.plan, ctx.job_type, notes)
    destination = ctx.work_dir / f"{ctx.job_id}-still.jpg"
    generate_still(ctx.settings, prompt, destination, stamp_logo=ctx.job_type == "STORY")
    ctx.still_path = str(destination)
    return f"Wrote still {destination}"


@function_tool
async def render_story_text(wrapper: RunContextWrapper[CreatorContext], text: str) -> str:
    ctx = wrapper.context
    if ctx.job_type != "STORY":
        return "Skipped story text (reel)"
    if not ctx.still_path:
        return "No still to overlay"
    source = Path(ctx.still_path)
    destination = ctx.work_dir / f"{ctx.job_id}-story.jpg"
    burn_text(source, text, destination)
    ctx.still_path = str(destination)
    return f"Burned story text onto {destination}"


@function_tool
async def write_caption(wrapper: RunContextWrapper[CreatorContext], caption: str) -> str:
    ctx = wrapper.context
    if ctx.job_type != "REEL":
        ctx.caption = ""
        return "Stories have no API caption"
    ctx.caption = caption.strip()
    return f"Caption set ({len(ctx.caption)} chars)"


def _still_prompt(
    plan: PlanOutput,
    job_type: JobType,
    notes: list[str],
    must_fix: str | None = None,
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
    still = work_dir / f"{job_id}-still.jpg"
    generate_still(
        settings,
        _still_prompt(plan, job_type, notes, must_fix),
        still,
        stamp_logo=job_type == "STORY",
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
