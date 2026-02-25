"""
Simulator URL configuration for the Quantum Education Toolkit.

Reads SIMULATOR_HOST from the environment so notebooks and course code
can embed or link to the q-sim UI without tight coupling. In dev, the
default is http://localhost:8001 when the simulator runs separately.
"""

import os

# Default when not running in Docker or when simulator is on same host
_DEFAULT_SIMULATOR_HOST = "http://localhost:8001"


def get_simulator_url(path: str = "") -> str:
    """
    Return the base URL of the simulator, with an optional path suffix.

    Uses the SIMULATOR_HOST environment variable. If unset, defaults to
    http://localhost:8001 (suitable for local dev with simulator on port 8001).

    Args:
        path: Optional path to append (e.g. "" for base, "labs/bb84" for a subpath).
              Leading slash is handled; the base URL has no trailing slash.

    Returns:
        Full URL to the simulator, e.g. "http://localhost:8001" or
        "http://localhost:8001/labs/bb84".
    """
    base = os.environ.get("SIMULATOR_HOST", _DEFAULT_SIMULATOR_HOST).rstrip("/")
    path = path.strip("/")
    return f"{base}/{path}" if path else base
