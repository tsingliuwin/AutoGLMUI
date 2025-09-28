# AutoGLMUI

A modern web interface for interacting with the AutoGLM API (z1 AutoGLM ). This project provides both a web-based UI and a command-line interface for sending tasks to AutoGLM and receiving real-time responses.

## Quick Start / 快速开始

### 1. Set API Token / 设置API Token

Before running, please set your AutoGLM API Token first:

**Windows:**
```cmd
set AUTOGLM_AUTOGLM_API_TOKEN=your_token
```

**Linux/Mac:**
```bash
export AUTOGLM_AUTOGLM_API_TOKEN=your_token
```

### 2. Run the Application / 运行应用

#### Method 1: Using the launcher (recommended) / 方式一：使用启动器（推荐）
```bash
python run.py
```

#### Method 2: Run web server directly / 方式二：直接运行Web服务器
```bash
python main.py
```
Then open your browser and visit: http://localhost:8000

#### Method 3: Use CLI client / 方式三：使用命令行客户端
```bash
python auto.py
```

### 3. Usage Instructions / 使用说明

#### Web Interface / Web界面
1. Open http://localhost:8000 in your browser
2. Enter your task in the input box
3. Click the "Send" button
4. View the returned results

#### Command Line Interface / 命令行界面
1. Enter your task directly after running
2. Press Enter to send
3. Type `quit` to exit

### Common Issues / 常见问题

1. **Connection Failed / 连接失败**
   - Check if API Token is set correctly
   - Check network connection
   - View error messages in console output

2. **Port Already in Use / 端口被占用**
   - Change port number: `set AUTOGLM_PORT=8001`

3. **Need Debug Information / 需要调试信息**
   - Enable debug mode: `set AUTOGLM_DEBUG=true`

## Features

- **Web Interface**: Clean, responsive web UI for interacting with AutoGLM
- **CLI Client**: Command-line interface for direct WebSocket communication
- **WebSocket Support**: Real-time bidirectional communication with AutoGLM API
- **Configuration Management**: Environment-based configuration with `.env` support
- **Logging**: Structured logging for debugging and monitoring
- **Auto-Reconnection**: Automatic reconnection with exponential backoff
- **Error Handling**: Comprehensive error handling and graceful degradation

## Installation

### Prerequisites

- Python 3.8 or higher
- An AutoGLM API token from Zhipu AI

### Install from source

```bash
git clone https://github.com/yourusername/AutoGLMUI.git
cd AutoGLMUI
pip install -e .
```

### Install development dependencies

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# AutoGLM API Configuration
AUTOGLM_AUTOGLM_API_TOKEN=your_autoglm_api_token_here

# Server Configuration
AUTOGLM_HOST=127.0.0.1
AUTOGLM_PORT=8000
AUTOGLM_DEBUG=false

# WebSocket Configuration
AUTOGLM_WEBSOCKET_TIMEOUT=30
AUTOGLM_MAX_RECONNECT_ATTEMPTS=5

# Logging Configuration
AUTOGLM_LOG_LEVEL=INFO
```

## Usage

### Web Interface

Start the web server:

```bash
python main.py
```

Or using the development server with hot reload:

```bash
AUTOGLM_DEBUG=true python main.py
```

Open your browser and navigate to `http://localhost:8000`

### Command Line Interface

Run the CLI client:

```bash
python auto.py
```

Or with a custom token:

```bash
python auto.py --token your_api_token
```

### Environment Variables

You can also configure the application using environment variables:

```bash
export AUTOGLM_AUTOGLM_API_TOKEN=your_token
export AUTOGLM_HOST=0.0.0.0
export AUTOGLM_PORT=8080
python main.py
```

## API Endpoints

### Web API

- `GET /` - Main web interface
- `POST /api/send-task` - Send a task to AutoGLM
- `GET /api/status` - Get WebSocket connection status
- `GET /api/responses` - Get recent responses
- `GET /health` - Health check endpoint

## Development

### Code Formatting

The project uses Black for code formatting and isort for import sorting:

```bash
black .
isort .
```

### Type Checking

```bash
mypy src/
```

### Linting

```bash
flake8 src/
```

### Running Tests

```bash
pytest
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pre-commit install
```

## Project Structure

```
AutoGLMUI/
├── src/
│   ├── __init__.py
│   ├── app.py              # FastAPI application
│   ├── config.py           # Configuration management
│   ├── logging_config.py   # Logging setup
│   ├── websocket_client.py # WebSocket client
│   └── dependencies.py     # Dependency injection
├── static/
│   └── style.css           # CSS styles
├── templates/
│   └── index.html          # Web interface template
├── main.py                 # Web server entry point
├── auto.py                 # CLI client
├── pyproject.toml          # Project configuration
├── .env.example            # Environment template
└── README.md               # This file
```

## Security Notes

- Never commit your API token to version control
- Use environment variables or a `.env` file for sensitive configuration
- The web interface is intended for local development use only
- Consider adding authentication for production deployment

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and ensure they pass tests
4. Format your code: `black . && isort .`
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the [documentation](https://github.com/yourusername/AutoGLMUI/wiki)
- Join our community discussions

## Acknowledgments

- [Zhipu AI](https://zhipuai.cn/) for the AutoGLM API
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [WebSocket-Client](https://github.com/websocket-client/websocket-client) for WebSocket support