from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from src.enrichment.enrichment_storage import EnrichmentStorage
from src.enrichment.name_matcher import pick_best_match
from src.enrichment.source_loader import CompanyLookupRow, load_companies_missing_website
from src.geo import matches_country
from src.logger import setup_logger
from src.maps_scraper import GoogleMapsScraper, random_delay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find missing company websites via Google Maps, for companies that already "
        "have a name/city/state/country but no website on file."
    )
    parser.add_argument("--input", required=True, help="Path to source CSV (native_id, company_name, website, city, state, country).")
    parser.add_argument("--output-dir", default="./output/enrichment", help="Where to write the progress DB and result CSV.")
    parser.add_argument("--config", default="./config.yaml", help="Config YAML path (reused from the main scraper).")
    parser.add_argument("--limit", type=int, help="Only process the first N pending companies (useful for a test run).")
    parser.add_argument("--max-candidates", type=int, default=3, help="How many Maps search results to open per company.")
    parser.add_argument("--threshold", type=float, default=0.72, help="Minimum name-match score (0-1) required to accept a website.")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (not recommended: breaks manual CAPTCHA solving).")
    parser.add_argument("--no-headless", action="store_true", help="Force a visible browser window.")
    return parser.parse_args()


def load_config(config_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    else:
        config = {}

    if args.headless:
        config["headless"] = True
    if args.no_headless:
        config["headless"] = False
    config.setdefault("headless", False)
    return config


def main() -> int:
    workspace = Path(__file__).resolve().parent
    args = parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = workspace / output_dir
    config_path = Path(args.config)
    config = load_config(config_path if config_path.is_absolute() else workspace / config_path, args)

    logger = setup_logger(output_dir / "logs", name="website_enrichment")
    logger.info("Input CSV: %s", input_path)
    logger.info("Output dir: %s", output_dir)
    logger.info("Browser mode: %s", "headless" if config.get("headless") else "headed")
    logger.info("Max candidates per company: %s | Match threshold: %s", args.max_candidates, args.threshold)

    all_rows = load_companies_missing_website(input_path)
    logger.info("Companies missing website in source CSV: %s", len(all_rows))

    storage = EnrichmentStorage(output_dir / "enrichment_progress.db")
    done_ids = storage.processed_native_ids()
    pending_rows = [row for row in all_rows if row.native_id not in done_ids]
    logger.info("Already processed (resumed): %s | Pending: %s", len(done_ids), len(pending_rows))

    if args.limit is not None:
        pending_rows = pending_rows[: max(0, args.limit)]
        logger.info("Test-run limit applied: processing %s companies this run.", len(pending_rows))

    if not pending_rows:
        logger.info("Nothing to do. Exporting current results.")
        storage.export_csv(output_dir / "companies_with_found_websites.csv")
        storage.close()
        return 0

    result_csv_path = output_dir / "companies_with_found_websites.csv"

    try:
        with GoogleMapsScraper(config, logger) as scraper:
            for idx, row in enumerate(pending_rows, start=1):
                logger.info("=" * 72)
                logger.info(
                    "[%s/%s] %s | %s, %s, %s",
                    idx, len(pending_rows), row.company_name, row.city, row.state, row.country,
                )

                if idx > 1:
                    random_delay(
                        float(config.get("delay_keyword_min", 1)),
                        float(config.get("delay_keyword_max", 2)),
                        logger,
                        "next company lookup",
                    )

                try:
                    result = process_company(row, scraper, config, logger, args.max_candidates, args.threshold)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    logger.exception("Lookup failed for %s; leaving pending for next run.", row.company_name)
                    continue

                storage.save_result(result)
                logger.info(
                    "Result: %s | score=%.2f | website=%s",
                    result["match_status"], result["match_score"] or 0.0, result["website_found"] or "-",
                )

                if idx % 20 == 0:
                    storage.export_csv(result_csv_path)
                    logger.info("Exported progress CSV (%s rows so far).", idx)
    finally:
        storage.export_csv(result_csv_path)
        counts = storage.counts()
        logger.info("FINAL COUNTS | matched=%s not_found=%s", counts.get("matched", 0), counts.get("not_found", 0))
        storage.close()

    logger.info("Run completed. Results: %s", result_csv_path)
    return 0


def process_company(
    row: CompanyLookupRow,
    scraper: GoogleMapsScraper,
    config: dict[str, Any],
    logger: Any,
    max_candidates: int,
    threshold: float,
) -> dict[str, Any]:
    query = f"{row.company_name} {row.city}, {row.country}".strip()
    result_urls = scraper.search(query, max_candidates, country=row.country, city=row.city)

    base_result = {
        "native_id": row.native_id,
        "company_name": row.company_name,
        "city": row.city,
        "state": row.state,
        "country": row.country,
    }

    if not result_urls:
        return {**base_result, "website_found": "", "maps_url": "", "phone": "", "match_status": "not_found", "matched_name": "", "match_score": 0.0}

    candidates: list[dict[str, Any]] = []
    for place_idx, url in enumerate(result_urls, start=1):
        if place_idx > 1:
            random_delay(
                float(config.get("delay_company_min", 0.8)),
                float(config.get("delay_company_max", 2)),
                logger,
                "next candidate detail open",
            )
        data = scraper.open_place(url)
        if data.get("company_name"):
            candidates.append(data)

    best_candidate, score = pick_best_match(row.company_name, candidates, threshold)

    if not best_candidate:
        return {**base_result, "website_found": "", "maps_url": "", "phone": "", "match_status": "not_found", "matched_name": "", "match_score": score}

    geo_ok, _reason = matches_country(best_candidate, row.country)
    if not geo_ok:
        return {**base_result, "website_found": "", "maps_url": "", "phone": "", "match_status": "not_found", "matched_name": "", "match_score": score}

    return {
        **base_result,
        "website_found": best_candidate.get("website") or "",
        "maps_url": best_candidate.get("maps_url") or "",
        "phone": best_candidate.get("phone") or "",
        "match_status": "matched",
        "matched_name": best_candidate.get("company_name") or "",
        "match_score": score,
    }


if __name__ == "__main__":
    sys.exit(main())
