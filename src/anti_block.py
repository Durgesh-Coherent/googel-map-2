from __future__ import annotations

import logging
import time

from playwright.sync_api import Page


BLOCK_TEXT_PATTERNS = [
    "unusual traffic",
    "our systems have detected",
    "sorry/index",
    "captcha",
    "verify you are human",
    "automated queries",
]


def detect_block(page: Page) -> tuple[bool, str]:
    url = page.url.lower()
    if "sorry/index" in url or "captcha" in url:
        return True, f"Blocked URL detected: {page.url}"

    try:
        body_text = page.locator("body").inner_text(timeout=3000).lower()
    except Exception:
        body_text = ""

    for pattern in BLOCK_TEXT_PATTERNS:
        if pattern in body_text or pattern in url:
            return True, f"Block/CAPTCHA text detected: {pattern}"
    return False, ""


def wait_for_manual_captcha(page: Page, logger: logging.Logger, recheck_delay: int = 5) -> None:
    while True:
        blocked, reason = detect_block(page)
        if not blocked:
            return
        logger.warning("%s", reason)
        logger.warning("CAPTCHA/block detected. Solve it in the visible browser, then press Enter here.")
        input("CAPTCHA detected. Solve it in the browser, then press Enter to continue...")
        time.sleep(recheck_delay)
