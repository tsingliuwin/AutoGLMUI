"""
Main entry point for AutoGLMUI
"""
import uvicorn
from src.app import app
from src.config import settings
from src.logging_config import logger


def main():
    """Run the AutoGLMUI application"""
    logger.info(f"Starting AutoGLMUI on {settings.host}:{settings.port}")

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )


if __name__ == "__main__":
    main()