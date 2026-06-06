#!/usr/bin/env python3
"""Capture Sprint 1 inbox demo screenshots."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/opt/cursor/artifacts/screenshots")
OUT.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "sprint1-inbox-all.png"), full_page=True)

        await page.fill("#inbox-search", "billing")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "sprint1-filter-billing.png"), full_page=True)

        await page.click("#inbox-clear")
        await page.wait_for_timeout(500)
        await page.select_option("#inbox-chat-type", "group")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "sprint1-filter-group.png"), full_page=True)

        await browser.close()
    print(f"Screenshots saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
