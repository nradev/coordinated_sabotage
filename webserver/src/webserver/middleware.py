"""
Middleware system for the web server.
"""

from typing import Optional, List, Dict, Any
from .request import Request
from .response import Response
import time
import logging


class Middleware:
    """Base middleware class."""

    def __call__(self, request: Request) -> Optional[Response]:
        """Process the request. Return None to continue, or Response to short-circuit."""
        return None


class LoggingMiddleware(Middleware):
    """Middleware for logging HTTP requests."""

    def __init__(self, logger_name: str = "webserver"):
        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def __call__(self, request: Request) -> Optional[Response]:
        """Log the incoming request."""
        client_ip = request.get_header("X-Forwarded-For", "unknown")
        user_agent = request.get_header("User-Agent", "unknown")

        self.logger.info(f"{request.method} {request.path} - Client: {client_ip} - User-Agent: {user_agent[:50]}...")
        return None


class CORSMiddleware(Middleware):
    """Middleware for handling Cross-Origin Resource Sharing (CORS)."""

    def __init__(
        self,
        allowed_origins: List[str] = None,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        max_age: int = 86400,
    ):
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["Content-Type", "Authorization"]
        self.max_age = max_age

    def __call__(self, request: Request) -> Optional[Response]:
        """Handle CORS headers and preflight requests."""
        origin = request.get_header("Origin")

        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            response = Response("", status_code=204)
            self._add_cors_headers(response, origin)
            response.set_header("Access-Control-Max-Age", str(self.max_age))
            return response

        return None

    def _add_cors_headers(self, response: Response, origin: str = None) -> None:
        """Add CORS headers to response."""
        if "*" in self.allowed_origins or (origin and origin in self.allowed_origins):
            response.set_header("Access-Control-Allow-Origin", origin or "*")

        response.set_header("Access-Control-Allow-Methods", ", ".join(self.allowed_methods))
        response.set_header("Access-Control-Allow-Headers", ", ".join(self.allowed_headers))
        response.set_header("Access-Control-Allow-Credentials", "true")


class AuthMiddleware(Middleware):
    """Middleware for authentication."""

    def __init__(self, protected_paths: List[str] = None, valid_tokens: List[str] = None):
        self.protected_paths = protected_paths or []
        self.valid_tokens = valid_tokens or ["valid-token", "admin-token"]

    def __call__(self, request: Request) -> Optional[Response]:
        """Check authentication for protected paths."""
        # Check if path is protected
        is_protected = any(request.path.startswith(path) for path in self.protected_paths)

        if not is_protected:
            return None

        # Check for Authorization header
        auth_header = request.get_header("Authorization")
        if not auth_header:
            return Response.json({"error": "Authorization header required"}, status_code=401)

        # Extract token from "Bearer <token>" format
        if not auth_header.startswith("Bearer "):
            return Response.json({"error": "Invalid authorization format. Use 'Bearer <token>'"}, status_code=401)

        token = auth_header[7:]  # Remove "Bearer " prefix

        if token not in self.valid_tokens:
            return Response.json({"error": "Invalid token"}, status_code=403)

        return None


class RateLimitMiddleware(Middleware):
    """Middleware for rate limiting requests."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, List[float]] = {}

    def __call__(self, request: Request) -> Optional[Response]:
        """Check rate limits for the client."""
        client_ip = request.get_header("X-Forwarded-For") or request.get_header("X-Real-IP") or "unknown"

        current_time = time.time()

        # Initialize client if not exists
        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # Clean old requests outside the window
        client_requests = self.clients[client_ip]
        client_requests[:] = [req_time for req_time in client_requests if current_time - req_time < self.window_seconds]

        # Check if limit exceeded
        if len(client_requests) >= self.max_requests:
            return Response.json(
                {
                    "error": "Rate limit exceeded",
                    "limit": self.max_requests,
                    "window": self.window_seconds,
                    "retry_after": self.window_seconds,
                },
                status_code=429,
            )

        # Add current request
        client_requests.append(current_time)

        return None
