"""Expand agri_keywords_product_v3.csv (Keyword, Entities, Group, Priority)
into per-country Google Maps search keyword CSVs, one row per keyword x city.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "agri_keywords_product_v3.csv"
OUT_DIR = ROOT / "keywords"

# mode "single": one product search per row, suffix picked from the Entities tag.
# mode "dual": two product searches per row, always "manufacturer" + "supplier",
#              for broader manufacturer coverage.
COUNTRIES = {
    "uae": ("UAE", ["Dubai", "Sharjah", "Abu Dhabi", "Ajman", "Ras Al Khaimah"], "single"),
    "saudi_arabia": ("Saudi Arabia", ["Riyadh", "Jeddah", "Dammam", "Khobar", "Jubail"], "single"),
    "qatar": ("Qatar", ["Doha", "Al Rayyan", "Al Wakrah", "Al Khor", "Mesaieed"], "single"),
    "oman": ("Oman", ["Muscat", "Sohar", "Salalah", "Nizwa", "Sur"], "single"),
    "kuwait": ("Kuwait", ["Kuwait City", "Al Ahmadi", "Farwaniya", "Hawalli", "Jahra"], "single"),
    "italy": ("Italy", ["Milan", "Bologna", "Modena", "Verona", "Padova"], "dual"),
    "france": ("France", ["Paris", "Lyon", "Toulouse", "Rennes", "Nantes"], "dual"),
    "denmark": ("Denmark", ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg"], "dual"),
    "norway": ("Norway", ["Oslo", "Bergen", "Trondheim", "Stavanger", "Tromso"], "dual"),
    "singapore": ("Singapore", ["Singapore", "Jurong"], "dual"),
    "spain": ("Spain", ["Madrid", "Barcelona", "Valencia", "Zaragoza", "Almeria"], "dual"),
    "netherlands": ("Netherlands", ["Amsterdam", "Rotterdam", "The Hague", "Westland", "Eindhoven"], "dual"),
    "sweden": ("Sweden", ["Stockholm", "Gothenburg", "Malmo", "Uppsala", "Orebro"], "dual"),
    "south_korea": ("South Korea", ["Seoul", "Busan", "Incheon", "Daegu", "Gwangju"], "dual"),
    "japan": ("Japan", ["Tokyo", "Osaka", "Nagoya", "Sapporo", "Fukuoka"], "dual"),
}

DUAL_SUFFIXES = ("manufacturer", "supplier")

SERVICE_PATTERN = "{k} {c}"

# Checked in order against the row's Entities text (lowercased).
ENTITY_SUFFIX_RULES = [
    (("manufacturer", "oem"), "manufacturer"),
    (("distributor", "dealer"), "distributor"),
    (("wholesale",), "wholesaler"),
    (("trading", "trader", "exporter", "importer"), "trading company"),
]
DEFAULT_PRODUCT_SUFFIX = "supplier"


def product_pattern(entity: str) -> str:
    entity_lower = entity.lower()
    for tokens, suffix in ENTITY_SUFFIX_RULES:
        if any(token in entity_lower for token in tokens):
            return "{k} " + suffix + " {c}"
    return "{k} " + DEFAULT_PRODUCT_SUFFIX + " {c}"


def load_seed() -> list[dict[str, str]]:
    with SEED.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_rows(
    seed_rows: list[dict[str, str]], cities: list[str], country_label: str, mode: str
) -> list[dict[str, str]]:
    rows = []
    for city in cities:
        for item in seed_rows:
            base_keyword = item["Keyword"].strip()
            entity = item["Entities"].strip()
            group = item["Group"].strip()
            priority = item["Priority"].strip()

            if group != "product_goods":
                patterns = [SERVICE_PATTERN]
            elif mode == "dual":
                patterns = ["{k} " + suffix + " {c}" for suffix in DUAL_SUFFIXES]
            else:
                patterns = [product_pattern(entity)]

            for pattern in patterns:
                keyword = pattern.format(k=base_keyword, c=city)
                rows.append(
                    {
                        "keyword": keyword,
                        "base_keyword": base_keyword,
                        "entity": entity,
                        "country": country_label,
                        "city": city,
                        "priority": priority,
                    }
                )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["keyword", "base_keyword", "entity", "country", "city", "priority"],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    seed_rows = load_seed()
    print(f"Loaded {len(seed_rows)} base keywords.")

    for slug, (label, cities, mode) in COUNTRIES.items():
        rows = build_rows(seed_rows, cities, label, mode)
        out_path = OUT_DIR / f"google_maps_keywords_{slug}.csv"
        write_csv(out_path, rows)
        print(f"{slug}: {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
