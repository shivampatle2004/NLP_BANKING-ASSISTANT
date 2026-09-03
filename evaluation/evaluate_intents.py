"""
BankSathi — Intent Classifier Evaluation Script

Runs evaluation on the held-out test suite (evaluation/test_queries.json),
computes Top-1 and Top-3 accuracy metrics, generates classification reports,
and persists an evaluation report artifact to outputs/intent_evaluation_report.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nlp.intent_classifier import IntentClassifier

TEST_PATH = PROJECT_ROOT / "evaluation" / "test_queries.json"
MODEL_PATH = PROJECT_ROOT / "models" / "intent_classifier.joblib"
OUTPUT_REPORT_PATH = PROJECT_ROOT / "outputs" / "intent_evaluation_report.json"


def run_evaluation(
    test_path: Path = TEST_PATH,
    model_path: Path = MODEL_PATH,
    output_path: Path = OUTPUT_REPORT_PATH,
    min_accuracy_threshold: float = 0.88,
) -> dict:
    """Run full intent evaluation and generate report."""
    print("=" * 65)
    print("BankSathi — Intent Evaluation Benchmark")
    print("=" * 65)

    clf = IntentClassifier()
    if model_path.exists():
        print(f"[1/4] Loading trained model artifact from: {model_path}")
        clf.load(model_path=model_path)
    else:
        print("[1/4] Model artifact not found. Training model now...")
        clf.train()
        clf.save(model_path=model_path)

    print(f"[2/4] Loading held-out test cases from: {test_path}")
    eval_results = clf.evaluate(test_path=test_path)

    total = eval_results["total_queries"]
    top1_hits = eval_results["top1_hits"]
    top1_acc = eval_results["top1_accuracy"]
    top3_hits = eval_results["top3_hits"]
    top3_acc = eval_results["top3_accuracy"]
    mismatches = eval_results["mismatches"]

    print("[3/4] Evaluation Results:")
    print(f"      Total Test Queries: {total}")
    print(f"      Top-1 Accuracy:     {top1_acc * 100:.2f}% ({top1_hits}/{total})")
    print(f"      Top-3 Accuracy:     {top3_acc * 100:.2f}% ({top3_hits}/{total})")
    print(f"      Total Mismatches:   {len(mismatches)}")

    if mismatches:
        print("\n  Detailed Mismatches:")
        for idx, m in enumerate(mismatches, 1):
            print(f"    {idx}. \"{m['query']}\"")
            print(f"       Expected:  {m['expected']}")
            print(f"       Predicted: {m['predicted']} ({m['confidence']*100:.1f}%)")

    report_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_dataset": str(test_path),
        "model_artifact": str(model_path),
        "total_queries": total,
        "top1_hits": top1_hits,
        "top1_accuracy": top1_acc,
        "top3_hits": top3_hits,
        "top3_accuracy": top3_acc,
        "num_mismatches": len(mismatches),
        "mismatches": mismatches,
        "classification_report": eval_results["classification_report"],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)
    print(f"\n[4/4] Saved evaluation report to: {output_path}")

    passed = top1_acc >= min_accuracy_threshold
    print("=" * 65)
    print(f"Status: {'PASSED' if passed else 'FAILED'} (Benchmark threshold >= {min_accuracy_threshold * 100:.1f}%)")
    print("=" * 65)

    return report_payload


if __name__ == "__main__":
    report = run_evaluation()
    if report["top1_accuracy"] < 0.88:
        sys.exit(1)
