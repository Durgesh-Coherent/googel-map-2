from __future__ import annotations

import logging
import random
import time
from typing import Any
from urllib.parse import quote_plus

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, TimeoutError, sync_playwright

from .anti_block import detect_block, wait_for_manual_captcha
from .geo import city_center, get_country_geo
from .parser import parse_place_page


class GoogleMapsScraper:
    def __init__(self, config: dict[str, Any], logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> "GoogleMapsScraper":
        self.playwright = sync_playwright().start()
        browser_type = getattr(self.playwright, self.config.get("browser", "chromium"))
        self.browser = browser_type.launch(
            headless=bool(self.config.get("headless", False)),
            slow_mo=int(self.config.get("slow_mo_ms", 0)),
        )
        self.context = self.browser.new_context(
            locale=self.config.get("locale", "en-US"),
            timezone_id=self.config.get("timezone_id", "Asia/Dubai"),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(int(self.config.get("page_timeout_ms", 60000)))
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def search(
        self,
        keyword: str,
        max_results: int,
        country: str = "",
        city: str = "",
    ) -> list[str]:
        page = self.require_page()
        search_url = self.build_search_url(keyword, country=country, city=city)
        self.logger.info("Searching Google Maps: %s", keyword)
        self.logger.info("Search URL: %s", search_url)
        page.goto(search_url, wait_until="domcontentloaded")
        self.handle_consent()
        wait_for_manual_captcha(
            page,
            self.logger,
            int(self.config.get("captcha_recheck_delay_seconds", 5)),
        )

        try:
            page.wait_for_selector("div[role='feed'], h1", timeout=12000)
        except TimeoutError:
            pass

        if "/maps/place/" in page.url:
            return [page.url]

        return self.collect_result_urls(max_results)

    def collect_result_urls(self, max_results: int) -> list[str]:
        page = self.require_page()
        urls: list[str] = []
        seen: set[str] = set()
        unchanged_rounds = 0
        effective_max = 40 if max_results <= 0 else min(max_results, 40)
        scroll_rounds = 12

        for _ in range(scroll_rounds):
            wait_for_manual_captcha(
                page,
                self.logger,
                int(self.config.get("captcha_recheck_delay_seconds", 5)),
            )
            for url in self.extract_place_links():
                if url not in seen:
                    urls.append(url)
                    seen.add(url)
                    if len(urls) >= effective_max:
                        return urls

            before = len(urls)
            self.scroll_results()
            time.sleep(random.uniform(0.5, 1.0))
            if len(urls) == before:
                unchanged_rounds += 1
            else:
                unchanged_rounds = 0
            if unchanged_rounds >= 3:
                break

        return urls[:effective_max]

    def open_place(self, url: str) -> dict[str, Any]:
        page = self.require_page()
        self.logger.info("Opening place: %s", url)
        page.goto(add_english_params(url), wait_until="domcontentloaded")
        self.handle_consent()
        wait_for_manual_captcha(
            page,
            self.logger,
            int(self.config.get("captcha_recheck_delay_seconds", 5)),
        )
        self.wait_for_place_panel()
        data = parse_place_page(
            page,
            scrape_description=bool(self.config.get("scrape_description", False)),
        )
        blocked, reason = detect_block(page)
        if blocked:
            raise RuntimeError(reason)
        return data

    def wait_for_place_panel(self) -> None:
        page = self.require_page()
        try:
            page.wait_for_selector(
                "h1, button[data-item-id='address'], button[data-item-id^='phone:tel:']",
                timeout=12000,
            )
            page.wait_for_timeout(250)
        except TimeoutError:
            self.logger.warning("Place panel did not appear before timeout.")

    def extract_place_links(self) -> list[str]:
        page = self.require_page()
        try:
            links = page.evaluate(
                """
                () => Array.from(document.querySelectorAll('a[href*="/maps/place/"]'))
                    .map((a) => a.href)
                    .filter(Boolean)
                """
            )
        except Exception:
            return []

        cleaned: list[str] = []
        seen: set[str] = set()
        for link in links:
            url = str(link)
            if "/maps/place/" not in url:
                continue
            url = add_english_params(url)
            if url not in seen:
                cleaned.append(url)
                seen.add(url)
        return cleaned

    def scroll_results(self) -> None:
        page = self.require_page()
        try:
            feed = page.locator("div[role='feed']").first
            if feed.count() > 0:
                feed.evaluate("(el) => { el.scrollTop = el.scrollHeight; }")
                return
        except Exception:
            pass
        page.mouse.wheel(0, 1800)

    def handle_consent(self) -> None:
        page = self.require_page()
        labels = [
            "Accept all",
            "I agree",
            "Accept",
            "Reject all",
        ]
        for label in labels:
            try:
                button = page.get_by_role("button", name=label).first
                if button.count() > 0:
                    button.click(timeout=3000)
                    time.sleep(0.4)
                    return
            except Exception:
                continue

    def build_search_url(self, keyword: str, country: str = "", city: str = "") -> str:
        base_url = self.config.get("maps_base_url", "https://www.google.com/maps").rstrip("/")
        geo = get_country_geo(country) if country else None
        gl = (geo or {}).get("gl", "")
        lat, lng = city_center(country, city) if country else (0.0, 0.0)
        zoom = int(self.config.get("search_zoom", 12))

        path = f"{base_url}/search/{quote_plus(keyword)}"
        params = ["hl=en"]
        if gl:
            params.append(f"gl={gl}")

        # Center map on target city to reduce IP-local bias.
        if lat and lng:
            path = f"{path}/@{lat},{lng},{zoom}z"

        return f"{path}?{'&'.join(params)}"

    def require_page(self) -> Page:
        if not self.page:
            raise RuntimeError("Browser page is not initialized.")
        return self.page


def add_english_params(url: str) -> str:
    if "hl=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}hl=en"


def random_delay(min_seconds: float, max_seconds: float, logger: logging.Logger, reason: str) -> None:
    seconds = random.uniform(min_seconds, max_seconds)
    logger.info("Waiting %.1f seconds before %s.", seconds, reason)
    time.sleep(seconds)
