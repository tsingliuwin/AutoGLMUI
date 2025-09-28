"""
Dependency injection utilities for AutoGLMUI
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from .app import app_instance
from .logging_config import logger


async def get_websocket_client():
    """Dependency to get WebSocket client"""
    if not app_instance.ws_client or not app_instance.ws_client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket service unavailable"
        )
    return app_instance.ws_client


async def require_websocket_connection():
    """Dependency that requires active WebSocket connection"""
    ws_status = app_instance.get_status()
    if not ws_status.connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket connection not available"
        )