"""
Tests for the Router class.
"""

import pytest
from webserver.router import Router, Route
from webserver.request import Request
from webserver.response import Response


class TestRoute:
    """Test cases for the Route class."""
    
    def test_simple_route_creation(self):
        """Test creating a simple route."""
        def handler(request):
            return Response("OK")
        
        route = Route("/test", handler, ["GET"])
        
        assert route.pattern == "/test"
        assert route.handler == handler
        assert route.methods == ["GET"]
    
    def test_route_with_parameters(self):
        """Test route with path parameters."""
        def handler(request, user_id):
            return Response(f"User {user_id}")
        
        route = Route("/users/{user_id}", handler, ["GET"])
        
        assert "user_id" in route.param_names
    
    def test_route_matching_simple(self):
        """Test simple route matching."""
        def handler(request):
            return Response("OK")
        
        route = Route("/test", handler, ["GET"])
        
        # Should match
        params = route.matches("/test", "GET")
        assert params == {}
        
        # Should not match different path
        params = route.matches("/other", "GET")
        assert params is None
        
        # Should not match different method
        params = route.matches("/test", "POST")
        assert params is None
    
    def test_route_matching_with_parameters(self):
        """Test route matching with path parameters."""
        def handler(request, user_id):
            return Response("OK")
        
        route = Route("/users/{user_id}", handler, ["GET"])
        
        # Should match and extract parameter
        params = route.matches("/users/123", "GET")
        assert params == {"user_id": "123"}
        
        # Should match with string parameter
        params = route.matches("/users/john", "GET")
        assert params == {"user_id": "john"}
        
        # Should not match incomplete path
        params = route.matches("/users", "GET")
        assert params is None
    
    def test_route_multiple_parameters(self):
        """Test route with multiple parameters."""
        def handler(request, category, item_id):
            return Response("OK")
        
        route = Route("/categories/{category}/items/{item_id}", handler, ["GET"])
        
        params = route.matches("/categories/electronics/items/123", "GET")
        assert params == {"category": "electronics", "item_id": "123"}
    
    def test_route_multiple_methods(self):
        """Test route with multiple HTTP methods."""
        def handler(request):
            return Response("OK")
        
        route = Route("/api/data", handler, ["GET", "POST", "PUT"])
        
        assert route.matches("/api/data", "GET") == {}
        assert route.matches("/api/data", "POST") == {}
        assert route.matches("/api/data", "PUT") == {}
        assert route.matches("/api/data", "DELETE") is None


