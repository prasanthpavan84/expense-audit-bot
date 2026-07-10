import json
import re

from app.core.agent_base import BaseExpenseAgent
from app.models.state import WorkflowState
from app.query_engine import execute_query


class QueryAgent(BaseExpenseAgent):
    def __init__(self):
        super().__init__(name="query_agent", system_instruction="Execute database queries")

    async def process_state(self, state: WorkflowState) -> WorkflowState:
        text = state.raw_input.lower()
        query_params = {}

        if "department" in text:
            query_params["action"] = "COMPARE_DEPTS"
            if "engineering" in text:
                query_params["departments"] = ["Engineering", "Sales"]
            else:
                query_params["departments"] = ["Sales", "HR"]
        elif "employee" in text or "emp" in text:
            query_params["action"] = "SUMMARIZE_EMPLOYEE"
            emp_match = re.search(r"emp\d+", text)
            if emp_match:
                query_params["employee_id"] = emp_match.group(0).upper()
            else:
                query_params["employee_id"] = "EMP101"
        else:
            query_params["action"] = "FILTER"
            if "travel" in text:
                query_params["category"] = "Travel"
            amt_match = re.search(r"above\s*(\d+)", text)
            if amt_match:
                query_params["amount_min"] = float(amt_match.group(1))

        result = execute_query(query_params)
        state.metadata["query_result"] = json.dumps(result, indent=2)
        return state
