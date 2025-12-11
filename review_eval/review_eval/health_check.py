"""Health check functionality for review evaluation system."""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import httpx
from pydantic import BaseModel


class HealthCheckResult(BaseModel):
    """Health check result model."""
    status: str
    timestamp: str
    service: str
    version: str
    checks: Dict[str, Dict[str, Any]]
    errors: List[str]
    warnings: List[str]


class HealthChecker:
    """Health checker for the review evaluation system."""

    def __init__(self):
        """Initialize health checker."""
        self.service_name = "open-reviewer"
        self.version = "0.1.0"
        self.start_time = time.time()

    async def check_health(self) -> HealthCheckResult:
        """Perform comprehensive health check.

        Returns:
            HealthCheckResult with overall system health status.
        """
        checks = {}
        errors = []
        warnings = []

        # Check API connectivity
        api_check = await self._check_api_connectivity()
        checks["api_connectivity"] = api_check
        if not api_check["healthy"]:
            if api_check.get("critical", False):
                errors.extend(api_check.get("errors", []))
            else:
                warnings.extend(api_check.get("warnings", []))

        # Check environment variables
        env_check = self._check_environment()
        checks["environment"] = env_check
        if not env_check["healthy"]:
            warnings.extend(env_check.get("warnings", []))

        # Check dependencies
        deps_check = self._check_dependencies()
        checks["dependencies"] = deps_check
        if not deps_check["healthy"]:
            errors.extend(deps_check.get("errors", []))

        # Check system resources
        system_check = self._check_system()
        checks["system"] = system_check

        # Determine overall status
        overall_status = "healthy"
        if errors:
            overall_status = "unhealthy"
        elif warnings:
            overall_status = "degraded"

        return HealthCheckResult(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            service=self.service_name,
            version=self.version,
            checks=checks,
            errors=errors,
            warnings=warnings
        )

    async def _check_api_connectivity(self) -> Dict[str, Any]:
        """Check API connectivity for supported models."""
        check_result = {
            "name": "API Connectivity",
            "healthy": True,
            "details": {},
            "warnings": [],
            "errors": []
        }

        # Check Anthropic API
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": anthropic_key},
                        timeout=10.0
                    )
                    # We expect a 400/401 for this endpoint without proper request body
                    # but if we can reach it, the API is accessible
                    check_result["details"]["anthropic"] = {
                        "status": "reachable",
                        "response_code": response.status_code
                    }
            except httpx.TimeoutException:
                check_result["warnings"].append("Anthropic API timeout")
                check_result["details"]["anthropic"] = {"status": "timeout"}
            except Exception as e:
                check_result["warnings"].append(f"Anthropic API error: {str(e)}")
                check_result["details"]["anthropic"] = {"status": "error", "error": str(e)}
        else:
            check_result["details"]["anthropic"] = {"status": "no_key"}

        # Check OpenAI API
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        check_result["details"]["openai"] = {"status": "healthy"}
                    else:
                        check_result["warnings"].append(f"OpenAI API returned {response.status_code}")
                        check_result["details"]["openai"] = {"status": "error", "response_code": response.status_code}
            except httpx.TimeoutException:
                check_result["warnings"].append("OpenAI API timeout")
                check_result["details"]["openai"] = {"status": "timeout"}
            except Exception as e:
                check_result["warnings"].append(f"OpenAI API error: {str(e)}")
                check_result["details"]["openai"] = {"status": "error", "error": str(e)}
        else:
            check_result["details"]["openai"] = {"status": "no_key"}

        # If no API keys are present, mark as unhealthy
        if not anthropic_key and not openai_key:
            check_result["healthy"] = False
            check_result["critical"] = True
            check_result["errors"].append("No API keys found. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY")

        return check_result

    def _check_environment(self) -> Dict[str, Any]:
        """Check environment configuration."""
        check_result = {
            "name": "Environment",
            "healthy": True,
            "details": {},
            "warnings": []
        }

        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        check_result["details"]["python_version"] = python_version

        # Check required environment variables
        env_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        missing_vars = []
        for var in env_vars:
            if os.getenv(var):
                check_result["details"][var.lower()] = "present"
            else:
                missing_vars.append(var)

        if missing_vars:
            check_result["warnings"].append(f"Missing optional environment variables: {', '.join(missing_vars)}")
            check_result["details"]["missing_env_vars"] = missing_vars

        return check_result

    def _check_dependencies(self) -> Dict[str, Any]:
        """Check critical dependencies."""
        check_result = {
            "name": "Dependencies",
            "healthy": True,
            "details": {},
            "errors": []
        }

        critical_imports = [
            ("httpx", "httpx"),
            ("pydantic", "pydantic"),
            ("anthropic", "anthropic"),
            ("openai", "openai"),
        ]

        for import_name, package_name in critical_imports:
            try:
                __import__(import_name)
                check_result["details"][package_name] = "available"
            except ImportError as e:
                check_result["healthy"] = False
                check_result["errors"].append(f"Missing dependency: {package_name}")
                check_result["details"][package_name] = f"import_error: {str(e)}"

        return check_result

    def _check_system(self) -> Dict[str, Any]:
        """Check basic system information."""
        uptime = time.time() - self.start_time

        return {
            "name": "System",
            "healthy": True,
            "details": {
                "uptime_seconds": round(uptime, 2),
                "python_executable": sys.executable,
                "platform": sys.platform,
                "working_directory": os.getcwd()
            }
        }


async def get_health_status() -> Dict[str, Any]:
    """Get health status as dictionary.

    Returns:
        Dictionary containing health check results.
    """
    checker = HealthChecker()
    result = await checker.check_health()
    return result.model_dump()


async def main() -> None:
    """Main entry point for health check command."""
    try:
        health_status = await get_health_status()
        print(json.dumps(health_status, indent=2))

        # Exit with non-zero code if unhealthy
        if health_status["status"] == "unhealthy":
            sys.exit(1)
    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "open-reviewer",
            "error": str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())