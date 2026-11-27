"""Backfill the `category` column for companies already in a scraper DB.

The main scraper's category selector misses several Google Maps DOM variants,
leaving `category` blank for most rows in some countries (India 98%, Japan 93%,
South Korea 91%, UAE 90%). This script re-opens each company's stored maps_url
and extracts the category only -- no keyword searching, no re-scraping of other
fields.

Two modes:

  --probe N   Open N place pages and dump every short text node near the H1,
              with its tag/class/jsaction. Use this first to confirm which
              selector actually carries the category. Writes nothing.

  (default)   Open every blank-category row, extract the category, write it
              back to the companies table. Resumable via its own progress
              table (`category_backfill`).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.logger import setup_logger
from src.maps_scraper import GoogleMapsScraper, add_english_params, random_delay
from src.storage import ScraperStorage


# Ordered most-specific first. Each is tried in the page; first non-empty wins.
CATEGORY_SELECTORS = [
    "button[jsaction*='pane.rating.category']",
    "button.DkEaL",
    "button[jsaction*='category']",
    ".skqShb button.DkEaL",
    "div.LBgpqf button.DkEaL",
    ".DkEaL",
    "button[aria-label*='Category']",
]

# Text that is never a business category, even if it lands in a matched node.
CATEGORY_BLOCKLIST = {
    "directions", "save", "nearby", "send to phone", "share", "overview",
    "reviews", "about", "photos", "updates", "menu", "order online",
    "website", "call", "claim this business", "suggest an edit",
    "open", "closed", "open 24 hours",
}

EXTRACT_JS = """
(selectors) => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  for (const sel of selectors) {
    let nodes;
    try { nodes = document.querySelectorAll(sel); } catch (e) { continue; }
    for (const node of nodes) {
      const t = clean(node.textContent);
      if (t && t.length <= 70) return { category: t, method: sel };
    }
  }
  return { category: '', method: '' };
}
"""

PROBE_JS = """
() => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const panel = document.querySelector("div[role='main']") || document.body;
  const out = [];
  let count = 0;
  for (const el of panel.querySelectorAll('button, span, div')) {
    if (el.children.length > 0) continue;
    const t = clean(el.textContent);
    if (!t || t.length > 60) continue;
    out.push({
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string') ? el.className : '',
      jsaction: (el.getAttribute('jsaction') || '').slice(0, 40),
      parentCls: (el.parentElement && typeof el.parentElement.className === 'string')
        ? el.parentElement.className : '',
      text: t,
    });
    if (++count >= 45) break;
  }
  return { h1: clean((document.querySelector('h1') || {}).textContent), nodes: out };
}
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill blank `category` values by re-opening stored maps_urls."
    )
    p.add_argument("--db", required=True, help="Path to the scraper SQLite DB, e.g. output/india/india.db")
    p.add_argument("--config", default="./config.yaml", help="Config YAML (browser settings only).")
    p.add_argument("--limit", type=int, help="Only process the first N pending rows.")
    p.add_argument("--probe", type=int, help="Probe mode: dump DOM candidates for N pages, write nothing.")
    p.add_argument("--retry-empty", action="store_true",
                   help="Also retry rows previously recorded as no_category.")
    p.add_argument("--headless", action="store_true", help="Run headless (breaks manual CAPTCHA solving).")
    p.add_argument("--no-headless", action="store_true", help="Force a visible browser window.")
    p.add_argument("--no-export", action="store_true",
                   help="Skip rewriting companies.csv / companies.jsonl at the end.")
    return p.parse_args()


