# BAD: Missing type annotations
# Expected issues: type annotation, return type, parameter type


def process_data(items, max_length=None):
    """Process data items."""
    result = {}
    for item in items:
        if max_length and len(item) > max_length:
            item = item[:max_length]
        result[item] = len(item)
    return result


def calculate_total(prices, discount):
    total = sum(prices)
    if discount:
        total = total * (1 - discount)
    return total
