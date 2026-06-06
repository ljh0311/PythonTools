#!/usr/bin/env python3
"""Capture Sprint 2 demo screenshots."""

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
        page = await browser.new_page(viewport={"width": 1400, "height": 1100})
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        await page.click("#btn-summarize")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "sprint2-summary.png"), full_page=True)

        await page.click("#btn-suggest")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "sprint2-suggestions.png"), full_page=True)

        await page.select_option("#inbox-chat-type", "group")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(1500)
        await page.click("#btn-summarize")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "sprint2-group-summary.png"), full_page=True)

        await browser.close()
    print(f"Screenshots saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
