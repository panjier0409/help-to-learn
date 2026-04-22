"""
AnkiConnect HTTP API integration.
Requires local Anki to be running with the AnkiConnect plugin installed.
Default URL: http://localhost:8765
"""
import httpx
import base64
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)
ANKI_VERSION = 6


def _request(url: str, action: str, **params) -> dict:
    payload = {"action": action, "version": ANKI_VERSION, "params": params}
    try:
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("error"):
            raise RuntimeError(f"AnkiConnect error: {result['error']}")
        return result
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot connect to Anki. Make sure Anki is running with AnkiConnect plugin installed."
        )


def ensure_deck(url: str, deck_name: str) -> None:
    """Create deck if it doesn't exist."""
    _request(url, "createDeck", deck=deck_name)


def store_media_file(url: str, filename: str, file_path: str) -> None:
    """Upload an audio file to Anki's media directory."""
    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    _request(url, "storeMediaFile", filename=filename, data=data)


def add_note(
    url: str,
    deck_name: str,
    front_text: str,
    back_text: str,
    audio_filename: str,
    translation: Optional[str] = None,
    model_name: str = "Basic",
    share_url: Optional[str] = None,
) -> int:
    """
    Add a note to Anki deck.
    Front: transcribed text (+ optional translation + share link)
    Back: audio player + full text (+ share link)
    Returns the Anki note ID.
    """
    ensure_deck(url, deck_name)

    front = front_text
    if translation:
        front += f"<br><small style='color:#666'>{translation}</small>"
    if share_url:
        front += f"<br><small><a href='{share_url}' style='color:#4a9eff'>🔗 View online</a></small>"

    back = f"[sound:{audio_filename}]<br><br>{back_text}"
    if translation:
        back += f"<br><small style='color:#666'>{translation}</small>"
    if share_url:
        back += f"<br><small><a href='{share_url}' style='color:#4a9eff'>🔗 View online</a></small>"

    result = _request(
        url,
        "addNote",
        note={
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {"正面": front, "背面": back},
            "options": {"allowDuplicate": False},
        },
    )
    note_id = result.get("result")
    if note_id is None:
        raise RuntimeError("AnkiConnect addNote returned null (duplicate or error)")
    return note_id


def check_connection(url: str) -> bool:
    """Returns True if AnkiConnect is reachable."""
    try:
        _request(url, "version")
        return True
    except Exception:
        return False
