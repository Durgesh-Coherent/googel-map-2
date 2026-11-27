from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = {"native_id", "company_name", "website", "city", "state", "country"}


@dataclass(frozen=True)
class CompanyLookupRow:
    native_id: str
    company_name: str
    city: str
    state: str
    country: str


def load_companies_missing_website(input_path: Path) -> list[CompanyLookupRow]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    rows: list[CompanyLookupRow] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")

        for row in reader:
            website = (row.get("website") or "").strip()
            if website:
                continue
            company_name = (row.get("company_name") or "").strip()
            native_id = (row.get("native_id") or "").strip()
            if not company_name or not native_id:
                continue
            rows.append(
                CompanyLookupRow(
                    native_id=native_id,
                    company_name=company_name,
                    city=(row.get("city") or "").strip(),
                    state=(row.get("state") or "").strip(),
                    country=(row.get("country") or "").strip(),
                )
            )
    return rows
