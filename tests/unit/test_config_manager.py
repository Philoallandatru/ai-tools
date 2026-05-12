"""Unit tests for ConfigManager with Pydantic validation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from crawler.config import ConfigManager
from crawler.config.models import AppConfig


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_load_valid_config(self):
        """Test loading a valid configuration."""
        config_data = {
            "sources": {
                "confluence": [],
                "jira": [],
            },
            "output": {"base_dir": "./sources"},
            "sync": {"state_file": "./.sync-state.json"},
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 5,
                "error_log": "./errors.log",
            },
            "llm": {
                "provider": "openai",
                "base_url": "http://localhost:1234/v1",
                "model": "test-model",
                "max_tokens": 1000,
                "temperature": 0.7,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load()

            assert config["llm"]["provider"] == "openai"
            assert config["llm"]["max_tokens"] == 1000
            assert config["output"]["base_dir"] == "./sources"
        finally:
            os.unlink(config_path)

    def test_invalid_llm_provider(self):
        """Test validation fails for invalid LLM provider."""
        config_data = {
            "llm": {
                "provider": "invalid_provider",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ValueError, match="provider must be"):
                manager.load()
        finally:
            os.unlink(config_path)

    def test_invalid_max_tokens(self):
        """Test validation fails for negative max_tokens."""
        config_data = {
            "llm": {
                "provider": "openai",
                "max_tokens": -100,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ValueError, match="greater than or equal to 1"):
                manager.load()
        finally:
            os.unlink(config_path)

    def test_env_var_expansion(self):
        """Test environment variable expansion."""
        os.environ["TEST_API_TOKEN"] = "secret-token-123"

        config_data = {
            "sources": {
                "jira": [
                    {
                        "name": "test-jira",
                        "url": "https://test.atlassian.net",
                        "username": "test@example.com",
                        "api_token": "${TEST_API_TOKEN}",
                        "projects": [{"key": "TEST", "name": "Test Project"}],
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load()

            assert config["sources"]["jira"][0]["api_token"] == "secret-token-123"
        finally:
            os.unlink(config_path)
            del os.environ["TEST_API_TOKEN"]

    def test_missing_env_var(self):
        """Test error when environment variable is not set."""
        config_data = {
            "sources": {
                "jira": [
                    {
                        "name": "test-jira",
                        "url": "https://test.atlassian.net",
                        "username": "test@example.com",
                        "api_token": "${MISSING_TOKEN}",
                        "projects": [],
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ValueError, match="Environment variable not set: MISSING_TOKEN"):
                manager.load()
        finally:
            os.unlink(config_path)

    def test_load_validated_returns_pydantic_model(self):
        """Test load_validated returns AppConfig instance."""
        config_data = {
            "llm": {
                "provider": "mock",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            validated_config = manager.load_validated()

            assert isinstance(validated_config, AppConfig)
            assert validated_config.llm.provider == "mock"
        finally:
            os.unlink(config_path)

    def test_default_values(self):
        """Test default values are applied correctly."""
        config_data = {}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load()

            # Check defaults
            assert config["output"]["base_dir"] == "./sources"
            assert config["sync"]["state_file"] == "./.atlassian-sync-state.json"
            assert config["error_handling"]["max_retries"] == 3
            assert config["llm"]["provider"] == "openai"
            assert config["llm"]["max_tokens"] == 2000
            assert config["logging"]["level"] == "INFO"
            assert config["logging"]["format"] == "json"
        finally:
            os.unlink(config_path)
