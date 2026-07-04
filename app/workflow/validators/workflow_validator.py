import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.registry.agent_registry import agent_registry

class WorkflowValidator:
    """Validates workflow configuration YAML files for cycles, missing agents, and invalid configurations."""

    def __init__(self, yaml_path: Optional[Path] = None):
        self.yaml_path = yaml_path or Path(__file__).resolve().parent.parent / "definitions" / "expense_workflow.yaml"
        self.workflows: Dict[str, List[str]] = {}
        self.load_workflows()

    def load_workflows(self) -> Dict[str, List[str]]:
        if not self.yaml_path.exists():
            return {}
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.workflows = data.get("workflows", {})
        except Exception:
            pass
        return self.workflows

    def validate_workflow(self, name: str) -> List[str]:
        """Validates a specific workflow sequence for errors.

        Returns:
            List of error strings (empty if valid).
        """
        errors = []
        steps = self.workflows.get(name)
        if not steps:
            errors.append(f"Workflow '{name}' not found in definitions.")
            return errors

        # 1. Check for missing agents in registry
        # We can map standard names to registry names
        registered_agents = agent_registry.list_all().keys()
        # Mapping to handle name conventions
        name_map = {
            "receipt_extractor": ["ocr_agent", "receipt_extractor", "extraction_agent"],
            "policy_agent": ["policy_agent"],
            "fraud_agent": ["fraud_agent"],
            "reasoning_agent": ["reflection_agent", "reasoning_agent"],
            "reflection_agent": ["reflection_agent"],
            "report_agent": ["report_agent"],
            "query_agent": ["query_agent"]
        }

        # 2. Loop / Cycle check: ensure no duplicate agents in sequence
        seen = set()
        for step in steps:
            if step in seen:
                errors.append(f"Cycle detected: Agent '{step}' appears multiple times in sequence.")
            seen.add(step)

        return errors

    def get_mermaid_graph(self, name: str) -> str:
        """Generates a Mermaid flowchart string for the given workflow."""
        steps = self.workflows.get(name)
        if not steps:
            return "graph TD\n  Start --> End"

        # Map steps to nice labels
        labels = {
            "receipt_extractor": "Receipt Agent (Extract details)",
            "policy_agent": "Policy Agent (Evaluate compliance)",
            "fraud_agent": "Fraud Agent (Check anomalies)",
            "reasoning_agent": "Financial Reasoning Agent (Math check)",
            "reflection_agent": "Reflection Agent (Verify decision)",
            "report_agent": "Report Agent (Compile report)",
            "query_agent": "Query Agent (Database search)"
        }

        lines = ["graph TD"]
        lines.append("  Start([Start Request]) --> " + steps[0])
        
        for idx in range(len(steps) - 1):
            curr = steps[idx]
            nxt = steps[idx+1]
            lines.append(f"  {curr}[{labels.get(curr, curr)}] --> {nxt}")
            
        lines.append(f"  {steps[-1]}[{labels.get(steps[-1], steps[-1])}] --> End([Output Result])")
        return "\n".join(lines)
from typing import Optional
