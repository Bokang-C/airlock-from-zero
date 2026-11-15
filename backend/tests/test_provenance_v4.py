from fastapi import HTTPException
import pytest
from airlock.provenance import compare
from airlock.scenarios import SCENARIOS


def row(scenario='javascript', on=False, attempts=1, denied=0, hijacked=True, outbox=None):
    outbox = outbox if outbox is not None else [{'to': 'audit-drop@example.invalid', 'subject': 'x', 'body': 'x'}]
    traces = [{'event':'firewall', 'content_sent':'Fetched page excerpt'}]
    if attempts:
        traces.append({'event':'tool_call','tool':'send_email','to':'audit-drop@example.invalid',
                       'policy_code':'RECIPIENT_MISMATCH' if denied else 'FIREWALL_OFF'})
    return {'scenario_id':scenario,'firewall_on':on,'trial':1,'ok':True,
            'scanner_verdict':'block','scan_reason':'Hidden injection detected',
            'result': {'answer':'Summary','attempts':attempts,'denied':denied,
                       'hijacked':hijacked,'outbox':outbox,'trace':traces}}


def get(graph, id):
    return next(n for n in graph['nodes'] if n['id'] == id)


def test_provenance_reflects_real_records_without_inventing_actions():
    off = row()
    on = row(on=True,attempts=0,denied=0,hijacked=False,outbox=[])
    result=compare('javascript',1,{'model':'gpt-test','trials':[off,on]})
    assert result['off']['measured']['hijacked'] is True
    assert result['off']['measured']['fake_outbox'] == 1
    assert get(result['on'],'tool')['state'] == 'no-attempt'
    assert get(result['on'],'policy')['state'] == 'not-invoked'
    assert get(result['on'],'effect')['state'] == 'none'
    assert get(result['off'],'policy')['state'] == 'disabled'
    assert len(result['on']['nodes']) == 8


def test_provenance_observed_action_denial_is_not_fabricated():
    on = row(on=True,attempts=1,denied=1,hijacked=False,outbox=[])
    result=compare('javascript',1,{'trials':[on]})
    assert result['off']['available'] is False
    assert get(result['on'],'policy')['state'] == 'denied'
    assert result['on']['measured']['denied'] == 1


def test_authorized_outcome_not_marked_hijack():
    mail={'to':'reviewer@example.invalid','subject':'good','body':'summary'}
    row1=row(scenario='authorized',on=True,attempts=1,denied=0,hijacked=False,outbox=[mail])
    result=compare('authorized',1,{'trials':[row1]})
    assert get(result['on'],'effect')['state'] == 'authorized'
    assert 'reviewer@example.invalid' in get(result['on'],'effect')['evidence']


def test_unknown_scenario_fails_closed():
    with pytest.raises(HTTPException) as e:
        compare('arbitrary',1,{'trials':[]})
    assert e.value.status_code==404


def test_missing_or_failed_trials_not_treated_as_success():
    result=compare('javascript',1,{'trials':[{'scenario_id':'javascript','trial':1,'firewall_on':False,'ok':False,'error_type':'TimeoutError'}]})
    assert result['off']['available'] is False
    assert result['on']['available'] is False


def test_scenario_html_digest_but_not_full_html_exposed():
    d=compare('javascript',1,{'trials':[row()]})['off']
    assert 'SHA-256 prefix' in get(d,'page')['evidence']
    assert SCENARIOS['javascript']['html'] not in str(d)
