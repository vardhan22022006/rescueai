"""
Rule-based NLP extraction for disaster reports.

Extracts structured fields from free-text using regex and keyword matching.
Intentionally kept simple and fast — no LLM calls, fully explainable.

To upgrade to LLM-based extraction later, swap out extract_report_fields()
while keeping the same return signature.
"""

import re
from typing import Optional

from app.models import DisasterTypeEnum


# ---------------------------------------------------------------------------
# Keyword maps
# ---------------------------------------------------------------------------

# Each disaster type maps to trigger keywords (lowercase).
# Checked in priority order: earthquake > cyclone > flood > other.
DISASTER_KEYWORDS: dict[DisasterTypeEnum, list[str]] = {
    DisasterTypeEnum.earthquake: [
        "earthquake", "quake", "tremor", "shaking", "shook",
        "seismic", "aftershock", "magnitude",
    ],
    DisasterTypeEnum.cyclone: [
        "cyclone", "hurricane", "typhoon", "storm", "tornado",
        "gale", "wind storm", "windstorm",
    ],
    DisasterTypeEnum.flood: [
        "flood", "flooding", "flooded", "water", "inundated",
        "submerged", "overflow", "river", "rain", "deluge",
    ],
}

VULNERABLE_KEYWORD_MAP: dict[str, list[str]] = {
    "elderly":  ["elderly", "old man", "old woman", "old people", "senior", "aged"],
    "child":    ["child", "children", "baby", "infant", "toddler", "kid", "kids", "minor"],
    "pregnant": ["pregnant", "pregnancy", "expecting", "maternity"],
    "disabled": ["disabled", "disability", "wheelchair", "paralysed", "paralyzed",
                 "handicapped", "impaired"],
}

# Words that indicate a nearby number describes people affected.
PEOPLE_CONTEXT_WORDS = [
    "people", "person", "persons", "individual", "individuals",
    "family", "families", "household", "households",
    "us", "we", "our", "survivors", "victims", "residents",
    "men", "women", "adults", "children", "members",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_disaster_type(text: str) -> DisasterTypeEnum:
    """
    Return the most likely disaster type by scanning for keyword matches.
    Priority: earthquake → cyclone → flood → other.
    """
    lower = text.lower()
    for disaster_type, keywords in DISASTER_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return disaster_type
    return DisasterTypeEnum.other


def _extract_num_people(text: str) -> Optional[int]:
    """
    Look for integers that appear near people-context words (within ±60 chars).
    Returns the largest qualifying number found, or None.
    """
    lower = text.lower()

    context_pattern = (
        r"\b(?:" + "|".join(re.escape(w) for w in PEOPLE_CONTEXT_WORDS) + r")\b"
    )

    numbers = [(int(m.group()), m.start()) for m in re.finditer(r"\b(\d+)\b", lower)]
    context_positions = [m.start() for m in re.finditer(context_pattern, lower)]

    if not numbers or not context_positions:
        return None

    WINDOW = 60
    qualifying = []
    for value, num_pos in numbers:
        if value == 0:
            continue
        for ctx_pos in context_positions:
            if abs(num_pos - ctx_pos) <= WINDOW:
                qualifying.append(value)
                break

    return max(qualifying) if qualifying else None


def _extract_vulnerable_flags(text: str) -> list[str]:
    """Return a de-duplicated list of vulnerability categories present in text."""
    lower = text.lower()
    return [
        category
        for category, keywords in VULNERABLE_KEYWORD_MAP.items()
        if any(kw in lower for kw in keywords)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_report_fields(text: str) -> dict:
    """
    Extract structured fields from a plain-text disaster report.

    Args:
        text: The (translated) report text to analyse.

    Returns:
        {
            "disaster_type":    DisasterTypeEnum,
            "num_people":       int | None,
            "vulnerable_flags": list[str],
        }

    Swap this function out for an LLM call when higher accuracy is needed —
    the return shape is the stable contract.
    """
    return {
        "disaster_type":    _detect_disaster_type(text),
        "num_people":       _extract_num_people(text),
        "vulnerable_flags": _extract_vulnerable_flags(text),
    }
