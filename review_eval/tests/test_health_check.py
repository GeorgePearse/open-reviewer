"""Tests for the health check module."""

import pytest
from datetime import datetime
from review_eval.health_check import get_health_status


def test_get_health_status():
    """Test that get_health_status returns expected structure."""
    status = get_health_status()

    # Check required fields
    assert status["status"] == "healthy"
    assert "timestamp" in status
    assert status["service"] == "open-reviewer"
    assert status["version"] == "0.1.0"
    assert "uptime" in status

    # Check timestamp format (should be ISO format)
    timestamp_str = status["timestamp"]
    parsed_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert isinstance(parsed_timestamp, datetime)

    # Check uptime is a number
    assert isinstance(status["uptime"], (int, float))
    assert status["uptime"] > 0


def test_health_status_consistency():
    """Test that consecutive calls return consistent structure."""
    status1 = get_health_status()
    status2 = get_health_status()

    # Structure should be the same
    assert set(status1.keys()) == set(status2.keys())
    assert status1["status"] == status2["status"]
    assert status1["service"] == status2["service"]
    assert status1["version"] == status2["version"]

    # Timestamp should be different (or at least not older)
    assert status2["timestamp"] >= status1["timestamp"]


def test_health_status_json_serializable():
    """Test that health status can be JSON serialized."""
    import json

    status = get_health_status()

    # Should not raise an exception
    json_str = json.dumps(status)

    # Should be able to parse back
    parsed = json.loads(json_str)
    assert parsed == status