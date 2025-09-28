"""
Main FastAPI application for AutoGLMUI - Simple version
"""
from typing import List, Optional
from contextlib import asynccontextmanager
import time
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config_simple import settings
from .logging_simple import logger
from .websocket_client import WebSocketClient, ConnectionStatus


class TaskRequest(BaseModel):
    """Request model for sending tasks"""
    task: str = Field(..., min_length=1, max_length=10000, description="Task instruction to send to AutoGLM")


class TaskResponse(BaseModel):
    """Response model for task submission"""
    success: bool
    message: str
    task_id: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for connection status"""
    connected: bool
    status: str
    recent_responses: int
    last_heartbeat: Optional[float] = None


class AutoGLMUI:
    """Main application class managing WebSocket client and state"""

    def __init__(self):
        self.ws_client: Optional[WebSocketClient] = None
        self.recent_responses: List[dict] = []
        self.max_responses = 100
        self._last_heartbeat: Optional[float] = None
        self._startup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the WebSocket client"""
        if not settings.autoglm_api_token:
            logger.error("AutoGLM API token not configured")
            return

        headers = {
            "Authorization": f"Bearer {settings.autoglm_api_token}"
        }

        self.ws_client = WebSocketClient(settings.autoglm_api_url, headers)
        self.ws_client.set_response_callback(self._handle_response)
        self.ws_client.set_error_callback(self._handle_error)

        # Start connection in background
        self._startup_task = asyncio.create_task(self._connect_with_retry())

    async def _connect_with_retry(self):
        """Attempt to connect with retries"""
        for attempt in range(settings.max_reconnect_attempts):
            try:
                logger.info(f"Attempting WebSocket connection (attempt {attempt + 1})")
                connected = await asyncio.get_event_loop().run_in_executor(
                    None, self.ws_client.connect
                )

                if connected:
                    self._last_heartbeat = time.time()
                    logger.info("WebSocket connection established successfully")
                    return

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")

            if attempt < settings.max_reconnect_attempts - 1:
                delay = min(2 ** attempt, 30)  # Exponential backoff
                logger.info(f"Retrying connection in {delay} seconds...")
                await asyncio.sleep(delay)

        logger.error("Failed to establish WebSocket connection after all attempts")

    def _handle_response(self, message: str):
        """Handle incoming WebSocket responses"""
        try:
            timestamp = time.time()
            self._last_heartbeat = timestamp

            response_data = {
                "message": message,
                "timestamp": timestamp,
                "id": len(self.recent_responses)
            }

            self.recent_responses.append(response_data)

            # Maintain response limit
            if len(self.recent_responses) > self.max_responses:
                self.recent_responses.pop(0)

            logger.debug(f"Stored response {len(self.recent_responses)}")

        except Exception as e:
            logger.error(f"Error handling response: {e}")

    def _handle_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error occurred: {error}")
        self._last_heartbeat = None

    async def send_task(self, task: str) -> TaskResponse:
        """Send a task through WebSocket"""
        if not self.ws_client or not self.ws_client.is_connected:
            raise HTTPException(
                status_code=503,
                detail="WebSocket client is not connected"
            )

        try:
            message = self.ws_client.create_message(task)
            success = self.ws_client.send_message(message)

            if success:
                return TaskResponse(
                    success=True,
                    message="Task sent successfully",
                    task_id=str(len(self.recent_responses))
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send task through WebSocket"
                )

        except Exception as e:
            logger.error(f"Error sending task: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    def get_status(self) -> StatusResponse:
        """Get current connection status"""
        connected = bool(self.ws_client and self.ws_client.is_connected)
        status = self.ws_client.status.value if self.ws_client else "disconnected"

        return StatusResponse(
            connected=connected,
            status=status,
            recent_responses=len(self.recent_responses),
            last_heartbeat=self._last_heartbeat
        )

    def get_recent_responses(self, limit: int = 10) -> List[dict]:
        """Get recent responses"""
        return self.recent_responses[-limit:]

    async def shutdown(self):
        """Shutdown the application gracefully"""
        logger.info("Shutting down AutoGLMUI...")

        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()
            try:
                await self._startup_task
            except asyncio.CancelledError:
                pass

        if self.ws_client:
            self.ws_client.disconnect()

        logger.info("AutoGLMUI shutdown complete")


# Global application instance
app_instance = AutoGLMUI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting AutoGLMUI application...")

    # Initialize application
    await app_instance.initialize()

    yield

    # Cleanup
    await app_instance.shutdown()


# Create FastAPI app
app = FastAPI(
    title="AutoGLMUI",
    description="A web interface for AutoGLM API",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main page"""
    status = app_instance.get_status()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "status_class": "connected" if status.connected else "disconnected",
            "status_text": "已连接" if status.connected else "未连接",
            "debug_mode": settings.debug
        }
    )


@app.post("/api/send-task", response_model=TaskResponse)
async def send_task(task_request: TaskRequest):
    """Send a task through WebSocket"""
    return await app_instance.send_task(task_request.task)


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get WebSocket connection status"""
    return app_instance.get_status()


@app.get("/api/responses")
async def get_recent_responses(limit: int = 10):
    """Get recent WebSocket responses"""
    if limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit cannot exceed 100"
        )

    return {"responses": app_instance.get_recent_responses(limit)}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = app_instance.get_status()

    return {
        "status": "healthy" if status.connected else "degraded",
        "websocket_connected": status.connected,
        "timestamp": time.time()
    }