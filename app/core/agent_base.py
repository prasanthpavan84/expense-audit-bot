from typing import Optional, Any
from google.adk.agents import Agent
from app.models.state import WorkflowState

class BaseExpenseAgent(Agent):
    """
    Base class for all AI agents in the Expense Audit Bot.
    Enforces standardized initialization and state handling.
    """
    def __init__(self, name: str, model: Optional[Any] = "", system_instruction: str = "", tools: Optional[list] = None):
        super().__init__(name=name, model=model, instruction=system_instruction, tools=tools or [])
        
    async def process_state(self, state: WorkflowState) -> WorkflowState:
        """
        Standardized method for processing workflow state.
        Can be implemented by subclasses to encapsulate state-based logic.
        """
        raise NotImplementedError("Subclasses must implement process_state()")
