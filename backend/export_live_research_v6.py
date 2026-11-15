r"""Run bounded, LOCAL-ONLY real-model multi-step experiments, review before publishing.

Example (PowerShell from backend):
.\.venv\Scripts\python.exe export_live_research_v6.py --cases recipient-pivot,authorized-action --repeats 1 --confirm-billable
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
from airlock import config
from airlock.live_research import BY_ID, MAX_STEPS, build_summary, run_live_trial, RECORDED_PATH

DEFAULT = 'recipient-pivot,forged-system,authorized-action'
HARD_CALL_CAP = 36


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='Airlock v6 local real-model bounded experiment runner')
    p.add_argument('--cases', default=DEFAULT, help='Comma-separated IDs from the 12 fixed v5 scenarios')
    p.add_argument('--repeats', type=int, default=1, help='Number of paired OFF/ON runs (1–3)')
    p.add_argument('--confirm-billable', action='store_true', help='Required to perform actual OpenAI API calls')
    p.add_argument('--dry-run', action='store_true', help='Only show number of potential API calls')
    return p.parse_args(argv)


def plan(args):
    names = [x.strip() for x in args.cases.split(',') if x.strip()]
    if not names or len(names) != len(set(names)) or len(names) > 6:
        raise ValueError('Select between 1 and 6 unique case IDs')
    if not 1 <= args.repeats <= 3:
        raise ValueError('--repeats must be between 1 and 3')
    if any(x not in BY_ID or len(BY_ID[x].events) > MAX_STEPS for x in names):
        raise ValueError('Unknown or oversized case ID; see /api/live-research/catalog')
    expected_calls = sum(len(BY_ID[x].events) * 2 * args.repeats for x in names)
    if expected_calls > HARD_CALL_CAP:
        raise ValueError(f'Planned {expected_calls} requests exceeds hard cap of {HARD_CALL_CAP}')
    return names, expected_calls


async def collect(names, repeats):
    trials = []
    for name in names:
        case = BY_ID[name]
        for trial_num in range(1, repeats + 1):
            for protected in (False, True):
                lane = 'ON' if protected else 'OFF'
                print(f'Running case={name} trial={trial_num} Airlock={lane}', flush=True)
                try:
                    result = await run_live_trial(case, protected, trial_num)
                    trials.append(result)
                    print(f"  complete: model_calls={result['model_calls']} attempts={result['attempts']} "
                          f"denied={result['denied']} unauthorized_fake_actions={result['unauthorized_fake_actions']}",flush=True)
                except Exception as exc:
                    # Do not output HTTP response bodies, headers, API keys, or tracebacks.
                    status = getattr(getattr(exc, 'response', None), 'status_code', None)
                    message = f'HTTP {status}' if status else type(exc).__name__
                    print(f'  ERROR {message}', flush=True)
                    trials.append({'case_id': name, 'protected': protected, 'trial': trial_num,
                                   'status': 'error', 'error_category': message})
    return trials


def main(argv=None):
    args = parse_args(argv)
    try:
        names, expected_calls = plan(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(f'Fixed cases: {", ".join(names)}')
    print(f'Paired trials per case: {args.repeats}; up to {expected_calls} billable model calls')
    if args.dry_run:
        print('Dry run: no OpenAI calls were made.')
        return 0
    if not args.confirm_billable:
        print('No API calls made. Pass --confirm-billable explicitly to run the paid experiment.')
        return 2
    if not config.OPENAI_API_KEY:
        print('OPENAI_API_KEY is absent; set it in the local backend/.env only.')
        return 2
    trials = asyncio.run(collect(names, args.repeats))
    now = datetime.now(timezone.utc).isoformat()
    result = {
        'schema_version': 1, 'kind': 'actual-multi-step-model-trials',
        'generated_at': now, 'model': config.OPENAI_MODEL,
        'selected_cases': names, 'repeats': args.repeats,
        'method': 'Actual OpenAI tool proposals across server-owned multi-step synthetic scenarios; temporary reviewed memory and fake outbox only.',
        'limitations': 'Small, fixed synthetic attack corpus. Memory review is heuristic; each turn rebuilds context instead of preserving complete chat history. This is not a real-world security guarantee.',
        'public_execution': False, 'trials': trials, 'summary': build_summary(trials),
    }
    # Never silently publish: save to a private staging filename that the API does NOT serve.
    candidate = RECORDED_PATH.with_suffix('.pending.json')
    candidate.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Saved {len(trials)} trials to PRIVATE REVIEW FILE: {candidate}')
    print('Review all data, then copy the pending JSON to live_research_v6.json for read-only public display.')
    print('Never commit backend/.env, credentials, or personal/private user data.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
