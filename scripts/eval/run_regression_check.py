import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
EVAL_DIR = WORKSPACE_DIR.parent / "Evaluation_Report"

def main():
    print("=" * 80)
    print("  AUTOMATED REGRESSION AND SLA VERIFICATION (PHASE 10A)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Run 1: Legacy Orchestrator (ENABLE_WORKFLOW_REGISTRY=false)
    # -------------------------------------------------------------------------
    print("\n[1/2] Running production legacy orchestrator benchmark...")
    env_legacy = {**os.environ, "ENABLE_WORKFLOW_REGISTRY": "false", "MOCK_LLM": "True", "PYTHONPATH": str(WORKSPACE_DIR)}
    t0 = time.time()
    res_legacy = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "enterprise_evaluate.py")],
        env=env_legacy,
        capture_output=True,
        text=True
    )
    t_legacy = time.time() - t0

    if res_legacy.returncode != 0:
        print("ERROR: Legacy orchestrator run failed!")
        print(res_legacy.stderr)
        sys.exit(1)

    with open(str(EVAL_DIR / "performance_metrics.json"), encoding="utf-8") as f:
        metrics = json.load(f)

    # -------------------------------------------------------------------------
    # Run 2: Verify Experimental Stub raises NotImplementedError
    # -------------------------------------------------------------------------
    print("\n[2/2] Verifying experimental registry stub fails fast...")
    env_registry = {**os.environ, "ENABLE_WORKFLOW_REGISTRY": "true", "MOCK_LLM": "True", "PYTHONPATH": str(WORKSPACE_DIR)}
    res_registry = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "enterprise_evaluate.py")],
        env=env_registry,
        capture_output=True,
        text=True
    )
    shutil.copy(str(EVAL_DIR / "detailed_results.json"), str(EVAL_DIR / "detailed_results_registry.json"))

    with open(str(EVAL_DIR / "detailed_results_registry.json"), encoding="utf-8") as f:
        registry_cases = json.load(f)

    stub_ok = any("Registry workflow engine planned for Phase 11" in str(c.get("reason", "")) for c in registry_cases)
    if stub_ok:
        print("Experimental registry stub check: PASS (correctly raises NotImplementedError)")
    else:
        print("Experimental registry stub check: FAIL (did not raise expected NotImplementedError)")

    print("\n" + "=" * 50)
    print("  VERIFICATION REPORT")
    print("=" * 50)

    # Check Accuracy
    acc_ok = (metrics["overall_score"] == 100.0)
    print(f"Accuracy Target (100.0%): {metrics['overall_score']}% -> {'PASS' if acc_ok else 'FAIL'}")

    # Check SLA Latency
    avg_latency = metrics["avg_latency"]
    p95_latency = metrics["p95_latency"]
    sla_ok = (avg_latency <= 5.0) and (p95_latency <= 6.0)
    print(f"Latency SLA (Avg <=5s, P95 <=6s): Avg={avg_latency}s, P95={p95_latency}s -> {'PASS' if sla_ok else 'FAIL'}")

    # Compile timestamped report
    from app.governance.evaluation_registry import EvaluationRegistry

    run_metrics = {
        "legacy_score": metrics["overall_score"],
        "passed_cases": metrics["passed_cases"],
        "total_cases": metrics["total_cases"],
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "stub_safeguard_passed": stub_ok,
        "sla_passed": sla_ok,
        "accuracy_passed": acc_ok
    }

    report_path = EvaluationRegistry.write_run_report(run_metrics, str(EVAL_DIR))

    print("\n" + "=" * 50)
    if acc_ok and sla_ok and stub_ok:
        print("  PRODUCTION READY CHECKLIST: COMPLIANT (PASS)")
        print("=" * 50)
        sys.exit(0)
    else:
        print("  PRODUCTION READY CHECKLIST: NON-COMPLIANT (FAIL)")
        print("=" * 50)
        sys.exit(1)

if __name__ == "__main__":
    main()
