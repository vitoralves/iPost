from __future__ import annotations

import math
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ipost.mux import STORY_HEIGHT, STORY_WIDTH


def write_placeholder_still(path: Path, text: str = "iPost") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (STORY_WIDTH, STORY_HEIGHT), (18, 18, 18))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=96)
    except TypeError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (STORY_WIDTH - (bbox[2] - bbox[0])) / 2
    y = (STORY_HEIGHT - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, fill=(245, 240, 232), font=font)
    image.save(path, format="JPEG", quality=92)
    return path


def write_tone_wav(path: Path, *, seconds: float = 8, hz: float = 220) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    amplitude = 8000
    n_frames = int(sample_rate * seconds)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(n_frames):
            value = int(amplitude * math.sin(2 * math.pi * hz * (index / sample_rate)))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
        wav.writeframes(frames)
    return path
