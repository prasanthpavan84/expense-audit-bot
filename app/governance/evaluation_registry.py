import json
import os
import datetime
from pathlib import Path
from typing import Dict, Any
from app.governance.validation import validate_evaluation_registry

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"

class EvaluationRegistry:
    _registry_data: Dict[str, Any] = {}
    
    @classmethod
    def load(cls):
        path = REGISTRY_DIR / "evaluations_v3.json"
        if not path.exists():
            raise FileNotFoundError(f"Evaluation registry file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate_evaluation_registry(data)
        cls._registry_data = data
        
    @classmethod
    def get_benchmark_targets(cls) -> Dict[str, Any]:
        if not cls._registry_data:
            cls.load()
        benchmarks = cls._registry_data.get("benchmarks", {})
        return benchmarks.get("latest", {})
        
    @classmethod
    def write_run_report(cls, run_metrics: Dict[str, Any], output_dir: str = "Evaluation_Report") -> str:
        """Writes run metrics to a separate timestamped report file to keep config read-only."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        report_filename = f"evaluation_report_{timestamp}.json"
        report_path = os.path.join(output_dir, report_filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "metrics": run_metrics
            }, f, indent=2)
            
        # Append to historical regression_history.jsonl
        history_path = os.path.join(output_dir, "regression_history.jsonl")
        with open(history_path, "a", encoding="utf-8") as f:
            log_line = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                **run_metrics
            }
            f.write(json.dumps(log_line) + "\n")
            
        print(f"Saved runtime evaluation report to: {report_path}")
        print(f"Appended runtime metrics to history log: {history_path}")
        return report_path

EvaluationRegistry.load()
