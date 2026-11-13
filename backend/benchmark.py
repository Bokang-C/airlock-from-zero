"""Do not publish rates without collecting real runs against a real model."""
import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
import httpx

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--scenario", default="opacity")
    args = parser.parse_args()
    rows = []
    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(args.repeats):
            for enabled in [False, True]:
                r = await client.post(args.base+"/api/demo", json={"scenario_id":args.scenario,"firewall_on":enabled})
                r.raise_for_status()
                data = r.json()
                row = {"trial":i+1,"firewall_on":enabled,"scenario":args.scenario,
                       "model":data["model"],"hijacked":data["hijacked"],
                       "tool_attempts":data["attempts"],"gate_denials":data["denied"]}
                rows.append(row)
                print(row)
                await asyncio.sleep(8)  # prevent hitting demo endpoint's rate limit
    out = Path(f"benchmark_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print("Saved",out)

if __name__ == "__main__":
    asyncio.run(main())
