"""
Tests for the Request class.
"""

import pytest
import json
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
        """Test parsing query parameters from URL."""
        request = Request("GET", "/test?name=john&age=25", {})
        
        params = request.query_params
        assert params["name"] == "john"
        assert params["age"] == "25"
    
    def test_query_params_multiple_values(self):
        """Test parsing query parameters with multiple values."""
        request = Request("GET", "/test?tags=python&tags=web&tags=server", {})
        
        params = request.query_params
        assert params["tags"] == ["python", "web", "server"]
    
    def test_query_params_empty(self):
        """Test query parameters when there are none."""
        request = Request("GET", "/test", {})
        
        params = request.query_params
        assert params == {}
    
    def test_json_parsing(self):
        """Test parsing JSON from request body."""
        json_data = {"name": "John", "age": 30}
        body = json.dumps(json_data).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        
        request = Request("POST", "/test", headers, body)
        
        assert request.json == json_data
    
    def test_json_parsing_invalid(self):
        """Test parsing invalid JSON."""
        body = b"invalid json"
        headers = {"Content-Type": "application/json"}
        
        request = Request("POST", "/test", headers, body)
        
        assert request.json is None
    
    def test_json_parsing_wrong_content_type(self):
        """Test JSON parsing with wrong content type."""
        json_data = {"name": "John"}
        body = json.dumps(json_data).encode('utf-8')
        headers = {"Content-Type": "text/plain"}
        
        request = Request("POST", "/test", headers, body)
        
        assert request.json is None
    
    def test_content_length(self):
        """Test content length calculation."""
        body = b"Hello, World!"
        request = Request("POST", "/test", {}, body)
        
        assert request.content_length == len(body)
    
    def test_get_header_case_insensitive(self):
        """Test getting headers case-insensitively."""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        request = Request("GET", "/test", headers)
        
        assert request.get_header("content-type") == "application/json"
        assert request.get_header("AUTHORIZATION") == "Bearer token"
        assert request.get_header("Content-Type") == "application/json"
    
    def test_get_header_default(self):
        """Test getting header with default value."""
        request = Request("GET", "/test", {})
        
        assert request.get_header("Missing-Header") is None
        assert request.get_header("Missing-Header", "default") == "default"
    
    def test_request_repr(self):
        """Test string representation of request."""
        request = Request("GET", "/test", {})
        
        repr_str = repr(request)
        assert "GET" in repr_str
        assert "/test" in repr_str
    
    def test_request_with_body(self):
        """Test request with body content."""
        body = b"Request body content"
        request = Request("POST", "/test", {}, body)
        
        assert request.body == body
        assert request.content_length == len(body)
    
    def test_complex_query_params(self):
        """Test complex query parameter scenarios."""
        request = Request("GET", "/search?q=python+web&sort=date&limit=10&active=true", {})
        
        params = request.query_params
        assert params["q"] == "python web"  # URL decoding
        assert params["sort"] == "date"
        assert params["limit"] == "10"
        assert params["active"] == "true"
    
    def test_empty_query_params(self):
        """Test handling of empty query parameters."""
        request = Request("GET", "/test?empty=&name=john&also_empty=", {})
        
        params = request.query_params
        assert params["empty"] == ""
        assert params["name"] == "john"
        assert params["also_empty"] == ""
