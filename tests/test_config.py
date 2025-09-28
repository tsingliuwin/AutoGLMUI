"""
Tests for configuration management
"""
import os
import pytest
from unittest.mock import patch

from src.config import Settings, get_settings


def test_settings_defaults():
    """Test default settings values"""
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.max_reconnect_attempts == 5


def test_settings_from_env():
    """Test settings from environment variables"""
    with patch.dict(os.environ, {
        "AUTOGLM_HOST": "0.0.0.0",
        "AUTOGLM_PORT": "9000",
        "AUTOGLM_DEBUG": "true",
        "AUTOGLM_LOG_LEVEL": "DEBUG"
    }):
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.debug is True
        assert settings.log_level == "DEBUG"


def test_get_settings():
    """Test get_settings function"""
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_settings_env_file():
    """Test settings from .env file"""
    # This test would require a temporary .env file
    pass