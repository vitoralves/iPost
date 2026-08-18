from __future__ import annotations

import base64
import json
import random
from io import BytesIO
from pathlib import Path

from ipost.fixtures import write_placeholder_still
from ipost.mux import STORY_HEIGHT, STORY_WIDTH
from ipost.settings import Settings

NEGATIVE_PROMPT = (
    "people, faces, hands, logos, watermarks, UI chrome, frames, borders, "
    "readable text, captions, subtitles, watermarks"
)


class StillError(RuntimeError):
    pass


CanvasError = StillError


def _resize_to_story(data: bytes, destination: Path) -> Path:
    from PIL import Image

    destination.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(BytesIO(data)).convert("RGB")
    image = image.resize((STORY_WIDTH, STORY_HEIGHT))
    image.save(destination, format="JPEG", quality=92)
    return destination


def generate_still(settings: Settings, prompt: str, destination: Path) -> Path:
    if settings.ipost_mock_bedrock:
        return write_placeholder_still(destination, prompt[:48] or "iPost")

    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
    body = {
        "prompt": prompt[:10000],
        "mode": "text-to-image",
        "aspect_ratio": "9:16",
        "output_format": "jpeg",
        "negative_prompt": NEGATIVE_PROMPT,
        "seed": random.randint(0, 4294967294),
    }
    response = client.invoke_model(
        modelId=settings.bedrock_image_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(response["body"].read())
    reasons = payload.get("finish_reasons") or []
    blocked = [item for item in reasons if item]
    if blocked:
        raise StillError(f"Image model filtered the request: {blocked[0]}")
    images = payload.get("images") or []
    if not images:
        raise StillError("Image model returned no images")
    first = images[0]
    raw = first.get("base64") if isinstance(first, dict) else first
    if not raw:
        raise StillError("Image model returned an empty image")
    return _resize_to_story(base64.b64decode(raw), destination)
