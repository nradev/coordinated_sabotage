"""
Middleware components for the web server.
"""

import time
import logging
from typing import Optional, Callable
from .request import Request
from .response import Response


class Middleware:
    """Base middleware class."""

    def __call__(self, request: Request) -> Optional[Response]:
        """Process the request. Return None to continue, or Response to short-circuit."""
        return None


class AuthMiddleware(Middleware):
    """Simple authentication middleware."""

    def __init__(
        self,
        auth_function: Callable[[Request], bool] = None,
        protected_paths: list = None,
    ):
        self.auth_function = auth_function or self._default_auth
        self.protected_paths = protected_paths or []

    def __call__(self, request: Request) -> Optional[Response]:
        """Check authentication for protected paths."""
        # Check if path requires authentication
        path_protected = any(request.path.startswith(path) for path in self.protected_paths)

        if path_protected:
            if not self.auth_function(request):
                return Response("Unauthorized", status_code=401)

        return None

    def _default_auth(self, request: Request) -> bool:
        """Default authentication - check for Authorization header."""
        auth_header = request.get_header("Authorization")
        return auth_header is not None and auth_header.startswith("Bearer ")


class RateLimitMiddleware(Middleware):
    """Simple rate limiting middleware."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # Simple in-memory storage

    def __call__(self, request: Request) -> Optional[Response]:
        """Check rate limits."""
        # Use a simple IP-based rate limiting (in real implementation,
        # you'd get the actual client IP)
        client_id = request.get_header("X-Forwarded-For") or "unknown"
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_entries(current_time)

        # Check current client's requests
        if client_id not in self.requests:
            self.requests[client_id] = []

        client_requests = self.requests[client_id]

        # Count requests in current window
        window_start = current_time - self.window_seconds
        recent_requests = [req_time for req_time in client_requests if req_time > window_start]

        if len(recent_requests) >= self.max_requests:
            return Response("Too Many Requests", status_code=429)

        # Add current request
        recent_requests.append(current_time)
        self.requests[client_id] = recent_requests

        return None

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove old entries to prevent memory leaks."""
        cutoff_time = current_time - self.window_seconds * 2  # Keep some buffer

        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [req_time for req_time in self.requests[client_id] if req_time > cutoff_time]

            # Remove empty entries
            if not self.requests[client_id]:
                del self.requests[client_id]


class LoggingMiddleware(Middleware):
    """Middleware for logging requests."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, request: Request) -> Optional[Response]:
        """Log the incoming request."""
        self.logger.info(f"{request.method} {request.path} from {request.get_header('Host', 'unknown')}")
        return None


class CORSMiddleware(Middleware):
    """Cross-Origin Resource Sharing (CORS) middleware."""

    def __init__(self, allowed_origins=None, allowed_methods=None, allowed_headers=None):
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["Content-Type", "Authorization"]

    def __call__(self, request: Request) -> Optional[Response]:
        """Handle CORS preflight requests."""
        if request.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": ", ".join(self.allowed_origins),
                "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
                "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
                "Access-Control-Max-Age": "86400",
            }
            return Response("", status_code=200, headers=headers)
        return None
