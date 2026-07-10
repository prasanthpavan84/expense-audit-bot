import asyncio
from functools import lru_cache

import mcp.server.fastmcp as fastmcp

# Create an MCP server instance named ExpenseAuditMCPServer
mcp = fastmcp.FastMCP("ExpenseAuditMCPServer")


@lru_cache(maxsize=128)
def _get_corporate_limits_cached() -> str:
    return (
        "Meals limit: Maximum $50.00 per transaction.\n"
        "Travel/Hotel limit: Maximum $300.00 per transaction.\n"
        "Software/Subscription limit: Maximum $100.00 per transaction.\n"
        "All other categories default to a $25.00 limit unless pre-approved."
    )


@lru_cache(maxsize=128)
def _get_exchange_rate_cached(base_currency: str) -> float:
    rates = {
        "EUR": 1.10,
        "GBP": 1.30,
        "INR": 0.012,
        "CAD": 0.74,
        "AUD": 0.66,
        "JPY": 0.0065,
        "USD": 1.0,
    }
    return rates.get(base_currency.upper(), 1.0)


@lru_cache(maxsize=128)
def _check_vendor_restrictions_cached(vendor_name: str) -> str:
    vendor_lower = vendor_name.lower()
    restricted_keywords = [
        "casino",
        "gambling",
        "club",
        "bar",
        "liquor",
        "pub",
        "lounge",
    ]
    for word in restricted_keywords:
        if word in vendor_lower:
            return f"WARNING: Vendor '{vendor_name}' contains restricted keyword '{word}'. Expenditures here are prohibited."
    return f"OK: Vendor '{vendor_name}' is not flagged as restricted."


@mcp.tool()
async def get_corporate_limits() -> str:
    """Get the current corporate spending limits policy for meals, travel, and software.

    Returns:
        A string summarizing the category limits.
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(_get_corporate_limits_cached), timeout=2.0)
    except TimeoutError:
        return "ERROR: Corporate limits lookup timed out."


@mcp.tool()
async def get_exchange_rate(base_currency: str) -> float:
    """Get exchange rate to USD for a given currency code.

    Args:
        base_currency: 3-letter currency code (e.g. EUR, GBP, INR, CAD).

    Returns:
        The conversion rate to USD (multiplication factor). Returns 1.0 if currency is USD or unknown.
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(_get_exchange_rate_cached, base_currency), timeout=2.0)
    except TimeoutError:
        return 1.0


@mcp.tool()
async def check_vendor_restrictions(vendor_name: str) -> str:
    """Check if a merchant or vendor is restricted under corporate expense policy.

    Args:
        vendor_name: The name of the vendor (merchant).

    Returns:
        A status message indicating if the vendor is flagged or OK.
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(_check_vendor_restrictions_cached, vendor_name), timeout=2.0)
    except TimeoutError:
        return f"TIMEOUT: Check for vendor '{vendor_name}' timed out. Defaulting to OK."


if __name__ == "__main__":
    mcp.run()
