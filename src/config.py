"""
Configuration management for AutoGLMUI - Simple version
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings"""

    def __init__(self):
        # Server settings
        self.host = os.getenv("AUTOGLM_HOST", "127.0.0.1")
        self.port = int(os.getenv("AUTOGLM_PORT", "8000"))
        self.debug = os.getenv("AUTOGLM_DEBUG", "false").lower() == "true"

        # AutoGLM API settings
        self.autoglm_api_url = os.getenv("AUTOGLM_AUTOGLM_API_URL", "wss://autoglm-api.zhipuai.cn/openapi/v1/autoglm/developer")
        self.autoglm_api_token = os.getenv("AUTOGLM_AUTOGLM_API_TOKEN")

        # WebSocket settings
        self.websocket_timeout = int(os.getenv("AUTOGLM_WEBSOCKET_TIMEOUT", "30"))
        self.max_reconnect_attempts = int(os.getenv("AUTOGLM_MAX_RECONNECT_ATTEMPTS", "5"))

        # Logging
        self.log_level = os.getenv("AUTOGLM_LOG_LEVEL", "INFO")
        self.log_format = os.getenv("AUTOGLM_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the current settings instance"""
    return settings