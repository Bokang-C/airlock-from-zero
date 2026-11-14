"""Airlock Attack Replay Studio: read-only real-model trial evidence + safe policy sandbox."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .scenarios import SCENARIOS
from .trust_policy import compile_trusted_intent, authorize_fake_tool
from .browser_budget import status as budget_status

router = APIRouter(prefix="/api/studio", tags=["Attack Replay Studio"])
REPLAY_PATH = Path(__file__).with_name("studio_replays.json")
SCANNER_REPORT = Path(__file__).with_name("scanner_benchmark.json")


class PolicyProbe(BaseModel):
    scenario_id: str = Field(max_length=80)
    tool: str = Field(default="send_email", max_length=80)
    to: str = Field(default="audit-drop@example.invalid", max_length=200)
    subject: str = Field(default="Example summary", max_length=200)
    body: str = Field(default="This is a fake outbox message.", max_length=500)
    used_actions: int = Field(default=0, ge=0, le=20)


def replay_data() -> dict:
    if not REPLAY_PATH.exists():
        return {"schema_version": 1, "kind": "actual-model-trials", "generated_at": None,
                "model": None, "trials": [], "disclaimer": "No recorded trials. Export real traces locally first."}
    try:
        data = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("kind") != "actual-model-trials" or not isinstance(data.get("trials"), list):
            raise ValueError("Bad schema")
        # Bounded responses; no secret keys or arbitrary filesystem access.
        return {**data, "trials": data["trials"][:500]}
    except (OSError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Stored trial data could not be loaded") from None


@router.get("/catalog")
def catalog():
    return {"scenarios": [{"id": k, "title": v["title"], "description": v["description"],
                           "task": v["task"]} for k, v in SCENARIOS.items()],
            "policies": ["only server-owned user intent grants permission", "exact recipient matching",
                         "per-run action budget", "deny unknown tools", "fake outbox only"],
            "browser_budget": budget_status(),
            "note": "Policy Lab evaluates proposed fake tool calls; it never invokes an LLM or sends email."}


@router.get("/replays")
def replays():
    return replay_data()


@router.post("/policy")
def policy_probe(data: PolicyProbe):
    scenario = SCENARIOS.get(data.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    intent = compile_trusted_intent(scenario["task"])
    decision = authorize_fake_tool(intent, data.tool, data.model_dump(exclude={"scenario_id", "tool", "used_actions"}), data.used_actions)
    return {"scenario_id": data.scenario_id, "user_task": scenario["task"], "decision": decision.dump(),
            "effects_performed": 0, "model_called": False,
            "simulation": "Deterministic policy check. No tool is executed and no email is sent."}


@router.get("/scanner-benchmark")
def scanner_benchmark():
    if not SCANNER_REPORT.exists():
        return {"schema_version": 1, "kind": "actual-browser-evaluation",
                "generated_at": None, "cases": [], "method": "No browser benchmark exported yet"}
    try:
        data = json.loads(SCANNER_REPORT.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("kind") != "actual-browser-evaluation" or not isinstance(data.get("cases"), list):
            raise ValueError('Bad schema')
        return {**data, "cases": data["cases"][:100]}
    except (OSError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Stored browser evaluation unavailable") from None
