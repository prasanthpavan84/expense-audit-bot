import subprocess
import sys
from pathlib import Path

# Force UTF-8 encoding on Windows to prevent output stream encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FROZEN_DIRS = [
    "app",
    "core",
    "workflow",
    "orchestrator",
    "security",
    "agents",
    "business_rules",
    "prompts",
    "graph",
    "routing"
]

def check_imports():
    print("[1] Validating critical Python module imports...")
    sys.path.insert(0, str(PROJECT_ROOT))
    modules = [
        "app.agent",
        "evaluation.evaluation_metrics",
        "evaluation.performance",
        "evaluation.reports",
        "evaluation.benchmark_runner"
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"  [OK] {mod} imported successfully.")
        except Exception as e:
            print(f"  [FAIL] Failed to import {mod}: {e}")
            return False
    return True

def check_git_status():
    print("[2] Verifying core directories are untouched and frozen...")
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        print("  [FAIL] Git command failed.")
        return False

    lines = res.stdout.strip().split("\n")
    modified_core = []

    for line in lines:
        if not line:
            continue
        status, filepath = line[:2], line[3:].replace("\\", "/")

        # Exclude dynamic runtime data files
        if filepath == "app/database.json" or "app/evaluation/" in filepath:
            continue

        path_parts = Path(filepath).parts

        # Check if any modified file is within a frozen directory
        for fd in FROZEN_DIRS:
            if fd in path_parts:
                modified_core.append(filepath)

    if modified_core:
        print("  [FAIL] VIOLATION: The following frozen core files have changes:")
        for mc in modified_core:
            print(f"    - {mc}")
        return False

    print("  [OK] Verification success: All core directories remain untouched.")
    return True

def main():
    print("=" * 80)
    print("  STATIC CODE VALIDATION & DEPLOYMENT HEALTH CHECK")
    print("=" * 80)

    ok = True
    ok = ok and check_imports()
    ok = ok and check_git_status()

    print("\n" + "=" * 80)
    if ok:
        print("  STATIC VALIDATION: COMPLIANT (PASS)")
        sys.exit(0)
    else:
        print("  STATIC VALIDATION: NON-COMPLIANT (FAIL)")
        sys.exit(1)

if __name__ == "__main__":
    main()
