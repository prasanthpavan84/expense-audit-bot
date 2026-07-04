import datetime
from typing import Dict, Any, List, Tuple
from app.plugins.base_plugin import BasePlugin

class CurrencyAnomalyPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Currency & Threshold Analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "Enterprise Security Core"

    @property
    def priority(self) -> int:
        return 3

    @property
    def description(self) -> str:
        return "Analyzes transaction thresholds and identifies receipt metadata manipulation."

    def check(
        self,
        expense: Dict[str, Any],
        history: List[Dict[str, Any]] = None,
        session_items: List[Dict[str, Any]] = None
    ) -> Tuple[int, str]:
        score = 0
        reasons = []
        
        amount = float(expense.get("amount", 0.0))
        currency = str(expense.get("currency", "USD")).upper()
        
        # 1. Just Under Review Threshold Check
        limit_usd = 200.0
        limit_inr = 16600.0
        threshold_val = limit_inr if currency == "INR" else limit_usd
        
        if threshold_val * 0.90 <= amount < threshold_val:
            score += 25
            reasons.append(f"Claim amount ({currency} {amount:.2f}) is close to review threshold ({currency} {threshold_val}) (+25)")
            
        # 2. Weekend claim check
        date_str = str(expense.get("date", ""))
        if date_str and date_str.lower() != "unknown":
            try:
                year, month, day = map(int, date_str.split("-"))
                dt = datetime.date(year, month, day)
                if dt.weekday() in [5, 6]:
                    score += 15
                    reasons.append(f"Expense claimed on weekend: {dt.strftime('%A')} (+15)")
            except Exception:
                pass

        # 2b. Holiday claim check
        holidays = ["01-01", "07-04", "11-26", "12-25"]
        if date_str and len(date_str) >= 10:
            mm_dd = date_str[5:10]
            if mm_dd in holidays:
                score += 20
                reasons.append(f"Expense claimed on holiday: {mm_dd} (+20)")

        # 2c. Round number claim check
        if amount >= 50.0 and amount % 10.0 == 0.0:
            score += 10
            reasons.append(f"Round claim amount: {currency} {amount:.2f} (+10)")

        # 3. Manipulation checks
        manipulated = expense.get("manipulated_receipt", False)
        if manipulated:
            score += 60
            reasons.append("Edited or manipulated receipt detected (+60)")
            
        ocr_confidence = expense.get("ocr_confidence_score", 1.0)
        if ocr_confidence < 0.7:
            score += 20
            reasons.append(f"Low OCR confidence ({ocr_confidence:.2f}) (+20)")

        return score, "; ".join(reasons)
