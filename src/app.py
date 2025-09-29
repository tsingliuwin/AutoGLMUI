"""
Main FastAPI application for AutoGLMUI - Simple version
"""
from typing import List, Optional
from contextlib import asynccontextmanager
import time
import asyncio
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import settings
from .logging_config import logger
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
        self.response_queues: dict = {}  # 存储streaming响应队列
        self._response_event = asyncio.Event()  # 用于通知新响应的事件

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

            # 解析消息类型
            try:
                msg_data = json.loads(message)
                msg_type = msg_data.get("msg_type", "unknown")
                # Log the full message structure for debugging
                logger.debug(f"Full message structure: {json.dumps(msg_data, indent=2, ensure_ascii=False)}")

                # 创建响应数据
                response_data = {
                    "message": message,
                    "timestamp": timestamp,
                    "id": len(self.recent_responses),
                    "msg_type": msg_type,
                    "parsed_data": msg_data
                }

                # 特殊处理不同类型的消息
                if msg_type == "server_heartbeat":
                    # 心跳消息，不需要推送到前端
                    logger.debug("Received heartbeat message")
                    return

                elif msg_type == "server_init":
                    # 初始化消息
                    logger.info("Received server initialization message")

                elif msg_type == "server_session":
                    # 会话消息 - 提取conversation_id
                    logger.info("Received server_session message")
                    if self.ws_client and hasattr(msg_data, 'get') and msg_data.get('conversation_id'):
                        self.ws_client._conversation_id = msg_data.get('conversation_id')
                        logger.info(f"Updated conversation_id: {msg_data.get('conversation_id')}")

                elif msg_type in ["agent_response", "task_result"]:
                    # 重要的任务相关消息
                    logger.info(f"Received {msg_type} message")

                else:
                    # 其他消息类型
                    logger.debug(f"Received message of type: {msg_type}")
                    # 如果是错误消息，记录详细信息
                    if msg_type == "server_error":
                        logger.error(f"Server error details: {msg_data}")

            except json.JSONDecodeError:
                # 非 JSON 消息
                response_data = {
                    "message": message,
                    "timestamp": timestamp,
                    "id": len(self.recent_responses),
                    "msg_type": "raw",
                    "parsed_data": None
                }

            self.recent_responses.append(response_data)

            # Maintain response limit
            if len(self.recent_responses) > self.max_responses:
                self.recent_responses.pop(0)

            # 通知所有streaming连接有新响应
            for task_id, queue in self.response_queues.items():
                try:
                    # 使用 put_nowait 避免阻塞
                    queue.put_nowait(json.dumps({
                        "type": "response",
                        "data": response_data
                    }))
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for task {task_id}, dropping response")

            # 触发响应事件
            self._response_event.set()
            self._response_event.clear()

            logger.debug(f"Stored response {len(self.recent_responses)} (type: {response_data.get('msg_type', 'unknown')})")

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

        # Wait a bit for connection to fully establish
        await asyncio.sleep(0.5)

        try:
            message = self.ws_client.create_message(task)
            logger.info(f"About to send task: {task}")
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
    logger.info(f"=== API SEND TASK START ===")
    logger.info(f"Received task request: {task_request.task}")
    logger.info(f"WebSocket client exists: {app_instance.ws_client is not None}")
    logger.info(f"WebSocket connected: {app_instance.ws_client.is_connected if app_instance.ws_client else False}")

    result = await app_instance.send_task(task_request.task)

    logger.info(f"Task sent successfully, task_id: {result.task_id}")
    logger.info(f"=== API SEND TASK END ===")

    return result


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


@app.post("/api/send-task-stream")
async def send_task_stream(task_request: TaskRequest):
    """Send a task through WebSocket and stream responses using HTTP chunked encoding"""
    logger.info(f"=== API SEND TASK STREAM START ===")
    logger.info(f"Received streaming task request: {task_request.task}")
    logger.info(f"WebSocket client exists: {app_instance.ws_client is not None}")
    logger.info(f"WebSocket connected: {app_instance.ws_client.is_connected if app_instance.ws_client else False}")

    if not app_instance.ws_client or not app_instance.ws_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="WebSocket client is not connected"
        )

    task_id = str(int(time.time() * 1000))
    queue = asyncio.Queue()
    app_instance.response_queues[task_id] = queue
    logger.info(f"Created queue for task_id: {task_id}")

    async def generate():
        try:
            # 发送任务
            logger.info(f"=== ABOUT TO SEND MESSAGE TO AUTOGLM ===")
            message = app_instance.ws_client.create_message(task_request.task)
            logger.info(f"Created message: {message}")
            logger.info(f"About to call ws_client.send_message...")
            success = app_instance.ws_client.send_message(message)
            logger.info(f"send_message returned: {success}")

            if not success:
                yield json.dumps({
                    "type": "error",
                    "message": "Failed to send task"
                }).encode('utf-8') + b"\n"
                return

            # 发送任务确认
            yield json.dumps({
                "type": "sent",
                "message": "Task sent successfully",
                "task_id": task_id
            }).encode('utf-8') + b"\n"

            # 等待响应
            timeout = 300  # 5分钟超时
            start_time = time.time()
            last_response_time = start_time
            response_count = 0

            while time.time() - start_time < timeout:
                try:
                    # 等待新响应或超时
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=1.0)
                        last_response_time = time.time()
                        response_count += 1

                        # 直接发送原始数据
                        yield data.encode('utf-8') + b"\n"

                        # 如果是任务完成相关的消息，可以结束流
                        parsed = json.loads(data)
                        if parsed.get('type') == 'response':
                            msg_type = parsed['data'].get('msg_type', '')

                            # 检查是否是任务结束消息
                            if msg_type in ['task_result', 'task_complete', 'agent_finish']:
                                # 延迟一下再结束，确保所有消息都已发送
                                await asyncio.sleep(2)
                                yield json.dumps({
                                    "type": "complete",
                                    "message": "Task processing completed",
                                    "response_count": response_count
                                }).encode('utf-8') + b"\n"
                                break

                    except asyncio.TimeoutError:
                        # 检查是否超时
                        if time.time() - start_time >= timeout:
                            yield json.dumps({
                                "type": "complete",
                                "message": "Stream ended due to timeout",
                                "response_count": response_count
                            }).encode('utf-8') + b"\n"
                            break

                        # 如果超过30秒没有新响应，也结束流
                        if time.time() - last_response_time > 30:
                            yield json.dumps({
                                "type": "complete",
                                "message": "No new responses for 30 seconds",
                                "response_count": response_count
                            }).encode('utf-8') + b"\n"
                            break
                        continue

                except Exception as e:
                    logger.error(f"Error in streaming: {e}")
                    yield json.dumps({
                        "type": "error",
                        "message": str(e)
                    }).encode('utf-8') + b"\n"
                    break

        finally:
            # 清理队列
            if task_id in app_instance.response_queues:
                del app_instance.response_queues[task_id]

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Transfer-Encoding": "chunked"
        }
    )




@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = app_instance.get_status()

    return {
        "status": "healthy" if status.connected else "degraded",
        "websocket_connected": status.connected,
        "timestamp": time.time()
    }