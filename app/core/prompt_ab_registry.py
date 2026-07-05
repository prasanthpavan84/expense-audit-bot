import hashlib
import os
from typing import Optional

class PromptABRegistry:
    """Manages prompt A/B testing splits.
    
    Assigns sessions to v1 (A) or v2 (B) based on session ID hashing.
    Allows manual override (e.g. environment variable FORCE_PROMPT_VERSION) for benchmark testing.
    """
    def __init__(self, v2_percentage: int = 50):
        self.v2_percentage = v2_percentage
        # Log to track selections
        self.log_file = "app/evaluation/reports/ab_test_selections.jsonl"
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def get_version(self, agent_id: str, session_id: Optional[str] = None) -> str:
        # Check override first
        forced = os.getenv("FORCE_PROMPT_VERSION")
        if forced in ("v1", "v2"):
            return forced

        if not session_id:
            # Default to v1 if no session context
            return "v1"

        # Deterministic hashing of session_id to get split
        hasher = hashlib.md5(f"{agent_id}:{session_id}".encode("utf-8"))
        hash_val = int(hasher.hexdigest()[:8], 16)
        percentile = hash_val % 100
        
        selected_version = "v2" if percentile < self.v2_percentage else "v1"
        
        # Log selection details for tracking
        self.log_selection(agent_id, session_id, selected_version)
        return selected_version

    def log_selection(self, agent_id: str, session_id: str, version: str):
        import json
        import time
        log_entry = {
            "timestamp": time.time(),
            "agent_id": agent_id,
            "session_id": session_id,
            "selected_version": version
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass

prompt_ab_registry = PromptABRegistry()
