#!/usr/bin/env python3
"""
Example usage of the health check endpoint.

This demonstrates how to use the health check functionality in Open Reviewer.
"""

from review_eval import get_health_status

def main():
    """Demonstrate health check functionality."""
    print("Open Reviewer - Health Check Example")
    print("=" * 40)

    # Get health status
    health = get_health_status()

    print("Health Status:")
    for key, value in health.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 40)
    print("Health check module is ready!")

    # Example of how to use as a web service
    print("\nTo run as a web service:")
    print("  python -m review_eval.health_check")
    print("  python -m review_eval.health_check 8080")
    print("  python -m review_eval.health_check flask")
    print("  python -m review_eval.health_check 8080 flask")

    print("\nOr use programmatically:")
    print("  from review_eval import run_health_server")
    print("  run_health_server(port=8000, framework='fastapi')")

if __name__ == "__main__":
    main()