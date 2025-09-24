"""
Main web server implementation.
"""

import socket
import threading
import logging
from typing import Optional, Callable
from .request import Request
from .response import Response
from .router import Router


class WebServer:
    """Simple HTTP web server."""
    
    def __init__(self, host: str = 'localhost', port: int = 8000, router: Router = None):
        self.host = host
        self.port = port
        self.router = router or Router()
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        

    
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
                    client_socket, address = self.socket.accept()
                    # Handle each request in a separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    thread.daemon = True
                    thread.start()
                    
                except socket.error as e:
                    if self.running:  # Only log if we're still supposed to be running
                        self.logger.error(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the web server."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        self.logger.info("Server stopped")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple) -> None:
        """Handle a client connection."""
        try:
            # Receive request data
            data = client_socket.recv(4096)
            if not data:
                return
            
            # Parse HTTP request
            request = self._parse_request(data)
            if request is None:
                # Send bad request response
                response = Response("Bad Request", status_code=400)
                client_socket.send(response.to_http_response())
                return
            
            # Process request through router
            response = self.router.dispatch(request)
            

            # Send response
            client_socket.send(response.to_http_response())
            
        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}")
            try:
                error_response = Response("Internal Server Error", status_code=500)
                client_socket.send(error_response.to_http_response())
            except:
                pass  # Client might have disconnected
        finally:
            client_socket.close()
    
    def _parse_request(self, data: bytes) -> Optional[Request]:
        """Parse raw HTTP request data into a Request object."""
        try:
            # Decode the request
            request_text = data.decode('utf-8')
            
            # Split headers and body
            if '\r\n\r\n' in request_text:
                headers_part, body_part = request_text.split('\r\n\r\n', 1)
                body = body_part.encode('utf-8')
            else:
                headers_part = request_text
                body = b''
            
            # Parse request line and headers
            lines = headers_part.split('\r\n')
            if not lines:
                return None
            
            # Parse request line (e.g., "GET /path HTTP/1.1")
            request_line = lines[0]
            parts = request_line.split(' ')
            if len(parts) < 3:
                return None
            
            method, path, _ = parts[0], parts[1], parts[2]
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            return Request(method, path, headers, body)
            
        except Exception as e:
            self.logger.error(f"Error parsing request: {e}")
            return None
    
    def add_route(self, pattern: str, handler: Callable, methods: list = None) -> None:
        """Add a route to the server's router."""
        self.router.add_route(pattern, handler, methods)
    
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
    
    def route(self, pattern: str, methods: list = None) -> Callable:
        """Generic route decorator."""
        return self.router.route(pattern, methods)
    