"""Watchdog: completes Round 1 once the Ollama Cloud session quota clears.

The free tier enforces a rolling ~5h session usage limit (429). This script
probes the winning model, and whenever calls succeed it re-runs 05_code.py
(which now resumes: already-successful records are never re-requested).
When every unit x question pair has a successful record, it regenerates the
consolidation draft, the metaphor report and the hub, then exits 0.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "bin" / "python")
MODEL = "kimi-k3:cloud"
QUESTIONS = ["BENEFICIARY", "MECHANISM", "SAFEGUARD", "RESPONSIBILITY",
             "PROJECTED_FUTURE", "ACTANTS", "NATURALISED_ORDER", "AGENCY",
             "MODALITY", "METAPHOR", "DEFINITIONAL"]
MAX_ATTEMPTS = 40
SLEEP_S = 1800  # 30 min between probes


def missing_pairs():
    units = [json.loads(l) for l in (ROOT / "coding" / "units.jsonl").open()]
    want = {(u["unit_id"], q) for u in units for q in QUESTIONS}
    have = set()
    for u in units:
        p = ROOT / "coding" / "round1" / f"{u['doc_id']}.jsonl"
        if not p.exists():
            continue
        for line in p.open():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not rec.get("error"):
                have.add((rec["unit_id"], rec["question"]))
    return len(want - have)


def quota_clear():
    try:
        r = requests.post("http://localhost:11434/api/generate", timeout=180,
                          json={"model": MODEL, "prompt": "Reply: OK", "stream": False})
        return r.status_code == 200
    except requests.RequestException:
        return False


def run(script):
    print(f"--- running {script}", flush=True)
    return subprocess.run([PY, str(ROOT / "scripts" / script)]).returncode


def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        m = missing_pairs()
        print(f"[attempt {attempt}/{MAX_ATTEMPTS}] missing pairs: {m}", flush=True)
        if m == 0:
            break
        if quota_clear():
            print("quota clear -> resuming 05_code.py", flush=True)
            run("05_code.py")
        else:
            print("quota still exhausted (429) or unreachable", flush=True)
        if missing_pairs() == 0:
            break
        time.sleep(SLEEP_S)

    m = missing_pairs()
    if m == 0:
        print("Round 1 COMPLETE -> regenerating consolidation, metaphors, hub", flush=True)
        run("06_consolidate.py")
        run("08_build_site.py")
        print("ALL DONE", flush=True)
        return 0
    print(f"Watchdog exhausted attempts with {m} pairs still missing. "
          f"Re-run scripts/05_code.py manually when the quota clears.", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
