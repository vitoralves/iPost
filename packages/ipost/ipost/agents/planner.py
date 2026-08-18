from __future__ import annotations

from agents import Agent, Runner, trace
from litellm.exceptions import RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ipost.agents.model import bedrock_model
from ipost.agents.schemas import JobType, PlanOutput, TopicSlug
from ipost.agents.templates import PLANNER_INSTRUCTIONS, PLANNER_PROMPT
from ipost.brand import apply_brand, load_brand_kit
from ipost.settings import Settings


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def run_planner(
    settings: Settings,
    *,
    job_type: JobType,
    date: str,
    topics: list[TopicSlug],
    forced_topic: TopicSlug | None = None,
    must_fix: str | None = None,
) -> PlanOutput:
    if settings.ipost_mock_bedrock:
        topic = forced_topic or topics[0]
        if job_type == "STORY":
            return PlanOutput(
                topic=topic,
                hook="Faith can be quiet and still be enough.",
                visual_prompt="9:16 photograph of mountain peaks above a sea of clouds at dawn, cool light, no people, no text",
                on_image_text="A fé também pode ser quieta.",
                caption="",
                avoid=["stock sunset cliché", "preaching"],
            )
        return PlanOutput(
            topic=topic,
            hook="Some days faith only has to carry you.",
            visual_prompt="9:16 photograph of wooden boats on a still mountain lake, early light, no people, no text",
            on_image_text="",
            caption="Some days, faith moves mountains. Other days, it simply carries you through.",
            avoid=["generic hustle caption", "off-brand neon"],
        )

    model = bedrock_model(settings)
    kit = load_brand_kit(settings)
    task = PLANNER_PROMPT.format(
        job_type=job_type,
        date=date,
        topics=", ".join(topics),
        forced_topic=forced_topic or "(none)",
        must_fix=must_fix or "(none)",
    )
    with trace("iPost Planner"):
        agent = Agent(
            name="Planner",
            instructions=apply_brand(PLANNER_INSTRUCTIONS, kit),
            model=model,
            tools=[],
            output_type=PlanOutput,
        )
        result = await Runner.run(agent, input=task, max_turns=4)
    return result.final_output_as(PlanOutput)
