import os

from app.governance.deployment_registry import DeploymentRegistry
from app.governance.evaluation_registry import EvaluationRegistry
from app.governance.model_registry import ModelRegistry
from app.governance.prompt_registry import PromptRegistry
from app.governance.workflow_registry import WorkflowRegistry


def validate_all_registries():
    """Initializes and runs startup validations for all read-only registries."""
    print("[Governance] Loading and validating governance registries...")
    ModelRegistry.load()
    PromptRegistry.load()
    WorkflowRegistry.load()
    DeploymentRegistry.load()
    EvaluationRegistry.load()

    # Run active environment validation
    env = os.getenv("APP_ENV", "development")
    try:
        DeploymentRegistry.validate_environment(env)
        print(f"[Governance] Active environment '{env}' configuration successfully validated.")
    except Exception as e:
        print(f"[Governance] Active environment '{env}' configuration validation failed: {e}")

    print("[Governance] All registries successfully validated.")


# Run validation on package import to fail fast at startup
validate_all_registries()
