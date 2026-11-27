from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from src.keyword_loader import (
    COUNTRY_LABELS,
    KeywordRow,
    load_keywords,
    prompt_country,
    resolve_input_file,
    slugify_country,
)
from src.geo import matches_country, url_outside_country
from src.logger import setup_logger
from src.maps_scraper import GoogleMapsScraper, random_delay
from src.storage import ScraperStorage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Slow Google Maps website scraper.")
    parser.add_argument("--input", help="Path to keyword CSV. If omitted, chosen from country.")
    parser.add_argument("--country", help="Country to scrape: UAE, Saudi Arabia, Qatar, Israel, all_countries.")
    parser.add_argument("--entity", help="Optional entity filter, e.g. raw_material.")
    parser.add_argument("--limit-keywords", type=int, help="Limit number of keywords to process.")
    parser.add_argument("--max-results", type=int, help="Top N Maps results per keyword.")
    parser.add_argument("--start-from", help="Start from 1-based index or exact keyword.")
    parser.add_argument("--output-dir", default="./output", help="Output directory or country output directory.")
    parser.add_argument("--config", default="./config.yaml", help="Config YAML path.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--no-headless", action="store_true", help="Run browser visibly.")
    return parser.parse_args()


def load_config(config_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    else:
        config = {}

    if args.max_results is not None:
        config["max_results"] = args.max_results
    if args.headless:
        config["headless"] = True
    if args.no_headless:
        config["headless"] = False
    config.setdefault("headless", False)
    config.setdefault("max_results", 15)
    return config


def main() -> int:
    workspace = Path(__file__).resolve().parent
    args = parse_args()

    country_slug = slugify_country(args.country) if args.country else prompt_country()
    input_path = resolve_input_file(workspace, country_slug, args.input)
    config = load_config((workspace / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config), args)
    output_root = resolve_output_root(workspace, Path(args.output_dir), country_slug)

    logger = setup_logger(output_root / "logs")
    logger.info("Selected country: %s", COUNTRY_LABELS.get(country_slug, country_slug))
    logger.info("Input CSV: %s", input_path)
    logger.info("Output root: %s", output_root)
    logger.info("Browser mode: %s", "headless" if config.get("headless") else "headed")

    rows = load_keywords(
        input_path=input_path,
        country_filter=None if country_slug == "all_countries" else COUNTRY_LABELS.get(country_slug, args.country),
        entity_filter=args.entity,
        limit_keywords=args.limit_keywords,
        start_from=args.start_from,
    )
    if not rows:
        logger.warning("No keywords found after filters.")
        return 0

    storage_cache: dict[str, ScraperStorage] = {}

    def storage_for(row: KeywordRow) -> ScraperStorage:
        row_country_slug = slugify_country(row.country or country_slug)
        if country_slug == "all_countries":
            country_output = output_root / row_country_slug
        else:
            country_output = output_root
        if row_country_slug not in storage_cache:
            db_path = country_output / f"{row_country_slug}.db"
            storage_cache[row_country_slug] = ScraperStorage(db_path, country_output)
        return storage_cache[row_country_slug]

    pending_rows: list[KeywordRow] = []
    for row in rows:
        storage = storage_for(row)
        if row.keyword.lower() in {kw.lower() for kw in storage.completed_keywords()}:
            continue
        pending_rows.append(row)

    logger.info("Loaded %s keywords, %s pending after resume check.", len(rows), len(pending_rows))
    if not pending_rows:
        logger.info("Nothing to scrape. Exporting current country data.")
        for storage in storage_cache.values():
            storage.export_all()
            storage.close()
        return 0

    run_stats = {
        "success": 0,
        "failed": 0,
        "captcha": 0,
        "blocked": 0,
        "companies_new": 0,
        "companies_linked": 0,
        "skipped_wrong_country": 0,
    }
    geo_filter_enabled = bool(config.get("geo_filter_enabled", True))
    logger.info("Geo filter enabled: %s", geo_filter_enabled)

    try:
        with GoogleMapsScraper(config, logger) as scraper:
            for idx, keyword_row in enumerate(pending_rows, start=1):
                storage = storage_for(keyword_row)
                logger.info("=" * 72)
                logger.info(
                    "STAT | keyword %s/%s | success=%s failed=%s captcha=%s blocked=%s | companies_in_db=%s | this_run_new=%s linked=%s",
                    idx,
                    len(pending_rows),
                    run_stats["success"],
                    run_stats["failed"],
                    run_stats["captcha"],
                    run_stats["blocked"],
                    storage.company_count(),
                    run_stats["companies_new"],
                    run_stats["companies_linked"],
                )
                logger.info(
                    "[%s/%s] Keyword: %s | %s | %s",
                    idx,
                    len(pending_rows),
                    keyword_row.keyword,
                    keyword_row.entity,
                    keyword_row.city,
                )
                storage.update_keyword_status(keyword_row, "pending")

                try:
                    if idx > 1:
                        random_delay(
                            float(config.get("delay_keyword_min", 8)),
                            float(config.get("delay_keyword_max", 18)),
                            logger,
                            "next keyword search",
                        )

                    result_urls = scraper.search(
                        keyword_row.keyword,
                        int(config.get("max_results", 15)),
                        country=keyword_row.country,
                        city=keyword_row.city,
                    )
                    logger.info("Collected %s candidate places.", len(result_urls))
                    companies_found, new_count, linked_count, skipped = process_places(
                        result_urls,
                        keyword_row,
                        storage,
                        scraper,
                        config,
                        logger,
                        geo_filter_enabled=geo_filter_enabled,
                    )
                    storage.update_keyword_status(keyword_row, "success", companies_found=companies_found)
                    run_stats["success"] += 1
                    run_stats["companies_new"] += new_count
                    run_stats["companies_linked"] += linked_count
                    run_stats["skipped_wrong_country"] += skipped
                    logger.info(
                        "Keyword finished: %s companies linked (%s new, %s already known, %s skipped wrong country).",
                        companies_found,
                        new_count,
                        linked_count - new_count,
                        skipped,
                    )
                except KeyboardInterrupt:
                    storage.update_keyword_status(keyword_row, "failed", error_message="Interrupted by user")
                    run_stats["failed"] += 1
                    raise
                except Exception as exc:
                    message = str(exc)
                    status = (
                        "captcha"
                        if "captcha" in message.lower()
                        else "blocked"
                        if "block" in message.lower()
                        else "failed"
                    )
                    run_stats[status] = run_stats.get(status, 0) + 1
                    logger.exception("Keyword failed: %s", keyword_row.keyword)
                    storage.update_keyword_status(keyword_row, status, error_message=message)

                if config.get("export_after_each_keyword", True):
                    storage.export_all()
                    logger.info("Exported latest CSV/JSONL/status files.")

                logger.info(
                    "STAT | done %s/%s | success=%s failed=%s captcha=%s blocked=%s | companies_in_db=%s",
                    idx,
                    len(pending_rows),
                    run_stats["success"],
                    run_stats["failed"],
                    run_stats["captcha"],
                    run_stats["blocked"],
                    storage.company_count(),
                )
    finally:
        for storage in storage_cache.values():
            storage.export_all()
            storage.close()

    logger.info(
        "FINAL STAT | success=%s failed=%s captcha=%s blocked=%s | new_companies=%s linked=%s skipped_wrong_country=%s",
        run_stats["success"],
        run_stats["failed"],
        run_stats["captcha"],
        run_stats["blocked"],
        run_stats["companies_new"],
        run_stats["companies_linked"],
        run_stats["skipped_wrong_country"],
    )
    logger.info("Run completed.")
    return 0


def process_places(
    result_urls: list[str],
    keyword_row: KeywordRow,
    storage: ScraperStorage,
    scraper: GoogleMapsScraper,
    config: dict[str, Any],
    logger: Any,
    geo_filter_enabled: bool = True,
) -> tuple[int, int, int, int]:
    companies_found = 0
    new_count = 0
    linked_count = 0
    skipped = 0
    for place_idx, url in enumerate(result_urls, start=1):
        logger.info("Place %s/%s", place_idx, len(result_urls))
        if storage.has_company_url(url):
            # Only link known companies if they already passed geo earlier.
            storage.upsert_company({"maps_url": url}, keyword_row)
            logger.info("Already known place URL; linked keyword without reopening.")
            companies_found += 1
            linked_count += 1
            continue

        if geo_filter_enabled:
            outside, reason = url_outside_country(url, keyword_row.country)
            if outside:
                skipped += 1
                logger.info("SKIPPED early wrong country (no open): %s | reason=%s", url[:120], reason)
                continue

        if place_idx > 1:
            random_delay(
                float(config.get("delay_company_min", 4)),
                float(config.get("delay_company_max", 9)),
                logger,
                "next company detail open",
            )

        data = scraper.open_place(url)
        if not data.get("company_name") and not data.get("maps_url"):
            logger.warning("Skipping empty company detail for URL: %s", url)
            continue

        if geo_filter_enabled:
            ok, reason = matches_country(data, keyword_row.country)
            if not ok:
                skipped += 1
                logger.info(
                    "SKIPPED wrong country: %s | reason=%s | lat=%s lng=%s | phone=%s",
                    data.get("company_name") or "(no name)",
                    reason,
                    data.get("latitude") or "-",
                    data.get("longitude") or "-",
                    data.get("phone") or "-",
                )
                continue

        _, created = storage.upsert_company(data, keyword_row)
        name = data.get("company_name") or "(no name)"
        desc_flag = "yes" if data.get("description") else "blank"
        logger.info("Saved: %s | phone=%s | description=%s", name, data.get("phone") or "-", desc_flag)
        companies_found += 1
        linked_count += 1
        if created:
            new_count += 1
    return companies_found, new_count, linked_count, skipped


def resolve_output_root(workspace: Path, output_dir: Path, country_slug: str) -> Path:
    if not output_dir.is_absolute():
        output_dir = workspace / output_dir
    if output_dir.name.lower() in {country_slug, "uae_pilot"} or country_slug == "all_countries":
        return output_dir
    return output_dir / country_slug


if __name__ == "__main__":
    sys.exit(main())
