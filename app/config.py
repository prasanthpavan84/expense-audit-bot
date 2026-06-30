import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load workspace root .env first (fallback), then project .env (overrides)
_project_dir = Path(__file__).resolve().parent.parent
_workspace_root = _project_dir.parent
load_dotenv(_workspace_root / ".env")  # workspace root .env
load_dotenv(_project_dir / ".env", override=True)  # project .env overrides if present
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")  # Gemini API key only


@dataclass
class AgentConfig:
    # Reads model from environment GEMINI_MODEL. Default gemini-2.5-flash (the 1.5 family is retired and returns 404). Use gemini-2.5-flash-lite for tighter free-tier quota.
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True


config = AgentConfig()
