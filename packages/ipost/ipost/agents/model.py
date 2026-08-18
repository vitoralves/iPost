from __future__ import annotations

import os

from ipost.settings import Settings


def bedrock_model(settings: Settings):
    from agents.extensions.models.litellm_model import LitellmModel

    os.environ["AWS_REGION_NAME"] = settings.bedrock_region
    return LitellmModel(model=f"bedrock/{settings.bedrock_model_id}")
