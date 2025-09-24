"""
HTTP Response handling.
"""

from typing import Dict, Any, Union
import json


class Response:
    """Represents an HTTP response."""
    
    def __init__(self, body: Union[str, bytes, Dict[str, Any]] = "", 
                 status_code: int = 200, headers: Dict[str, str] = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body
        
        # Set default headers
        if 'Content-Type' not in self.headers:
            if isinstance(body, dict):
                self.headers['Content-Type'] = 'application/json'
            else:
                self.headers['Content-Type'] = 'text/html; charset=utf-8'
    
    @property
    def body(self) -> bytes:
        """Return the response body as bytes."""
        if isinstance(self._body, dict):
            return json.dumps(self._body).encode('utf-8')
        elif isinstance(self._body, str):
            return self._body.encode('utf-8')
        elif isinstance(self._body, bytes):
            return self._body
        else:
            return str(self._body).encode('utf-8')
    
    @property
    def status_text(self) -> str:
        """Return the status text for the status code."""
        status_texts = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            500: 'Internal Server Error',
        }
        return status_texts.get(self.status_code, 'Unknown')
    
    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        self.headers[name] = value
    
    def set_cookie(self, name: str, value: str, max_age: int = None, 
                   path: str = "/", secure: bool = False, httponly: bool = False) -> None:
        """Set a cookie in the response."""
        cookie_value = f"{name}={value}; Path={path}"
        if max_age is not None:
            cookie_value += f"; Max-Age={max_age}"
        if secure:
            cookie_value += "; Secure"
        if httponly:
            cookie_value += "; HttpOnly"
        
        # Handle multiple cookies
        if 'Set-Cookie' in self.headers:
            existing = self.headers['Set-Cookie']
            if isinstance(existing, list):
                existing.append(cookie_value)
            else:
                self.headers['Set-Cookie'] = [existing, cookie_value]
        else:
            self.headers['Set-Cookie'] = cookie_value
    
    def to_http_response(self) -> bytes:
        """Convert the response to HTTP format."""
        body = self.body
        
        # Update Content-Length header
        self.headers['Content-Length'] = str(len(body))
        
        # Build status line
        status_line = f"HTTP/1.1 {self.status_code} {self.status_text}\r\n"
        
        # Build headers
        header_lines = []
        for name, value in self.headers.items():
            if isinstance(value, list):
                for v in value:
                    header_lines.append(f"{name}: {v}\r\n")
            else:
                header_lines.append(f"{name}: {value}\r\n")
        
        # Combine all parts
        response = status_line.encode('utf-8')
        response += ''.join(header_lines).encode('utf-8')
        response += b"\r\n"  # Empty line between headers and body
        response += body
        
        return response
    
    @classmethod
    def json(cls, data: Dict[str, Any], status_code: int = 200) -> 'Response':
        """Create a JSON response."""
        return cls(body=data, status_code=status_code, 
                  headers={'Content-Type': 'application/json'})
    
    @classmethod
    def text(cls, text: str, status_code: int = 200) -> 'Response':
        """Create a plain text response."""
        return cls(body=text, status_code=status_code,
                  headers={'Content-Type': 'text/plain; charset=utf-8'})
    
    @classmethod
    def html(cls, html: str, status_code: int = 200) -> 'Response':
        """Create an HTML response."""
        return cls(body=html, status_code=status_code,
                  headers={'Content-Type': 'text/html; charset=utf-8'})
    
    def __repr__(self) -> str:
        return f"Response(status_code={self.status_code}, body_length={len(self.body)})"
