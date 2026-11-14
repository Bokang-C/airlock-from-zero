import httpx
import pytest
from airlock.main import app


@pytest.mark.asyncio
async def test_catalog_and_empty_or_real_trials():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        cat=(await client.get('/api/studio/catalog')).json()
        assert any(s['id']=='authorized' for s in cat['scenarios'])
        rep=(await client.get('/api/studio/replays')).json()
        assert rep['kind']=='actual-model-trials'
        assert isinstance(rep['trials'], list)


@pytest.mark.asyncio
async def test_policy_has_no_side_effects():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        denied=await client.post('/api/studio/policy',json={'scenario_id':'javascript','to':'audit-drop@example.invalid'})
        assert denied.status_code==200
        assert not denied.json()['decision']['allowed']
        assert denied.json()['effects_performed']==0
        ok=await client.post('/api/studio/policy',json={'scenario_id':'authorized','to':'reviewer@example.invalid'})
        assert ok.json()['decision']['allowed']
        assert ok.json()['effects_performed']==0
        bad=await client.post('/api/studio/policy',json={'scenario_id':'missing'})
        assert bad.status_code==404
