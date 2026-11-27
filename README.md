# Google Maps Website Scraper

Slow, resumable Python scraper for collecting company details from the free Google Maps website. It does not use Google Places API or any paid API.

## Important Precautions

Google Maps can show CAPTCHA or unusual traffic pages. This scraper is intentionally slow and runs in a visible browser by default so you can solve CAPTCHA manually. Do not use it for high-speed crawling.

Country lock is enabled for all markets:
- Search URL uses `hl=en` + country `gl=` (`ae`, `sa`, `qa`, `il`)
- Map is centered on the keyword city
- Companies outside the target country (by coordinates/phone/address) are skipped

Use this responsibly:

- Keep `--max-results` small for pilots.
- Keep headed mode enabled.
- Use random delays between keywords and company pages.
- If CAPTCHA appears, solve it in the browser and press Enter in the terminal.
- The scraper saves progress after every keyword.

## Install

Open PowerShell in this folder:

```powershell
cd "C:\Users\durgesh\Desktop\google map"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Input CSV Format

Each keyword CSV must contain:

```csv
keyword,base_keyword,entity,country,city
```

Example:

```csv
"BCAA Amino Acid Blend supplier Dubai","BCAA Amino Acid Blend","raw_material","UAE","Dubai"
```

Supported country files:

- `google_maps_keywords_uae.csv`
- `google_maps_keywords_saudi_arabia.csv`
- `google_maps_keywords_qatar.csv`
- `google_maps_keywords_israel.csv`
- `google_maps_keywords_all_countries.csv`

## How To Run

Interactive country prompt:

```powershell
python main.py
```

UAE pilot with first 20 keywords and top 10 Maps results:

```powershell
python main.py `
  --country UAE `
  --input "C:\Users\durgesh\Desktop\google map\google_maps_keywords_uae.csv" `
  --limit-keywords 20 `
  --max-results 10 `
  --output-dir "./output/uae_pilot"
```

Same command can be run again to resume:

```powershell
python main.py `
  --country UAE `
  --input "C:\Users\durgesh\Desktop\google map\google_maps_keywords_uae.csv" `
  --limit-keywords 20 `
  --max-results 10 `
  --output-dir "./output/uae_pilot"
```

Filter by entity:

```powershell
python main.py `
  --country UAE `
  --entity raw_material `
  --limit-keywords 50 `
  --max-results 15 `
  --output-dir "./output/uae_raw_material"
```

## CLI Options

- `--input`: Keyword CSV path. If omitted, the scraper selects the country CSV.
- `--country`: Country to scrape. If omitted, the scraper asks before run.
- `--entity`: Optional entity filter.
- `--limit-keywords`: Process only first N keywords after filters.
- `--max-results`: Top N Google Maps company results per keyword.
- `--start-from`: 1-based row position after filters, or exact keyword text.
- `--output-dir`: Output folder. For one country, the DB and exports go here.
- `--headless`: Run invisible browser. Not recommended for pilot.
- `--no-headless`: Force visible browser.

## Outputs

For UAE pilot, files are written to:

```text
output/uae_pilot/
  uae.db
  companies.csv
  companies.jsonl
  keyword_status.csv
  logs/
    run.log
```

Company export columns:

- `company_name`
- `full_address`
- `city`
- `country`
- `phone`
- `website`
- `category`
- `description`
- `rating`
- `review_count`
- `maps_url`
- `place_id`
- `latitude`
- `longitude`
- `source_keywords`
- `base_keywords`
- `entities`
- `scraped_at`
- `updated_at`

Keyword status columns:

- `keyword`
- `entity`
- `country`
- `city`
- `status`
- `companies_found`
- `error_message`
- `scraped_at`

## Resume Behavior

SQLite is the source of truth. Each country has its own database, for example `uae.db`.

After every keyword:

1. Company rows are inserted or updated.
2. Duplicate companies are merged.
3. Keyword status is updated.
4. CSV and JSONL files are exported.

When you run the same command again, keywords with `status = success` are skipped.

## Duplicate Handling

The scraper does not scrape a known company URL again. It deduplicates by:

- normalized `maps_url`
- normalized `phone`
- normalized `company_name + full_address`

If the same company appears for multiple searches, it keeps one company row and appends all matching searches into:

- `source_keywords`
- `base_keywords`
- `entities`

Values are separated with ` | `.

## CAPTCHA Handling

If Google shows CAPTCHA or unusual traffic:

1. The scraper pauses.
2. Solve CAPTCHA in the visible browser.
3. Return to PowerShell and press Enter.
4. The scraper checks again and continues.

## Notes

Google Maps page structure changes often. The scraper uses flexible selectors and stores empty values when optional fields are missing instead of crashing.




#commands

cd "C:\Users\durgesh\Desktop\google map"

# UAE
py main.py --country UAE --input ".\keywords_v2\google_maps_keywords_uae.csv" --output-dir "./output/uae_keywords_v2"

# Saudi Arabia
py main.py --country "Saudi Arabia" --input ".\keywords_v2\google_maps_keywords_saudi_arabia.csv" --output-dir "./output/saudi_keywords_v2"

# Qatar
py main.py --country Qatar --input ".\keywords_v2\google_maps_keywords_qatar.csv" --output-dir "./output/qatar_keywords_v2"

# Israel
py main.py --country Israel --input ".\keywords_v2\google_maps_keywords_israel.csv" --output-dir "./output/israel_keywords_v2"

# All countries (one run)
py main.py --country all_countries --input ".\keywords_v2\google_maps_keywords_all_countries.csv" --output-dir "./output/keywords_v2_all"