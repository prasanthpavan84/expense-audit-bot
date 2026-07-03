from app.core.agent_base import BaseExpenseAgent
from app.models.state import WorkflowState
from app.validation import check_hallucination, load_policy_config
from app.models.evidence import EvidenceCollector

class HallucinationAgent(BaseExpenseAgent):
    def __init__(self):
        super().__init__(name="hallucination_agent", system_instruction="Guard against hallucinated extractions")
        
    async def process_state(self, state: WorkflowState) -> WorkflowState:
        policy_config = load_policy_config()
        raw_text_lower = state.raw_input.lower()
        
        for idx, exp in enumerate(state.expenses):
            exp_dict = exp.model_dump()
            errors = check_hallucination(exp_dict, state.raw_input)
            
            # Additional amount cross-verification
            if exp.amount:
                amount_str = str(exp.amount)
                # Check integer part or full amount in raw text
                int_part = amount_str.split('.')[0]
                if int_part not in raw_text_lower and amount_str not in raw_text_lower:
                    errors.append(f"Amount {exp.amount} not found in raw input.")
                    EvidenceCollector.add(state, "ocr", "amount", exp.amount, 0.2, "hallucination_agent", False)
                else:
                    EvidenceCollector.add(state, "ocr", "amount", exp.amount, 1.0, "hallucination_agent", True)
            
            # Additional date cross-verification
            if exp.date:
                if exp.date not in raw_text_lower:
                    errors.append(f"Date {exp.date} not found in raw input.")
                    EvidenceCollector.add(state, "ocr", "date", exp.date, 0.2, "hallucination_agent", False)
                else:
                    EvidenceCollector.add(state, "ocr", "date", exp.date, 1.0, "hallucination_agent", True)
                    
            # Additional merchant cross-verification
            if exp.merchant:
                if exp.merchant.lower() not in raw_text_lower:
                    # check_hallucination handles it, but let's log to evidence
                    EvidenceCollector.add(state, "ocr", "merchant", exp.merchant, 0.2, "hallucination_agent", False)
                else:
                    EvidenceCollector.add(state, "ocr", "merchant", exp.merchant, 1.0, "hallucination_agent", True)
                    
            # Additional policy rules verification
            res = state.audit_results.get(f"expense_{idx}")
            if res and res.policy_violations:
                limits = policy_config.get("category_limits", {})
                restricted = policy_config.get("restricted_vendors", [])
                for violation in res.policy_violations:
                    # Check if the violation refers to a valid policy rule
                    rule_found = False
                    for category in limits:
                        if category.lower() in violation.lower():
                            rule_found = True
                    for vendor in restricted:
                        if vendor.lower() in violation.lower():
                            rule_found = True
                    if not rule_found and "limit" not in violation.lower() and "restricted" not in violation.lower():
                        errors.append(f"Referenced policy violation '{violation}' is not defined in company policy.")
            
            if errors:
                state.expenses[idx].confidence_score = 0.1
                state.metadata["hallucinations_detected"] = True
                if "hallucinations" not in state.metadata:
                    state.metadata["hallucinations"] = []
                state.metadata["hallucinations"].extend(errors)
                if "hallucination_errors" not in state.metadata:
                    state.metadata["hallucination_errors"] = []
                state.metadata["hallucination_errors"].extend(errors)
                
        return state

