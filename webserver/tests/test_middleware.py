"""
Tests for middleware classes.
"""

import sys
import os
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from webserver.middleware import (
    AuthMiddleware,
    CORSMiddleware,
    LoggingMiddleware,
    Middleware,
    RateLimitMiddleware,
)
from webserver.request import Request
from webserver.response import Response


class TestMiddleware:
    """Test cases for the base Middleware class."""

    def test_base_middleware_call(self):
        """Test base middleware returns None."""
        middleware = Middleware()
        request = Request("GET", "/test", {})

        result = middleware(request)
        assert result is None


class TestLoggingMiddleware:
    """Test cases for LoggingMiddleware."""

    def test_logging_middleware_creation(self):
        """Test creating logging middleware."""
        middleware = LoggingMiddleware()
        assert middleware.logger is not None

    @patch("webserver.middleware.logging.getLogger")
    def test_logging_middleware_logs_request(self, mock_get_logger):
        """Test that logging middleware logs requests."""
        mock_logger = mock_get_logger.return_value

        middleware = LoggingMiddleware()
        request = Request("GET", "/test", {"Host": "localhost:8000"})

        result = middleware(request)

        # Should return None (not intercept request)
        assert result is None

        # Should have logged the request
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "GET" in call_args
        assert "/test" in call_args


class TestCORSMiddleware:
    """Test cases for CORSMiddleware."""

    def test_cors_middleware_creation(self):
        """Test creating CORS middleware with defaults."""
        middleware = CORSMiddleware()

        assert middleware.allowed_origins == ["*"]
        assert "GET" in middleware.allowed_methods
        assert "POST" in middleware.allowed_methods

    def test_cors_middleware_custom_config(self):
        """Test creating CORS middleware with custom configuration."""
        middleware = CORSMiddleware(
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type"],
        )

        assert middleware.allowed_origins == ["https://example.com"]
        assert middleware.allowed_methods == ["GET", "POST"]
        assert middleware.allowed_headers == ["Content-Type"]

    def test_cors_preflight_request(self):
        """Test CORS preflight OPTIONS request."""
        middleware = CORSMiddleware()
        request = Request("OPTIONS", "/test", {"Origin": "https://example.com"})

        response = middleware(request)

        assert isinstance(response, Response)
        assert response.status_code == 204  # CORS preflight returns 204
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_regular_request(self):
        """Test CORS headers added to regular request."""
        middleware = CORSMiddleware()
        request = Request("GET", "/test", {"Origin": "https://example.com"})

        result = middleware(request)

        # Should not intercept regular requests
        assert result is None

    def test_cors_no_origin_header(self):
        """Test CORS middleware with no Origin header."""
        middleware = CORSMiddleware()
        request = Request("GET", "/test", {})

        result = middleware(request)
        assert result is None


class TestAuthMiddleware:
    """Test cases for AuthMiddleware."""

    def test_auth_middleware_creation(self):
        """Test creating auth middleware."""
        middleware = AuthMiddleware(
            protected_paths=["/admin"], valid_tokens=["token123"]
        )

        assert middleware.protected_paths == ["/admin"]
        assert middleware.valid_tokens == ["token123"]

    def test_auth_middleware_unprotected_path(self):
        """Test auth middleware allows unprotected paths."""
        middleware = AuthMiddleware(protected_paths=["/admin"])
        request = Request("GET", "/public", {})

        result = middleware(request)
        assert result is None

    def test_auth_middleware_protected_path_no_token(self):
        """Test auth middleware blocks protected path without token."""
        middleware = AuthMiddleware(protected_paths=["/admin"])
        request = Request("GET", "/admin", {})

        response = middleware(request)

        assert isinstance(response, Response)
        assert response.status_code == 401

    def test_auth_middleware_protected_path_invalid_token(self):
        """Test auth middleware blocks protected path with invalid token."""
        middleware = AuthMiddleware(
            protected_paths=["/admin"], valid_tokens=["valid_token"]
        )
        request = Request("GET", "/admin", {"Authorization": "Bearer invalid_token"})

        response = middleware(request)

        assert isinstance(response, Response)
        assert response.status_code == 403  # Invalid token returns 403

    def test_auth_middleware_protected_path_valid_token(self):
        """Test auth middleware allows protected path with valid token."""
        middleware = AuthMiddleware(
            protected_paths=["/admin"], valid_tokens=["valid_token"]
        )
        request = Request("GET", "/admin", {"Authorization": "Bearer valid_token"})

        result = middleware(request)
        assert result is None

    def test_auth_middleware_malformed_auth_header(self):
        """Test auth middleware handles malformed Authorization header."""
        middleware = AuthMiddleware(protected_paths=["/admin"])
        request = Request("GET", "/admin", {"Authorization": "InvalidFormat"})

        response = middleware(request)

        assert isinstance(response, Response)
        assert response.status_code == 401


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""

    def test_rate_limit_middleware_creation(self):
        """Test creating rate limit middleware."""
        middleware = RateLimitMiddleware(max_requests=5, window_seconds=60)

        assert middleware.max_requests == 5
        assert middleware.window_seconds == 60
        assert middleware.clients == {}  # The actual attribute name is 'clients'

    def test_rate_limit_allows_initial_requests(self):
        """Test rate limit allows initial requests."""
        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})

        # First request should be allowed
        result = middleware(request)
        assert result is None

        # Second request should be allowed
        result = middleware(request)
        assert result is None

    def test_rate_limit_blocks_excess_requests(self):
        """Test rate limit blocks requests exceeding limit."""
        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})

        # First request should be allowed
        result = middleware(request)
        assert result is None

        # Second request should be blocked
        response = middleware(request)
        assert isinstance(response, Response)
        assert response.status_code == 429

    def test_rate_limit_different_clients(self):
        """Test rate limit tracks different clients separately."""
        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60)

        request1 = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})
        request2 = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.2"})

        # Both clients should be allowed their first request
        result1 = middleware(request1)
        result2 = middleware(request2)

        assert result1 is None
        assert result2 is None

    @patch("webserver.middleware.time.time")
    def test_rate_limit_window_expiry(self, mock_time):
        """Test rate limit window expiry."""
        # Start at time 0
        mock_time.return_value = 0

        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})

        # First request at time 0
        result = middleware(request)
        assert result is None

        # Second request at time 0 should be blocked
        response = middleware(request)
        assert response.status_code == 429

        # Move time forward past window
        mock_time.return_value = 61

        # Request should now be allowed again
        result = middleware(request)
        assert result is None
