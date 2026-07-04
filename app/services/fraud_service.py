import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from app.services.base_service import BaseService
from app.plugins.base_plugin import BasePlugin
from app.models.domain import FraudSignal

class FraudService(BaseService):
    """Business service orchestrating fraud checks using dynamic plugin discovery."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path(__file__).resolve().parent.parent / "plugins"
        self._plugins: List[BasePlugin] = []
        self._discover_plugins()

    def _discover_plugins(self):
        """Scans the plugins directory and registers classes subclassing BasePlugin."""
        self._plugins.clear()
        if not self.plugins_dir.exists():
            return

        for path in self.plugins_dir.glob("*.py"):
            if path.name in ["__init__.py", "base_plugin.py"]:
                continue
                
            module_name = f"app.plugins.{path.stem}"
            try:
                module = importlib.import_module(module_name)
                # Find all classes that inherit from BasePlugin
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        # Instantiate the plugin
                        self._plugins.append(obj())
            except Exception as e:
                # Fallback logging if load fails
                pass
                
        # Sort by priority
        self._plugins.sort(key=lambda x: x.priority)

    def verify_fraud(
        self,
        expense: Dict[str, Any],
        history: List[Dict[str, Any]] = None,
        session_items: List[Dict[str, Any]] = None
    ) -> FraudSignal:
        """Run all discovered fraud plugins and aggregate risk score and indicators."""
        # Reload plugins to support hot-reloading during dev
        self._discover_plugins()

        total_score = 0
        indicators = []
        
        for plugin in self._plugins:
            try:
                score, reason = plugin.check(expense, history, session_items)
                if score > 0:
                    total_score += score
                    if reason:
                        indicators.append(reason)
            except Exception as e:
                # Log execution error for plugin and continue
                pass

        # Cap score at 100
        final_score = min(total_score, 100)
        explanation = "; ".join(indicators) if indicators else "No suspicious anomalies detected."
        
        return FraudSignal(
            score=final_score / 100.0,
            indicators=indicators,
            explanation=explanation
        )
