from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = {"keyword", "base_keyword", "entity", "country", "city"}

COUNTRY_FILES = {
    "uae": "google_maps_keywords_uae.csv",
    "saudi_arabia": "google_maps_keywords_saudi_arabia.csv",
    "qatar": "google_maps_keywords_qatar.csv",
    "israel": "google_maps_keywords_israel.csv",
    "egypt": "keywords/egypt/google_maps_keywords_egypt.csv",
    "south_africa": "keywords/south_africa/google_maps_keywords_south_africa.csv",
    "nigeria": "keywords/nigeria/google_maps_keywords_nigeria.csv",
    "algeria": "keywords/algeria/google_maps_keywords_algeria.csv",
    "ethiopia": "keywords/ethiopia/google_maps_keywords_ethiopia.csv",
    "tanzania": "keywords/tanzania/google_maps_keywords_tanzania.csv",
    "cote_divoire": "keywords/cote_divoire/google_maps_keywords_cote_divoire.csv",
    "mali": "keywords/mali/google_maps_keywords_mali.csv",
    "ghana": "keywords/ghana/google_maps_keywords_ghana.csv",
    "gambia": "keywords/gambia/google_maps_keywords_gambia.csv",
    "uganda": "keywords/uganda/google_maps_keywords_uganda.csv",
    "guinea_bissau": "keywords/guinea_bissau/google_maps_keywords_guinea_bissau.csv",
    "sudan": "keywords/sudan/google_maps_keywords_sudan.csv",
    "all_countries": "google_maps_keywords_all_countries.csv",
}

COUNTRY_LABELS = {
    "uae": "UAE",
    "saudi_arabia": "Saudi Arabia",
    "qatar": "Qatar",
    "israel": "Israel",
    "egypt": "Egypt",
    "south_africa": "South Africa",
    "nigeria": "Nigeria",
    "algeria": "Algeria",
    "ethiopia": "Ethiopia",
    "tanzania": "Tanzania",
    "cote_divoire": "Cote d'Ivoire",
    "mali": "Mali",
    "ghana": "Ghana",
    "gambia": "The Gambia",
    "uganda": "Uganda",
    "guinea_bissau": "Guinea-Bissau",
    "sudan": "Sudan",
    "all_countries": "All Countries",
}


@dataclass(frozen=True)
class KeywordRow:
    keyword: str
    base_keyword: str
    entity: str
    country: str
    city: str
    row_number: int
    priority: str = ""


def slugify_country(country: str) -> str:
    return country.strip().lower().replace(" ", "_").replace("-", "_")


def prompt_country() -> str:
    print("Which country do you want to scrape?")
    options = list(COUNTRY_FILES.keys())
    for idx, key in enumerate(options, start=1):
        print(f"{idx}) {COUNTRY_LABELS[key]}")

    while True:
        choice = input("Enter number or country name: ").strip().lower()
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
        normalized = slugify_country(choice)
        if normalized in COUNTRY_FILES:
            return normalized
        if choice in {"saudi", "ksa", "saudi arabia"}:
            return "saudi_arabia"
        if choice in {"all", "all countries"}:
            return "all_countries"
        print("Invalid choice. Please try again.")


def resolve_input_file(workspace: Path, country_slug: str, explicit_input: str | None) -> Path:
    if explicit_input:
        return Path(explicit_input).expanduser().resolve()
    filename = COUNTRY_FILES.get(country_slug)
    if not filename:
        raise ValueError(f"Unsupported country: {country_slug}")
    return workspace / filename


def load_keywords(
    input_path: Path,
    country_filter: str | None = None,
    entity_filter: str | None = None,
    limit_keywords: int | None = None,
    start_from: str | None = None,
) -> list[KeywordRow]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    rows: list[KeywordRow] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")

        for row_number, row in enumerate(reader, start=2):
            keyword = (row.get("keyword") or "").strip()
            if not keyword:
                continue
            item = KeywordRow(
                keyword=keyword,
                base_keyword=(row.get("base_keyword") or "").strip(),
                entity=(row.get("entity") or "").strip(),
                country=(row.get("country") or "").strip(),
                city=(row.get("city") or "").strip(),
                row_number=row_number,
                priority=(row.get("priority") or "").strip(),
            )
            if country_filter and country_filter.lower() not in {
                item.country.lower(),
                slugify_country(item.country),
            }:
                continue
            if entity_filter and item.entity.lower() != entity_filter.lower():
                continue
            rows.append(item)

    rows.sort(key=_priority_sort_key)
    rows = apply_start_from(rows, start_from)
    if limit_keywords is not None:
        rows = rows[: max(0, limit_keywords)]
    return rows


def _priority_sort_key(row: "KeywordRow") -> int:
    try:
        return int(row.priority)
    except (TypeError, ValueError):
        return 10**9


def apply_start_from(rows: list[KeywordRow], start_from: str | None) -> list[KeywordRow]:
    if not start_from:
        return rows

    value = start_from.strip()
    if value.isdigit():
        index = max(0, int(value) - 1)
        return rows[index:]

    lowered = value.lower()
    for idx, row in enumerate(rows):
        if row.keyword.lower() == lowered:
            return rows[idx:]
    return rows


def without_completed(rows: Iterable[KeywordRow], completed_keywords: set[str]) -> list[KeywordRow]:
    completed = {keyword.lower() for keyword in completed_keywords}
    return [row for row in rows if row.keyword.lower() not in completed]
