"""Airlock v4: evidence-grounded, read-only provenance of recorded agent trials.

A provenance graph describes *recorded processing stages*. It does NOT claim
causal attribution for a model's reasoning or reconstruct missing DOM snapshots.
"""
from __future__ import annotations

from hashlib import sha256
from fastapi import APIRouter, HTTPException, Query
from .scenarios import SCENARIOS
from .studio import replay_data
from .trust_policy import compile_trusted_intent

router = APIRouter(prefix="/api/provenance", tags=["Recorded security provenance"])


def _cut(value: object, size: int = 380) -> str:
    return str(value if value is not None else "")[:size]


def _node(key: str, label: str, layer: str, state: str, evidence: str,
          source: str, observed: bool, note: str = "") -> dict:
    return {"id": key, "label": label, "layer": layer, "state": state,
            "evidence": _cut(evidence, 1200), "source": source,
            "observed": observed, "note": note}


def _trial(rows: list, scenario_id: str, n: int, firewall_on: bool) -> dict | None:
    for row in rows:
        if (isinstance(row, dict) and row.get("scenario_id") == scenario_id
            and row.get("trial") == n and row.get("firewall_on") is firewall_on):
            return row
    return None


def _graph(scenario_id: str, trial_number: int, firewall_on: bool, row: dict | None,
           model: str | None) -> dict:
    if not row:
        return {"available": False, "firewall_on": firewall_on, "trial": trial_number,
                "reason": "No matching recorded trial; nothing was reconstructed."}
    if not row.get("ok"):
        return {"available": False, "firewall_on": firewall_on, "trial": trial_number,
                "reason": "Recorded trial failed; it cannot be treated as a successful defense.",
                "failure_stage": _cut(row.get("stage"), 60),
                "failure_type": _cut(row.get("error_type"), 80)}
    result = row.get("result") or {}
    if not isinstance(result, dict):
        return {"available": False, "firewall_on": firewall_on, "trial": trial_number,
                "reason": "Recorded trial has no usable result."}
    scenario = SCENARIOS[scenario_id]
    trusted = compile_trusted_intent(scenario["task"])
    trace = result.get("trace") if isinstance(result.get("trace"), list) else []
    firewall_events = [e for e in trace if isinstance(e, dict) and e.get("event") == "firewall"]
    tool_events = [e for e in trace if isinstance(e, dict) and e.get("event") == "tool_call"]
    context_snippet = _cut(firewall_events[0].get("content_sent"), 240) if firewall_events else ""
    attempts = int(result.get("attempts") or 0)
    denied = int(result.get("denied") or 0)
    outbox = result.get("outbox") if isinstance(result.get("outbox"), list) else []
    hijacked = bool(result.get("hijacked"))
    path = "protected" if firewall_on else "unprotected"
    html_digest = sha256(scenario["html"].encode("utf-8")).hexdigest()[:16]
    nodes = [
        _node("user", "Trusted user request", "authority", "trusted", scenario["task"],
              "server-owned scenario catalog", True, "Permissions originate here; page text has no authority."),
        _node("page", "Retrieved webpage", "source", "untrusted", f"Scenario: {scenario['title']} · HTML SHA-256 prefix: {html_digest}",
              "server-owned scenario HTML", True, "This is the scenario supplied to the browser, not a live Internet crawl."),
        _node("render", "Chromium visibility decision", "perception", _cut(row.get("scanner_verdict"), 30) or "unknown",
              _cut(row.get("scan_reason"), 340), "recorded scanner verdict", bool(row.get("scanner_verdict")),
              "Recorded verdict; per-segment DOM geometry is not part of the LLM replay."),
        _node("context", "Agent context boundary", "input gate", "blocked" if firewall_on and row.get("scanner_verdict") == "block" else path,
              context_snippet or "No context excerpt recorded", "recorded agent trace (excerpt up to 240 characters)",
              bool(firewall_events), "An excerpt proves what was logged, not the full text supplied to the model."),
        _node("model", "Model response", "inference", "observed", _cut(result.get("answer"), 650) or "No response text recorded",
              f"recorded {model or 'LLM'} trial", True, "Model motivations cannot be inferred from outcome or tool-call logs."),
        _node("tool", "Tool proposals", "tool", "attempted" if attempts else "no-attempt",
              f"{attempts} recorded proposal(s)" + (" · " + " | ".join(
                  f"{_cut(e.get('tool'),36)} → {_cut(e.get('to'),75)}" for e in tool_events[:3]) if tool_events else ""),
              "recorded model tool-call trace", True,
              "No tool proposal means the Action Gateway was not exercised in this trial." if not attempts else "Tool proposals are separate from actions executed."),
        _node("policy", "Action authorization", "action gate",
              "not-invoked" if not attempts else "disabled" if not firewall_on else "denied" if denied else "allowed",
              "No gateway evaluation because no tool was proposed" if not attempts else
              (f"{denied} denial(s) / {attempts} proposal(s) · " + ", ".join(
                  _cut(e.get("policy_code") or "not recorded", 40) for e in tool_events[:3])),
              "recorded execution trace", bool(tool_events),
              "Protection OFF does not enforce the trusted-intent action policy." if not firewall_on else
              "An absence of denials does not prove the gate rejected an attack."),
        _node("effect", "Fake outbox outcome", "effect",
              "unauthorized" if hijacked else "authorized" if outbox else "none",
              f"{len(outbox)} fake email(s) written; unauthorized outcome = {str(hijacked).lower()}" +
              (" · recipient(s): " + ", ".join(_cut(item.get("to"), 90)
                    for item in outbox[:3] if isinstance(item, dict)) if outbox else ""),
              "recorded in-memory fake outbox", True, "No real SMTP, external email, or inbox integration is used."),
    ]
    edges = [
        {"from": "page", "to": "render", "kind": "processing", "note": "Page rendered for scanner"},
        {"from": "render", "to": "context", "kind": "processing", "note": "Input gate decides what context is supplied"},
        {"from": "user", "to": "context", "kind": "authority", "note": "Trusted task remains the authority"},
        {"from": "context", "to": "model", "kind": "processing", "note": "Model receives context"},
        {"from": "model", "to": "tool", "kind": "observed" if attempts else "pipeline", "note": "Observed proposals only when recorded"},
        {"from": "user", "to": "policy", "kind": "authority", "note": "Tool permission derives only from trusted task"},
        {"from": "tool", "to": "policy", "kind": "observed" if attempts else "pipeline", "note": "Authorization invoked only on proposal"},
        {"from": "policy", "to": "effect", "kind": "observed" if attempts else "pipeline", "note": "Only allowed proposals reach fake outbox"},
    ]
    return {"available": True, "firewall_on": firewall_on, "trial": trial_number,
            "scenario_id": scenario_id, "nodes": nodes, "edges": edges,
            "measured": {"attempts": attempts, "denied": denied, "fake_outbox": len(outbox),
                         "hijacked": hijacked, "duration_ms": row.get("duration_ms")},
            "grounding": "Graph nodes summarize recorded execution and trusted scenario inputs. Edges show the pipeline structure, not proven causal influence on model reasoning."}


