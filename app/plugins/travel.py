import datetime
from typing import Dict, Any, List, Tuple, Optional
from app.plugins.base_plugin import BasePlugin

class ImpossibleTravelPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Impossible Travel Anomaly Detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "Enterprise Security Core"

    @property
    def priority(self) -> int:
        return 4

    @property
    def description(self) -> str:
        return "Detects expenses claimed in physically distinct geographic locations within an impossible timeframe."

    def _extract_city(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        cities = ["boston", "paris", "new york", "london", "tokyo", "san francisco", "chicago"]
        for city in cities:
            if city in text_lower:
                return city
        return None

    def check(
        self,
        expense: Dict[str, Any],
        history: List[Dict[str, Any]] = None,
        session_items: List[Dict[str, Any]] = None
    ) -> Tuple[int, str]:
        score = 0
        reasons = []

        raw_input = str(expense.get("raw_text", "")) or str(expense.get("merchant", ""))
        current_city = self._extract_city(raw_input)
        current_date_str = str(expense.get("date", ""))

        if current_city and current_date_str and current_date_str.lower() != "unknown" and history:
            try:
                curr_date = datetime.date.fromisoformat(current_date_str)
                for past in history:
                    past_raw = str(past.get("raw_text", "")) or str(past.get("merchant", ""))
                    past_city = self._extract_city(past_raw)
                    past_date_str = str(past.get("date", ""))

                    if past_city and past_city != current_city and past_date_str and past_date_str.lower() != "unknown":
                        past_date = datetime.date.fromisoformat(past_date_str)
                        days_diff = abs((curr_date - past_date).days)
                        
                        # Trigger anomaly if different cities are claimed within 24 hours (1 day)
                        if days_diff <= 1:
                            score += 35
                            reasons.append(f"Impossible Travel: Claimed in {current_city.capitalize()} and {past_city.capitalize()} within {days_diff} day(s) (+35)")
                            break
            except Exception:
                pass

        return score, "; ".join(reasons)
