"""
Tests for the Response class.
"""

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

    def test_response_with_custom_status(self):
        """Test response with custom status code."""
        response = Response("Not Found", status_code=404)

        assert response.status_code == 404
        assert response.status_text == "Not Found"

    def test_response_with_custom_headers(self):
        """Test response with custom headers."""
        headers = {"Custom-Header": "test-value"}
        response = Response("test", headers=headers)

        assert response.headers["Custom-Header"] == "test-value"
        assert "Content-Type" in response.headers

    def test_json_response_creation(self):
        """Test creating JSON responses."""
        data = {"message": "test", "value": 123}
        response = Response.json(data)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

        body_data = json.loads(response.body.decode())
        assert body_data["message"] == "test"
        assert body_data["value"] == 123

    def test_text_response_creation(self):
        """Test creating text responses."""
        response = Response.text("Plain text content")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        assert response.body == b"Plain text content"

    def test_html_response_creation(self):
        """Test creating HTML responses."""
        html = "<h1>Hello</h1>"
        response = Response.html(html)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert response.body == b"<h1>Hello</h1>"

    def test_set_header(self):
        """Test setting response headers."""
        response = Response("test")
        response.set_header("X-Custom", "value")

        assert response.headers["X-Custom"] == "value"

    def test_set_cookie(self):
        """Test setting cookies."""
        response = Response("test")
        response.set_cookie("session", "abc123", max_age=3600, secure=True)

        cookie = response.headers["Set-Cookie"]
        assert "session=abc123" in cookie
        assert "Max-Age=3600" in cookie
        assert "Secure" in cookie

    def test_multiple_cookies(self):
        """Test setting multiple cookies."""
        response = Response("test")
        response.set_cookie("session", "abc123")
        response.set_cookie("user", "john")

        cookies = response.headers["Set-Cookie"]
        assert isinstance(cookies, list)
        assert len(cookies) == 2

    def test_status_text_mapping(self):
        """Test status text mapping."""
        test_cases = [
            (200, "OK"),
            (201, "Created"),
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (999, "Unknown"),
        ]

        for status_code, expected_text in test_cases:
            response = Response("test", status_code=status_code)
            assert response.status_text == expected_text

    def test_body_types(self):
        """Test different body types."""
        # String body
        response = Response("string body")
        assert response.body == b"string body"

        # Bytes body
        response = Response(b"bytes body")
        assert response.body == b"bytes body"

        # Dict body (JSON)
        response = Response({"key": "value"})
        assert json.loads(response.body.decode()) == {"key": "value"}

    def test_to_http_response(self):
        """Test HTTP response formatting."""
        response = Response("Hello", status_code=200)
        response.set_header("X-Test", "value")

        http_response = response.to_http_response()

        # Check it's bytes
        assert isinstance(http_response, bytes)

        # Check status line
        assert b"HTTP/1.1 200 OK" in http_response

        # Check headers
        assert b"Content-Type: text/html; charset=utf-8" in http_response
        assert b"X-Test: value" in http_response
        assert b"Content-Length: 5" in http_response

        # Check body
        assert http_response.endswith(b"Hello")

    def test_repr(self):
        """Test string representation."""
        response = Response("test content")
        repr_str = repr(response)

        assert "200" in repr_str
        assert "12" in repr_str  # body length
