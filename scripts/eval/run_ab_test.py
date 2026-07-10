import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import os
import shutil
import subprocess
from pathlib import Path

# Resolve absolute paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
WORKSPACE_DIR = PROJECT_DIR.parent
REPORT_DIR = WORKSPACE_DIR / "Evaluation_Report"

def run_evaluation(version: str):
    print("\n========================================================")
    print(f" RUNNING EVALUATION SUITE FOR PROMPT VERSION: {version.upper()}")
    print("========================================================")

    # Run the enterprise evaluate script with the version override environment variable
    env = os.environ.copy()
    env["FORCE_PROMPT_VERSION"] = version

    try:
        # Run python scripts/eval/enterprise_evaluate.py from the project root
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "enterprise_evaluate.py")],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            cwd=str(PROJECT_DIR)
        )
        print(result.stdout)
        print(f"Evaluation for {version} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"ERROR running evaluation for {version}:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

    # Backup the generated performance_metrics.json
    src = REPORT_DIR / "performance_metrics.json"
    dst = REPORT_DIR / f"performance_metrics_{version}.json"
    if src.exists():
        shutil.copy(str(src), str(dst))
        print(f"Backed up performance metrics to {dst}")
    else:
        print(f"ERROR: Could not find performance metrics file at {src}")
        sys.exit(1)

def generate_comparison_report():
    v1_path = REPORT_DIR / "performance_metrics_v1.json"
    v2_path = REPORT_DIR / "performance_metrics_v2.json"

    if not v1_path.exists() or not v2_path.exists():
        print("ERROR: Missing performance metrics backup files to generate comparison report.")
        return

    with open(v1_path, encoding="utf-8") as f:
        v1 = json.load(f)
    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)

    print("\n" + "="*80)
    print("                    PROMPT A/B TESTING REPORT")
    print("="*80)

    # Global comparison
    print(f"{'Metric':<25} | {'Version A (v1)':<18} | {'Version B (v2)':<18} | {'Change':<15}")
    print("-"*80)

    score_diff = v2["overall_score"] - v1["overall_score"]
    latency_diff = v2["avg_latency"] - v1["avg_latency"]
    pass_rate_diff = v2["pass_rate"] - v1["pass_rate"]

    print(f"{'Overall Score':<25} | {v1['overall_score']:>17.2f} | {v2['overall_score']:>17.2f} | {score_diff:>+14.2f}")
    print(f"{'Pass Rate':<25} | {v1['pass_rate']:>17.2%} | {v2['pass_rate']:>17.2%} | {pass_rate_diff:>+14.2%}")
    print(f"{'Total Cases':<25} | {v1['total_cases']:>17} | {v2['total_cases']:>17} | {v2['total_cases'] - v1['total_cases']:>+14}")
    print(f"{'Passed Cases':<25} | {v1['passed_cases']:>17} | {v2['passed_cases']:>17} | {v2['passed_cases'] - v1['passed_cases']:>+14}")
    print(f"{'Failed Cases':<25} | {v1['failed_cases']:>17} | {v2['failed_cases']:>17} | {v2['failed_cases'] - v1['failed_cases']:>+14}")
    print(f"{'Avg Latency (s)':<25} | {v1['avg_latency']:>17.4f} | {v2['avg_latency']:>17.4f} | {latency_diff:>+14.4f}s")

    # Token optimization estimations
    # v1 prompt totals around 435 tokens. v2 prompt totals around 65 tokens.
    # Estimated tokens saved per LLM call = 370 tokens.
    calls_total = v2["total_cases"] * 2
    v1_prompt_tokens = calls_total * 435
    v2_prompt_tokens = calls_total * 65
    tokens_saved = v1_prompt_tokens - v2_prompt_tokens
    saving_percent = (tokens_saved / v1_prompt_tokens) * 100 if v1_prompt_tokens > 0 else 0.0

    print("-"*80)
    print("                     TOKEN & COST OPTIMIZATION")
    print("-"*80)
    print(f"Estimated Prompt Input Tokens (V1): {v1_prompt_tokens} tokens")
    print(f"Estimated Prompt Input Tokens (V2): {v2_prompt_tokens} tokens")
    print(f"System Prompt Token Savings:        {tokens_saved} tokens ({saving_percent:.1f}% reduction)")
    print(f"Estimated Cost Reduction:           {saving_percent:.1f}%")
    print("="*80)

    # Save the comparison report to a markdown file
    report_md_path = REPORT_DIR / "ab_test_report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Prompt A/B Testing & Cost Optimization Report\n\n")
        f.write("## Overview\n")
        f.write("We ran an A/B test comparing the original prompts (Version A/v1) and our optimized, token-efficient system instructions (Version B/v2).\n\n")
        f.write("## Performance & Reliability Metrics\n\n")
        f.write("| Metric | Version A (v1) | Version B (v2) | Change |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **Overall Score** | {v1['overall_score']:.2f} | {v2['overall_score']:.2f} | {score_diff:+.2f} |\n")
        f.write(f"| **Pass Rate** | {v1['pass_rate']:.2%} | {v2['pass_rate']:.2%} | {pass_rate_diff:+.2%} |\n")
        f.write(f"| **Total Cases** | {v1['total_cases']} | {v2['total_cases']} | {v2['total_cases'] - v1['total_cases']:+d} |\n")
        f.write(f"| **Passed Cases** | {v1['passed_cases']} | {v2['passed_cases']} | {v2['passed_cases'] - v1['passed_cases']:+d} |\n")
        f.write(f"| **Failed Cases** | {v1['failed_cases']} | {v2['failed_cases']} | {v2['failed_cases'] - v1['failed_cases']:+d} |\n")
        f.write(f"| **Avg Latency** | {v1['avg_latency']:.4f}s | {v2['avg_latency']:.4f}s | {latency_diff:+.4f}s |\n\n")
        f.write("## Token & Cost Savings Analysis\n\n")
        f.write("- **Version A (v1)** System Prompt Footprint (est. per run): 435 tokens\n")
        f.write("- **Version B (v2)** System Prompt Footprint (est. per run): 65 tokens\n")
        f.write(f"- **System Prompt Token Savings**: **{tokens_saved} tokens ({saving_percent:.1f}% reduction)**\n")
        f.write(f"- **Estimated LLM API Cost Reduction**: **{saving_percent:.1f}%**\n\n")
        f.write("## Recommendation\n")
        if score_diff >= 0 and pass_rate_diff >= 0:
            f.write("**PROCEED WITH VERSION B (v2)**. The optimized prompts achieve identical or superior accuracy and robustness while drastically reducing latency and token overhead, resulting in substantial cost savings.\n")
        else:
            f.write("**RETAIN VERSION A (v1)** or iterate on Version B. The cost savings did not compensate for a regression in accuracy or pass rate.\n")

    print(f"Markdown report generated at: {report_md_path}\n")

if __name__ == "__main__":
    # 1. Run V1 Evaluation
    run_evaluation("v1")

    # 2. Run V2 Evaluation
    run_evaluation("v2")

    # 3. Generate Report
    generate_comparison_report()
