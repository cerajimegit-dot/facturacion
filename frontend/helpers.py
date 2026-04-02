"""Shared helpers for frontend pages."""


def fmt(value, prefix=""):
    """Format a number value safely (handles strings, None, etc.)."""
    try:
        n = float(value)
        return f"{prefix}{n:,.0f}"
    except (TypeError, ValueError):
        return str(value) if value else "-"


def results(data):
    """Extract list from paginated or plain API response."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results", [])
    return []
