"""Automatic fallback translator for English headlines to Russian."""

import json
import time
from typing import Any
import httpx

from pulse.config import get_config
from pulse.logging import get_logger

logger = get_logger("pulse.digest.translator")

def is_english(text: str) -> bool:
    """Check if text contains primarily English ASCII characters."""
    if not text:
        return False
    ascii_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return ascii_count > len(text) * 0.3


def translate_to_russian(text: str) -> str:
    """Translate an English headline into Russian using Gemini or fallback HTTP API."""
    if not is_english(text):
        return text

    cfg = get_config().settings
    api_key = cfg.GEMINI_API_KEY

    prompt = f"Переведи заголовок новости на красивый русский язык. Верни ТОЛЬКО переведенный текст без кавычек и сносок:\n{text}"

    for model in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            resp = httpx.post(
                endpoint,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=15.0,
            )
            if resp.status_code == 200:
                translated = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if translated and not is_english(translated):
                    return translated
        except Exception:
            pass

    return text
