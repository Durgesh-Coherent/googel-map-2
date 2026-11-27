import csv
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"c:\Users\durgesh\Desktop\google map")
SEED = ROOT / "seed_keywords_fg_raw_priority_10k.csv"
OUT_DIR = ROOT / "keywords_v2"
OUT_DIR.mkdir(exist_ok=True)

TARGET_TOTAL = 1000
RM_RATIO = 4000 / 7500.0
FG_RATIO = 3500 / 7500.0
RM_TARGET = round(TARGET_TOTAL * RM_RATIO)
FG_TARGET = TARGET_TOTAL - RM_TARGET

JUNK_WORDS = {
    "registered", "billiong", "milliong", "exportf", "cwd", "bvp", "gbp",
    "ethanoic", "hplc", "usp", "cpc", "tgps",
}

VITAMIN_WHITELIST = {
    "b1", "b2", "b3", "b5", "b6", "b7", "b9", "b12",
    "d2", "d3", "k1", "k2", "coq10",
}

JUNK_CODE_RE = re.compile(r"^[a-z]{1,5}\d{2,}[a-z]?$")

STOPWORD_END = {"and", "for", "of", "with", "the", "or", "a", "an", "s", "on", "ep", "usp", "bp", "jp", "de", "ip", "in", "by"}

# Multi-word marketing qualifier phrases stripped from the front of a listing
QUALIFIER_PREFIXES = [
    "clinical strength", "professional grade", "whole food",
    "pharmaceutical grade", "medical grade", "extra strength",
    "maximum strength", "premium organic", "certified organic",
    "non gmo", "advanced formula",
]

# Single leading adjective qualifiers, stripped only if 2+ words remain after
SINGLE_QUALIFIERS = {"natural", "organic", "premium", "pure", "advanced", "select"}

# Group keys that are known-bad / not real standalone products -> drop entirely
DROP_KEYS = {"new zealand", "old world"}

# Group keys whose *bare* 2-word form is too vague standalone; prefer a longer variant
FORCE_LONGER_KEYS = {"full spectrum", "full body", "coconut activated", "cod liver"}

ACRONYM_MAP = {
    "cbn": "CBN",
    "htp": "HTP", "dha": "DHA", "epa": "EPA", "gaba": "GABA", "mct": "MCT",
    "cla": "CLA", "bcaa": "BCAA", "hmb": "HMB", "coq10": "CoQ10", "pqq": "PQQ",
    "dhea": "DHEA", "hcl": "HCl", "atp": "ATP", "ala": "ALA", "gla": "GLA",
    "nad": "NAD", "nmn": "NMN", "dna": "DNA", "rna": "RNA", "ph": "pH",
    "b1": "B1", "b2": "B2", "b3": "B3", "b5": "B5", "b6": "B6", "b7": "B7",
    "b9": "B9", "b12": "B12", "d2": "D2", "d3": "D3", "k1": "K1", "k2": "K2",
    "cfu": "CFU", "cbd": "CBD", "5htp": "5-HTP", "gpc": "GPC", "cdp": "CDP",
    "nac": "NAC", "tmg": "TMG", "msm": "MSM", "dmae": "DMAE",
    "hmo": "HMO", "psk": "PSK", "ip": "IP", "ahcc": "AHCC", "eaa": "EAA", "dl": "DL", "bhb": "BHB", "orac": "ORAC",
}


def fix_possessive(text: str) -> str:
    return re.sub(r"\b(\w+) s\b", r"\1's", text)


def clean_listing(raw: str) -> str | None:
    text = raw.strip().lower()
    if not text:
        return None
    if "ngebb" in text or "nbaseblend" in text:
        return None
    text = fix_possessive(text)
    tokens = text.split()
    kept = []
    for tok in tokens:
        if tok in JUNK_WORDS:
            continue
        if tok not in VITAMIN_WHITELIST and JUNK_CODE_RE.match(tok):
            continue
        if tok not in VITAMIN_WHITELIST and len(tok) >= 9 and any(c.isdigit() for c in tok):
            continue
        kept.append(tok)
    if not kept:
        return None
    text = " ".join(kept).strip()
    if len(text) < 3:
        return None
    words = text.split()
    if words[-1] in STOPWORD_END:
        return None
    # drop bare possessive fragments with no following noun, e.g. "lion's"
    if len(words) == 1 and words[0].endswith("'s"):
        return None
    return text


def strip_qualifier(text: str) -> tuple[str, bool]:
    for q in QUALIFIER_PREFIXES:
        if text == q:
            return text, True
        if text.startswith(q + " "):
            return text[len(q) + 1:].strip(), True
    words = text.split()
    if len(words) >= 3 and words[0] in SINGLE_QUALIFIERS:
        return " ".join(words[1:]), True
    return text, False


def group_key(core: str) -> str:
    parts = core.split()
    if len(parts) >= 2:
        return parts[0] + " " + parts[1]
    return parts[0]


