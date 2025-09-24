# Simple Web Server

A lightweight HTTP web server implementation in Python with routing, middleware support, and comprehensive testing.

## Features

- **HTTP Server**: Basic HTTP/1.1 server implementation
- **Routing**: URL routing with path parameters (e.g., `/users/{id}`)
- **Middleware**: Pluggable middleware system with built-in components
- **Request/Response**: Clean request and response handling
- **JSON Support**: Automatic JSON parsing and response generation
- **Threading**: Multi-threaded request handling

## Project Structure

```
webserver/
├── src/webserver/       # Source package (src layout)
│   ├── __init__.py      # Package initialization
│   ├── server.py        # Main WebServer class
│   ├── router.py        # URL routing and path parameters
│   ├── request.py       # HTTP request handling
│   ├── response.py      # HTTP response handling
│   └── middleware.py    # Middleware components
├── example_app.py       # Example application
├── demo.py              # Interactive demo server
├── run_tests.py         # Test runner script
├── pyproject.toml       # Project configuration (uv/pip)
├── .python-version      # Python version specification
├── uv.lock              # Dependency lock file
├── requirements-test.txt # Test dependencies (legacy)
├── README.md            # This file
└── tests/               # Test suite
    ├── __init__.py
    ├── test_request.py
    ├── test_response.py
    ├── test_router.py
    ├── test_middleware.py
    ├── test_server.py
    └── test_integration.py
```

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the project and dependencies
uv sync

# Or install in development mode with test dependencies
uv sync --dev
```

### Using pip

```bash
# No external dependencies required - uses only Python standard library
python3 -m pip install -r requirements-test.txt  # Only for running tests
```

## Quick Start

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

### Running the Example

```bash
# Using uv
uv run python example_app.py

# Or using the demo script
uv run python demo.py

# Using regular Python
cd webserver
python example_app.py
```

Visit `http://localhost:8000` to see the example application.

## API Reference

### WebServer

```python
server = WebServer(host='localhost', port=8000, router=None)
```

**Methods:**
- `start()` - Start the server
- `stop()` - Stop the server
- `@server.get(pattern)` - Add GET route
- `@server.post(pattern)` - Add POST route
- `@server.put(pattern)` - Add PUT route
- `@server.delete(pattern)` - Add DELETE route
- `@server.route(pattern, methods=[])` - Add route with custom methods
- `add_middleware(middleware)` - Add middleware

### Request

```python
request.method          # HTTP method (GET, POST, etc.)
request.path           # Request path
request.headers        # Dictionary of headers
request.body           # Raw request body (bytes)
request.query_params   # Parsed query parameters
request.json           # Parsed JSON data (if Content-Type is application/json)
request.content_length # Content length
request.get_header(name, default=None)  # Get header value
```

### Response

```python
response = Response(body, status_code=200, headers={})

# Class methods
Response.json(data, status_code=200)    # JSON response
Response.text(text, status_code=200)    # Plain text response
Response.html(html, status_code=200)    # HTML response

# Methods
response.set_header(name, value)        # Set header
response.set_cookie(name, value, ...)   # Set cookie
```

### Router

```python
router = Router()

@router.get('/path/{param}')
def handler(request, param):
    return Response('OK')

router.add_middleware(middleware_function)
```


## Testing

### Install Test Dependencies

```bash
# Using uv (installs test dependencies automatically)
uv sync --dev

# Using pip
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Using uv
uv run python run_tests.py

# Using pytest directly with uv
uv run pytest tests/ -v

# Using regular Python
python run_tests.py
```

### Run Specific Test File

```bash
# Using uv
uv run python run_tests.py test_server
uv run python run_tests.py test_router.py

# Using regular Python
python run_tests.py test_server
python run_tests.py test_router.py
```

### Run Tests with pytest Directly

```bash
# Using uv
uv run pytest tests/ -v --tb=short

# Using regular Python
pytest tests/ -v --cov=webserver
```

### Test Coverage

The test suite includes:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end server testing
- **Middleware Tests**: All middleware components
- **Error Handling**: Exception and error scenarios
- **Concurrent Requests**: Multi-threading tests

Coverage report is generated in `htmlcov/` directory.

## Examples

### Path Parameters

```python
@app.get('/users/{user_id}/posts/{post_id}')
def get_user_post(request, user_id, post_id):
    return Response.json({
        'user_id': int(user_id),
        'post_id': int(post_id)
    })
```

### JSON API

```python
@app.post('/api/data')
def create_data(request):
    data = request.json
    if not data:
        return Response.json({'error': 'No data provided'}, status_code=400)
    
    # Process data...
    return Response.json({'id': 123, 'status': 'created'}, status_code=201)
```

### Custom Middleware

```python
def custom_middleware(request):
    # Add custom header to all responses
    if request.path.startswith('/api/'):
        # Could modify request or return early response
        pass
    return None  # Continue to next middleware/handler

app.add_middleware(custom_middleware)
```

### Error Handling

```python
@app.get('/api/error')
def error_handler(request):
    try:
        # Some operation that might fail
        result = risky_operation()
        return Response.json({'result': result})
    except Exception as e:
        return Response.json({'error': str(e)}, status_code=500)
```

## Development

### Using uv for Development

```bash
# Install in development mode with all dependencies
uv sync --dev

# Run linting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run mypy webserver/

# Run tests with coverage
uv run pytest tests/ -v --tb=short

# Install additional development tools
uv add --dev black isort flake8
```

### Project Scripts

The project includes a console script that can be installed:

```bash
# After installation, you can run the demo directly
uv run webserver-demo

# Or if installed globally
webserver-demo
```

### Building and Publishing

```bash
# Build the package
uv build

# Install locally for testing
uv pip install dist/simple_webserver-*.whl
```

## License

This project is provided as-is for educational and demonstration purposes.
