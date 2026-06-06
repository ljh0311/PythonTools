#!/usr/bin/env python3
"""Capture dashboard demo screenshots."""

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
        page = await browser.new_page(viewport={"width": 1400, "height": 1000})
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(OUT / "inbox-threads-summary.png"), full_page=True)

        await page.goto(f"{URL}/feedback", wait_until="networkidle")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "feedback-page.png"), full_page=True)

        await browser.close()
    print(f"Screenshots saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
