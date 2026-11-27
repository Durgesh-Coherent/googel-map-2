"""Build Google Maps search keywords for cocopeat companies in India.

Expands product terms x company-type suffixes x cities into the standard
keyword CSV format. Tamil Nadu cities get priority 1 (biggest cocopeat
processing belt), other states priority 2.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "keywords" / "google_maps_keywords_india_cocopeat.csv"

PRODUCT_TERMS = [
    "Cocopeat",
    "Coco Peat",
    "Coir Pith",
    "Coco Coir",
    "Coir Fiber",
    "Coco Chips",
    "Cocopeat Block",
    "Cocopeat Grow Bag",
    "Cocopeat Briquette",
    "Coir Pith Compost",
    "Coco Peat Powder",
    "Coir Products",
]

SUFFIXES = ["manufacturer", "exporter", "supplier"]

# (city, state, priority)
CITIES = [
    ("Pollachi", "Tamil Nadu", 1),
    ("Coimbatore", "Tamil Nadu", 1),
    ("Udumalpet", "Tamil Nadu", 1),
    ("Dharapuram", "Tamil Nadu", 1),
    ("Tirupur", "Tamil Nadu", 1),
    ("Dindigul", "Tamil Nadu", 1),
    ("Theni", "Tamil Nadu", 1),
    ("Madurai", "Tamil Nadu", 1),
    ("Tuticorin", "Tamil Nadu", 1),
    ("Nagercoil", "Tamil Nadu", 1),
    ("Chennai", "Tamil Nadu", 1),
    ("Alappuzha", "Kerala", 2),
    ("Kochi", "Kerala", 2),
    ("Kollam", "Kerala", 2),
    ("Thrissur", "Kerala", 2),
    ("Kozhikode", "Kerala", 2),
    ("Amalapuram", "Andhra Pradesh", 2),
    ("Rajahmundry", "Andhra Pradesh", 2),
    ("Vijayawada", "Andhra Pradesh", 2),
    ("Visakhapatnam", "Andhra Pradesh", 2),
    ("Tiptur", "Karnataka", 2),
    ("Hassan", "Karnataka", 2),
    ("Mangalore", "Karnataka", 2),
    ("Bangalore", "Karnataka", 2),
]

COUNTRY_LABEL = "India"


def build_rows() -> list[dict[str, str]]:
    rows = []
    for city, state, priority in CITIES:
        for term in PRODUCT_TERMS:
            for suffix in SUFFIXES:
                rows.append(
                    {
                        "keyword": f"{term} {suffix} {city}",
                        "base_keyword": term,
                        "entity": f"Cocopeat {suffix} ({state})",
                        "country": COUNTRY_LABEL,
                        "city": city,
                        "priority": str(priority),
                    }
                )
    return rows


def main() -> None:
    OUT_PATH.parent.mkdir(exist_ok=True)
    rows = build_rows()

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["keyword", "base_keyword", "entity", "country", "city", "priority"],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)

    p1 = sum(1 for r in rows if r["priority"] == "1")
    print(f"{len(rows)} keywords ({p1} priority-1, {len(rows) - p1} priority-2) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
