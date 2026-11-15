import pytest
from fastapi import HTTPException
from airlock import llm_budget


@pytest.mark.asyncio
async def test_llm_budget_caps_requests(monkeypatch):
    monkeypatch.setenv('AIRLOCK_LLM_HOURLY_LIMIT','2')
    monkeypatch.setenv('AIRLOCK_LLM_DAILY_LIMIT','2')
    monkeypatch.setattr(llm_budget,'_hour',None)
    monkeypatch.setattr(llm_budget,'_day',None)
    monkeypatch.setattr(llm_budget,'_hour_count',0)
    monkeypatch.setattr(llm_budget,'_day_count',0)
    await llm_budget.consume()
    await llm_budget.consume()
    with pytest.raises(HTTPException) as e:
        await llm_budget.consume()
    assert e.value.status_code==429


@pytest.mark.asyncio
async def test_llm_slot_releases_after_error():
    with pytest.raises(ValueError):
        async with llm_budget.inference_slot():
            raise ValueError('test')
    async with llm_budget.inference_slot():
        assert True
