"""Test the real Airlock pipeline against Browserless, without exposing any token."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
if not os.environ.get("BROWSERLESS_TOKEN"):
    raise SystemExit("Set BROWSERLESS_TOKEN in backend/.env first")
from airlock import config
from airlock.pipeline import scan_html
from airlock.scenarios import SCENARIOS

EXPECTED = {"opacity":"block", "class":"block", "javascript":"block",
            "benign":"allow", "newsletter":"sanitize"}

async def main():
    for key, expected in EXPECTED.items():
        s=SCENARIOS[key]
        try:
            result, screenshot = await asyncio.wait_for(
                scan_html(s["html"]), timeout=config.SCAN_TIMEOUT_SECONDS)
        except Exception as exc:
            text=str(exc).replace(os.environ["BROWSERLESS_TOKEN"], "[REDACTED]")
            print(f"FAIL {key}: {type(exc).__name__}: {text[:350]}")
            raise SystemExit(1)
        ok=(result.verdict==expected and len(screenshot)>40)
        print(f"{'PASS' if ok else 'FAIL'} {key}: verdict={result.verdict}, expected={expected}, screenshot={'yes' if screenshot else 'no'}")
        if not ok:
            raise SystemExit(1)
    print("PASS: All five real Airlock scan scenarios use remote Chromium.")

if __name__ == '__main__':
    asyncio.run(main())
