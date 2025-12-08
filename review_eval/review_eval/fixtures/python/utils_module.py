# BAD: Generic utils module instead of purposeful package
# Expected issues: utils, misc, purposeful, specific module
# File path would be: myapp/utils.py or myapp/misc.py


def format_date(date_str: str) -> str:
    """Format a date string."""
    return date_str.replace("-", "/")


def parse_json(text: str) -> dict:
    """Parse JSON text."""
    import json

    return json.loads(text)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email."""
    # Implementation here
    return True


def calculate_checksum(data: bytes) -> str:
    """Calculate checksum."""
    import hashlib

    return hashlib.md5(data).hexdigest()
