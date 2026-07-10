from collections.abc import Callable
from typing import Any

from app.mcp_server import (
    check_vendor_restrictions,
    get_corporate_limits,
    get_exchange_rate,
)


class ToolRegistry:
    """Capability-Based Tool Registry resolving abstract needs to specific tool implementations."""

    def __init__(self):
        self._capabilities: dict[str, list[Callable[..., Any]]] = {}
        self._register_default_mcp_tools()

    def register(self, capability: str, tool_func: Callable[..., Any]) -> None:
        """Register a concrete tool function under a capability name."""
        if capability not in self._capabilities:
            self._capabilities[capability] = []
        self._capabilities[capability].append(tool_func)

    def resolve(self, capability: str) -> Callable[..., Any] | None:
        """Resolve a capability to the first registered active tool."""
        tools = self._capabilities.get(capability)
        if not tools:
            return self._get_fallback_tool(capability)
        return tools[0]

    def _register_default_mcp_tools(self):
        """Wires our FastMCP tools to the Capability Registry."""
        self.register("READ_POLICY", get_corporate_limits)
        self.register("CURRENCY_CONVERSION", get_exchange_rate)
        self.register("CHECK_VENDOR", check_vendor_restrictions)

    def _get_fallback_tool(self, capability: str) -> Callable[..., Any]:
        """Provides dynamic fallback functions to mock tools when real MCP is unavailable."""
        if capability == "CURRENCY_CONVERSION":
            return lambda amt, from_curr, to_curr: amt * 1.0
        elif capability == "CHECK_VENDOR":
            return lambda vendor_name: "OK"
        elif capability == "READ_POLICY":
            return lambda category: {}
        return lambda *args, **kwargs: None


# Global Tool Registry
tool_registry = ToolRegistry()
