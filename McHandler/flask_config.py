"""
Shared Flask runtime configuration from environment variables.
"""

import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def get_secret_key(app_name: str = "mchandler") -> str:
    return (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or f"dev-{app_name}-change-in-production"
    )


def get_run_kwargs(default_port: int = 5000) -> dict:
    port_env = os.environ.get("FLASK_PORT") or os.environ.get("CDID_PORT")
    return {
        "debug": env_bool("FLASK_DEBUG", False),
        "host": os.environ.get("FLASK_HOST", "127.0.0.1"),
        "port": int(port_env or default_port),
    }
