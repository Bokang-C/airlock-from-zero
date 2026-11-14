"""Generate TRUE local LLM outcomes for the public read-only Attack Replay Studio.

Usage (from backend/): .\\.venv\\Scripts\\python.exe export_studio_replays.py --repeats 3
Needs OPENAI_API_KEY and browser access locally. Never deploy your key.
"""
import argparse
import asyncio
import json
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
from airlock import config
from airlock.agent import demo_run
from airlock.pipeline import scan_html
from airlock.scenarios import SCENARIOS

OUTPUT = Path(__file__).resolve().parent / "airlock" / "studio_replays.json"


def safe_result(data: dict) -> dict:
    """Allowlist fields only. Avoid recording raw API responses or credentials."""
    return {
        "answer": str(data.get("answer", ""))[:1800],
        "attempts": int(data.get("attempts", 0)),
        "denied": int(data.get("denied", 0)),
        "hijacked": bool(data.get("hijacked", False)),
        "outbox": [{"to": str(x.get("to", ""))[:200],
                    "subject": str(x.get("subject", ""))[:200],
                    "body": str(x.get("body", ""))[:500]}
                   for x in data.get("outbox", [])[:3]],
        "trace": [{"event": str(x.get("event", ""))[:60],
                   "detail": str(x.get("detail", ""))[:240],
                   "content_sent": str(x.get("content_sent", ""))[:240],
                   "tool": str(x.get("tool", ""))[:80],
                   "to": str(x.get("to", ""))[:200],
                   "outcome": str(x.get("outcome", ""))[:200],
                   "policy_code": str(x.get("policy_code", ""))[:90]}
                  for x in data.get("trace", [])[:10]],
    }


async def export(repeats: int, ids: list[str]):
    if not config.OPENAI_API_KEY:
        raise SystemExit('Set OPENAI_API_KEY locally in backend/.env. Do NOT set it on DeployXA.')
    if not (1 <= repeats <= 20):
        raise SystemExit('Choose between 1 and 20 repeats; each trial makes a billable API call.')
    data = {"schema_version": 1, "kind": "actual-model-trials",
            "generated_at": datetime.now(timezone.utc).isoformat(), "model": config.OPENAI_MODEL,
            "trials": [], "disclaimer": "Recorded real model trials. The scanner and model are stochastic; results do not guarantee future protection. All emails use a fake in-memory outbox."}
    for scenario_id in ids:
        if scenario_id not in SCENARIOS:
            raise SystemExit(f'Unknown scenario: {scenario_id}')
        scenario = SCENARIOS[scenario_id]
        print(f'Browser scan: {scenario_id}', flush=True)
        try:
            scan, _ = await scan_html(scenario['html'])
        except Exception as e:
            print(f'  Scan failed: {type(e).__name__}: {str(e)[:160]}', flush=True)
            data['trials'].append({"scenario_id": scenario_id, "firewall_on": None, "trial": 0, "ok": False,
                                   "error_type": type(e).__name__, "stage": "scanner"})
            continue
        for i in range(1, repeats + 1):
            for enabled in (False, True):
                t = perf_counter()
                row = {"scenario_id": scenario_id, "firewall_on": enabled, "trial": i,
                       "scanner_verdict": scan.verdict, "scan_reason": scan.reason}
                try:
                    result = await demo_run(scenario['task'], scan, enabled)
                    row.update({"ok": True, "duration_ms": round((perf_counter()-t)*1000),
                                "result": safe_result(result)})
                    print(f'  trial {i} firewall={enabled} hijacked={result["hijacked"]} attempts={result["attempts"]} denied={result["denied"]}', flush=True)
                except Exception as e:
                    row.update({"ok": False, "duration_ms": round((perf_counter()-t)*1000),
                                "error_type": type(e).__name__, "stage": "model"})
                    if isinstance(e, httpx.HTTPStatusError):
                        status = e.response.status_code
                        try:
                            provider_error = e.response.json().get("error", {})
                            if not isinstance(provider_error, dict):
                                provider_error = {}
                        except (ValueError, TypeError, AttributeError):
                            provider_error = {}
                        code = str(provider_error.get("code") or "")[:80]
                        error_type = str(provider_error.get("type") or "")[:80]
                        row.update({"http_status": status,
                                    "provider_error_code": code,
                                    "provider_error_type": error_type})
                        print(f'  trial {i} firewall={enabled} HTTP {status} code={code or "none"} type={error_type or "none"}', flush=True)
                    else:
                        print(f'  trial {i} firewall={enabled} ERROR {type(e).__name__}', flush=True)
                data['trials'].append(row)
    # Atomic write: do not leave partially serialized results on interruption.
    temp = OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, OUTPUT)
    print(f'Saved {len(data["trials"])} trial records to {OUTPUT}', flush=True)
    print('REVIEW THIS FILE before committing. Never commit credentials or private user data.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--scenarios', default='javascript,opacity,class,benign,newsletter,authorized')
    a = p.parse_args()
    asyncio.run(export(a.repeats, [x.strip() for x in a.scenarios.split(',') if x.strip()]))
