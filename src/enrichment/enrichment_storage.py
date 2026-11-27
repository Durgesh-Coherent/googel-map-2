from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_COLUMNS = [
    "native_id",
    "company_name",
    "city",
    "state",
    "country",
    "website_found",
    "maps_url",
    "phone",
    "match_status",
    "matched_name",
    "match_score",
    "scraped_at",
]

DONE_STATUSES = {"matched", "not_found"}


class EnrichmentStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def close(self) -> None:
        self.conn.close()

    def init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS enrichment_results (
                native_id TEXT PRIMARY KEY,
                company_name TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                website_found TEXT,
                maps_url TEXT,
                phone TEXT,
                match_status TEXT,
                matched_name TEXT,
                match_score REAL,
                scraped_at TEXT
            );
            """
        )
        self.conn.commit()

    def processed_native_ids(self) -> set[str]:
        rows = self.conn.execute(
            "SELECT native_id FROM enrichment_results WHERE match_status IN ('matched', 'not_found')"
        ).fetchall()
        return {row["native_id"] for row in rows}

    def save_result(self, result: dict[str, Any]) -> None:
        result = dict(result)
        result.setdefault("scraped_at", utc_now())
        self.conn.execute(
            """
            INSERT INTO enrichment_results (
                native_id, company_name, city, state, country,
                website_found, maps_url, phone, match_status,
                matched_name, match_score, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(native_id) DO UPDATE SET
                company_name = excluded.company_name,
                city = excluded.city,
                state = excluded.state,
                country = excluded.country,
                website_found = excluded.website_found,
                maps_url = excluded.maps_url,
                phone = excluded.phone,
                match_status = excluded.match_status,
                matched_name = excluded.matched_name,
                match_score = excluded.match_score,
                scraped_at = excluded.scraped_at
            """,
            (
                result.get("native_id"),
                result.get("company_name"),
                result.get("city"),
                result.get("state"),
                result.get("country"),
                result.get("website_found") or "",
                result.get("maps_url") or "",
                result.get("phone") or "",
                result.get("match_status"),
                result.get("matched_name") or "",
                result.get("match_score"),
                result.get("scraped_at"),
            ),
        )
        self.conn.commit()

    def counts(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT match_status, COUNT(*) AS c FROM enrichment_results GROUP BY match_status"
        ).fetchall()
        return {str(row["match_status"]): int(row["c"]) for row in rows}

    def export_csv(self, output_csv_path: Path) -> None:
        rows = self.conn.execute(
            f"SELECT {', '.join(RESULT_COLUMNS)} FROM enrichment_results ORDER BY scraped_at"
        ).fetchall()
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with output_csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row[column] for column in RESULT_COLUMNS})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
