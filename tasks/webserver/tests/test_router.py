"""
Tests for the Router and Route classes.
"""

from webserver.request import Request
from webserver.response import Response
from webserver.router import Route, Router


class TestRoute:
    """Test cases for the Route class."""

    def test_route_creation(self):
        """Test creating a route."""

        def handler(request):
            return Response("test")

        route = Route("GET", "/test", handler)

        assert route.method == "GET"
        assert route.pattern == "/test"
        assert route.handler == handler
        assert route.path_params == []

    def test_route_method_normalization(self):
        """Test that route methods are normalized to uppercase."""

        def handler(request):
            return Response("test")

        route = Route("get", "/test", handler)
        assert route.method == "GET"

    def test_simple_route_matching(self):
        """Test simple route matching without parameters."""

        def handler(request):
            return Response("test")

        route = Route("GET", "/test", handler)

        # Should match
        params = route.match("GET", "/test")
        assert params == {}

        # Should not match - wrong method
        params = route.match("POST", "/test")
        assert params is None

        # Should not match - wrong path
        params = route.match("GET", "/other")
        assert params is None

    def test_route_with_path_parameters(self):
        """Test route matching with path parameters."""

        def handler(request, user_id):
            return Response(f"User {user_id}")

        route = Route("GET", "/users/{user_id}", handler)

        # Check path parameters were extracted
        assert route.path_params == ["user_id"]

        # Should match and extract parameter
        params = route.match("GET", "/users/123")
        assert params == {"user_id": "123"}

        # Should match with different parameter
        params = route.match("GET", "/users/abc")
        assert params == {"user_id": "abc"}

        # Should not match - missing parameter
        params = route.match("GET", "/users/")
        assert params is None

    def test_route_with_multiple_parameters(self):
        """Test route with multiple path parameters."""

        def handler(request, user_id, post_id):
            return Response(f"User {user_id}, Post {post_id}")

        route = Route("GET", "/users/{user_id}/posts/{post_id}", handler)

        assert route.path_params == ["user_id", "post_id"]

        params = route.match("GET", "/users/123/posts/456")
        assert params == {"user_id": "123", "post_id": "456"}

    def test_route_repr(self):
        """Test route string representation."""

        def handler(request):
            return Response("test")

        route = Route("GET", "/test", handler)
        repr_str = repr(route)

        assert "GET" in repr_str
        assert "/test" in repr_str


class TestRouter:
    """Test cases for the Router class."""

    def test_router_creation(self):
        """Test creating a router."""
        router = Router()

        assert router.routes == []
        assert router.middleware == []

    def test_add_route(self):
        """Test adding routes to router."""
        router = Router()

        def handler(request):
            return Response("test")

        router.add_route("GET", "/test", handler)

        assert len(router.routes) == 1
        assert router.routes[0].method == "GET"
        assert router.routes[0].pattern == "/test"

    def test_route_decorators(self):
        """Test route decorator methods."""
        router = Router()

        @router.get("/get-test")
        def get_handler(request):
            return Response("GET")

        @router.post("/post-test")
        def post_handler(request):
            return Response("POST")

        @router.put("/put-test")
        def put_handler(request):
            return Response("PUT")

        @router.delete("/delete-test")
        def delete_handler(request):
            return Response("DELETE")

        assert len(router.routes) == 4

        # Check methods were set correctly
        methods = [route.method for route in router.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_dispatch_simple_route(self):
        """Test dispatching to a simple route."""
        router = Router()

        @router.get("/test")
        def handler(request):
            return Response("success")

        request = Request("GET", "/test", {})
        response = router.dispatch(request)

        assert isinstance(response, Response)
        assert response.body == b"success"

    def test_dispatch_with_path_parameters(self):
        """Test dispatching with path parameters."""
        router = Router()

        @router.get("/users/{user_id}")
        def handler(request, user_id):
            return Response(f"User {user_id}")

        request = Request("GET", "/users/123", {})
        response = router.dispatch(request)

        assert response.body == b"User 123"

    def test_dispatch_not_found(self):
        """Test dispatching to non-existent route."""
        router = Router()

        request = Request("GET", "/nonexistent", {})
        response = router.dispatch(request)

        assert response.status_code == 404
        assert b"Not found" in response.body

    def test_dispatch_with_query_string(self):
        """Test dispatching with query string in path."""
        router = Router()

        @router.get("/test")
        def handler(request):
            return Response("success")

        # Path with query string should still match
        request = Request("GET", "/test?param=value", {})
        response = router.dispatch(request)

        assert response.body == b"success"

    def test_dispatch_handler_exception(self):
        """Test handling exceptions in route handlers."""
        router = Router()

        @router.get("/error")
        def handler(request):
            raise ValueError("Test error")

        request = Request("GET", "/error", {})
        response = router.dispatch(request)

        assert response.status_code == 500
        assert b"Internal server error" in response.body

    def test_dispatch_handler_returns_string(self):
        """Test handler returning string instead of Response."""
        router = Router()

        @router.get("/string")
        def handler(request):
            return "Just a string"

        request = Request("GET", "/string", {})
        response = router.dispatch(request)

        assert isinstance(response, Response)
        assert response.body == b"Just a string"

    def test_dispatch_handler_returns_dict(self):
        """Test handler returning dict (should be converted to JSON)."""
        router = Router()

        @router.get("/dict")
        def handler(request):
            return {"message": "test"}

        request = Request("GET", "/dict", {})
        response = router.dispatch(request)

        assert isinstance(response, Response)
        assert response.headers["Content-Type"] == "application/json"

    def test_add_middleware(self):
        """Test adding middleware to router."""
        router = Router()

        class TestMiddleware:
            def __call__(self, request):
                return None

        middleware = TestMiddleware()
        router.add_middleware(middleware)

        assert len(router.middleware) == 1
        assert router.middleware[0] == middleware

    def test_middleware_processing(self):
        """Test middleware processing in dispatch."""
        router = Router()

        class TestMiddleware:
            def __call__(self, request):
                if request.path == "/blocked":
                    return Response("Blocked", status_code=403)
                return None

        router.add_middleware(TestMiddleware())

        @router.get("/blocked")
        def handler(request):
            return Response("Should not reach here")

        @router.get("/allowed")
        def handler2(request):
            return Response("Allowed")

        # Blocked request
        request = Request("GET", "/blocked", {})
        response = router.dispatch(request)
        assert response.status_code == 403
        assert response.body == b"Blocked"

        # Allowed request
        request = Request("GET", "/allowed", {})
        response = router.dispatch(request)
        assert response.body == b"Allowed"
