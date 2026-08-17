from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

STORY_WIDTH = 1080
STORY_HEIGHT = 1920


class MuxError(RuntimeError):
    pass


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise MuxError("ffmpeg is not installed. On macOS run: brew install ffmpeg")
    return path


def mux_still_with_audio(
    still_path: Path,
    audio_path: Path,
    output_path: Path,
    *,
    max_seconds: int = 20,
) -> Path:
    ffmpeg = require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        "format=yuv420p"
    )
    command = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(still_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-t",
        str(max_seconds),
        "-vf",
        vf,
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MuxError(result.stderr.strip() or "ffmpeg failed")
    return output_path
