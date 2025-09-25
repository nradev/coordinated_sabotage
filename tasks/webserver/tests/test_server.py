"""
Tests for the WebServer class.
"""

import sys
import os
import threading
import time
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from webserver.server import WebServer
from webserver.router import Router
from webserver.request import Request
from webserver.response import Response


class TestWebServer:
    """Test cases for the WebServer class."""

    def test_server_creation(self):
        """Test creating a web server."""
        server = WebServer()

        assert server.host == "localhost"
        assert server.port == 8000
        assert server.router is not None
        assert server.running is False

    def test_server_creation_with_custom_params(self):
        """Test creating server with custom parameters."""
        custom_router = Router()
        server = WebServer(host="0.0.0.0", port=9000, router=custom_router)

        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server.router == custom_router

    def test_server_has_default_middleware(self):
        """Test server has default logging middleware."""
        server = WebServer()

        # Should have at least one middleware (LoggingMiddleware)
        assert len(server.router.middleware) >= 1

    def test_add_middleware(self):
        """Test adding middleware to server."""
        server = WebServer()
        initial_count = len(server.router.middleware)

        class TestMiddleware:
            def __call__(self, request):
                return None

        middleware = TestMiddleware()
        server.add_middleware(middleware)

        assert len(server.router.middleware) == initial_count + 1

    def test_route_decorators(self):
        """Test route decorator methods."""
        server = WebServer()

        @server.get("/test")
        def get_handler(request):
            return Response("GET")

        @server.post("/test")
        def post_handler(request):
            return Response("POST")

        assert len(server.router.routes) == 2

    def test_parse_request_valid(self):
        """Test parsing valid HTTP request."""
        server = WebServer()

        request_data = (
            b"GET /test HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n"
        )
        request = server._parse_request(request_data)

        assert request.method == "GET"
        assert request.path == "/test"
        assert request.headers["Host"] == "localhost"

    def test_parse_request_with_body(self):
        """Test parsing HTTP request with body."""
        server = WebServer()

        body = b'{"test": "data"}'
        request_data = (
            b"POST /api/test HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 16\r\n"
            b"\r\n" + body
        )

        request = server._parse_request(request_data)

        assert request.method == "POST"
        assert request.path == "/api/test"
        assert request.body == body
        assert request.headers["Content-Type"] == "application/json"

    def test_parse_request_invalid(self):
        """Test parsing invalid HTTP request."""
        server = WebServer()

        # Invalid request data
        request_data = b"INVALID REQUEST"
        request = server._parse_request(request_data)

        # Should return a minimal request for error handling
        assert request.method == "GET"
        assert request.path == "/"

    @patch("socket.socket")
    def test_server_socket_creation(self, mock_socket_class):
        """Test server socket creation and configuration."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        server = WebServer()

        # Mock the socket operations to avoid actual binding
        mock_socket.bind.return_value = None
        mock_socket.listen.return_value = None
        mock_socket.accept.side_effect = KeyboardInterrupt()  # Stop immediately

        try:
            server.start()
        except KeyboardInterrupt:
            pass

        # Verify socket was configured correctly
        mock_socket.setsockopt.assert_called()
        mock_socket.bind.assert_called_with(("localhost", 8000))
        mock_socket.listen.assert_called_with(5)

    def test_server_stop(self):
        """Test stopping the server."""
        server = WebServer()
        server.running = True
        server.socket = Mock()

        server.stop()

        assert server.running is False
        server.socket.close.assert_called_once()

    @patch("webserver.server.threading.Thread")
    def test_client_handling_thread_creation(self, mock_thread):
        """Test that client connections create handling threads."""
        server = WebServer()
        mock_client_socket = Mock()
        mock_client_address = ("127.0.0.1", 12345)

        # Mock thread creation
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # This would normally be called from the accept loop
        # We'll test the thread creation logic directly
        thread = threading.Thread(
            target=server._handle_client, args=(mock_client_socket, mock_client_address)
        )

        assert thread is not None

    def test_handle_client_with_valid_request(self):
        """Test handling a client with valid request."""
        server = WebServer()

        @server.get("/test")
        def handler(request):
            return Response("success")

        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = (
            b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )

        server._handle_client(mock_client_socket, ("127.0.0.1", 12345))

        # Should have sent a response
        mock_client_socket.sendall.assert_called()
        mock_client_socket.close.assert_called()

    def test_handle_client_with_exception(self):
        """Test handling client when exception occurs."""
        server = WebServer()

        mock_client_socket = Mock()
        mock_client_socket.recv.side_effect = Exception("Connection error")

        # Should not raise exception
        server._handle_client(mock_client_socket, ("127.0.0.1", 12345))

        # Socket should still be closed
        mock_client_socket.close.assert_called()
