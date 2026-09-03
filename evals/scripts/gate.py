import json
import sys
from pathlib import Path

def check_quality_gate(report_path: str = "evals/report.json"):
    path = Path(report_path)
    if not path.exists():
        print(f"❌ Error: Report file {report_path} does not exist. Run run_eval.py first.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)

    cats = report["categories"]
    recall_acc = cats["long_range_recall"]["accuracy"]
    contra_rate = cats["contradiction_trap"]["contradiction_rate"]
    persona_acc = cats["persona_consistency"]["accuracy"]
    abstention_acc = cats["abstention"]["accuracy"]

    failures = []

    print("=" * 60)
    print("🔍 VERIFYING CI HARD QUALITY GATES:")
    print("=" * 60)

    # Gate 1: Contradiction Rate == 0.0%
    if contra_rate > 0.0:
        failures.append(f"❌ Gate 1 FAILED: Contradiction Rate is {contra_rate}% (Target: 0.0%)")
    else:
        print(f"✅ Gate 1 PASSED: Contradiction Rate = {contra_rate}% (Target: 0.0%)")

    # Gate 2: Long-Range Recall >= 85.0%
    if recall_acc < 85.0:
        failures.append(f"❌ Gate 2 FAILED: Long-Range Recall is {recall_acc}% (Target: >= 85.0%)")
    else:
        print(f"✅ Gate 2 PASSED: Long-Range Recall = {recall_acc}% (Target: >= 85.0%)")

    # Gate 3: Persona Consistency >= 85.0%
    if persona_acc < 85.0:
        failures.append(f"❌ Gate 3 FAILED: Persona Consistency is {persona_acc}% (Target: >= 85.0%)")
    else:
        print(f"✅ Gate 3 PASSED: Persona Consistency = {persona_acc}% (Target: >= 85.0%)")

    # Gate 4: Abstention Rate >= 85.0%
    if abstention_acc < 85.0:
        failures.append(f"❌ Gate 4 FAILED: Abstention Accuracy is {abstention_acc}% (Target: >= 85.0%)")
    else:
        print(f"✅ Gate 4 PASSED: Abstention Accuracy = {abstention_acc}% (Target: >= 85.0%)")

    print("=" * 60)
    if failures:
        print("\n".join(failures))
        print("❌ QUALITY GATE FAILED.")
        sys.exit(1)
    else:
        print("🎉 ALL QUALITY GATES PASSED! SYSTEM READY FOR DEPLOYMENT.")
        sys.exit(0)

if __name__ == "__main__":
    report_file = sys.argv[1] if len(sys.argv) > 1 else "evals/report.json"
    check_quality_gate(report_file)
