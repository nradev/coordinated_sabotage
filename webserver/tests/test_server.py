"""
Tests for the WebServer class.
"""

import pytest
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from webserver.server import WebServer
from webserver.router import Router
from webserver.request import Request
from webserver.response import Response


class TestWebServer:
    """Test cases for the WebServer class."""
    
    def test_server_creation(self):
        """Test creating a web server."""
        server = WebServer()
        
        assert server.host == 'localhost'
        assert server.port == 8000
        assert isinstance(server.router, Router)
        assert server.running is False
        assert server.socket is None
    
    def test_server_custom_config(self):
        """Test creating server with custom configuration."""
        router = Router()
        server = WebServer(host='127.0.0.1', port=9000, router=router)
        
        assert server.host == '127.0.0.1'
        assert server.port == 9000
        assert server.router == router
    
    def test_parse_request_valid(self):
        """Test parsing a valid HTTP request."""
        server = WebServer()
        
        request_data = (
            b"GET /test?param=value HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            b"\r\n"
            b'{"key": "value"}'
        )
        
        request = server._parse_request(request_data)
        
        assert request is not None
        assert request.method == "GET"
        assert request.path == "/test?param=value"
        assert request.headers["Host"] == "localhost"
        assert request.headers["Content-Type"] == "application/json"
        assert request.body == b'{"key": "value"}'
    
    def test_parse_request_no_body(self):
        """Test parsing request without body."""
        server = WebServer()
        
        request_data = (
            b"GET /test HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        
        request = server._parse_request(request_data)
        
        assert request is not None
        assert request.method == "GET"
        assert request.path == "/test"
        assert request.body == b""
    
    def test_parse_request_invalid(self):
        """Test parsing invalid HTTP request."""
        server = WebServer()
        
        # Invalid request line
        request_data = b"INVALID REQUEST\r\n\r\n"
        
        request = server._parse_request(request_data)
        
        assert request is None
    
    def test_parse_request_malformed(self):
        """Test parsing malformed HTTP request."""
        server = WebServer()
        
        # Request with insufficient parts
        request_data = b"GET\r\n\r\n"
        
        request = server._parse_request(request_data)
        
        assert request is None
    
    def test_add_route(self):
        """Test adding routes to server."""
        server = WebServer()
        
        def handler(request):
            return Response("OK")
        
        server.add_route("/test", handler, ["GET"])
        
        assert len(server.router.routes) > 0  # Should have routes (including default middleware routes)
    
    def test_route_decorators(self):
        """Test route decorators on server."""
        server = WebServer()
        
        @server.get("/get-test")
        def get_handler(request):
            return Response("GET")
        
        @server.post("/post-test")
        def post_handler(request):
            return Response("POST")
        
        @server.put("/put-test")
        def put_handler(request):
            return Response("PUT")
        
        @server.delete("/delete-test")
        def delete_handler(request):
            return Response("DELETE")
        
        # Check that routes were added
        routes = server.router.routes
        route_patterns = [route.pattern for route in routes]
        
        assert "/get-test" in route_patterns
        assert "/post-test" in route_patterns
        assert "/put-test" in route_patterns
        assert "/delete-test" in route_patterns
    
    def test_generic_route_decorator(self):
        """Test generic route decorator."""
        server = WebServer()
        
        @server.route("/multi", methods=["GET", "POST"])
        def multi_handler(request):
            return Response("Multi")
        
        # Find the route
        route = None
        for r in server.router.routes:
            if r.pattern == "/multi":
                route = r
                break
        
        assert route is not None
        assert set(route.methods) == {"GET", "POST"}
    
    def test_add_middleware(self):
        """Test adding middleware to server."""
        server = WebServer()
        
        def test_middleware(request):
            return None
        
        initial_middleware_count = len(server.router.middleware)
        server.add_middleware(test_middleware)
        
        assert len(server.router.middleware) == initial_middleware_count + 1
    
    @patch('socket.socket')
    def test_server_start_stop(self, mock_socket_class):
        """Test starting and stopping the server."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        server = WebServer()
        
        # Mock socket operations
        mock_socket.bind.return_value = None
        mock_socket.listen.return_value = None
        mock_socket.accept.side_effect = socket.error("Test error")  # Force exit from loop
        
        # Start server in a thread to avoid blocking
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Stop the server
        server.stop()
        
        # Wait for thread to finish
        server_thread.join(timeout=1)
        
        # Verify socket operations were called
        mock_socket.bind.assert_called_once_with(('localhost', 8000))
        mock_socket.listen.assert_called_once_with(5)
        mock_socket.close.assert_called_once()
    
    @patch('socket.socket')
    def test_handle_client_success(self, mock_socket_class):
        """Test handling a client request successfully."""
        server = WebServer()
        
        # Add a test route
        @server.get("/test")
        def test_handler(request):
            return Response("Test Response")
        
        # Mock client socket
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = (
            b"GET /test HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        
        # Handle the client
        server._handle_client(mock_client_socket, ('127.0.0.1', 12345))
        
        # Verify response was sent
        mock_client_socket.send.assert_called_once()
        sent_data = mock_client_socket.send.call_args[0][0]
        
        # Check that it's a valid HTTP response
        assert b"HTTP/1.1 200 OK" in sent_data
        assert b"Test Response" in sent_data
        
        # Verify socket was closed
        mock_client_socket.close.assert_called_once()
    
    @patch('socket.socket')
    def test_handle_client_bad_request(self, mock_socket_class):
        """Test handling a bad client request."""
        server = WebServer()
        
        # Mock client socket with bad request
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b"INVALID REQUEST"
        
        # Handle the client
        server._handle_client(mock_client_socket, ('127.0.0.1', 12345))
        
        # Verify bad request response was sent
        mock_client_socket.send.assert_called_once()
        sent_data = mock_client_socket.send.call_args[0][0]
        
        assert b"HTTP/1.1 400 Bad Request" in sent_data
        mock_client_socket.close.assert_called_once()
    
    @patch('socket.socket')
    def test_handle_client_empty_request(self, mock_socket_class):
        """Test handling empty client request."""
        server = WebServer()
        
        # Mock client socket with empty request
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b""
        
        # Handle the client
        server._handle_client(mock_client_socket, ('127.0.0.1', 12345))
        
        # Should not send any response for empty request
        mock_client_socket.send.assert_not_called()
        mock_client_socket.close.assert_called_once()
    
    @patch('socket.socket')
    def test_handle_client_exception(self, mock_socket_class):
        """Test handling client when exception occurs."""
        server = WebServer()
        
        # Mock client socket that raises exception
        mock_client_socket = Mock()
        mock_client_socket.recv.side_effect = Exception("Test exception")
        
        # Handle the client (should not raise exception)
        server._handle_client(mock_client_socket, ('127.0.0.1', 12345))
        
        # Socket should still be closed
        mock_client_socket.close.assert_called_once()
    
    def test_default_middleware_added(self):
        """Test that default middleware is added to server."""
        server = WebServer()
        
        # Should have logging and CORS middleware by default
        assert len(server.router.middleware) >= 2
        
        # Check middleware types
        middleware_types = [type(mw).__name__ for mw in server.router.middleware]
        assert 'LoggingMiddleware' in middleware_types
        assert 'CORSMiddleware' in middleware_types
    
    def test_server_with_custom_router(self):
        """Test server with custom router."""
        custom_router = Router()
        
        @custom_router.get("/custom")
        def custom_handler(request):
            return Response("Custom")
        
        server = WebServer(router=custom_router)
        
        # Should use the custom router
        assert server.router == custom_router
        
        # Custom route should be available
        route_patterns = [route.pattern for route in server.router.routes]
        assert "/custom" in route_patterns