def load_config(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    if args.headless:
        config["headless"] = True
    if args.no_headless:
        config["headless"] = False
    config.setdefault("headless", False)
    return config


def init_progress_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_backfill (
            company_id INTEGER PRIMARY KEY,
            maps_url   TEXT,
            category   TEXT,
            method     TEXT,
            status     TEXT,
            checked_at TEXT
        )
        """
    )
    conn.commit()


def pending_rows(conn: sqlite3.Connection, retry_empty: bool) -> list[sqlite3.Row]:
    if retry_empty:
        retry_clause = "AND (b.company_id IS NULL OR b.status = 'no_category')"
    else:
        retry_clause = "AND b.company_id IS NULL"
    sql = f"""
        SELECT c.id, c.company_name, c.maps_url
        FROM companies c
        LEFT JOIN category_backfill b ON b.company_id = c.id
        WHERE TRIM(COALESCE(c.category, '')) = ''
          AND TRIM(COALESCE(c.maps_url, '')) <> ''
          {retry_clause}
        ORDER BY c.id
    """
    return conn.execute(sql).fetchall()


def clean_category(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    # Google sometimes renders "Manufacturer - Floor 1" style suffixes.
    text = text.split("·")[0].strip()
    if not text or text.lower() in CATEGORY_BLOCKLIST:
        return ""
    if len(text) < 3:
        return ""
    return text


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_place_page(scraper: GoogleMapsScraper, maps_url: str) -> None:
    page = scraper.require_page()
    page.goto(add_english_params(maps_url), wait_until="domcontentloaded")
    scraper.handle_consent()
    scraper.wait_for_place_panel()


def run_probe(scraper: GoogleMapsScraper, conn: sqlite3.Connection, count: int, logger: Any) -> None:
    rows = pending_rows(conn, retry_empty=True)[:count]
    logger.info("PROBE MODE: inspecting %s place pages, writing nothing.", len(rows))
    page = scraper.require_page()
    for idx, row in enumerate(rows, start=1):
        logger.info("=" * 72)
        logger.info("[%s/%s] %s", idx, len(rows), row["company_name"])
        open_place_page(scraper, row["maps_url"])
        page.wait_for_timeout(900)

        hit = page.evaluate(EXTRACT_JS, CATEGORY_SELECTORS)
        logger.info("SELECTOR HIT -> %r via %s", hit.get("category"), hit.get("method") or "none")

        dump = page.evaluate(PROBE_JS)
        logger.info("h1: %s", dump.get("h1"))
        for node in dump.get("nodes", [])[:30]:
            logger.info(
                "  <%s class=%r parent=%r jsaction=%r> %s",
                node["tag"], node["cls"][:40], node["parentCls"][:30],
                node["jsaction"][:30], node["text"],
            )
        if idx < len(rows):
            page.wait_for_timeout(1200)


def main() -> int:
    workspace = Path(__file__).resolve().parent
    args = parse_args()

    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = workspace / db_path
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 1

    config_path = Path(args.config)
    config = load_config(config_path if config_path.is_absolute() else workspace / config_path, args)

    output_dir = db_path.parent
    logger = setup_logger(output_dir / "logs", name="category_backfill")
    logger.info("DB: %s", db_path)
    logger.info("Browser mode: %s", "headless" if config.get("headless") else "headed")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_progress_table(conn)

    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    blank = conn.execute(
        "SELECT COUNT(*) FROM companies WHERE TRIM(COALESCE(category,'')) = ''"
    ).fetchone()[0]
    logger.info("Companies: %s | blank category: %s (%.1f%%)", total, blank, blank * 100 / max(total, 1))

    if args.probe:
        try:
            with GoogleMapsScraper(config, logger) as scraper:
                run_probe(scraper, conn, args.probe, logger)
        finally:
            conn.close()
        logger.info("Probe finished. Nothing written.")
        return 0

    rows = pending_rows(conn, args.retry_empty)
    logger.info("Pending rows this run: %s", len(rows))
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]
        logger.info("Limit applied: processing %s rows.", len(rows))

    if not rows:
        logger.info("Nothing to do.")
        conn.close()
        return 0

    found = 0
    empty = 0
    failed = 0

    try:
        with GoogleMapsScraper(config, logger) as scraper:
            page = scraper.require_page()
            for idx, row in enumerate(rows, start=1):
                if idx > 1:
                    random_delay(
                        float(config.get("delay_company_min", 0.8)),
                        float(config.get("delay_company_max", 2)),
                        logger,
                        "next place open",
                    )
                try:
                    open_place_page(scraper, row["maps_url"])
                    page.wait_for_timeout(400)
                    hit = page.evaluate(EXTRACT_JS, CATEGORY_SELECTORS)
                    category = clean_category(hit.get("category", ""))
                    method = hit.get("method", "")
                except KeyboardInterrupt:
                    raise
                except Exception:
                    logger.exception("Failed on %s; leaving pending.", row["company_name"])
                    failed += 1
                    continue

                status = "found" if category else "no_category"
                if category:
                    conn.execute(
                        "UPDATE companies SET category = ?, updated_at = ? WHERE id = ?",
                        (category, utc_now(), row["id"]),
                    )
                    found += 1
                else:
                    empty += 1

                conn.execute(
                    """
                    INSERT INTO category_backfill
                        (company_id, maps_url, category, method, status, checked_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company_id) DO UPDATE SET
                        category   = excluded.category,
                        method     = excluded.method,
                        status     = excluded.status,
                        checked_at = excluded.checked_at
                    """,
                    (row["id"], row["maps_url"], category, method, status, utc_now()),
                )
                conn.commit()

                logger.info(
                    "[%s/%s] %s -> %s%s",
                    idx, len(rows), row["company_name"],
                    category or "(none)",
                    f"  [{method}]" if method else "",
                )
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Progress saved; rerun the same command to resume.")
    finally:
        conn.commit()
        remaining = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE TRIM(COALESCE(category,'')) = ''"
        ).fetchone()[0]
        logger.info("=" * 72)
        logger.info("THIS RUN | found=%s no_category=%s failed=%s", found, empty, failed)
        logger.info("DB NOW   | blank category: %s of %s (%.1f%%)",
                    remaining, total, remaining * 100 / max(total, 1))
        conn.close()

        if not args.no_export:
            storage = ScraperStorage(db_path, output_dir)
            try:
                storage.export_all()
                logger.info("Re-exported companies.csv / companies.jsonl in %s", output_dir)
            except PermissionError:
                logger.warning("Could not rewrite CSV (file open in Excel?). DB is up to date.")
            finally:
                storage.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
