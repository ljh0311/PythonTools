#!/usr/bin/env python3
"""Capture inbox filter demo screenshots."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/opt/cursor/artifacts/screenshots/inbox-demo")
OUT.mkdir(parents=True, exist_ok=True)


async def snap(page, name: str) -> None:
    await page.locator(".inbox-card").scroll_into_view_if_needed()
    await page.wait_for_timeout(800)
    await page.screenshot(path=str(OUT / f"{name}.png"))


async def apply(page) -> None:
    await page.click("#inbox-apply")
    await page.wait_for_timeout(1500)


async def clear(page) -> None:
    await page.click("#inbox-clear")
    await page.wait_for_timeout(1200)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 1100})
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        await snap(page, "00-default-thread-view")

        await page.fill("#inbox-search", "billing")
        await apply(page)
        await snap(page, "01-search-billing")

        await clear(page)
        await page.fill("#inbox-topics", "billing")
        await apply(page)
        await snap(page, "02-topic-billing")

        await clear(page)
        await page.select_option("#inbox-users", ["101"])
        await apply(page)
        await snap(page, "03-user-alice")

        await clear(page)
        await page.select_option("#inbox-chat-type", "group")
        await apply(page)
        await snap(page, "04-chat-type-group")

        await clear(page)
        await page.select_option("#inbox-direction", "incoming")
        await apply(page)
        await snap(page, "05-direction-incoming")

        await clear(page)
        await page.select_option("#inbox-view", "flat")
        await apply(page)
        await snap(page, "06-flat-view")

        await clear(page)
        await page.select_option("#inbox-view", "threads")
        await page.select_option("#summary-type", "bullets")
        await page.click("#btn-summarize")
        await page.wait_for_timeout(2000)
        await snap(page, "07-ai-summarize-bullets")

        await browser.close()
    print(f"Inbox demo screenshots saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
