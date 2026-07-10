from pathlib import Path

from app.core.config_manager import config


class PromptLoader:
    """Utility class to dynamically load versioned agent system instructions from text files."""

    @staticmethod
    def load_prompt(agent_id: str, version: str | None = None, session_id: str | None = None) -> str:
        """Loads prompt content for agent_id and specified version."""
        v = version
        if not v:
            try:
                from app.core.prompt_ab_registry import prompt_ab_registry

                v = prompt_ab_registry.get_version(agent_id, session_id)
            except Exception:
                v = config.prompt_versions.get(agent_id, "v1")

        prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        prompt_file = prompts_dir / v / f"{agent_id}.txt"

        # Fallback mapping if standard names differ
        if not prompt_file.exists():
            # Try mapping receipt_extractor to receipt_extractor if needed
            mapped_id = "receipt_extractor" if agent_id == "receipt_agent" else agent_id
            prompt_file = prompts_dir / v / f"{mapped_id}.txt"

        if prompt_file.exists():
            try:
                with open(prompt_file, encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass

        # Generous default fallback strings to avoid crashing
        defaults = {
            "planner_agent": "Analyze request and determine workflow/capabilities required.",
            "receipt_extractor": "Extract details (amount, currency, merchant, date) from receipts.",
            "policy_agent": "Evaluate compliance with spending limits and restrictions.",
            "fraud_agent": "Analyze for duplicates and risk anomalies.",
            "reasoning_agent": "Verify arithmetic claims and convert currencies.",
            "reflection_agent": "Self-critique results, check OCR confidence, flag human review.",
            "report_agent": "Format final summary outcome report.",
        }
        return defaults.get(agent_id, "Analyze and process context data.")
