"""
Tests for WebSocket client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time

from src.websocket_client import WebSocketClient, ConnectionStatus


class TestWebSocketClient:
    """Test cases for WebSocketClient"""

    def test_init(self):
        """Test WebSocketClient initialization"""
        client = WebSocketClient("ws://test.com", {"Authorization": "Bearer token"})
        assert client.url == "ws://test.com"
        assert client.headers == {"Authorization": "Bearer token"}
        assert client.status == ConnectionStatus.DISCONNECTED
        assert client.is_connected is False

    def test_create_message(self):
        """Test message creation"""
        client = WebSocketClient("ws://test.com", {})
        message = client.create_message("test instruction")

        # Parse JSON to verify structure
        msg_data = json.loads(message)
        assert msg_data["msg_type"] == "client_test"
        assert msg_data["data"]["instruction"] == "test instruction"
        assert msg_data["conversation_id"] == ""
        assert "timestamp" in msg_data
        assert "msg_id" in msg_data

    @patch('websocket.WebSocketApp')
    def test_connect_success(self, mock_websocket):
        """Test successful connection"""
        # Mock WebSocketApp
        mock_ws = Mock()
        mock_websocket.return_value = mock_ws

        client = WebSocketClient("ws://test.com", {})

        with patch.object(client, '_wait_for_connection', return_value=True):
            result = client.connect()
            assert result is True

    @patch('websocket.WebSocketApp')
    def test_connect_failure(self, mock_websocket):
        """Test connection failure"""
        mock_websocket.side_effect = Exception("Connection failed")

        client = WebSocketClient("ws://test.com", {})
        result = client.connect()
        assert result is False
        assert client.status == ConnectionStatus.ERROR

    def test_on_open(self):
        """Test on_open callback"""
        client = WebSocketClient("ws://test.com", {})
        client.on_open(None)
        assert client.status == ConnectionStatus.CONNECTED

    def test_on_error(self):
        """Test on_error callback"""
        client = WebSocketClient("ws://test.com", {})
        error_callback = Mock()
        client.set_error_callback(error_callback)

        test_error = Exception("Test error")
        client.on_error(None, test_error)

        assert client.status == ConnectionStatus.ERROR
        error_callback.assert_called_once_with(test_error)

    def test_on_close(self):
        """Test on_close callback"""
        client = WebSocketClient("ws://test.com", {})
        client.on_close(None, 1000, "Normal closure")
        assert client.status == ConnectionStatus.DISCONNECTED

    def test_send_message_connected(self):
        """Test sending message when connected"""
        client = WebSocketClient("ws://test.com", {})
        client.ws = Mock()
        client.ws.sock = Mock()
        client.ws.sock.connected = True
        client._status = ConnectionStatus.CONNECTED

        result = client.send_message("test message")
        assert result is True
        client.ws.send.assert_called_once_with("test message")

    def test_send_message_disconnected(self):
        """Test sending message when disconnected"""
        client = WebSocketClient("ws://test.com", {})
        client._status = ConnectionStatus.DISCONNECTED

        result = client.send_message("test message")
        assert result is False

    def test_wait_for_connection(self):
        """Test waiting for connection"""
        client = WebSocketClient("ws://test.com", {})

        # Test successful connection
        client._status = ConnectionStatus.CONNECTED
        result = client._wait_for_connection(timeout=1)
        assert result is True

        # Test timeout
        client._status = ConnectionStatus.CONNECTING
        result = client._wait_for_connection(timeout=0.1)
        assert result is False

    def test_callbacks(self):
        """Test setting callbacks"""
        client = WebSocketClient("ws://test.com", {})

        # Test response callback
        response_callback = Mock()
        client.set_response_callback(response_callback)
        assert client.response_callback == response_callback

        # Test error callback
        error_callback = Mock()
        client.set_error_callback(error_callback)
        assert client.error_callback == error_callback