"""Health check endpoint for Open Reviewer service."""

import time
from datetime import datetime, timezone
from typing import Dict, Any

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from flask import Flask, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


def get_health_status() -> Dict[str, Any]:
    """Get the current health status of the service.

    Returns:
        Dict containing status, timestamp, and service information.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "open-reviewer",
        "version": "0.1.0",
        "uptime": time.time()  # Basic uptime since module load
    }


def create_fastapi_health_app() -> FastAPI:
    """Create a FastAPI application with health check endpoint.

    Returns:
        FastAPI application instance.

    Raises:
        ImportError: If FastAPI is not available.
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is not available. Install with: pip install fastapi uvicorn")

    app = FastAPI(title="Open Reviewer Health Check", version="0.1.0")

    @app.get("/health")
    async def health_check():
        """Health check endpoint that returns service status and timestamp."""
        return get_health_status()

    @app.get("/")
    async def root():
        """Root endpoint redirects to health check."""
        return get_health_status()

    return app


def create_flask_health_app() -> Flask:
    """Create a Flask application with health check endpoint.

    Returns:
        Flask application instance.

    Raises:
        ImportError: If Flask is not available.
    """
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is not available. Install with: pip install flask")

    app = Flask(__name__)

    @app.route("/health")
    def health_check():
        """Health check endpoint that returns service status and timestamp."""
        return jsonify(get_health_status())

    @app.route("/")
    def root():
        """Root endpoint redirects to health check."""
        return jsonify(get_health_status())

    return app


def run_health_server(port: int = 8000, framework: str = "fastapi") -> None:
    """Run the health check server.

    Args:
        port: Port to run the server on (default: 8000).
        framework: Web framework to use ("fastapi" or "flask").

    Raises:
        ImportError: If the requested framework is not available.
        ValueError: If an unsupported framework is specified.
    """
    if framework.lower() == "fastapi":
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is not available. Install with: pip install fastapi uvicorn")

        app = create_fastapi_health_app()
        try:
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=port)
        except ImportError:
            raise ImportError("uvicorn is not available. Install with: pip install uvicorn")

    elif framework.lower() == "flask":
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is not available. Install with: pip install flask")

        app = create_flask_health_app()
        app.run(host="0.0.0.0", port=port)

    else:
        raise ValueError(f"Unsupported framework: {framework}. Use 'fastapi' or 'flask'.")


if __name__ == "__main__":
    # Simple CLI interface
    import sys

    port = 8000
    framework = "fastapi"

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            framework = sys.argv[1]

    if len(sys.argv) > 2:
        framework = sys.argv[2]

    print(f"Starting health check server on port {port} using {framework}")
    run_health_server(port=port, framework=framework)