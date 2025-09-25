"""
HTTP Web Server implementation.
"""

import socket
import threading
from typing import Optional, Callable
from .router import Router
from .request import Request
from .response import Response
import logging


class WebServer:
    """A simple HTTP web server with routing."""
    
    def __init__(self, host: str = "localhost", port: int = 8000, router: Router = None):
        self.host = host
        self.port = port
        self.router = router or Router()
        self.socket: Optional[socket.socket] = None
        self.running = False
        
        
        # Set up logging
        self.logger = logging.getLogger("webserver")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    
    def start(self) -> None:
        """Start the web server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            self.logger.info(f"Server starting on http://{self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    # Handle each request in a separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    thread.daemon = True
                    thread.start()
                except OSError:
                    if self.running:
                        self.logger.error("Socket error occurred")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the web server."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.logger.info("Server stopped")
    
    def _handle_client(self, client_socket: socket.socket, client_address) -> None:
        """Handle a client connection."""
        try:
            # Receive request data
            request_data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                
                # Check if we have received the complete headers
                if b"\r\n\r\n" in request_data:
                    headers_end = request_data.find(b"\r\n\r\n")
                    headers_part = request_data[:headers_end]
                    body_part = request_data[headers_end + 4:]
                    
                    # Parse Content-Length to determine if we need more data
                    headers_str = headers_part.decode('utf-8', errors='ignore')
                    content_length = 0
                    for line in headers_str.split('\r\n')[1:]:  # Skip request line
                        if line.lower().startswith('content-length:'):
                            content_length = int(line.split(':', 1)[1].strip())
                            break
                    
                    # Read remaining body if needed
                    while len(body_part) < content_length:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        body_part += chunk
                    
                    request_data = headers_part + b"\r\n\r\n" + body_part
                    break
            
            if request_data:
                request = self._parse_request(request_data)
                response = self.router.dispatch(request)
                
                # Send response
                client_socket.sendall(response.to_http_response())
            
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
            # Send error response
            error_response = Response.json(
                {"error": "Internal server error"},
                status_code=500
            )
            try:
                client_socket.sendall(error_response.to_http_response())
            except:
                pass
        finally:
            client_socket.close()
    
    def _parse_request(self, request_data: bytes) -> Request:
        """Parse raw HTTP request data into a Request object."""
        try:
            # Split headers and body
            headers_end = request_data.find(b"\r\n\r\n")
            if headers_end == -1:
                raise ValueError("Invalid HTTP request format")
            
            headers_part = request_data[:headers_end].decode('utf-8')
            body_part = request_data[headers_end + 4:]
            
            # Parse request line
            lines = headers_part.split('\r\n')
            request_line = lines[0]
            method, path, _ = request_line.split(' ', 2)
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            return Request(method, path, headers, body_part)
            
        except Exception as e:
            self.logger.error(f"Error parsing request: {e}")
            # Return a minimal request for error handling
            return Request("GET", "/", {})
    
    # Route decorators - delegate to router
    def get(self, pattern: str) -> Callable:
        """Decorator for GET routes."""
        return self.router.get(pattern)
    
    def post(self, pattern: str) -> Callable:
        """Decorator for POST routes."""
        return self.router.post(pattern)
    
    def put(self, pattern: str) -> Callable:
        """Decorator for PUT routes."""
        return self.router.put(pattern)
    
    def delete(self, pattern: str) -> Callable:
        """Decorator for DELETE routes."""
        return self.router.delete(pattern)
    
    def patch(self, pattern: str) -> Callable:
        """Decorator for PATCH routes."""
        return self.router.patch(pattern)
    
    def options(self, pattern: str) -> Callable:
        """Decorator for OPTIONS routes."""
        return self.router.options(pattern)