class TestRouter:
    """Test cases for the Router class."""
    
    def test_router_creation(self):
        """Test creating a router."""
        router = Router()
        
        assert router.routes == []
        assert router.middleware == []
    
    def test_add_route(self):
        """Test adding a route to the router."""
        router = Router()
        
        def handler(request):
            return Response("OK")
        
        router.add_route("/test", handler, ["GET"])
        
        assert len(router.routes) == 1
        assert router.routes[0].pattern == "/test"
    
    def test_get_decorator(self):
        """Test the @router.get decorator."""
        router = Router()
        
        @router.get("/test")
        def handler(request):
            return Response("GET OK")
        
        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.methods == ["GET"]
        assert route.pattern == "/test"
    
    def test_post_decorator(self):
        """Test the @router.post decorator."""
        router = Router()
        
        @router.post("/test")
        def handler(request):
            return Response("POST OK")
        
        route = router.routes[0]
        assert route.methods == ["POST"]
    
    def test_multiple_decorators(self):
        """Test using multiple route decorators."""
        router = Router()
        
        @router.get("/get-test")
        def get_handler(request):
            return Response("GET")
        
        @router.post("/post-test")
        def post_handler(request):
            return Response("POST")
        
        assert len(router.routes) == 2
    
    def test_route_decorator_with_methods(self):
        """Test the generic @router.route decorator."""
        router = Router()
        
        @router.route("/test", methods=["GET", "POST"])
        def handler(request):
            return Response("OK")
        
        route = router.routes[0]
        assert set(route.methods) == {"GET", "POST"}
    
    def test_find_route(self):
        """Test finding routes."""
        router = Router()
        
        @router.get("/test")
        def handler(request):
            return Response("OK")
        
        # Should find the route
        result = router.find_route("/test", "GET")
        assert result is not None
        route, params = result
        assert route.pattern == "/test"
        assert params == {}
        
        # Should not find non-existent route
        result = router.find_route("/nonexistent", "GET")
        assert result is None
    
    def test_find_route_with_parameters(self):
        """Test finding routes with parameters."""
        router = Router()
        
        @router.get("/users/{user_id}")
        def handler(request, user_id):
            return Response(f"User {user_id}")
        
        result = router.find_route("/users/123", "GET")
        assert result is not None
        route, params = result
        assert params == {"user_id": "123"}
    
    def test_dispatch_simple(self):
        """Test dispatching a simple request."""
        router = Router()
        
        @router.get("/test")
        def handler(request):
            return Response("Test Response")
        
        request = Request("GET", "/test", {})
        response = router.dispatch(request)
        
        assert isinstance(response, Response)
        assert response.body == b"Test Response"
        assert response.status_code == 200
    
    def test_dispatch_with_parameters(self):
        """Test dispatching request with path parameters."""
        router = Router()
        
        @router.get("/users/{user_id}")
        def handler(request, user_id):
            return Response(f"User ID: {user_id}")
        
        request = Request("GET", "/users/42", {})
        response = router.dispatch(request)
        
        assert response.body == b"User ID: 42"
    
    def test_dispatch_not_found(self):
        """Test dispatching request to non-existent route."""
        router = Router()
        
        request = Request("GET", "/nonexistent", {})
        response = router.dispatch(request)
        
        assert response.status_code == 404
        assert b"Not Found" in response.body
    
    def test_dispatch_method_not_allowed(self):
        """Test dispatching with wrong HTTP method."""
        router = Router()
        
        @router.get("/test")
        def handler(request):
            return Response("OK")
        
        request = Request("POST", "/test", {})
        response = router.dispatch(request)
        
        assert response.status_code == 404  # No matching route
    
    def test_dispatch_handler_exception(self):
        """Test dispatching when handler raises exception."""
        router = Router()
        
        @router.get("/error")
        def handler(request):
            raise ValueError("Test error")
        
        request = Request("GET", "/error", {})
        response = router.dispatch(request)
        
        assert response.status_code == 500
        assert b"Internal Server Error" in response.body
    
    def test_dispatch_return_dict(self):
        """Test handler returning dictionary (auto-converted to JSON)."""
        router = Router()
        
        @router.get("/json")
        def handler(request):
            return {"message": "Hello", "status": "success"}
        
        request = Request("GET", "/json", {})
        response = router.dispatch(request)
        
        assert response.headers["Content-Type"] == "application/json"
        assert b'"message": "Hello"' in response.body
    
    def test_dispatch_return_string(self):
        """Test handler returning string (auto-converted to Response)."""
        router = Router()
        
        @router.get("/string")
        def handler(request):
            return "Simple string response"
        
        request = Request("GET", "/string", {})
        response = router.dispatch(request)
        
        assert response.body == b"Simple string response"
    
    def test_middleware(self):
        """Test middleware functionality."""
        router = Router()
        
        # Middleware that adds a header
        def add_header_middleware(request):
            # This middleware doesn't return a response, so it continues
            return None
        
        # Middleware that blocks requests
        def blocking_middleware(request):
            if request.path == "/blocked":
                return Response("Blocked", status_code=403)
            return None
        
        router.add_middleware(add_header_middleware)
        router.add_middleware(blocking_middleware)
        
        @router.get("/blocked")
        def handler(request):
            return Response("Should not reach here")
        
        request = Request("GET", "/blocked", {})
        response = router.dispatch(request)
        
        assert response.status_code == 403
        assert response.body == b"Blocked"
    
    def test_route_priority(self):
        """Test that routes are matched in order of registration."""
        router = Router()
        
        @router.get("/test/{param}")
        def param_handler(request, param):
            return Response(f"Param: {param}")
        
        @router.get("/test/specific")
        def specific_handler(request):
            return Response("Specific")
        
        # The first registered route should match
        request = Request("GET", "/test/specific", {})
        response = router.dispatch(request)
        
        assert response.body == b"Param: specific"
