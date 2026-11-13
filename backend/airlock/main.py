import asyncio
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel
from . import config
from .models import ScanRequest, DemoRequest
from .fetch import fetch_public_html, UnsafeURL
from .pipeline import scan_html
from .scenarios import SCENARIOS, scenario_list
from .agent import demo_run

app = FastAPI(title="Airlock API", description="Visibility-aware prompt-injection research prototype", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_methods=["GET","POST"], allow_headers=["Content-Type"])
_rate: dict[str, deque] = defaultdict(deque)
_rate_lock = asyncio.Lock()


async def throttle(request: Request, group: str, limit: int):
    # Single-process demo limiter. Add Redis and proxy-aware IP controls in production.
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{group}"
    async with _rate_lock:
        q = _rate[key]
        now = time.monotonic()
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit reached; retry in one minute")
        q.append(now)


@app.get("/api/health")
def health():
    return {"ok":True, "service":"airlock"}


@app.get("/api/status")
def status():
    return {"llm_configured":bool(config.OPENAI_API_KEY), "url_mode_enabled":config.ALLOW_URL_SCAN,
            "model":config.OPENAI_MODEL if config.OPENAI_API_KEY else None,
            "demo_email_mode":"fake_outbox_only"}


@app.get("/api/scenarios")
def scenarios():
    return scenario_list()


@app.post("/api/scan")
async def scan(payload: ScanRequest, request: Request):
    await throttle(request,"scan",24)
    if payload.url:
        if not config.ALLOW_URL_SCAN:
            raise HTTPException(status_code=403, detail="URL scanning is disabled. Paste HTML instead, or opt in locally with AIRLOCK_ENABLE_URL_SCAN=1")
        try:
            content = await fetch_public_html(payload.url)
        except (UnsafeURL, ValueError, OSError, asyncio.TimeoutError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        content = payload.content or ""
    try:
        result, screenshot = await asyncio.wait_for(scan_html(content), timeout=config.SCAN_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Browser analysis timed out") from exc
    except Exception as exc:
        # Keep internal stack traces out of public responses.
        raise HTTPException(status_code=503, detail="Browser analysis unavailable; check Chromium installation and sandbox setup") from exc
    return {**result.model_dump(), "screenshot_base64":screenshot}


@app.post("/api/demo")
async def demo(payload: DemoRequest, request: Request):
    await throttle(request,"demo",8)
    if payload.scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    s = SCENARIOS[payload.scenario_id]
    try:
        report, _ = await asyncio.wait_for(scan_html(s["html"]), timeout=config.SCAN_TIMEOUT_SECONDS)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Chromium scanner failed") from exc
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY in backend/.env to enable the real LLM agent")
    try:
        result = await demo_run(s["task"], report, payload.firewall_on)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"LLM API request failed: {str(exc)[:200]}") from exc
    return {**result, "scenario_id":payload.scenario_id,"firewall_on":payload.firewall_on,
            "scanner_verdict":report.verdict,"scan_reason":report.reason,"user_task":s["task"]}


# Docker builds the Vite assets here. In local development, Vite serves on localhost:5173.
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
