from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

LEGAL_SUFFIX_TOKENS = {
    "llc", "l.l.c", "fze", "fz", "fzco", "fzc", "dmcc", "wll", "w.l.l",
    "llp", "ltd", "inc", "co", "company", "corp", "corporation",
    "est", "establishment", "trading", "group", "holding", "holdings",
    "industries", "industry", "enterprises", "enterprise",
    "international", "intl", "contracting", "services", "pjsc", "psc",
    "pvt", "private", "limited", "sole", "proprietorship", "gen",
    "general", "trade",
}


def normalize_name(name: str) -> str:
    lowered = (name or "").lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    # Collapse spaced-out abbreviations like "f z e" -> "fze" before suffix filtering.
    lowered = re.sub(r"\b(?:[a-z](?:\s+|$)){2,}", lambda m: m.group(0).replace(" ", ""), lowered)
    tokens = [t for t in lowered.split() if t not in LEGAL_SUFFIX_TOKENS]
    return " ".join(tokens).strip()


def similarity(name_a: str, name_b: str) -> float:
    norm_a, norm_b = normalize_name(name_a), normalize_name(name_b)
    if not norm_a or not norm_b:
        return 0.0

    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()

    set_a, set_b = set(norm_a.split()), set(norm_b.split())
    jaccard = len(set_a & set_b) / len(set_a | set_b) if (set_a and set_b) else 0.0

    return 0.6 * ratio + 0.4 * jaccard


def pick_best_match(
    target_name: str,
    candidates: list[dict[str, Any]],
    threshold: float,
) -> tuple[dict[str, Any] | None, float]:
    """Return the highest-scoring candidate that clears `threshold`, else (None, best_score)."""
    scored = sorted(
        (
            (candidate, similarity(target_name, candidate.get("company_name") or ""))
            for candidate in candidates
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    if not scored:
        return None, 0.0

    best_candidate, best_score = scored[0]
    if best_score >= threshold:
        return best_candidate, best_score
    return None, best_score
