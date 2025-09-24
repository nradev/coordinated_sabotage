"""
Tests for middleware components.
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch
from webserver.middleware import (
    Middleware, LoggingMiddleware, CORSMiddleware, 
    AuthMiddleware, RateLimitMiddleware
)
from webserver.request import Request
from webserver.response import Response


class TestMiddleware:
    """Test cases for the base Middleware class."""
    
    def test_base_middleware(self):
        """Test base middleware functionality."""
        middleware = Middleware()
        request = Request("GET", "/test", {})
        
        result = middleware(request)
        assert result is None


class TestLoggingMiddleware:
    """Test cases for LoggingMiddleware."""
    
    def test_logging_middleware_creation(self):
        """Test creating logging middleware."""
        logger = Mock()
        middleware = LoggingMiddleware(logger)
        
        assert middleware.logger == logger
    
    def test_logging_middleware_default_logger(self):
        """Test logging middleware with default logger."""
        middleware = LoggingMiddleware()
        
        assert middleware.logger is not None
    
    def test_logging_middleware_call(self):
        """Test logging middleware processing request."""
        logger = Mock()
        middleware = LoggingMiddleware(logger)
        request = Request("GET", "/test", {})
        
        result = middleware(request)
        
        assert result is None  # Should not block request
        logger.info.assert_called_once()
        assert "GET /test - Started" in logger.info.call_args[0][0]
    
    def test_logging_middleware_response_logging(self):
        """Test logging response."""
        logger = Mock()
        middleware = LoggingMiddleware(logger)
        request = Request("GET", "/test", {})
        response = Response("OK", status_code=200)
        
        # First call to start timing
        middleware(request)
        
        # Then log response
        middleware.log_response(request, response)
        
        assert logger.info.call_count == 2
        response_log = logger.info.call_args[0][0]
        assert "GET /test - 200" in response_log
        assert "ms" in response_log


class TestCORSMiddleware:
    """Test cases for CORSMiddleware."""
    
    def test_cors_middleware_creation(self):
        """Test creating CORS middleware."""
        middleware = CORSMiddleware()
        
        assert "*" in middleware.allowed_origins
        assert "GET" in middleware.allowed_methods
    
    def test_cors_middleware_custom_config(self):
        """Test CORS middleware with custom configuration."""
        middleware = CORSMiddleware(
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Authorization"],
            allow_credentials=True
        )
        
        assert middleware.allowed_origins == ["https://example.com"]
        assert middleware.allowed_methods == ["GET", "POST"]
        assert middleware.allowed_headers == ["Authorization"]
        assert middleware.allow_credentials is True
    
    def test_cors_preflight_request(self):
        """Test handling CORS preflight OPTIONS request."""
        middleware = CORSMiddleware()
        request = Request("OPTIONS", "/api/test", {"Origin": "https://example.com"})
        
        response = middleware(request)
        
        assert isinstance(response, Response)
        assert response.status_code == 204
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_cors_regular_request(self):
        """Test CORS middleware with regular request."""
        middleware = CORSMiddleware()
        request = Request("GET", "/api/test", {"Origin": "https://example.com"})
        
        result = middleware(request)
        
        assert result is None  # Should not block regular requests
    
    def test_cors_process_response(self):
        """Test adding CORS headers to response."""
        middleware = CORSMiddleware(allowed_origins=["https://example.com"])
        request = Request("GET", "/test", {"Origin": "https://example.com"})
        response = Response("OK")
        
        middleware.process_response(request, response)
        
        assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert "Access-Control-Allow-Methods" in response.headers
    
    def test_cors_wildcard_origin(self):
        """Test CORS with wildcard origin."""
        middleware = CORSMiddleware(allowed_origins=["*"])
        request = Request("GET", "/test", {"Origin": "https://any-domain.com"})
        response = Response("OK")
        
        middleware.process_response(request, response)
        
        assert response.headers["Access-Control-Allow-Origin"] == "*"
    
    def test_cors_credentials(self):
        """Test CORS with credentials enabled."""
        middleware = CORSMiddleware(allow_credentials=True)
        request = Request("GET", "/test", {"Origin": "https://example.com"})
        response = Response("OK")
        
        middleware.process_response(request, response)
        
        assert response.headers["Access-Control-Allow-Credentials"] == "true"


class TestAuthMiddleware:
    """Test cases for AuthMiddleware."""
    
    def test_auth_middleware_creation(self):
        """Test creating auth middleware."""
        middleware = AuthMiddleware()
        
        assert middleware.protected_paths == []
        assert middleware.auth_function is not None
    
    def test_auth_middleware_custom_config(self):
        """Test auth middleware with custom configuration."""
        def custom_auth(request):
            return True
        
        middleware = AuthMiddleware(
            auth_function=custom_auth,
            protected_paths=["/admin", "/api/private"]
        )
        
        assert middleware.auth_function == custom_auth
        assert "/admin" in middleware.protected_paths
    
    def test_auth_middleware_unprotected_path(self):
        """Test auth middleware with unprotected path."""
        middleware = AuthMiddleware(protected_paths=["/admin"])
        request = Request("GET", "/public", {})
        
        result = middleware(request)
        
        assert result is None  # Should not block unprotected paths
    
    def test_auth_middleware_protected_path_authorized(self):
        """Test auth middleware with authorized request to protected path."""
        def always_authorized(request):
            return True
        
        middleware = AuthMiddleware(
            auth_function=always_authorized,
            protected_paths=["/admin"]
        )
        request = Request("GET", "/admin/users", {})
        
        result = middleware(request)
        
        assert result is None  # Should allow authorized requests
    
    def test_auth_middleware_protected_path_unauthorized(self):
        """Test auth middleware with unauthorized request to protected path."""
        def never_authorized(request):
            return False
        
        middleware = AuthMiddleware(
            auth_function=never_authorized,
            protected_paths=["/admin"]
        )
        request = Request("GET", "/admin/users", {})
        
        result = middleware(request)
        
        assert isinstance(result, Response)
        assert result.status_code == 401
        assert b"Unauthorized" in result.body
    
    def test_auth_middleware_default_auth(self):
        """Test default authentication function."""
        middleware = AuthMiddleware(protected_paths=["/admin"])
        
        # Request without Authorization header
        request = Request("GET", "/admin", {})
        result = middleware(request)
        assert isinstance(result, Response)
        assert result.status_code == 401
        
        # Request with Bearer token
        request = Request("GET", "/admin", {"Authorization": "Bearer token123"})
        result = middleware(request)
        assert result is None  # Should allow


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""
    
    def test_rate_limit_middleware_creation(self):
        """Test creating rate limit middleware."""
        middleware = RateLimitMiddleware()
        
        assert middleware.max_requests == 100
        assert middleware.window_seconds == 60
        assert middleware.requests == {}
    
    def test_rate_limit_middleware_custom_config(self):
        """Test rate limit middleware with custom configuration."""
        middleware = RateLimitMiddleware(max_requests=10, window_seconds=30)
        
        assert middleware.max_requests == 10
        assert middleware.window_seconds == 30
    
    def test_rate_limit_within_limit(self):
        """Test rate limiting within allowed limits."""
        middleware = RateLimitMiddleware(max_requests=5, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})
        
        # Make requests within limit
        for i in range(5):
            result = middleware(request)
            assert result is None  # Should not block
    
    def test_rate_limit_exceeded(self):
        """Test rate limiting when limit is exceeded."""
        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})
        
        # Make requests up to limit
        for i in range(2):
            result = middleware(request)
            assert result is None
        
        # Next request should be blocked
        result = middleware(request)
        assert isinstance(result, Response)
        assert result.status_code == 429
        assert b"Too Many Requests" in result.body
    
    def test_rate_limit_different_clients(self):
        """Test rate limiting with different clients."""
        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60)
        
        request1 = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})
        request2 = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.2"})
        
        # Each client should have their own limit
        result1 = middleware(request1)
        result2 = middleware(request2)
        
        assert result1 is None
        assert result2 is None
    
    @patch('time.time')
    def test_rate_limit_window_expiry(self, mock_time):
        """Test that rate limit window expires correctly."""
        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60)
        request = Request("GET", "/test", {"X-Forwarded-For": "192.168.1.1"})
        
        # First request at time 0
        mock_time.return_value = 0
        result = middleware(request)
        assert result is None
        
        # Second request immediately should be blocked
        result = middleware(request)
        assert isinstance(result, Response)
        assert result.status_code == 429
        
        # Request after window expires should be allowed
        mock_time.return_value = 61  # After 60-second window
        result = middleware(request)
        assert result is None
    
    def test_rate_limit_cleanup(self):
        """Test cleanup of old entries."""
        middleware = RateLimitMiddleware(max_requests=10, window_seconds=60)
        
        # Add some old entries
        middleware.requests["old_client"] = [time.time() - 200]  # Very old
        middleware.requests["recent_client"] = [time.time() - 30]  # Recent
        
        request = Request("GET", "/test", {"X-Forwarded-For": "new_client"})
        middleware(request)
        
        # Old client should be cleaned up, recent should remain
        assert "old_client" not in middleware.requests
        assert "recent_client" in middleware.requests
        assert "new_client" in middleware.requests
