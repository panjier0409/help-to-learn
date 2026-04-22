"""
TTS service using wangwangit/tts worker.
Endpoint: POST /v1/audio/speech
Used for article/text materials that have no original audio.
"""
import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-JennyNeural"


def synthesize(
    text: str,
    output_path: str,
    worker_url: str,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
) -> str:
    """
    Convert text to speech and save as mp3.
    Returns the output_path.
    """
    url = f"{worker_url.rstrip('/')}/v1/audio/speech"

    payload = {
        "input": text,
        "voice": voice,
        "speed": speed,
        "pitch": "0",
        "style": "general",
    }

    logger.info(f"Calling TTS API for {len(text)} chars: {url}")
    response = httpx.post(url, json=payload, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(f"TTS API error {response.status_code}: {response.text}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    logger.info(f"TTS audio saved: {output_path}")
    return output_path
