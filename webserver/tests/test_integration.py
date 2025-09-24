"""
Integration tests for the web server.
"""

import pytest
import threading
import time
import requests
import json
from webserver.server import WebServer
from webserver.request import Request
from webserver.response import Response


class TestIntegration:
    """Integration test cases for the complete web server."""
    
    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        server = WebServer(host='localhost', port=8888)
        
        # Add test routes
        @server.get('/')
        def home(request):
            return Response.html("<h1>Test Server</h1>")
        
        @server.get('/api/users')
        def get_users(request):
            users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
            return Response.json({"users": users})
        
        @server.get('/api/users/{user_id}')
        def get_user(request, user_id):
            return Response.json({"user_id": int(user_id), "name": f"User {user_id}"})
        
        @server.post('/api/users')
        def create_user(request):
            data = request.json
            if not data or 'name' not in data:
                return Response.json({"error": "Name required"}, status_code=400)
            
            return Response.json({"id": 123, "name": data["name"]}, status_code=201)
        
        @server.get('/api/error')
        def error_endpoint(request):
            raise ValueError("Test error")
        
        return server
    
    def start_server_thread(self, server):
        """Start server in a separate thread."""
        def run_server():
            try:
                server.start()
            except Exception:
                pass  # Server might be stopped during test
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        return thread
    
    def test_server_startup_and_shutdown(self, server):
        """Test that server can start and stop properly."""
        thread = self.start_server_thread(server)
        
        # Server should be running
        assert server.running is True
        
        # Stop server
        server.stop()
        
        # Wait for thread to finish
        thread.join(timeout=2)
        
        assert server.running is False
    
    def test_get_request(self, server):
        """Test GET request to server."""
        thread = self.start_server_thread(server)
        
        try:
            # Make GET request
            response = requests.get('http://localhost:8888/', timeout=5)
            
            assert response.status_code == 200
            assert "<h1>Test Server</h1>" in response.text
            assert "text/html" in response.headers.get('Content-Type', '')
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_json_api_endpoint(self, server):
        """Test JSON API endpoint."""
        thread = self.start_server_thread(server)
        
        try:
            # Make GET request to API
            response = requests.get('http://localhost:8888/api/users', timeout=5)
            
            assert response.status_code == 200
            assert response.headers.get('Content-Type') == 'application/json'
            
            data = response.json()
            assert 'users' in data
            assert len(data['users']) == 2
            assert data['users'][0]['name'] == 'Alice'
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_path_parameters(self, server):
        """Test endpoint with path parameters."""
        thread = self.start_server_thread(server)
        
        try:
            # Make GET request with path parameter
            response = requests.get('http://localhost:8888/api/users/42', timeout=5)
            
            assert response.status_code == 200
            
            data = response.json()
            assert data['user_id'] == 42
            assert data['name'] == 'User 42'
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_post_request_with_json(self, server):
        """Test POST request with JSON data."""
        thread = self.start_server_thread(server)
        
        try:
            # Make POST request with JSON
            user_data = {"name": "Charlie"}
            response = requests.post(
                'http://localhost:8888/api/users',
                json=user_data,
                timeout=5
            )
            
            assert response.status_code == 201
            
            data = response.json()
            assert data['id'] == 123
            assert data['name'] == 'Charlie'
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_post_request_bad_data(self, server):
        """Test POST request with invalid data."""
        thread = self.start_server_thread(server)
        
        try:
            # Make POST request with invalid JSON
            response = requests.post(
                'http://localhost:8888/api/users',
                json={},  # Missing required 'name' field
                timeout=5
            )
            
            assert response.status_code == 400
            
            data = response.json()
            assert 'error' in data
            assert data['error'] == 'Name required'
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_404_not_found(self, server):
        """Test 404 response for non-existent endpoint."""
        thread = self.start_server_thread(server)
        
        try:
            # Make request to non-existent endpoint
            response = requests.get('http://localhost:8888/nonexistent', timeout=5)
            
            assert response.status_code == 404
            assert "Not Found" in response.text
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_500_internal_server_error(self, server):
        """Test 500 response when handler raises exception."""
        thread = self.start_server_thread(server)
        
        try:
            # Make request to endpoint that raises exception
            response = requests.get('http://localhost:8888/api/error', timeout=5)
            
            assert response.status_code == 500
            assert "Internal Server Error" in response.text
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_cors_headers(self, server):
        """Test CORS headers are added to responses."""
        thread = self.start_server_thread(server)
        
        try:
            # Make request with Origin header
            headers = {'Origin': 'https://example.com'}
            response = requests.get('http://localhost:8888/', headers=headers, timeout=5)
            
            assert response.status_code == 200
            # CORS middleware should add these headers
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Methods' in response.headers
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_options_preflight_request(self, server):
        """Test CORS preflight OPTIONS request."""
        thread = self.start_server_thread(server)
        
        try:
            # Make OPTIONS preflight request
            headers = {
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            response = requests.options('http://localhost:8888/api/users', headers=headers, timeout=5)
            
            assert response.status_code == 204
            assert 'Access-Control-Allow-Origin' in response.headers
            assert 'Access-Control-Allow-Methods' in response.headers
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_concurrent_requests(self, server):
        """Test handling multiple concurrent requests."""
        thread = self.start_server_thread(server)
        
        try:
            import concurrent.futures
            
            def make_request(i):
                response = requests.get(f'http://localhost:8888/api/users/{i}', timeout=5)
                return response.status_code, response.json()
            
            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(1, 11)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # All requests should succeed
            assert len(results) == 10
            for status_code, data in results:
                assert status_code == 200
                assert 'user_id' in data
                assert 'name' in data
            
        finally:
            server.stop()
            thread.join(timeout=2)
    
    def test_large_request_body(self, server):
        """Test handling large request body."""
        thread = self.start_server_thread(server)
        
        try:
            # Create large JSON payload
            large_data = {"name": "User", "data": "x" * 10000}  # 10KB of data
            
            response = requests.post(
                'http://localhost:8888/api/users',
                json=large_data,
                timeout=5
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data['name'] == 'User'
            
        finally:
            server.stop()
            thread.join(timeout=2)