def title_word(word: str) -> str:
    if "-" in word:
        parts = word.split("-")
        out = []
        for p in parts:
            if p in ACRONYM_MAP:
                out.append(ACRONYM_MAP[p])
            elif len(p) == 1:
                out.append(p.upper())
            elif p.isdigit():
                out.append(p)
            else:
                out.append(p.capitalize())
        return "-".join(out)
    if word in ACRONYM_MAP:
        return ACRONYM_MAP[word]
    if len(word) == 1:
        return word.upper()
    if word.isdigit():
        return word
    return word.capitalize()


def title_case(text: str) -> str:
    return " ".join(title_word(w) for w in text.split())


def load_seed():
    rows = []
    with SEED.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entity = (row.get("Entity") or "").strip()
            listing = (row.get("Listing") or "").strip()
            if entity in ("raw_material", "finished_goods") and listing:
                rows.append((entity, listing))
    return rows


def build_groups(rows, entity_name):
    groups = defaultdict(list)
    for entity, listing in rows:
        if entity != entity_name:
            continue
        cleaned = clean_listing(listing)
        if not cleaned:
            continue
        core, had_qualifier = strip_qualifier(cleaned)
        core_tokens = core.split()
        if not core_tokens:
            continue
        if len(core_tokens) == 1 and core_tokens[0].endswith("'s"):
            continue
        key = group_key(core)
        word_count = len(core_tokens)
        groups[key].append((core, had_qualifier, word_count))
    return groups


def pick_representative(key, members):
    plain = [m for m in members if not m[1]]
    pool = plain if plain else members
    min_words = 3 if key in FORCE_LONGER_KEYS else 2
    multi = [m for m in pool if m[2] >= min_words]
    chosen_pool = multi if multi else pool
    chosen = min(chosen_pool, key=lambda m: m[2])
    return chosen[0]


def select_products(groups, target_n):
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    selected = []
    for key, members in ranked:
        if len(selected) >= target_n:
            break
        if key in DROP_KEYS:
            continue
        rep = pick_representative(key, members)
        selected.append(rep)
    return selected


def main():
    seed_rows = load_seed()
    rm_groups = build_groups(seed_rows, "raw_material")
    fg_groups = build_groups(seed_rows, "finished_goods")

    print(f"RM distinct groups available: {len(rm_groups)} | target {RM_TARGET}")
    print(f"FG distinct groups available: {len(fg_groups)} | target {FG_TARGET}")

    rm_products = select_products(rm_groups, RM_TARGET)
    fg_products = select_products(fg_groups, FG_TARGET)

    def finalize(products):
        seen = set()
        out = []
        for p in products:
            titled = title_case(p)
            key = titled.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(titled)
        return out

    rm_final = finalize(rm_products)
    fg_final = finalize(fg_products)

    print(f"RM final: {len(rm_final)} | FG final: {len(fg_final)} | total {len(rm_final)+len(fg_final)}")

    prod_path = OUT_DIR / "products_selected_1000.csv"
    with prod_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["entity", "base_keyword"])
        for p in rm_final:
            writer.writerow(["raw_material", p])
        for p in fg_final:
            writer.writerow(["finished_goods", p])

    COUNTRIES = {
        "qatar": ("Qatar", ["Umm Salal", "Al Daayen", "Dukhan", "Al Wukair", "Industrial Area"]),
        "uae": ("UAE", ["Jebel Ali", "Mussafah", "Umm Al Quwain", "Al Quoz", "Ruwais"]),
        "saudi_arabia": ("Saudi Arabia", ["Taif", "Buraidah", "Hofuf", "Dhahran", "Jazan"]),
        "israel": ("Israel", ["Ramat Gan", "Ra'anana", "Rehovot", "Ashkelon", "Modiin"]),
    }

    RM_PATTERNS = ["{p} supplier {c}", "{p} distributor {c}", "{p} importer {c}"]
    FG_PATTERNS = ["{p} manufacturer {c}", "{p} producer {c}", "{p} company {c}"]

    all_rows = []
    per_country_rows = {}

    for slug, (label, cities) in COUNTRIES.items():
        rows = []
        for city in cities:
            for p in rm_final:
                for pat in RM_PATTERNS:
                    kw = pat.format(p=p, c=city)
                    rows.append((kw, p, "raw_material", label, city))
            for p in fg_final:
                for pat in FG_PATTERNS:
                    kw = pat.format(p=p, c=city)
                    rows.append((kw, p, "finished_goods", label, city))
        per_country_rows[slug] = rows
        all_rows.extend(rows)

    def write_csv(path, rows):
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(["keyword", "base_keyword", "entity", "country", "city"])
            writer.writerows(rows)

    for slug, rows in per_country_rows.items():
        write_csv(OUT_DIR / f"google_maps_keywords_{slug}.csv", rows)
        print(f"{slug}: {len(rows)} rows")

    write_csv(OUT_DIR / "google_maps_keywords_all_countries.csv", all_rows)
    print(f"all_countries: {len(all_rows)} rows")


if __name__ == "__main__":
    main()
