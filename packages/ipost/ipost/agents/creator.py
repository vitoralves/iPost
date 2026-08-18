from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agents import Agent, RunContextWrapper, Runner, function_tool, trace

from ipost.agents.canvas import generate_still
from ipost.agents.model import bedrock_model
from ipost.agents.schemas import JobType, PlanOutput
from ipost.agents.templates import CREATOR_INSTRUCTIONS, CREATOR_PROMPT
from ipost.fixtures import write_tone_wav
from ipost.mux import MuxError, mux_still_with_audio
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
    lines: list[str] = []
    for ref in kit.refs:
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
        return "No style refs in Brand Kit"
    return "Style refs:\n" + "\n".join(f"- {line}" for line in ctx.refs)


@function_tool
async def generate_still_tool(wrapper: RunContextWrapper[CreatorContext], prompt: str) -> str:
    ctx = wrapper.context
    destination = ctx.work_dir / f"{ctx.job_id}-still.jpg"
    generate_still(ctx.settings, prompt, destination)
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


@function_tool
async def mux_reel(wrapper: RunContextWrapper[CreatorContext]) -> str:
    ctx = wrapper.context
    if ctx.job_type != "REEL":
        return "Skipped mux (story)"
    if not ctx.still_path:
        return "No still to mux"
    audio = ctx.work_dir / f"{ctx.job_id}-audio.wav"
    if not audio.exists():
        write_tone_wav(audio)
    video = ctx.work_dir / f"{ctx.job_id}-reel.mp4"
    try:
        mux_still_with_audio(Path(ctx.still_path), audio, video)
    except MuxError as exc:
        return f"Mux failed: {exc}"
    ctx.video_path = str(video)
    return f"Wrote reel {video}"


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
    context = CreatorContext(
        settings=settings,
        job_id=job_id,
        job_type=job_type,
        plan=plan,
        work_dir=work_dir,
        audio_id=audio_id,
        caption=plan.caption,
    )
    if settings.ipost_mock_bedrock:
        still = work_dir / f"{job_id}-still.jpg"
        generate_still(settings, plan.visual_prompt, still)
        if job_type == "STORY" and plan.on_image_text:
            burned = work_dir / f"{job_id}-story.jpg"
            burn_text(still, plan.on_image_text, burned)
            still = burned
        video = ""
        if job_type == "REEL":
            audio = work_dir / f"{job_id}-audio.wav"
            write_tone_wav(audio)
            dest = work_dir / f"{job_id}-reel.mp4"
            mux_still_with_audio(still, audio, dest)
            video = str(dest)
        return CreatorResult(still_path=str(still), video_path=video, caption=plan.caption)

    model = bedrock_model(settings)
    task = CREATOR_PROMPT.format(
        job_type=job_type,
        date=date,
        topic=plan.topic,
        hook=plan.hook,
        visual_prompt=plan.visual_prompt,
        on_image_text=plan.on_image_text or "(none)",
        caption=plan.caption or "(none)",
        audio_id=audio_id or "(none)",
        attempt=attempt,
        max_attempts=max_attempts,
        must_fix=must_fix or "(none)",
    )
    with trace("iPost Creator"):
        agent = Agent[CreatorContext](
            name="Creator",
            instructions=CREATOR_INSTRUCTIONS,
            model=model,
            tools=[
                retrieve_style_refs,
                generate_still_tool,
                render_story_text,
                write_caption,
                mux_reel,
            ],
        )
        await Runner.run(agent, input=task, context=context, max_turns=12)
    return CreatorResult(
        still_path=context.still_path,
        video_path=context.video_path,
        caption=context.caption,
    )
