"""Automatic fallback translator for English headlines to Russian."""

import json
import urllib.parse
import urllib.request
from pulse.logging import get_logger

logger = get_logger("pulse.digest.translator")

def is_english(text: str) -> bool:
    """Check if text contains primarily English ASCII characters."""
    if not text:
        return False
    ascii_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return ascii_count > len(text) * 0.3


def translate_to_russian(text: str) -> str:
    """Translate an English headline into Russian instantly using Google Translate API with fallback."""
    if not text or not is_english(text):
        return text

    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ru&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in res[0] if part[0]]).strip()
            if translated and not is_english(translated):
                return translated
    except Exception as e:
        logger.warning("translation_fallback_failed", error=str(e), text=text)

    return text