def compare(scenario_id: str, trial_number: int, data: dict | None = None) -> dict:
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    if trial_number < 1 or trial_number > 100:
        raise HTTPException(status_code=422, detail="Trial number must be 1 to 100")
    data = data if data is not None else replay_data()
    rows = data.get("trials") or []
    if not isinstance(rows, list):
        rows = []
    off = _graph(scenario_id, trial_number, False, _trial(rows, scenario_id, trial_number, False), data.get("model"))
    on = _graph(scenario_id, trial_number, True, _trial(rows, scenario_id, trial_number, True), data.get("model"))
    return {"scenario": {"id": scenario_id, "title": SCENARIOS[scenario_id]["title"],
                         "description": SCENARIOS[scenario_id]["description"],
                         "task": SCENARIOS[scenario_id]["task"]},
            "model": data.get("model"), "generated_at": data.get("generated_at"),
            "off": off, "on": on,
            "disclaimer": "Read-only historical runs, not simultaneous or causally paired counterfactuals. No invented actions or DOM coordinates. Live rescan is a separate observation."}


@router.get("/overview")
def overview():
    data = replay_data()
    trials = data.get("trials") or []
    choices = []
    for sid, scenario in SCENARIOS.items():
        numbered = sorted({r.get("trial") for r in trials if isinstance(r, dict)
                          and r.get("scenario_id") == sid and isinstance(r.get("trial"), int)
                          and r.get("trial") > 0})
        choices.append({"id": sid, "title": scenario["title"],
                        "description": scenario["description"], "trial_numbers": numbered[:100]})
    return {"scenarios": choices, "model": data.get("model"),
            "generated_at": data.get("generated_at"), "trial_count": len(trials),
            "privacy": "Only reviewed, exported trial data is served; verify contents before committing."}


@router.get("/compare")
def compare_api(scenario_id: str = Query(max_length=80), trial: int = Query(default=1, ge=1, le=100)):
    return compare(scenario_id, trial)
