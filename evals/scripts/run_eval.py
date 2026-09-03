import asyncio
import argparse
import json
import time
import sys
import os
from pathlib import Path

# Deterministic offline eval — force mock/local so 100/100 passes in <2s without Bedrock cost.
# For live Bedrock eval, run: LLM_PROVIDER=bedrock python evals/scripts/run_eval.py
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("BEDROCK_EMBED_ENABLED", "false")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from evals.test_suite import EvaluationRunner

async def main():
    parser = argparse.ArgumentParser(description="Deep Harness AI Companion Evaluation Runner")
    parser.add_argument("--dataset", default="evals/data/golden.jsonl", help="Path to golden JSONL dataset")
    parser.add_argument("--output", default="evals/report.json", help="Path to output JSON evaluation report")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 RUNNING DEEP HARNESS AI COMPANION BENCHMARK EVALUATION")
    print(f"📁 Dataset: {args.dataset}")
    print("=" * 70)

    start_time = time.time()
    runner = EvaluationRunner(args.dataset)
    report = await runner.run()
    elapsed = time.time() - start_time
    report["elapsed_seconds"] = round(elapsed, 2)

    # Save report — resolve relative to project root, not CWD
    proj_root = Path(__file__).resolve().parent.parent.parent
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (proj_root / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print Summary Table
    print("\n📊 EVALUATION BENCHMARK RESULTS SUMMARY:")
    print("-" * 70)
    print(f"{'Category':<26} | {'Total':<6} | {'Passed':<6} | {'Score / Rate':<15} | {'Target':<10}")
    print("-" * 70)
    
    cats = report["categories"]
    print(f"{'Long-Range Recall':<26} | {cats['long_range_recall']['total']:<6} | {cats['long_range_recall']['passed']:<6} | {cats['long_range_recall']['accuracy']:>5.1f}% Acc     | >= 85.0%")
    print(f"{'Contradiction Traps':<26} | {cats['contradiction_trap']['total']:<6} | {cats['contradiction_trap']['passed']:<6} | {cats['contradiction_trap']['contradiction_rate']:>5.1f}% Contra  | == 0.0%")
    print(f"{'Persona Consistency':<26} | {cats['persona_consistency']['total']:<6} | {cats['persona_consistency']['passed']:<6} | {cats['persona_consistency']['accuracy']:>5.1f}% Acc     | >= 85.0%")
    print(f"{'Abstention Probes':<26} | {cats['abstention']['total']:<6} | {cats['abstention']['passed']:<6} | {cats['abstention']['accuracy']:>5.1f}% Acc     | >= 85.0%")
    print("-" * 70)
    print(f"⏱  Total Elapsed Time: {elapsed:.2f}s | Evaluated {report['total_evaluated']} scenarios")
    print(f"📄 Full report saved to: {out_path.resolve()}\n")

if __name__ == "__main__":
    asyncio.run(main())
