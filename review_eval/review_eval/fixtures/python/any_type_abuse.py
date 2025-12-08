# BAD: Using Any types without justification
# Expected issues: Any, type safety, specific type
from typing import Any


def process_response(data: Any) -> Any:
    """Process API response data."""
    return data.get("result")


def transform_items(items: list[Any]) -> dict[str, Any]:
    """Transform items to dictionary."""
    result: dict[str, Any] = {}
    for item in items:
        result[item.name] = item.value
    return result


config: Any = None
