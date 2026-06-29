import mcp.server.fastmcp as fastmcp

# Create an MCP server instance named ExpenseAuditMCPServer
mcp = fastmcp.FastMCP("ExpenseAuditMCPServer")

@mcp.tool()
def get_corporate_limits() -> str:
    """Get the current corporate spending limits policy for meals, travel, and software.
    
    Returns:
        A string summarizing the category limits.
    """
    return (
        "Meals limit: Maximum $50.00 per transaction.\n"
        "Travel/Hotel limit: Maximum $300.00 per transaction.\n"
        "Software/Subscription limit: Maximum $100.00 per transaction.\n"
        "All other categories default to a $25.00 limit unless pre-approved."
    )

@mcp.tool()
def get_exchange_rate(base_currency: str) -> float:
    """Get exchange rate to USD for a given currency code.
    
    Args:
        base_currency: 3-letter currency code (e.g. EUR, GBP, INR, CAD).
        
    Returns:
        The conversion rate to USD (multiplication factor). Returns 1.0 if currency is USD or unknown.
    """
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

@mcp.tool()
def check_vendor_restrictions(vendor_name: str) -> str:
    """Check if a merchant or vendor is restricted under corporate expense policy.
    
    Args:
        vendor_name: The name of the vendor (merchant).
        
    Returns:
        A status message indicating if the vendor is flagged or OK.
    """
    vendor_lower = vendor_name.lower()
    restricted_keywords = ["casino", "gambling", "club", "bar", "liquor", "pub", "lounge"]
    for word in restricted_keywords:
        if word in vendor_lower:
            return f"WARNING: Vendor '{vendor_name}' contains restricted keyword '{word}'. Expenditures here are prohibited."
    return f"OK: Vendor '{vendor_name}' is not flagged as restricted."

if __name__ == "__main__":
    mcp.run()
