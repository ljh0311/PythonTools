#!/usr/bin/env python3
"""Capture first-open and setup demo screenshots."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/opt/cursor/artifacts/screenshots/first-open")
OUT.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # 1 — Login (first visit when password is configured)
        await page.goto(f"{URL}/login", wait_until="networkidle")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(OUT / "01-login-page.png"), full_page=True)

        await page.fill("#username", "admin")
        await page.fill("#password", "demo123")
        await page.screenshot(path=str(OUT / "02-login-filled.png"), full_page=True)
        await page.click("button[type=submit]")
        await page.wait_for_timeout(2500)

        # 2 — Dashboard first view (may be empty or with data)
        await page.screenshot(path=str(OUT / "03-dashboard-first-view.png"), full_page=True)

        # 3 — Scroll to workflow + inbox
        await page.locator(".workflow-card").scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "04-operator-workflow.png"), full_page=True)

        await page.locator(".inbox-card").scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "05-inbox-empty-or-loaded.png"), full_page=True)

        # 4 — Per-chat mode (setup feature)
        await page.select_option("#reply-mode", "per_chat")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT / "06-per-chat-after-setup.png"), full_page=True)

        await browser.close()
    print(f"First-open demo saved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
