"""Independent Confidence Calibration Engine for the AI Cognitive Layer.

Calculates a deterministic, explainable confidence score from various
cognitive signals, applying rules-based penalties for anomalies.
Zero LLM calls.
"""

from dataclasses import dataclass, field
from typing import Dict, List
from app.models.state import WorkflowState

# Default weights for confidence signals
# Must sum to 1.0
DEFAULT_WEIGHTS = {
    "intent": 0.20,
    "nlu_entities": 0.25,
    "ocr": 0.20,
    "validation": 0.15,
    "reflection": 0.20,
}


@dataclass
class ConfidenceResult:
    """Dataclass holding calibrated confidence details."""
    overall: float
    explanation: str
    factors: Dict[str, float]
    penalties: List[str] = field(default_factory=list)


class ConfidenceCalibrationEngine:
    """Deterministic engine to calculate calibrated confidence scores."""

    @staticmethod
    def calibrate_confidence(
        state: WorkflowState, weights: Dict[str, float] = None
    ) -> ConfidenceResult:
        """Calculates overall calibrated confidence with explainable breakdown and penalties."""
        if weights is None:
            weights = DEFAULT_WEIGHTS

        factors = {}
        penalties = []
        explanation_parts = []

        # 1. Intent confidence
        intent_conf = state.metadata.get("intent_confidence", 1.0)
        factors["intent"] = intent_conf
        explanation_parts.append(f"Intent Confidence: {intent_conf:.2f} (weight={weights['intent']:.2f})")

        # 2. NLU Entity confidence
        nlu_entities = state.metadata.get("nlu_entities", {})
        nlu_conf = 1.0
        # If the input was empty or had no entities, confidence is lower
        if not nlu_entities:
            nlu_conf = 0.3
        else:
            # Fraction of optional fields present can influence entity confidence slightly
            missing_opt = state.metadata.get("missing_optional", [])
            nlu_conf = max(0.4, 1.0 - (0.1 * len(missing_opt)))
        factors["nlu_entities"] = nlu_conf
        explanation_parts.append(f"NLU Entities Confidence: {nlu_conf:.2f} (weight={weights['nlu_entities']:.2f})")

        # 3. OCR confidence (from receipt extraction)
        ocr_conf = state.metadata.get("ocr_confidence", 1.0)
        # If extraction happened, try to read OCR confidence
        extraction_res = state.metadata.get("extraction_results", {})
        if extraction_res and "ocr_confidence" in extraction_res:
            ocr_conf = extraction_res["ocr_confidence"]
        elif "ocr_confidence" in state.metadata:
            ocr_conf = state.metadata["ocr_confidence"]
        factors["ocr"] = ocr_conf
        explanation_parts.append(f"OCR Confidence: {ocr_conf:.2f} (weight={weights['ocr']:.2f})")

        # 4. Validation success
        val_errors = state.metadata.get("validation_errors", [])
        val_conf = 1.0 if not val_errors else 0.5
        factors["validation"] = val_conf
        explanation_parts.append(f"Validation Success Rate: {val_conf:.2f} (weight={weights['validation']:.2f})")

        # 5. Reflection confidence
        reflection_conf = 1.0
        if "reflection_results" in state.metadata:
            ref_res = state.metadata["reflection_results"]
            if isinstance(ref_res, dict):
                reflection_conf = ref_res.get("confidence", 1.0)
        factors["reflection"] = reflection_conf
        explanation_parts.append(f"Reflection Confidence: {reflection_conf:.2f} (weight={weights['reflection']:.2f})")

        # Weighted baseline
        baseline = sum(factors[k] * weights[k] for k in weights)

        # 6. Apply Penalties (applied sequentially to raw baseline)
        calibrated_score = baseline

        # Penalty: Missing critical fields (-0.15 per field)
        missing_crit = state.metadata.get("missing_critical", [])
        if missing_crit:
            p_val = 0.15 * len(missing_crit)
            calibrated_score -= p_val
            penalties.append(f"Missing critical fields: {missing_crit} (-{p_val:.2f})")

        # Penalty: Low OCR confidence (-0.1)
        if ocr_conf < 0.6:
            calibrated_score -= 0.1
            penalties.append("OCR confidence is below acceptable threshold (-0.10)")

        # Penalty: Hallucinations detected (-0.2)
        if state.metadata.get("hallucinations_detected") or state.metadata.get("hallucination_errors"):
            calibrated_score -= 0.2
            penalties.append("Hallucinations detected in extraction results (-0.20)")

        # Penalty: Validation errors (-0.2)
        if val_errors:
            calibrated_score -= 0.2
            penalties.append(f"Validation errors present (-0.20)")

        # Penalty: Clarification retry cycles
        clar_session = state.metadata.get("clarification_session", {})
        retry_count = clar_session.get("retry_count", 0)
        if retry_count > 0:
            p_val = 0.05 * retry_count
            calibrated_score -= p_val
            penalties.append(f"Clarification retries: {retry_count} (-{p_val:.2f})")

        # Cap score between 0.0 and 1.0
        calibrated_score = max(0.0, min(calibrated_score, 1.0))
        calibrated_score = round(calibrated_score, 3)

        explanation = (
            f"Base Score: {baseline:.2f}. " +
            " | ".join(explanation_parts)
        )
        if penalties:
            explanation += " [Penalties: " + " ; ".join(penalties) + "]"
        explanation += f" -> Calibrated Confidence: {calibrated_score:.2f}"

        return ConfidenceResult(
            overall=calibrated_score,
            explanation=explanation,
            factors=factors,
            penalties=penalties
        )


def calibrate_confidence(state: WorkflowState) -> ConfidenceResult:
    """Wrapper function to calibrate confidence."""
    return ConfidenceCalibrationEngine.calibrate_confidence(state)
