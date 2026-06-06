#!/usr/bin/env python3
"""Capture Sprint 3 demo screenshots."""

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
        page = await browser.new_page(viewport={"width": 1400, "height": 1200})
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUT / "sprint3-workflow.png"), full_page=True)

        await page.select_option("#reply-mode", "per_chat")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUT / "sprint3-per-chat.png"), full_page=True)

        await page.select_option("#topic-mode", "ai_assign")
        await page.fill("#inbox-topics", "billing")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "sprint3-topic-filter.png"), full_page=True)

        await page.select_option("#inbox-view", "flat")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "sprint3-flat-view.png"), full_page=True)

        await page.select_option("#inbox-view", "threads")
        await page.fill("#inbox-topics", "")
        await page.click("#inbox-apply")
        await page.wait_for_timeout(1000)
        await page.click("#btn-suggest")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "sprint3-suggestions.png"), full_page=True)

        done_btn = page.locator(".mark-done").first
        if await done_btn.count():
            await done_btn.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUT / "sprint3-suggestion-done.png"), full_page=True)

        await browser.close()
    print(f"Screenshots saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
