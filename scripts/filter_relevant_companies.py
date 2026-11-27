"""Split each country's companies.csv into relevant (manufacturer/supplier/etc.)
vs excluded (shop/unrelated) vs unknown, using category + company_name wordlists.
Writes the relevant rows into relevant_companies/<country>.csv.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DEST_DIR = ROOT / "relevant_companies"

COUNTRIES = [
    "uae", "saudi_arabia", "qatar", "oman", "kuwait",
    "italy", "france", "denmark", "norway", "singapore",
    "netherlands", "spain", "sweden", "japan", "south_korea",
]

INCLUDE_TERMS = [
    "supplier", "manufacturer", "distributor", "wholesaler", "trading", "exporter", "importer",
    "equipment", "machinery", "producer", "factory", "industrial", "dealer", "mill", "plant",
    "irrigation", "fertilizer", "agricultural service", "agri", "chemical company", "corporation",
]
EXCLUDE_TERMS = [
    "store", "shop", "mart", "supermarket", "hypermarket", "pharmacy", "restaurant", "cafe", "hotel",
    "salon", "clinic", "hospital", "school", "bank", "gym", "laundry", "grocery", "convenience",
    "gas station", "car wash", "real estate", "clothing", "furniture", "pet ", "aquarium",
    "recycling center", "swimming pool supply", "corporate office",
]


def classify(category: str, name: str) -> str:
    text = (category or "").strip().lower()
    for term in EXCLUDE_TERMS:
        if term in text:
            return "excluded_shop_or_unrelated"
    for term in INCLUDE_TERMS:
        if term in text:
            return "relevant"

    name_l = (name or "").lower()
    for term in EXCLUDE_TERMS:
        if term in name_l:
            return "excluded_shop_or_unrelated"
    for term in INCLUDE_TERMS:
        if term in name_l:
            return "relevant"

    return "unknown"


def main() -> None:
    DEST_DIR.mkdir(exist_ok=True)

    for country in COUNTRIES:
        src = OUTPUT_DIR / country / "companies.csv"
        if not src.exists():
            print(f"{country}: no companies.csv yet, skipping")
            continue

        with src.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)

        relevant_rows = [r for r in rows if classify(r.get("category", ""), r.get("company_name", "")) == "relevant"]

        dest = DEST_DIR / f"{country}_relevant.csv"
        with dest.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(relevant_rows)

        print(f"{country}: {len(relevant_rows)} relevant / {len(rows)} total -> {dest}")


if __name__ == "__main__":
    main()
