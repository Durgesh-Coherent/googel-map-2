from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

from playwright.sync_api import Page


def parse_place_page(page: Page, scrape_description: bool = False) -> dict[str, Any]:
    # Core business fields first. Do NOT open About before these.
    text = safe_body_text(page)
    url = page.url
    latitude, longitude = extract_lat_lng(url)
    rating, review_count = extract_rating_reviews(page, text)

    company_name = first_text(page, ["h1", "h1[role='heading']"])
    if not company_name:
        company_name = company_name_from_url(url)

    full_address = extract_button_value(
        page,
        [
            "button[data-item-id='address']",
            "button[aria-label^='Address:']",
            "button[aria-label*='Address']",
        ],
    )
    phone = extract_button_value(
        page,
        [
            "button[data-item-id^='phone:tel:']",
            "button[aria-label^='Phone:']",
            "button[aria-label*='Phone']",
        ],
    )
    website = extract_website(page)
    category = extract_category(page, text)

    # Description last, so About-tab clicks cannot break name/address/phone.
    description = extract_description(page) if scrape_description else ""

    return {
        "company_name": company_name,
        "full_address": full_address,
        "phone": phone,
        "website": website,
        "category": category,
        "description": description,
        "rating": rating,
        "review_count": review_count,
        "maps_url": url,
        "place_id": extract_place_id(url),
        "latitude": latitude,
        "longitude": longitude,
    }


def company_name_from_url(url: str) -> str:
    match = re.search(r"/maps/place/([^/@]+)", url)
    if not match:
        return ""
    raw = unquote(match.group(1)).replace("+", " ")
    raw = raw.replace("\u200e", "").replace("\u200f", "").replace("\u202a", "").replace("\u202c", "")
    return clean_label(raw)


def extract_description(page: Page) -> str:
    """Best-effort About text. Leave blank when no real description exists."""
    # Prefer explicit About selectors only. Avoid generic panel classes.
    for selector in [
        "div[aria-label^='About'] div.PYvSYb",
        "[data-attrid='description']",
        "div[aria-label*='About this place'] div.PYvSYb",
        "div[aria-label*='From the business'] div.PYvSYb",
    ]:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            value = clean_label(locator.inner_text(timeout=2000))
            if is_useful_description(value):
                return value[:2000]
        except Exception:
            continue

    open_about_section(page)

    for selector in [
        "div[aria-label^='About'] div.PYvSYb",
        "[data-attrid='description']",
        "div[aria-label*='About this place'] div.PYvSYb",
        "div[aria-label*='From the business']",
    ]:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            value = clean_label(locator.inner_text(timeout=3000))
            if is_useful_description(value):
                return value[:2000]
        except Exception:
            continue

    # No reliable About text found.
    return ""


def open_about_section(page: Page) -> None:
    # Only click the About tab, not Overview (Overview can change panel layout).
    try:
        tab = page.get_by_role("tab", name=re.compile(r"^About$", re.I)).first
        if tab.count() > 0:
            tab.click(timeout=2000)
            page.wait_for_timeout(700)
            return
    except Exception:
        pass


def is_useful_description(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if len(value) < 40:
        return False

    junk_tokens = (
        "suggest an edit",
        "add a missing place",
        "update to add",
        "directions",
        "nearby",
        "send to phone",
        "share",
        "save",
        "accessibility",
        "wheelchair",
        "credit cards",
        "debit cards",
        "nfc mobile",
        "sign in",
        "service options",
        "popular times",
        "map data",
        "send product feedback",
        "layers imagery",
        "in-store shopping",
        "in-store pick-up",
        "curbside",
        "opens ",
        "closes ",
        "see more hours",
        "plus code",
    )
    junk_hits = sum(1 for token in junk_tokens if token in lowered)
    if junk_hits >= 1:
        return False

    # Reject strings that are mostly address/phone/website repeats.
    if re.search(r"\+\d[\d\s\-]{7,}", value) and ("http" in lowered or ".co" in lowered):
        return False
    return True


def safe_body_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""


def first_text(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                value = locator.inner_text(timeout=5000).strip()
                if value:
                    return clean_label(value)
        except Exception:
            continue
    return ""


def extract_button_value(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            aria = locator.get_attribute("aria-label", timeout=3000) or ""
            text = locator.inner_text(timeout=3000) or ""
            value = aria or text
            value = re.sub(r"^(Address|Phone):\s*", "", value, flags=re.I)
            value = clean_label(value)
            if value:
                return value
        except Exception:
            continue
    return ""


def extract_website(page: Page) -> str:
    selectors = [
        "a[data-item-id='authority']",
        "a[aria-label^='Website:']",
        "a[aria-label*='Website']",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            href = locator.get_attribute("href", timeout=3000) or ""
            if href and "google.com" not in href:
                return href.strip()
            text = locator.inner_text(timeout=3000).strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def extract_category(page: Page, body_text: str) -> str:
    selectors = [
        "button[jsaction*='pane.rating.category']",
        "button[aria-label*='Category']",
    ]
    value = first_text(page, selectors)
    if value:
        return value

    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        if re.match(r"^\d+(?:\.\d+)?\s*\(", line) and idx + 1 < len(lines):
            candidate = lines[idx + 1]
            if len(candidate) < 80:
                return candidate
    return ""


def extract_rating_reviews(page: Page, body_text: str) -> tuple[str, str]:
    try:
        candidates = page.locator("[aria-label*='stars'], [aria-label*='reviews']").all()
        for candidate in candidates[:20]:
            label = candidate.get_attribute("aria-label", timeout=1000) or ""
            rating, reviews = parse_rating_review_text(label)
            if rating or reviews:
                return rating, reviews
    except Exception:
        pass
    return parse_rating_review_text(body_text)


def parse_rating_review_text(text: str) -> tuple[str, str]:
    rating = ""
    reviews = ""

    rating_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:stars?|star rating)", text, re.I)
    if not rating_match:
        rating_match = re.search(r"\b([1-5](?:\.\d)?)\b\s*\(([\d,]+)\)", text)
    if rating_match:
        rating = rating_match.group(1)
        if rating_match.lastindex and rating_match.lastindex >= 2:
            reviews = rating_match.group(2).replace(",", "")

    review_match = re.search(r"([\d,]+)\s+reviews?", text, re.I)
    if review_match:
        reviews = review_match.group(1).replace(",", "")
    return rating, reviews


def extract_lat_lng(url: str) -> tuple[str, str]:
    at_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if at_match:
        return at_match.group(1), at_match.group(2)

    d_match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    if d_match:
        return d_match.group(1), d_match.group(2)
    return "", ""


def extract_place_id(url: str) -> str:
    decoded = unquote(url)
    candidates = [
        r"!1s([^!]+)",
        r"(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)",
    ]
    for pattern in candidates:
        match = re.search(pattern, decoded)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return ""


def clean_label(value: str) -> str:
    value = value.replace("\u200e", "").replace("\u200f", "")
    return re.sub(r"\s+", " ", value).strip()
