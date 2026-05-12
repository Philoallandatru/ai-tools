"""
Configuration loading utilities with Pydantic validation.

This module centralizes YAML loading, environment variable expansion, and
type-safe validation using Pydantic models.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from crawler.config.models import AppConfig


class ConfigManager:
    """Load and validate application configuration using Pydantic."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._validated_config: Optional[AppConfig] = None

    def load(self) -> Dict[str, Any]:
        """Load config from YAML, expand env vars, and validate with Pydantic."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\nPlease run: python cli.py init"
            )

        with open(self.config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        # Expand environment variables
        expanded_config = self._replace_env_vars(raw_config)

        # Validate with Pydantic
        try:
            self._validated_config = AppConfig(**expanded_config)
        except ValidationError as e:
            # Format validation errors for user-friendly output
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"  - {field}: {message}")

            raise ValueError(
                f"Configuration validation failed:\n" + "\n".join(error_messages)
            ) from e

        # Return as dict for backward compatibility
        return self._validated_config.model_dump()

    def load_validated(self) -> AppConfig:
        """Load and return validated Pydantic model directly."""
        if self._validated_config is None:
            self.load()
        return self._validated_config

    def _replace_env_vars(self, obj: Any) -> Any:
        """Recursively replace string values like ${NAME} with environment values."""
        if isinstance(obj, dict):
            return {key: self._replace_env_vars(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            value = os.getenv(env_var, "")
            if not value:
                raise ValueError(
                    f"Environment variable not set: {env_var}\n"
                    f"Please set it in your environment or .env file"
                )
            return value
        return obj

    @staticmethod
    def load_from_env() -> Dict[str, Any]:
        """Load configuration from .env file if it exists."""
        env_file = Path(".env")
        if not env_file.exists():
            return {}

        env_vars = {}
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
                        # Set in environment for ${VAR} expansion
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        return env_vars


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Compatibility wrapper for loading configuration."""
    manager = ConfigManager(config_path)
    manager.load_from_env()  # Load .env if exists
    return manager.load()
