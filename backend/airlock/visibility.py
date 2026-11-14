"""Render pasted/fetched HTML in Chromium with all browser network access blocked."""
import asyncio
import base64
from urllib.parse import quote
from pathlib import Path
from playwright.async_api import async_playwright
from . import config

_SCRIPT = Path(__file__).with_name("visibility.js").read_text(encoding="utf-8")
_BROWSER_CONCURRENCY = asyncio.Semaphore(1 if config.BROWSERLESS_TOKEN else 2)


async def analyze_html(content: str) -> tuple[list[dict], str]:
    if len(content.encode("utf-8")) > config.MAX_HTML_BYTES:
        raise ValueError("HTML too large")
    async with _BROWSER_CONCURRENCY:
        async with async_playwright() as p:
            if config.BROWSERLESS_TOKEN:
                # Native Playwright protocol is required for context.route and
                # context.route_web_socket. Do not use connect_over_cdp here.
                endpoint = (
                    "wss://production-sfo.browserless.io/chromium/playwright?token="
                    + quote(config.BROWSERLESS_TOKEN, safe="")
                )
                try:
                    browser = await p.chromium.connect(endpoint, timeout=18000)
                except Exception as exc:
                    # Keep API tokens out of logs, tracebacks, and HTTP responses.
                    detail = str(exc).replace(config.BROWSERLESS_TOKEN, "[REDACTED]")
                    raise RuntimeError(
                        f"Browserless connection failed ({type(exc).__name__}): {detail[:400]}"
                    ) from None
            else:
                browser = await p.chromium.launch(
                    headless=True,
                    chromium_sandbox=config.CHROMIUM_SANDBOX,
                    executable_path=config.CHROMIUM_EXECUTABLE,
                )
            context = None
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
                return segments, base64.b64encode(shot).decode("ascii")
            except Exception as exc:
                if config.BROWSERLESS_TOKEN:
                    detail = str(exc).replace(config.BROWSERLESS_TOKEN, "[REDACTED]")
                    raise RuntimeError(
                        f"Browserless scan failed ({type(exc).__name__}): {detail[:400]}"
                    ) from None
                raise
            finally:
                if context is not None:
                    await context.close()
                await browser.close()
