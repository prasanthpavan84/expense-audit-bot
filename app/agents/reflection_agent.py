from app.core.agent_base import BaseExpenseAgent
from app.models.state import WorkflowState
from app.models.evidence import EvidenceCollector

class ReflectionAgent(BaseExpenseAgent):
    def __init__(self):
        super().__init__(name="reflection_agent", system_instruction="Reflect on audit results to provide reasoning")
        
    async def process_state(self, state: WorkflowState) -> WorkflowState:
        evidence_list = EvidenceCollector.get_or_create_evidence_list(state)
        
        for idx, exp in enumerate(state.expenses):
            res = state.audit_results.get(f"expense_{idx}")
            if res:
                trace = []
                trace.append(f"Analyzed expense: {exp.merchant} for {exp.currency} {exp.amount}.")
                
                # Check for evidence supporting extraction
                merchant_ev = [ev for ev in evidence_list if ev.get("field") == "merchant" and ev.get("value") == exp.merchant]
                amount_ev = [ev for ev in evidence_list if ev.get("field") == "amount" and ev.get("value") == exp.amount]
                
                if not merchant_ev or not amount_ev:
                    trace.append("[NEEDS_EVIDENCE] Extraction details are missing solid source document evidence.")
                
                if exp.confidence_score < 0.5:
                    trace.append("Extraction confidence is low, possibly due to hallucination.")
                
                # Verify fraud flags reference specific risk indicators
                if res.fraud_score > 0:
                    # Look for fraud evidence in metadata
                    fraud_indicators = state.metadata.get("fraud_indicators", [])
                    if fraud_indicators:
                        trace.append(f"Fraud check returned a risk score of {res.fraud_score} based on: {', '.join(fraud_indicators)}.")
                        EvidenceCollector.add(state, "fraud_agent", "fraud_risk", res.fraud_score, 0.9, "fraud_agent", True)
                    else:
                        trace.append(f"[UNSUPPORTED] Fraud check returned a risk score of {res.fraud_score} without clear risk indicators.")
                        EvidenceCollector.add(state, "fraud_agent", "fraud_risk", res.fraud_score, 0.4, "fraud_agent", False)
                    
                # Verify policy violations have matching evidence
                if res.policy_violations:
                    verified_violations = []
                    for violation in res.policy_violations:
                        # Policy check should produce policy evidence or metadata
                        policy_meta = state.metadata.get("policy_checks", {})
                        if violation in policy_meta or "policy" in str(state.metadata):
                            verified_violations.append(violation)
                            EvidenceCollector.add(state, "policy_agent", "policy_violation", violation, 1.0, "policy_agent", True)
                        else:
                            verified_violations.append(f"[UNSUPPORTED] {violation}")
                            EvidenceCollector.add(state, "policy_agent", "policy_violation", violation, 0.5, "policy_agent", False)
                            
                    trace.append(f"Identified {len(res.policy_violations)} policy violations: {', '.join(verified_violations)}.")
                else:
                    trace.append("No corporate policy violations were found.")
                    
                # Contradiction Detection
                has_violations = len(res.policy_violations) > 0
                high_fraud = res.fraud_score > 50
                
                conclusion = ""
                if res.is_approved:
                    if has_violations or high_fraud:
                        conclusion = "[CONTRADICTION] Conclusion: The expense is approved despite Compliancy/Fraud violations."
                    else:
                        conclusion = "Conclusion: The expense appears legitimate and compliant."
                else:
                    if not has_violations and not high_fraud:
                        conclusion = "[CONTRADICTION] Conclusion: The expense is rejected without any compliance violations or fraud indicators."
                    else:
                        conclusion = "Conclusion: The expense is rejected based on the violations and risk scores."
                        
                trace.append(conclusion)
                res.reasoning_trace = " ".join(trace)
                res.evidence_links = ["policy://company_policy.json", "validation://rules"]
                
                # Save reflection results in state metadata
                if "reflection_results" not in state.metadata:
                    state.metadata["reflection_results"] = {}
                state.metadata["reflection_results"][f"expense_{idx}"] = {
                    "confidence": 0.9 if "[CONTRADICTION]" not in conclusion and "[UNSUPPORTED]" not in res.reasoning_trace else 0.5,
                    "has_contradictions": "[CONTRADICTION]" in conclusion,
                    "has_unsupported": "[UNSUPPORTED]" in res.reasoning_trace
                }
                
        return state

