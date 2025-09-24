"""
Tests for the Request class.
"""

import json
import pytest

from webserver.request import Request


class TestRequest:
    """Test cases for the Request class."""

    def test_basic_request_creation(self):
        """Test creating a basic request."""
        request = Request("GET", "/test", {"Host": "localhost"})

        assert request.method == "GET"
        assert request.path == "/test"
        assert request.headers == {"Host": "localhost"}
        assert request.body == b""

    def test_method_normalization(self):
        """Test that HTTP methods are normalized to uppercase."""
        request = Request("get", "/test", {})
        assert request.method == "GET"

        request = Request("post", "/test", {})
        assert request.method == "POST"

    def test_query_params_parsing(self):
        """Test query parameter parsing."""
        request = Request("GET", "/search?q=test&limit=10", {})
        params = request.query_params
        assert params["q"] == "test"
        assert params["limit"] == "10"

    def test_query_params_multiple_values(self):
        """Test query parameters with multiple values."""
        request = Request("GET", "/search?tags=python&tags=web", {})
        params = request.query_params
        assert params["tags"] == ["python", "web"]

    def test_query_params_empty(self):
        """Test request without query parameters."""
        request = Request("GET", "/", {})
        params = request.query_params
        assert params == {}

    def test_json_parsing(self):
        """Test JSON body parsing."""
        headers = {"content-type": "application/json"}
        body = b'{"name": "test", "value": 123}'
        request = Request("POST", "/", headers, body)

        json_data = request.json
        assert json_data["name"] == "test"
        assert json_data["value"] == 123

    def test_json_parsing_invalid(self):
        """Test invalid JSON body parsing."""
        headers = {"content-type": "application/json"}
        body = b'{"invalid": json}'
        request = Request("POST", "/", headers, body)

        json_data = request.json
        assert json_data is None

    def test_json_parsing_wrong_content_type(self):
        """Test JSON parsing with wrong content type."""
        headers = {"content-type": "text/plain"}
        body = b'{"name": "test"}'
        request = Request("POST", "/", headers, body)

        json_data = request.json
        assert json_data is None

    def test_content_length(self):
        """Test content length calculation."""
        body = b"Hello, World!"
        request = Request("POST", "/", {}, body)
        assert request.content_length == len(body)

    def test_get_header_case_insensitive(self):
        """Test case-insensitive header retrieval."""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        request = Request("GET", "/", headers)

        assert request.get_header("content-type") == "application/json"
        assert request.get_header("AUTHORIZATION") == "Bearer token"
        assert request.get_header("Content-Type") == "application/json"

    def test_get_header_default(self):
        """Test header retrieval with default value."""
        request = Request("GET", "/", {})
        assert request.get_header("missing") is None
        assert request.get_header("missing", "default") == "default"

    def test_repr(self):
        """Test string representation."""
        request = Request("GET", "/test", {})
        repr_str = repr(request)
        assert "GET" in repr_str
        assert "/test" in repr_str
