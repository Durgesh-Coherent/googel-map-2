from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dedupe import merge_pipe_values, name_address_key, normalize_maps_url, normalize_phone
from .keyword_loader import KeywordRow


COMPANY_COLUMNS = [
    "company_name",
    "full_address",
    "city",
    "country",
    "phone",
    "website",
    "category",
    "description",
    "rating",
    "review_count",
    "maps_url",
    "place_id",
    "latitude",
    "longitude",
    "source_keywords",
    "base_keywords",
    "entities",
    "scraped_at",
    "updated_at",
]

STATUS_COLUMNS = [
    "keyword",
    "entity",
    "country",
    "city",
    "status",
    "companies_found",
    "error_message",
    "scraped_at",
]


class ScraperStorage:
    def __init__(self, db_path: Path, output_dir: Path) -> None:
        self.db_path = db_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def close(self) -> None:
        self.conn.close()

    def init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                full_address TEXT,
                city TEXT,
                country TEXT,
                phone TEXT,
                phone_key TEXT,
                website TEXT,
                category TEXT,
                description TEXT,
                rating TEXT,
                review_count TEXT,
                maps_url TEXT,
                maps_url_key TEXT,
                place_id TEXT,
                latitude TEXT,
                longitude TEXT,
                name_address_key TEXT,
                source_keywords TEXT,
                base_keywords TEXT,
                entities TEXT,
                scraped_at TEXT,
                updated_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_companies_maps_url_key ON companies(maps_url_key);
            CREATE INDEX IF NOT EXISTS idx_companies_phone_key ON companies(phone_key);
            CREATE INDEX IF NOT EXISTS idx_companies_name_address_key ON companies(name_address_key);

            CREATE TABLE IF NOT EXISTS keyword_status (
                keyword TEXT PRIMARY KEY,
                entity TEXT,
                country TEXT,
                city TEXT,
                status TEXT,
                companies_found INTEGER DEFAULT 0,
                error_message TEXT,
                scraped_at TEXT
            );
            """
        )
        self.ensure_column("companies", "description", "TEXT")
        self.conn.commit()

    def ensure_column(self, table: str, column: str, column_type: str) -> None:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row["name"] for row in rows}
        if column not in existing:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def completed_keywords(self) -> set[str]:
        rows = self.conn.execute(
            "SELECT keyword FROM keyword_status WHERE status = 'success'"
        ).fetchall()
        return {row["keyword"] for row in rows}

    def has_company_url(self, maps_url: str | None) -> bool:
        key = normalize_maps_url(maps_url)
        if not key:
            return False
        row = self.conn.execute(
            "SELECT id FROM companies WHERE maps_url_key = ? LIMIT 1", (key,)
        ).fetchone()
        return row is not None

    def upsert_company(self, company: dict[str, Any], keyword_row: KeywordRow) -> tuple[int, bool]:
        now = utc_now()
        company = dict(company)
        company.setdefault("scraped_at", now)
        company["updated_at"] = now

        maps_url_key = normalize_maps_url(company.get("maps_url"))
        phone_key = normalize_phone(company.get("phone"))
        name_key = name_address_key(company.get("company_name"), company.get("full_address"))
        existing = self.find_existing(maps_url_key, phone_key, name_key)

        if existing:
            self.conn.execute(
                """
                UPDATE companies SET
                    phone = COALESCE(NULLIF(phone, ''), ?),
                    phone_key = COALESCE(NULLIF(phone_key, ''), ?),
                    website = COALESCE(NULLIF(website, ''), ?),
                    category = COALESCE(NULLIF(category, ''), ?),
                    description = COALESCE(NULLIF(description, ''), ?),
                    rating = COALESCE(NULLIF(rating, ''), ?),
                    review_count = COALESCE(NULLIF(review_count, ''), ?),
                    place_id = COALESCE(NULLIF(place_id, ''), ?),
                    latitude = COALESCE(NULLIF(latitude, ''), ?),
                    longitude = COALESCE(NULLIF(longitude, ''), ?),
                    source_keywords = ?,
                    base_keywords = ?,
                    entities = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    company.get("phone") or "",
                    phone_key,
                    company.get("website") or "",
                    company.get("category") or "",
                    company.get("description") or "",
                    company.get("rating") or "",
                    company.get("review_count") or "",
                    company.get("place_id") or "",
                    company.get("latitude") or "",
                    company.get("longitude") or "",
                    merge_pipe_values(existing["source_keywords"], keyword_row.keyword),
                    merge_pipe_values(existing["base_keywords"], keyword_row.base_keyword),
                    merge_pipe_values(existing["entities"], keyword_row.entity),
                    now,
                    existing["id"],
                ),
            )
            self.conn.commit()
            return int(existing["id"]), False

        cursor = self.conn.execute(
            """
            INSERT INTO companies (
                company_name, full_address, city, country, phone, phone_key, website,
                category, description, rating, review_count, maps_url, maps_url_key, place_id,
                latitude, longitude, name_address_key, source_keywords, base_keywords,
                entities, scraped_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company.get("company_name") or "",
                company.get("full_address") or "",
                company.get("city") or keyword_row.city,
                company.get("country") or keyword_row.country,
                company.get("phone") or "",
                phone_key,
                company.get("website") or "",
                company.get("category") or "",
                company.get("description") or "",
                company.get("rating") or "",
                company.get("review_count") or "",
                company.get("maps_url") or "",
                maps_url_key,
                company.get("place_id") or "",
                company.get("latitude") or "",
                company.get("longitude") or "",
                name_key,
                keyword_row.keyword,
                keyword_row.base_keyword,
                keyword_row.entity,
                company.get("scraped_at") or now,
                now,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid), True

    def find_existing(
        self, maps_url_key: str, phone_key: str, name_key: str
    ) -> sqlite3.Row | None:
        checks = [
            ("maps_url_key", maps_url_key),
            ("phone_key", phone_key),
            ("name_address_key", name_key),
        ]
        for column, value in checks:
            if not value:
                continue
            row = self.conn.execute(
                f"SELECT * FROM companies WHERE {column} = ? LIMIT 1", (value,)
            ).fetchone()
            if row:
                return row
        return None

    def update_keyword_status(
        self,
        keyword_row: KeywordRow,
        status: str,
        companies_found: int = 0,
        error_message: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO keyword_status (
                keyword, entity, country, city, status, companies_found, error_message, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                entity = excluded.entity,
                country = excluded.country,
                city = excluded.city,
                status = excluded.status,
                companies_found = excluded.companies_found,
                error_message = excluded.error_message,
                scraped_at = excluded.scraped_at
            """,
            (
                keyword_row.keyword,
                keyword_row.entity,
                keyword_row.country,
                keyword_row.city,
                status,
                companies_found,
                error_message[:1000],
                utc_now(),
            ),
        )
        self.conn.commit()

    def company_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM companies").fetchone()
        return int(row["c"] if row else 0)

    def status_counts(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS c FROM keyword_status GROUP BY status"
        ).fetchall()
        return {str(row["status"]): int(row["c"]) for row in rows}

    def export_all(self) -> None:
        self.export_companies_csv()
        self.export_companies_jsonl()
        self.export_keyword_status_csv()

    def export_companies_csv(self) -> None:
        rows = self.conn.execute(
            f"SELECT {', '.join(COMPANY_COLUMNS)} FROM companies ORDER BY id"
        ).fetchall()
        write_csv(self.output_dir / "companies.csv", COMPANY_COLUMNS, rows)

    def export_companies_jsonl(self) -> None:
        rows = self.conn.execute(
            f"SELECT {', '.join(COMPANY_COLUMNS)} FROM companies ORDER BY id"
        ).fetchall()
        with (self.output_dir / "companies.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")

    def export_keyword_status_csv(self) -> None:
        rows = self.conn.execute(
            f"SELECT {', '.join(STATUS_COLUMNS)} FROM keyword_status ORDER BY scraped_at, keyword"
        ).fetchall()
        write_csv(self.output_dir / "keyword_status.csv", STATUS_COLUMNS, rows)


def write_csv(path: Path, columns: list[str], rows: list[sqlite3.Row]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
