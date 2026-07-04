import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# Load workspace root .env first (fallback), then project .env (overrides)
_project_dir = Path(__file__).resolve().parent.parent.parent
_workspace_root = _project_dir.parent
load_dotenv(_workspace_root / ".env")  # workspace root .env
load_dotenv(_project_dir / ".env", override=True)  # project .env overrides if present

# Set defaults
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "False")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

@dataclass
class AgentConfig:
    # Basic Configuration
    env: str = "development"
    model: str = "gemini-2.5-flash"
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True
    database_path: str = "app/database.db"
    
    # Feature Flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "planner": True,
        "reflection": True,
        "rag": True,
        "dashboard": True,
        "auth_enabled": False
    })
    
    # Rate Limits
    rate_limit: Dict[str, int] = field(default_factory=lambda: {
        "requests_per_minute": 120
    })
    
    # Prompt Versions
    prompt_versions: Dict[str, str] = field(default_factory=lambda: {
        "planner_agent": "v1",
        "receipt_agent": "v1",
        "fraud_agent": "v1",
        "policy_agent": "v1",
        "reasoning_agent": "v1",
        "reflection_agent": "v1",
        "report_agent": "v1"
    })

    def load_profile(self):
        # Determine environment
        # If pytest is running, force "testing" profile
        if "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or "PYTEST" in os.environ:
            self.env = "testing"
        else:
            self.env = os.getenv("ENV", "development").lower()

        config_dir = Path(__file__).resolve().parent.parent / "config"
        config_file = config_dir / f"{self.env}.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                app_data = data.get("app", {})
                self.model = os.getenv("GEMINI_MODEL", app_data.get("model", self.model))
                self.mcp_server_port = app_data.get("mcp_server_port", self.mcp_server_port)
                self.max_iterations = app_data.get("max_iterations", self.max_iterations)
                self.database_path = app_data.get("database_path", self.database_path)
                
                if "feature_flags" in data:
                    self.feature_flags.update(data["feature_flags"])
                if "rate_limit" in data:
                    self.rate_limit.update(data["rate_limit"])
                if "prompt_versions" in data:
                    self.prompt_versions.update(data["prompt_versions"])
            except Exception as e:
                # Fallback silently or log
                pass
        
        # Override model if GEMINI_MODEL is set in environment (highest priority)
        if os.getenv("GEMINI_MODEL"):
            self.model = os.getenv("GEMINI_MODEL")

# Instantiate and load profile
config = AgentConfig()
config.load_profile()
