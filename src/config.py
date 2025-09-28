"""
Configuration management for AutoGLMUI
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    # AutoGLM API settings
    autoglm_api_url: str = "wss://open.bigmodel.cn/api/paas/v4/channel/task"
    autoglm_api_token: Optional[str] = None

    # WebSocket settings
    websocket_timeout: int = 30
    max_reconnect_attempts: int = 5

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        env_prefix = "AUTOGLM_"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the current settings instance"""
    return settings