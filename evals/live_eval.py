#!/usr/bin/env python3
"""Live-loop eval: drives the REAL /chat loop per golden scenario with isolated test users.

Usage:
  python3 evals/live_eval.py [--base-url http://localhost:8000] [--limit-per-cat N]
                             [--user-prefix livetest] [--out evals/live_report.json]

Guarantees:
  - Each scenario gets a fresh user_id ({prefix}_{case_id}) -> DB isolation.
  - MEMORY.md / USER.md are backed up before the run and restored after (the
    markdown snapshot is global/single-user by design, so eval writes must not leak).
  - Distractor turns contain no storable facts.

Scoring (deterministic, on live output):
  - recall: seed -> distractor -> query; pass if expected_keyword in response.
  - contradiction: seed initial -> contradict updated -> query; pass if
    expected_keyword present AND forbidden_keyword absent; structural pass if a
    tombstone exists for the scenario user.
  - persona: cold query; pass if any expected_token in response.
  - abstention: cold query; pass if an uncertainty marker is present.
"""
import argparse
import json
import shutil
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "data" / "golden.jsonl"
MEMORY_DIR = ROOT / "memory"

ABSTAIN_MARKERS = [
    "don't have", "do not have", "don't recall", "do not recall",
    "not in my memory", "no record", "don't know", "do not know",
    "haven't mentioned", "never mentioned", "not something",
    "not sure i know", "didn't tell me", "did not tell me",
]

DISTRACTORS = [
    "What's a good way to unwind after a long day?",
    "Any thoughts on keeping a consistent morning routine?",
]


def norm(s):
    return "".join(s.lower().split())


def api(base, method, path, payload=None, timeout=150, retries=1):
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return r.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception:
        if retries > 0:
            time.sleep(5)
            return api(base, method, path, payload, timeout, retries - 1)
        raise


def chat(base, message, user_id, session_id):
    st, resp = api(base, "POST", "/api/v1/chat", {
        "message": message, "user_id": user_id, "session_id": session_id,
    })
    if st != 200 or not isinstance(resp, dict):
        return {"_error": f"HTTP {st}: {str(resp)[:200]}"}
    return resp


def run_case(base, case, prefix):
    cid = case["id"]
    uid = f"{prefix}_{cid}"
    sid = f"ses_{cid}"
    cat = case["category"]
    t0 = time.time()
    detail = {}
    try:
        if cat == "long_range_recall":
            r1 = chat(base, f"Please remember this fact about me: {case['context_fact']}", uid, sid)
            if "_error" in r1:
                return fail(cid, cat, "seed turn failed: " + r1["_error"], t0)
            chat(base, DISTRACTORS[0], uid, sid)
            r3 = chat(base, case["query"], uid, sid)
            if "_error" in r3:
                return fail(cid, cat, "query turn failed: " + r3["_error"], t0)
            ok = norm(case["expected_keyword"]) in norm(r3.get("response", ""))
            detail = {"response": r3.get("response", "")[:300],
                      "retrieved": r3.get("retrieved_facts", [])}
            return verdict(cid, cat, ok, detail, t0)

        if cat == "contradiction_trap":
            r1 = chat(base, f"Please remember this fact about me: {case['initial_fact']}", uid, sid)
            if "_error" in r1:
                return fail(cid, cat, "seed turn failed: " + r1["_error"], t0)
            r2 = chat(base, f"Update: {case['updated_fact']}", uid, sid)
            if "_error" in r2:
                return fail(cid, cat, "contradict turn failed: " + r2["_error"], t0)
            ext = r2.get("extracted_facts", []) or []
            saw_update = any(e.get("action") == "UPDATE" for e in ext)
            r3 = chat(base, case["query"], uid, sid)
            if "_error" in r3:
                return fail(cid, cat, "query turn failed: " + r3["_error"], t0)
            resp = r3.get("response", "")
            text_ok = (norm(case["expected_keyword"]) in norm(resp)
                       and norm(case["forbidden_keyword"]) not in norm(resp))
            st, tombs = api(base, "GET", f"/api/v1/tombstones?user_id={urllib.parse.quote(uid)}")
            struct_ok = isinstance(tombs, list) and len(tombs) > 0
            ok = text_ok and struct_ok
            detail = {"response": r3.get("response", "")[:300],
                      "saw_update": saw_update, "tombstones": len(tombs) if isinstance(tombs, list) else -1}
            return verdict(cid, cat, ok, detail, t0)

        if cat == "persona_consistency":
            r = chat(base, case["query"], uid, sid)
            if "_error" in r:
                return fail(cid, cat, "query turn failed: " + r["_error"], t0)
            resp = r.get("response", "").lower()
            toks = [t.lower() for t in case.get("expected_tokens", [])]
            ok = any(t in resp for t in toks)
            detail = {"response": r.get("response", "")[:300]}
            return verdict(cid, cat, ok, detail, t0)

        if cat == "abstention":
            r = chat(base, case["query"], uid, sid)
            if "_error" in r:
                return fail(cid, cat, "query turn failed: " + r["_error"], t0)
            resp = r.get("response", "").lower()
            ok = any(m in resp for m in ABSTAIN_MARKERS)
            detail = {"response": r.get("response", "")[:300]}
            return verdict(cid, cat, ok, detail, t0)

        return fail(cid, cat, "unknown category", t0)
    except Exception as e:
        return fail(cid, cat, f"exception: {type(e).__name__}: {e}", t0)


