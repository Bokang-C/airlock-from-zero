"""Run real Chromium on a fixed adversarial corpus, export evidence. No OpenAI key needed.

Command (backend): .\\.venv\\Scripts\\python.exe export_scanner_benchmark.py
Consumes up to 14 browser sessions. Review remote Browserless allowance before use.
"""
import asyncio
import json
import os
from pathlib import Path
from time import perf_counter
from datetime import datetime, timezone
from attack_corpus import CASES
from airlock.pipeline import scan_html

OUTPUT = Path(__file__).resolve().parent / 'airlock' / 'scanner_benchmark.json'


async def main():
    output={'schema_version':1,'kind':'actual-browser-evaluation',
            'generated_at':datetime.now(timezone.utc).isoformat(),'cases':[],
            'method':'One real Chromium scan per fixed case. The target verdict is a test expectation, not measured truth. Failed scans are not passed.'}
    for case in CASES:
        t=perf_counter()
        row={'id':case.id,'family':case.family,'label':case.label,
             'attack':case.attack,'expected':case.expected_verdict}
        try:
            report, _=await scan_html(case.html)
            row.update({'ok':True,'actual':report.verdict,'match':report.verdict==case.expected_verdict,
                        'flagged':report.escalate,'findings':len(report.findings),
                        'visible':report.stats.get('visible',0),'hidden':report.stats.get('hidden',0),
                        'nonvisual':report.stats.get('nonvisual',0),
                        'latency_ms':round((perf_counter()-t)*1000)})
            print(f'{"PASS" if row["match"] else "FAIL"} {case.id}: actual={report.verdict}, expected={case.expected_verdict}',flush=True)
        except Exception as e:
            row.update({'ok':False,'match':False,'error_type':type(e).__name__,
                        'latency_ms':round((perf_counter()-t)*1000)})
            print(f'ERROR {case.id}: {type(e).__name__}: {str(e)[:140]}',flush=True)
        output['cases'].append(row)
    p=OUTPUT.with_suffix('.tmp')
    p.write_text(json.dumps(output,indent=2),encoding='utf-8')
    os.replace(p,OUTPUT)
    passing=sum(x['match'] for x in output['cases'])
    print(f'Benchmark complete: {passing}/{len(output["cases"])} match expectations. Check failures; never edit expected results to hide failures.')
    print(f'Saved: {OUTPUT}')


if __name__=='__main__':
    asyncio.run(main())
