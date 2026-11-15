import argparse
import pytest

from export_live_research_v6 import plan


def ns(cases, repeats=1):
    return argparse.Namespace(cases=cases, repeats=repeats)


def test_plan_counts_actual_turns():
    names, calls = plan(ns('recipient-pivot,authorized-action'))
    assert names == ['recipient-pivot', 'authorized-action']
    assert calls == 8


@pytest.mark.parametrize('cases,repeats', [
    ('unknown', 1), ('recipient-pivot,recipient-pivot', 1), ('authorized-action', 4),
    ('forged-system,tool-output,recipient-pivot,budget-flood,summary-poison,fake-approval', 3),
])
def test_invalid_cost_plans_rejected(cases, repeats):
    with pytest.raises(ValueError):
        plan(ns(cases, repeats))
