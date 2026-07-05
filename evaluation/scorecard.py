import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
SCORECARD_JSON = EVAL_DIR / "scorecard.json"
METRICS_JSON = EVAL_DIR / "metrics.json"

def display_scorecard():
    if not SCORECARD_JSON.exists() or not METRICS_JSON.exists():
        print("[Scorecard] Error: Scorecard or metrics JSON files do not exist.")
        return
        
    with open(SCORECARD_JSON, "r", encoding="utf-8") as f:
        scorecard = json.load(f)
    with open(METRICS_JSON, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    print("=" * 60)
    print("                 EXPENSE AUDIT BOT SCORECARD")
    print("=" * 60)
    print(f"  Overall AI Score:          {scorecard['overall_ai_score']}%")
    print(f"  Production Readiness:      {scorecard['production_readiness_score']}%")
    print(f"  Capstone Readiness:        {scorecard['capstone_readiness_score']}%")
    print(f"  Enterprise Readiness:      {scorecard['enterprise_readiness_score']}%")
    print("-" * 60)
    print("  Key Subsystem Metrics:")
    print(f"    OCR Accuracy:            {metrics['ocr_accuracy']:.1%}")
    print(f"    Policy Enforcement:      {metrics['policy_accuracy']:.1%}")
    print(f"    Security Integrity:      {metrics['security_accuracy']:.1%}")
    print(f"    Average Latency:         {metrics['latency_stats']['mean']} seconds")
    print(f"    95% Confidence Interval: {metrics['latency_stats']['confidence_interval_95']} seconds")
    print(f"    Peak Memory Usage:       {metrics['memory_stats']['peak_mb']} MB")
    print("=" * 60)

if __name__ == "__main__":
    display_scorecard()
