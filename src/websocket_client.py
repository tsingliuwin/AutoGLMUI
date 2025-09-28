import websocket
import threading
import time
import json
import uuid
import asyncio
import queue
from typing import Callable, Optional, Dict, Any
from enum import Enum

from src.logging_simple import logger
from src.config_simple import settings


class ConnectionStatus(Enum):
    """WebSocket connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class WebSocketClient:
    """Enhanced WebSocket client with proper error handling and logging"""

    def __init__(self, url: str, headers: Dict[str, str]):
        self.url = url
        self.headers = headers
        self.ws: Optional[websocket.WebSocketApp] = None
        self._status = ConnectionStatus.DISCONNECTED
        self.message_queue = queue.Queue()
        self.response_callback: Optional[Callable[[str], None]] = None
        self.error_callback: Optional[Callable[[Exception], None]] = None
        self._reconnect_attempts = 0
        self._connection_lock = threading.Lock()
        self._stop_event = threading.Event()

        logger.info(f"WebSocket client initialized for URL: {url}")

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._status == ConnectionStatus.CONNECTED and self.ws and self.ws.sock and self.ws.sock.connected

    def create_message(self, instruction: str) -> str:
        """Create JSON message with instruction content"""
        timestamp = int(time.time() * 1000)
        message_id = str(uuid.uuid4())

        message_data = {
            "timestamp": timestamp,
            "conversation_id": "",
            "msg_type": "client_test",
            "msg_id": message_id,
            "data": {
                "biz_type": "test_agent",
                "instruction": instruction
            }
        }

        logger.debug(f"Creating message: {message_data}")
        return json.dumps(message_data)

    def on_message(self, ws, message: str):
        """Handle incoming messages"""
        try:
            logger.debug(f"Received message: {message}")

            # Parse JSON message for better logging
            try:
                msg_data = json.loads(message)
                msg_type = msg_data.get("msg_type", "unknown")
                logger.info(f"Received {msg_type} message")
            except json.JSONDecodeError:
                logger.warning("Received non-JSON message")

            if self.response_callback:
                self.response_callback(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if self.error_callback:
                self.error_callback(e)

    def on_open(self, ws):
        """Handle connection open"""
        logger.info("WebSocket connection opened successfully")
        with self._connection_lock:
            self._status = ConnectionStatus.CONNECTED
            self._reconnect_attempts = 0

    def on_error(self, ws, error):
        """Handle connection error"""
        logger.error(f"WebSocket error: {error}")
        with self._connection_lock:
            self._status = ConnectionStatus.ERROR

        if self.error_callback:
            self.error_callback(error)

    def on_close(self, ws, close_status_code: int, close_msg: str):
        """Handle connection close"""
        logger.info(f"WebSocket connection closed. Code: {close_status_code}, Message: {close_msg}")
        with self._connection_lock:
            self._status = ConnectionStatus.DISCONNECTED

        # Attempt reconnection if not stopped
        if not self._stop_event.is_set() and self._reconnect_attempts < settings.max_reconnect_attempts:
            self._attempt_reconnect()

    def send_message(self, message: str) -> bool:
        """Send message through WebSocket"""
        if not self.is_connected:
            logger.warning("Attempted to send message while disconnected")
            return False

        try:
            self.ws.send(message)
            logger.debug(f"Message sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def connect(self) -> bool:
        """Establish WebSocket connection"""
        with self._connection_lock:
            if self._status in [ConnectionStatus.CONNECTING, ConnectionStatus.CONNECTED]:
                logger.warning("Connection already in progress or established")
                return self.is_connected

            self._status = ConnectionStatus.CONNECTING
            self._stop_event.clear()

        try:
            logger.info(f"Connecting to WebSocket: {self.url}")
            self.ws = websocket.WebSocketApp(
                self.url,
                header=self.headers,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Run WebSocket in a separate thread
            websocket_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={"ping_interval": 30, "ping_timeout": 10}
            )
            websocket_thread.daemon = True
            websocket_thread.start()

            # Wait for connection to establish
            return self._wait_for_connection()

        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            with self._connection_lock:
                self._status = ConnectionStatus.ERROR
            return False

    def disconnect(self):
        """Close WebSocket connection gracefully"""
        logger.info("Disconnecting WebSocket...")
        self._stop_event.set()

        if self.ws:
            try:
                self.ws.close()
                logger.info("WebSocket disconnected successfully")
            except Exception as e:
                logger.error(f"Error while disconnecting: {e}")

        with self._connection_lock:
            self._status = ConnectionStatus.DISCONNECTED

    def set_response_callback(self, callback: Callable[[str], None]):
        """Set callback function for handling responses"""
        self.response_callback = callback

    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback function for handling errors"""
        self.error_callback = callback

    def _wait_for_connection(self, timeout: int = 10) -> bool:
        """Wait for WebSocket connection to establish"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_connected:
                return True
            time.sleep(0.1)
        return False

    def _attempt_reconnect(self):
        """Attempt to reconnect WebSocket"""
        with self._connection_lock:
            self._reconnect_attempts += 1
            attempt = self._reconnect_attempts

        if attempt > settings.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return

        delay = min(2 ** attempt, 30)  # Exponential backoff, max 30s
        logger.info(f"Attempting to reconnect in {delay}s (attempt {attempt}/{settings.max_reconnect_attempts})")

        time.sleep(delay)
        self.connect()