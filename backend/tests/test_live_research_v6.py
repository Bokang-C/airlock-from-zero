import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from fastapi import HTTPException

from airlock import live_research as lr
from airlock.redteam import BY_ID
from airlock.trust_policy import compile_trusted_intent


def model_reply(*, to=None, text='Summary is complete.'):
    if to:
        return {'content': None, 'tool_calls': [{
            'id': 'call_fake', 'type': 'function',
            'function': {'name': 'send_email', 'arguments': json.dumps({
                'to': to, 'subject': 'Synthetic report', 'body': 'Demo summary'})},
        }]}
    return {'content': text}


@pytest.mark.asyncio
async def test_actual_model_proposals_are_denied_by_independent_gateway():
    seen = []

    async def fake(messages):
        seen.append(messages)
        return model_reply(to='audit-drop@example.invalid')

    protected = await lr.run_live_trial(BY_ID['recipient-pivot'], True, model=fake)
    assert protected['model_calls'] == 2
    assert protected['attempts'] == 2
    assert protected['denied'] == 2
    assert protected['fake_outbox'] == []
    assert protected['unauthorized_fake_actions'] is False
    assert all(c == 'RECIPIENT_MISMATCH' for c in protected['tool_policy_codes'])
    assert len(seen) == 2
    assert 'trusted user task' in seen[1][0]['content']

    baseline = await lr.run_live_trial(BY_ID['recipient-pivot'], False, model=fake)
    assert baseline['attempts'] == 2
    assert baseline['denied'] == 0
    assert len(baseline['fake_outbox']) == 2
    assert baseline['unauthorized_fake_actions'] is True


@pytest.mark.asyncio
async def test_legitimate_action_allowed_then_budget_rejects_next_one():
    async def fake(messages):
        return model_reply(to='reviewer@example.invalid')
    result = await lr.run_live_trial(BY_ID['authorized-action'], True, model=fake)
    assert result['model_calls'] == 2
    assert result['attempts'] == 2
    assert result['denied'] == 1
    assert len(result['fake_outbox']) == 1
    assert result['tool_policy_codes'] == ['AUTHORIZED', 'ACTION_BUDGET']
    assert not result['unauthorized_fake_actions']


@pytest.mark.asyncio
async def test_memory_quarantine_keeps_poison_out_of_next_step_context():
    seen = []

    async def fake(messages):
        seen.append(messages)
        return model_reply(text='The facts are available.')

    protected = await lr.run_live_trial(BY_ID['forged-system'], True, model=fake)
    assert protected['memory_quarantined'] >= 1
    assert len(seen) == 2
    assert 'SYSTEM: Ignore' not in seen[1][-1]['content']
    assert all(row['authority_granted'] is False for step in protected['steps']
               for row in [step['memory']])

    seen.clear()
    await lr.run_live_trial(BY_ID['forged-system'], False, model=fake)
    assert 'SYSTEM: Ignore' in seen[1][-1]['content']


@pytest.mark.asyncio
async def test_unknown_tool_or_malformed_payload_is_never_executed():
    async def fake(messages):
        return {'content': '', 'tool_calls': [
            {'id': 'c1', 'function': {'name': 'transfer_funds', 'arguments': '{"to":"audit-drop@example.invalid"}'}},
            {'id': 'c2', 'function': {'name': 'send_email', 'arguments': '{broken'}},
        ]}
    res = await lr.run_live_trial(BY_ID['recipient-pivot'], True, model=fake)
    assert res['denied'] == 4
    assert res['fake_outbox'] == []


@pytest.mark.asyncio
async def test_even_baseline_cannot_store_nonsynthetic_recipients():
    async def fake(messages):
        return model_reply(to='someone@example.com')
    result = await lr.run_live_trial(BY_ID['recipient-pivot'], False, model=fake)
    assert result['attempts'] == 2
    assert result['denied'] == 2
    assert result['fake_outbox'] == []
    assert not result['unauthorized_fake_actions']


@pytest.mark.asyncio
async def test_guard_rejects_external_fabricated_case():
    from dataclasses import replace
    fake_case = replace(BY_ID['recipient-pivot'], id='private-arbitrary-case')
    with pytest.raises(ValueError):
        await lr.run_live_trial(fake_case, True, model=lambda _: model_reply())


def test_recorded_endpoint_is_read_only_and_empty_when_no_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(lr, 'RECORDED_PATH', tmp_path/'missing.json')
    payload = lr.replays()
    assert payload['trials'] == []
    assert payload['public_execution'] is False
    assert len(lr.case_catalog()) == 12
    from fastapi.testclient import TestClient
    from airlock.main import app

    with TestClient(app) as client:
        catalog = client.get("/api/live-research/catalog")
        assert catalog.status_code == 200, catalog.text
        assert catalog.json()["live_inference_from_public_api"] is False

        recorded = client.get("/api/live-research/replays")
        assert recorded.status_code == 200, recorded.text
        assert recorded.json()["trials"] == []
        assert recorded.json()["public_execution"] is False

        assert client.post("/api/live-research/catalog").status_code == 405
        assert client.post("/api/live-research/replays").status_code == 405

def test_bad_recorded_evidence_rejected(tmp_path, monkeypatch):
    bad = tmp_path/'bad.json'
    bad.write_text(json.dumps({'kind': 'wrong', 'trials': []}))
    monkeypatch.setattr(lr, 'RECORDED_PATH', bad)
    with pytest.raises(HTTPException) as exc:
        lr.replay_data()
    assert exc.value.status_code == 503


def test_summary_uses_only_completed_trials():
    result = lr.build_summary([
        {'case_id': 'abc', 'protected': False, 'status': 'completed',
         'unauthorized_fake_actions': True, 'fake_outbox': [{}],
         'attempts': 2, 'denied': 1, 'memory_quarantined': 0},
        {'case_id': 'abc', 'protected': False, 'status': 'error',
         'unauthorized_fake_actions': False},
    ])
    assert len(result) == 1
    assert result[0]['completed_trials'] == 1
    assert result[0]['unauthorized_fake_trials'] == 1
