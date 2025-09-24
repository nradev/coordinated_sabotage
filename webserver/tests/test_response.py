"""
Tests for the Response class.
"""

import pytest
import json
from webserver.response import Response


class TestResponse:
    """Test cases for the Response class."""
    
    def test_basic_response_creation(self):
        """Test creating a basic response."""
        response = Response("Hello, World!")
        
        assert response.status_code == 200
        assert response.body == b"Hello, World!"
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    
    def test_response_with_status_code(self):
        """Test creating response with custom status code."""
        response = Response("Not Found", status_code=404)
        
        assert response.status_code == 404
        assert response.status_text == "Not Found"
    
    def test_response_with_headers(self):
        """Test creating response with custom headers."""
        headers = {"Custom-Header": "custom-value"}
        response = Response("Test", headers=headers)
        
        assert response.headers["Custom-Header"] == "custom-value"
    
    def test_json_response(self):
        """Test creating JSON response."""
        data = {"message": "Hello", "status": "success"}
        response = Response(data)
        
        assert response.headers["Content-Type"] == "application/json"
        assert json.loads(response.body.decode('utf-8')) == data
    
    def test_bytes_response(self):
        """Test creating response with bytes body."""
        body = b"Binary content"
        response = Response(body)
        
        assert response.body == body
    
    def test_status_text_mapping(self):
        """Test status text mapping for common status codes."""
        test_cases = [
            (200, "OK"),
            (201, "Created"),
            (204, "No Content"),
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (405, "Method Not Allowed"),
            (500, "Internal Server Error"),
            (999, "Unknown"),  # Unknown status code
        ]
        
        for status_code, expected_text in test_cases:
            response = Response("", status_code=status_code)
            assert response.status_text == expected_text
    
    def test_set_header(self):
        """Test setting response headers."""
        response = Response("Test")
        response.set_header("X-Custom", "value")
        
        assert response.headers["X-Custom"] == "value"
    
    def test_set_cookie_basic(self):
        """Test setting a basic cookie."""
        response = Response("Test")
        response.set_cookie("session_id", "abc123")
        
        assert "Set-Cookie" in response.headers
        cookie = response.headers["Set-Cookie"]
        assert "session_id=abc123" in cookie
        assert "Path=/" in cookie
    
    def test_set_cookie_with_options(self):
        """Test setting cookie with options."""
        response = Response("Test")
        response.set_cookie("secure_cookie", "value", max_age=3600, 
                          path="/admin", secure=True, httponly=True)
        
        cookie = response.headers["Set-Cookie"]
        assert "secure_cookie=value" in cookie
        assert "Max-Age=3600" in cookie
        assert "Path=/admin" in cookie
        assert "Secure" in cookie
        assert "HttpOnly" in cookie
    
    def test_multiple_cookies(self):
        """Test setting multiple cookies."""
        response = Response("Test")
        response.set_cookie("cookie1", "value1")
        response.set_cookie("cookie2", "value2")
        
        cookies = response.headers["Set-Cookie"]
        assert isinstance(cookies, list)
        assert len(cookies) == 2
        assert any("cookie1=value1" in cookie for cookie in cookies)
        assert any("cookie2=value2" in cookie for cookie in cookies)
    
    def test_to_http_response(self):
        """Test converting response to HTTP format."""
        response = Response("Hello", status_code=200)
        http_response = response.to_http_response()
        
        # Check that it's bytes
        assert isinstance(http_response, bytes)
        
        # Decode and check structure
        response_str = http_response.decode('utf-8')
        lines = response_str.split('\r\n')
        
        # Check status line
        assert lines[0] == "HTTP/1.1 200 OK"
        
        # Check that headers are present
        header_section = '\r\n'.join(lines[1:]).split('\r\n\r\n')[0]
        assert "Content-Type: text/html; charset=utf-8" in header_section
        assert "Content-Length: 5" in header_section
        
        # Check body
        assert response_str.endswith("Hello")
    
    def test_json_class_method(self):
        """Test Response.json() class method."""
        data = {"key": "value", "number": 42}
        response = Response.json(data)
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert json.loads(response.body.decode('utf-8')) == data
    
    def test_json_class_method_with_status(self):
        """Test Response.json() with custom status code."""
        data = {"error": "Not found"}
        response = Response.json(data, status_code=404)
        
        assert response.status_code == 404
        assert json.loads(response.body.decode('utf-8')) == data
    
    def test_text_class_method(self):
        """Test Response.text() class method."""
        text = "Plain text response"
        response = Response.text(text)
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        assert response.body == text.encode('utf-8')
    
    def test_html_class_method(self):
        """Test Response.html() class method."""
        html = "<h1>Hello World</h1>"
        response = Response.html(html)
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert response.body == html.encode('utf-8')
    
    def test_response_repr(self):
        """Test string representation of response."""
        response = Response("Test content", status_code=201)
        
        repr_str = repr(response)
        assert "201" in repr_str
        assert "body_length" in repr_str
    
    def test_content_length_header(self):
        """Test that Content-Length header is set correctly."""
        content = "Test content with specific length"
        response = Response(content)
        http_response = response.to_http_response()
        
        response_str = http_response.decode('utf-8')
        expected_length = len(content.encode('utf-8'))
        assert f"Content-Length: {expected_length}" in response_str
    
    def test_empty_response(self):
        """Test empty response."""
        response = Response("")
        
        assert response.body == b""
        assert response.status_code == 200
        
        http_response = response.to_http_response()
        response_str = http_response.decode('utf-8')
        assert "Content-Length: 0" in response_str