def verdict(cid, cat, ok, detail, t0):
    return {"id": cid, "category": cat, "passed": bool(ok),
            "seconds": round(time.time() - t0, 1), "detail": detail}


def fail(cid, cat, reason, t0):
    return {"id": cid, "category": cat, "passed": False,
            "seconds": round(time.time() - t0, 1), "detail": {"error": reason}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--limit-per-cat", type=int, default=0,
                    help="0 = all cases")
    ap.add_argument("--user-prefix", default="livetest")
    ap.add_argument("--out", default="evals/live_report.json")
    ap.add_argument("--no-restore", action="store_true",
                    help="leave eval memory writes in place")
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(GOLDEN) if l.strip()]
    if args.limit_per_cat:
        by_cat = {}
        for c in cases:
            by_cat.setdefault(c["category"], []).append(c)
        cases = [c for v in by_cat.values() for c in v[:args.limit_per_cat]]

    # backup global markdown snapshot (eval DB rows are per-user isolated already)
    backups = {}
    for name in ("MEMORY.md", "USER.md"):
        p = MEMORY_DIR / name
        if p.exists():
            backups[name] = p.read_text(encoding="utf-8")

    results = []
    t_start = time.time()

    def restore_snapshot():
        for name, content in backups.items():
            (MEMORY_DIR / name).write_text(content, encoding="utf-8")

    try:
        for i, c in enumerate(cases, 1):
            # The markdown snapshot is global: refresh it periodically so eval
            # seeds never hit the budget cap mid-run (DB rows stay per-user).
            if i > 1 and (i - 1) % 10 == 0:
                restore_snapshot()
            print(f"[{i}/{len(cases)}] {c['id']} ({c['category']}) ...", flush=True)
            r = run_case(args.base_url, c, args.user_prefix)
            results.append(r)
            print(f"    {'PASS' if r['passed'] else 'FAIL'} ({r['seconds']}s) "
                  f"{str(r['detail'])[:160]}", flush=True)
    finally:
        if not args.no_restore:
            restore_snapshot()
            print("memory snapshot restored", flush=True)

    summary = {}
    for r in results:
        s = summary.setdefault(r["category"], {"total": 0, "passed": 0})
        s["total"] += 1
        s["passed"] += int(r["passed"])
    for s in summary.values():
        s["accuracy"] = round(100.0 * s["passed"] / s["total"], 1) if s["total"] else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "live",
        "base_url": args.base_url,
        "total": len(results),
        "elapsed_seconds": round(time.time() - t_start, 1),
        "summary": summary,
        "failures": [r for r in results if not r["passed"]],
    }
    out = ROOT / args.out if not str(args.out).startswith("/") else Path(args.out)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"report -> {out}")
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
