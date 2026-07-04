from core.agents.base_agent import BaseAgent, AgentResult, WorkflowContext
from core.metadata.capability import capability
from app.models.domain import DecisionTrace
from app.core.config_manager import config
import time

@capability(
    name="planner_agent",
    version="1.0.0",
    inputs=["input"],
    outputs=["workflow_plan"]
)
class PlannerAgent(BaseAgent):
    """Planner Agent decides which workflow, tools, and reflection settings are required."""

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Planner Agent executing.")
        text = (context.input or "").lower()
        
        # 1. Determine workflow based on intent keywords
        workflow = "AUDIT"
        if any(w in text for w in ["policy", "limit", "rule", "allowed"]):
            workflow = "POLICY"
        elif any(w in text for w in ["compare", "history", "search", "spending", "total", "calculate"]):
            workflow = "QUERY"

        # 2. Decide tool capabilities needed
        capabilities = ["FILE_READ"]
        if workflow == "AUDIT":
            capabilities.extend(["CURRENCY_CONVERSION", "CHECK_VENDOR", "READ_POLICY"])
        elif workflow == "POLICY":
            capabilities.append("READ_POLICY")
        elif workflow == "QUERY":
            capabilities.extend(["DB_READ", "DB_WRITE"])

        # 3. Determine if reflection is required (e.g., for expensive claims or high-risk inputs)
        reflection_required = config.feature_flags.get("reflection", True)
        if "reflection" in config.feature_flags:
            reflection_required = config.feature_flags["reflection"]

        # Assemble plan
        plan = {
            "workflow": workflow,
            "required_capabilities": capabilities,
            "reflection_required": reflection_required,
            "model_version": config.model,
            "prompt_version": config.prompt_versions.get("planner_agent", "v1")
        }

        # Store in context metadata
        context.metadata["workflow_plan"] = plan
        context.metadata["workflow_version"] = "v2"

        return AgentResult(
            success=True,
            output=plan,
            explanation=f"Planner selected workflow '{workflow}' with capabilities {capabilities}."
        )
