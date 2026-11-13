"""Render pasted/fetched HTML in Chromium with all browser network access blocked."""
import asyncio
import base64
from pathlib import Path
from playwright.async_api import async_playwright
from . import config

_SCRIPT = Path(__file__).with_name("visibility.js").read_text(encoding="utf-8")
_BROWSER_CONCURRENCY = asyncio.Semaphore(2)


async def analyze_html(content: str) -> tuple[list[dict], str]:
    if len(content.encode("utf-8")) > config.MAX_HTML_BYTES:
        raise ValueError("HTML too large")
    async with _BROWSER_CONCURRENCY:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, chromium_sandbox=config.CHROMIUM_SANDBOX,
                                              executable_path=config.CHROMIUM_EXECUTABLE)
            try:
                context = await browser.new_context(
                    viewport={"width": 1060, "height": 670},
                    java_script_enabled=True,
                    service_workers="block",
                    accept_downloads=False,
                )
                # All external resource loads, fetch(), XHR, images and frames are denied.
                await context.route("**/*", lambda route: route.abort())
                # Playwright HTTP routes do not cover WebSocket connections.
                await context.route_web_socket("**/*", lambda ws: ws.close())
                page = await context.new_page()
                page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
                await page.set_content(content, wait_until="domcontentloaded", timeout=6500)
                await page.wait_for_timeout(180)  # short grace period for inline JS to insert text
                segments = await page.evaluate(_SCRIPT)
                shot = await page.screenshot(type="png", animations="disabled", timeout=3000)
                await context.close()
                return segments, base64.b64encode(shot).decode("ascii")
            finally:
                await browser.close()
