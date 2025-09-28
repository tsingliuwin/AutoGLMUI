"""
Pytest configuration and fixtures
"""
import pytest
import os
from unittest.mock import Mock

from src.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return Settings(
        autoglm_api_token="test_token",
        host="127.0.0.1",
        port=8001,
        debug=True,
        log_level="DEBUG"
    )


@pytest.fixture
def clean_env():
    """Clean environment before and after tests"""
    original_env = os.environ.copy()

    # Remove AUTOGLM_ variables
    for key in list(os.environ.keys()):
        if key.startswith("AUTOGLM_"):
            del os.environ[key]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket client"""
    mock_ws = Mock()
    mock_ws.sock = Mock()
    mock_ws.sock.connected = True
    return mock_ws