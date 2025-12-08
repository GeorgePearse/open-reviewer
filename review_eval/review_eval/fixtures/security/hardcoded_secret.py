# BAD: Hardcoded secrets and API keys
# Expected issues: hardcoded, secret, API key, environment variable
import requests

# BAD: Hardcoded API key
API_KEY = "sk-1234567890abcdef1234567890abcdef"
DATABASE_PASSWORD = "super_secret_password_123"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def call_api(endpoint: str) -> dict:
    """Call external API with hardcoded key."""
    headers = {
        # BAD: Using hardcoded API key
        "Authorization": f"Bearer {API_KEY}",
        "X-API-Key": "another-hardcoded-key-12345",
    }
    response = requests.get(f"https://api.example.com/{endpoint}", headers=headers)
    return response.json()


def connect_to_db():
    """Connect to database with hardcoded credentials."""
    # BAD: Hardcoded connection string with password
    return f"postgresql://admin:{DATABASE_PASSWORD}@localhost:5432/mydb"
