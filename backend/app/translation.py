"""
Pluggable translation layer for RescueAI.

Default backend : argos-translate (fully offline, no API key, no cost).
Optional backend: Google Translate free tier via deep-translator
                  — enabled by setting TRANSLATE_BACKEND=google in .env.

Switching backends
------------------
TRANSLATE_BACKEND=argos   (default) — offline, no key needed
TRANSLATE_BACKEND=google  — uses deep-translator's GoogleTranslator (free tier,
                             requires: pip install deep-translator==1.11.4)

Public API
----------
translate_text(text: str, source_lang: str) -> str
    Translates `text` from `source_lang` to English.
    Returns the original text unchanged when:
      - source_lang is already "en"
      - translation fails for any reason  (fail-safe: never lose a report)
"""

import logging
from functools import lru_cache

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Argos-translate backend (default)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _argos_package_installed(from_code: str, to_code: str = "en") -> bool:
    """Return True if the argos package for from_code→to_code is installed."""
    try:
        from argostranslate import package as ap
        return any(
            p.from_code == from_code and p.to_code == to_code
            for p in ap.get_installed_packages()
        )
    except Exception:
        return False


def _ensure_argos_package(from_code: str, to_code: str = "en") -> bool:
    """
    Auto-download and install the argos package for from_code→to_code if missing.
    Returns True when the package is ready to use.
    """
    if _argos_package_installed(from_code, to_code):
        return True

    try:
        from argostranslate import package as ap

        logger.info("argos-translate: downloading package %s→%s …", from_code, to_code)
        ap.update_package_index()
        available = ap.get_available_packages()
        matches = [p for p in available if p.from_code == from_code and p.to_code == to_code]

        if not matches:
            logger.warning("argos-translate: no package for %s→%s", from_code, to_code)
            return False

        ap.install_from_path(matches[0].download())
        _argos_package_installed.cache_clear()
        logger.info("argos-translate: installed %s→%s", from_code, to_code)
        return True

    except Exception as exc:
        logger.warning("argos-translate: auto-install failed %s→%s: %s", from_code, to_code, exc)
        return False


def _translate_argos(text: str, source_lang: str) -> str:
    """
    Translate using argos-translate.
    Falls back to a two-hop via Spanish when a direct package isn't available.
    """
    try:
        from argostranslate import translate as at

        if _ensure_argos_package(source_lang, "en"):
            return at.translate(text, source_lang, "en")

        # Two-hop pivot via Spanish
        logger.info("argos-translate: trying two-hop %s→es→en", source_lang)
        if _ensure_argos_package(source_lang, "es") and _ensure_argos_package("es", "en"):
            return at.translate(at.translate(text, source_lang, "es"), "es", "en")

        raise RuntimeError(f"No argos-translate path found for {source_lang}→en")

    except Exception as exc:
        raise RuntimeError(f"argos-translate failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Google Translate backend (optional)
# ---------------------------------------------------------------------------

def _translate_google(text: str, source_lang: str) -> str:
    """
    Translate using deep-translator's GoogleTranslator (free tier, no key).
    Install: pip install deep-translator==1.11.4
    """
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source=source_lang, target="en").translate(text) or text
    except ImportError:
        raise RuntimeError(
            "deep-translator not installed. Run: pip install deep-translator==1.11.4"
        )
    except Exception as exc:
        raise RuntimeError(f"Google Translate failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def translate_text(text: str, source_lang: str) -> str:
    """
    Translate `text` from `source_lang` to English.

    - Returns `text` unchanged if source_lang == "en".
    - Chooses backend from TRANSLATE_BACKEND env var (default: "argos").
    - On any failure, logs a warning and returns the original text so the
      report is never silently dropped.
    """
    if source_lang == "en" or not text.strip():
        return text

    backend = getattr(settings, "translate_backend", "argos").lower().strip()

    try:
        if backend == "google":
            logger.info("Translation: Google Translate (%s→en)", source_lang)
            return _translate_google(text, source_lang)
        else:
            logger.info("Translation: argos-translate (%s→en)", source_lang)
            return _translate_argos(text, source_lang)

    except Exception as exc:
        logger.warning(
            "Translation failed (%s→en) [backend=%s]: %s — keeping original text.",
            source_lang, backend, exc,
        )
        return text
