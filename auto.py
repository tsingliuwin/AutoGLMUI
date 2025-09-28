#!/usr/bin/env python3
"""
Standalone AutoGLM WebSocket client
"""
import sys
import argparse
import signal
from typing import Optional

from src.config_simple import settings
from src.logging_simple import logger
from src.websocket_client import WebSocketClient


class AutoGLMCLI:
    """Command-line interface for AutoGLM"""

    def __init__(self):
        self.ws_client: Optional[WebSocketClient] = None
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.ws_client:
            self.ws_client.disconnect()
        sys.exit(0)

    def _handle_response(self, message: str):
        """Handle incoming messages"""
        print(f"\nReceived: {message}")
        print("\n> ", end="", flush=True)

    def _handle_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        print(f"\nError: {error}")
        print("> ", end="", flush=True)

    def run(self):
        """Run the CLI client"""
        # Check configuration
        if not settings.autoglm_api_token:
            logger.error("AutoGLM API token not configured. Please set AUTOGLM_AUTOGLM_API_TOKEN environment variable.")
            sys.exit(1)

        # Create WebSocket client
        headers = {
            "Authorization": f"Bearer {settings.autoglm_api_token}"
        }

        self.ws_client = WebSocketClient(settings.autoglm_api_url, headers)
        self.ws_client.set_response_callback(self._handle_response)
        self.ws_client.set_error_callback(self._handle_error)

        # Connect to WebSocket
        logger.info("Connecting to AutoGLM WebSocket...")
        if not self.ws_client.connect():
            logger.error("Failed to connect to WebSocket")
            sys.exit(1)

        print("\n" + "="*50)
        print("AutoGLM WebSocket Client")
        print("="*50)
        print("\nType your task to send to AutoGLM, or 'quit' to exit:")
        print("Example: 帮我在小红书找三篇云南的旅游攻略汇总一篇\n")

        # Main interaction loop
        try:
            while self.running and self.ws_client.is_connected:
                try:
                    # Get user input
                    task = input("> ").strip()

                    # Check commands
                    if task.lower() in ['quit', 'exit', 'q']:
                        break
                    elif task.lower() in ['help', 'h']:
                        self._print_help()
                        continue
                    elif not task:
                        continue

                    # Send task
                    message = self.ws_client.create_message(task)
                    if not self.ws_client.send_message(message):
                        print("Failed to send message")

                except KeyboardInterrupt:
                    break
                except EOFError:
                    break

        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        finally:
            # Cleanup
            logger.info("Shutting down...")
            if self.ws_client:
                self.ws_client.disconnect()
            print("\nGoodbye!")

    def _print_help(self):
        """Print help information"""
        print("\nAvailable commands:")
        print("  quit/exit/q  - Exit the client")
        print("  help/h       - Show this help message")
        print("\nJust type your task and press Enter to send it to AutoGLM")
        print("> ", end="", flush=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AutoGLM WebSocket CLI Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  auto.py
  AUTOGLM_AUTOGLM_API_TOKEN=your_token auto.py
        """
    )

    parser.add_argument(
        "--token",
        help="AutoGLM API token (overrides environment variable)"
    )

    args = parser.parse_args()

    # Override token if provided
    if args.token:
        settings.autoglm_api_token = args.token

    # Run CLI
    cli = AutoGLMCLI()
    cli.run()


if __name__ == "__main__":
    main()