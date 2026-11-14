"""Integration probe: verify Playwright intercepts attempted browser HTTP + WebSocket access.

This establishes client-side interception for tested calls; it is NOT a proof of
provider-wide network egress isolation. Run only against your Browserless account.
"""
import asyncio
import os
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv(Path(__file__).with_name('.env'))


async def verify():
    token = os.environ.get('BROWSERLESS_TOKEN', '').strip()
    if not token:
        raise SystemExit('BROWSERLESS_TOKEN must be in backend/.env')
    uri = 'wss://production-sfo.browserless.io/chromium/playwright?token='+quote(token,safe='')
    events = {'http_abort_attempts':[], 'ws_rejections':[], 'finished_external_requests':[]}
    async with async_playwright() as p:
        browser=await p.chromium.connect(uri,timeout=20000)
        context=None
        try:
            context=await browser.new_context(service_workers='block',java_script_enabled=True)
            async def deny_http(route):
                events['http_abort_attempts'].append(route.request.url)
                await route.abort()
            async def deny_ws(ws):
                events['ws_rejections'].append(ws.url)
                await ws.close()
            await context.route('**/*',deny_http)
            await context.route_web_socket('**/*',deny_ws)
            page=await context.new_page()
            page.on('requestfinished',lambda request: events['finished_external_requests'].append(request.url) if request.url.startswith(('http:','https:')) else None)
            # The page contains controlled test addresses only, no credentials or exfiltration.
            await page.set_content("""<!doctype html><html><body><script>
                fetch('https://example.com/airlock-egress-test').catch(()=>{});
                new Image().src='https://example.com/airlock-image-test.png';
                try { new WebSocket('wss://echo.websocket.events/'); } catch(e) {}
            </script></body></html>""",wait_until='domcontentloaded')
            await page.wait_for_timeout(900)
        finally:
            if context: await context.close()
            await browser.close()
    http_blocked=sum('example.com/' in u for u in events['http_abort_attempts'])
    ws_blocked=sum('echo.websocket.events' in u for u in events['ws_rejections'])
    escaped=[u for u in events['finished_external_requests'] if 'example.com' in u]
    assert http_blocked>=2, f'Expected fetch and image to hit HTTP interception, got: {events}'
    assert ws_blocked>=1, f'Expected WebSocket to hit WS handler, got: {events}'
    assert not escaped, f'Browser request escaped tested HTTP route: {escaped}'
    print(f'PASS: intercepted/aborted {http_blocked} HTTP attempts')
    print(f'PASS: intercepted/closed {ws_blocked} WebSocket attempt(s)')
    print('PASS: no tested external HTTP requests completed')
    print('LIMITATION: This does not verify provider-level egress, DNS, WebRTC, or browser sandbox configuration.')


if __name__=='__main__':
    asyncio.run(verify())
