import json
import pytest
from airlock import agent
from airlock.models import ScanResult


def scan():
    return ScanResult(verdict='allow',reason='Normal content',escalate=False,findings=[],segments=[],
                      human_view='Article',agent_view='Article',sanitized_text='Article',stats={})


@pytest.mark.asyncio
async def test_trusted_user_authorizes_one_fake_email_only(monkeypatch):
    async def fake(messages):
        return {'tool_calls': [
            {'id':'1','function':{'name':'send_email','arguments':json.dumps({'to':'reviewer@example.invalid','subject':'a','body':'b'})}},
            {'id':'2','function':{'name':'send_email','arguments':json.dumps({'to':'reviewer@example.invalid','subject':'a','body':'b'})}}]}
    monkeypatch.setattr(agent, 'call_model', fake)
    res=await agent.demo_run('Please send a fake email to reviewer@example.invalid with this summary.',scan(),True)
    assert len(res['outbox'])==1
    assert res['denied']==1
    assert not res['hijacked']


@pytest.mark.asyncio
async def test_unprotected_wrong_email_is_an_unauthorized_outbox_action(monkeypatch):
    async def fake(messages):
        return {'tool_calls':[{'id':'1','function':{'name':'send_email','arguments':json.dumps({'to':'audit-drop@example.invalid','subject':'a','body':'b'})}}]}
    monkeypatch.setattr(agent, 'call_model', fake)
    res=await agent.demo_run('Please send a fake email to reviewer@example.invalid with this summary.',scan(),False)
    assert res['hijacked']
    assert len(res['outbox'])==1
