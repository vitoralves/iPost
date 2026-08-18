from __future__ import annotations

from agents import Agent, Runner, trace
from litellm.exceptions import RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ipost.agents.model import bedrock_model
from ipost.agents.schemas import CriticSubscores, CritiqueOutput, JobType, PlanOutput
from ipost.agents.templates import CRITIC_INSTRUCTIONS, CRITIC_PROMPT
from ipost.brand import apply_brand, load_brand_kit
from ipost.settings import Settings


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def run_critic(
    settings: Settings,
    *,
    job_type: JobType,
    plan: PlanOutput,
    still_path: str,
    caption: str,
    attempt: int,
    max_attempts: int,
) -> CritiqueOutput:
    if settings.ipost_mock_bedrock:
        if job_type == "STORY":
            return CritiqueOutput(
                score=8.4,
                hard_fail=False,
                must_fix=None,
                subscores=CriticSubscores(
                    brand=8.2, clarity=8.0, spec=8.6, originality=7.4, safety=9.1
                ),
            )
        if attempt < max_attempts:
            return CritiqueOutput(
                score=4.8,
                hard_fail=False,
                must_fix="Text too small; off-brand color.",
                subscores=CriticSubscores(
                    brand=4.5, clarity=5.8, spec=6.0, originality=5.1, safety=8.5
                ),
            )
        return CritiqueOutput(
            score=5.2,
            hard_fail=False,
            must_fix="Text too small; off-brand color.",
            subscores=CriticSubscores(
                brand=4.5, clarity=5.8, spec=6.0, originality=5.1, safety=8.5
            ),
        )

    model = bedrock_model(settings)
    kit = load_brand_kit(settings)
    task = apply_brand(CRITIC_PROMPT, kit).format(
        job_type=job_type,
        topic=plan.topic,
        hook=plan.hook,
        on_image_text=plan.on_image_text or "(none)",
        caption=caption or "(none)",
        still_path=still_path,
        attempt=attempt,
        max_attempts=max_attempts,
    )
    with trace("iPost Critic"):
        agent = Agent(
            name="Critic",
            instructions=CRITIC_INSTRUCTIONS,
            model=model,
            tools=[],
            output_type=CritiqueOutput,
        )
        result = await Runner.run(agent, input=task, max_turns=4)
    return result.final_output_as(CritiqueOutput)
