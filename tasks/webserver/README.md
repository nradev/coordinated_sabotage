# Simple Web Server

A lightweight HTTP web server implementation in Python with routing, middleware support, and comprehensive testing.

## Features

- **HTTP Server**: Basic HTTP/1.1 server implementation with multi-threading
- **Routing**: URL routing with path parameters (e.g., `/users/{id}`)
- **Middleware System**: Fully integrated pluggable middleware architecture
  - **LoggingMiddleware**: Request logging (enabled by default)
  - **AuthMiddleware**: Path-based authentication
  - **RateLimitMiddleware**: Request rate limiting
  - **CORSMiddleware**: Cross-Origin Resource Sharing support
- **Request/Response**: Clean request and response handling
- **JSON Support**: Automatic JSON parsing and response generation
- **Testing**: Complete test suite with 95%+ coverage

## Project Structure

```
webserver/
├── src/webserver/          # Main package
│   ├── __init__.py         # Package exports
│   ├── server.py           # HTTP server implementation
│   ├── router.py           # URL routing system
│   ├── request.py          # HTTP request handling
│   ├── response.py         # HTTP response handling
│   └── middleware.py       # Middleware components
├── tests/                  # Test suite
│   ├── test_server.py      # Server tests
│   ├── test_router.py      # Router tests
│   ├── test_request.py     # Request tests
│   ├── test_response.py    # Response tests
│   └── test_middleware.py  # Middleware tests
├── example_app.py          # Example application
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Installation

### Using uv (recommended)

```bash
# Clone or create the project
cd webserver

# Install dependencies
uv sync --dev

# Install in development mode
uv pip install -e .
```

### Using pip

```bash
# Install dependencies
pip install -e .
pip install pytest pytest-cov requests ruff mypy
```

## Usage

### Basic Usage

```python
from webserver import WebServer, Response

# Create server
app = WebServer(host='localhost', port=8000)

# Add routes
@app.get('/')
def home(request):
    return Response.html('<h1>Hello, World!</h1>')

@app.get('/api/users/{user_id}')
def get_user(request, user_id):
    return Response.json({'user_id': int(user_id), 'name': f'User {user_id}'})

@app.post('/api/users')
def create_user(request):
    data = request.json
    if not data or 'name' not in data:
        return Response.json({'error': 'Name required'}, status_code=400)
    
    return Response.json({'id': 123, 'name': data['name']}, status_code=201)

# Start server
if __name__ == '__main__':
    try:
        print("Server starting on http://localhost:8000")
        app.start()
    except KeyboardInterrupt:
        app.stop()
```

### Middleware Usage

The webserver includes a comprehensive middleware system with built-in components:

```python
from webserver import (
    WebServer, Response, 
    AuthMiddleware, RateLimitMiddleware, CORSMiddleware
)

# Create server (LoggingMiddleware added automatically)
app = WebServer()

# Add CORS support
app.add_middleware(CORSMiddleware(
    allowed_origins=["http://localhost:3000"],
    allowed_methods=["GET", "POST", "PUT", "DELETE"]
))

# Add authentication for protected routes
app.add_middleware(AuthMiddleware(
    protected_paths=["/api/admin", "/api/users"]
))

# Add rate limiting
app.add_middleware(RateLimitMiddleware(
    max_requests=100, 
    window_seconds=60
))

@app.get('/api/public')
def public_endpoint(request):
    return Response.json({'message': 'Public endpoint'})

@app.get('/api/admin')  # Protected by AuthMiddleware
def admin_endpoint(request):
    return Response.json({'message': 'Admin access granted'})
```

**Available Middleware:**
- **LoggingMiddleware**: Automatically logs all requests (enabled by default)
- **CORSMiddleware**: Handles Cross-Origin Resource Sharing headers and preflight requests
- **AuthMiddleware**: Protects specified paths with Bearer token authentication
- **RateLimitMiddleware**: Limits requests per client within a time window

### Running the Example

```bash
# Using uv
uv run python example_app.py

# Or using the demo script
uv run python demo.py

# Run middleware integration demo
uv run python middleware_demo.py

# Using regular Python
cd webserver
python example_app.py
```

## Testing

Run the comprehensive test suite:

```bash
# Using uv
uv run pytest

# With coverage
uv run pytest --cov=webserver --cov-report=html

# Using regular Python
python -m pytest
python -m pytest --cov=webserver --cov-report=html
```

## Development

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run mypy src/webserver
```

### Project Structure

The project follows modern Python packaging standards:
- **src layout**: Package code in `src/webserver/`
- **pyproject.toml**: Modern project configuration
- **uv**: Fast Python package manager
- **pytest**: Testing framework with coverage
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking

## API Reference

### WebServer

Main server class with routing and middleware support.

```python
server = WebServer(host="localhost", port=8000)
server.add_middleware(middleware)
server.start()
server.stop()
```

### Request

HTTP request object with parsing capabilities.

```python
request.method          # HTTP method (GET, POST, etc.)
request.path            # Request path
request.headers         # Request headers dict
request.body            # Raw request body (bytes)
request.json            # Parsed JSON data (if applicable)
request.query_params    # Parsed query parameters
request.get_header(name, default=None)  # Get header value
```

### Response

HTTP response object with various content types.

```python
Response.json(data, status_code=200)
Response.html(html, status_code=200)
Response.text(text, status_code=200)
response.set_header(name, value)
response.set_cookie(name, value, **options)
```

### Middleware

Base middleware class for custom middleware development.

```python
class CustomMiddleware(Middleware):
    def __call__(self, request):
        # Process request
        # Return None to continue, or Response to short-circuit
        return None
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Changelog

### v0.1.0
- Initial release
- HTTP/1.1 server implementation
- URL routing with path parameters
- Comprehensive middleware system
- Request/response handling
- JSON support
- Complete test suite
