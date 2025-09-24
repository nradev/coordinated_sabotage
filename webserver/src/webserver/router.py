"""
URL routing system.
"""

from typing import Dict, List, Callable, Any, Optional, Tuple
import re
from .request import Request
from .response import Response


class Route:
    """Represents a single route."""
    
    def __init__(self, method: str, pattern: str, handler: Callable, path_params: List[str] = None):
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self.path_params = path_params or []
        self.regex = self._compile_pattern(pattern)
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Convert URL pattern to regex, extracting path parameters."""
        # Find path parameters like {id}, {name}, etc.
        param_pattern = r'\{([^}]+)\}'
        params = re.findall(param_pattern, pattern)
        self.path_params = params
        
        # Replace path parameters with regex groups
        regex_pattern = re.sub(param_pattern, r'([^/]+)', pattern)
        
        # Ensure exact match
        regex_pattern = f"^{regex_pattern}$"
        
        return re.compile(regex_pattern)
    
    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        """Check if this route matches the request method and path."""
        if self.method != method.upper():
            return None
        
        match = self.regex.match(path)
        if not match:
            return None
        
        # Extract path parameters
        path_params = {}
        for i, param_name in enumerate(self.path_params):
            path_params[param_name] = match.group(i + 1)
        
        return path_params
    
    def __repr__(self) -> str:
        return f"Route({self.method} {self.pattern})"


class Router:
    """URL router with middleware support."""
    
    def __init__(self):
        self.routes: List[Route] = []
        self.middleware: List[Any] = []
    
    def add_route(self, method: str, pattern: str, handler: Callable) -> None:
        """Add a route to the router."""
        route = Route(method, pattern, handler)
        self.routes.append(route)
    
    def add_middleware(self, middleware: Any) -> None:
        """Add middleware to the router."""
        self.middleware.append(middleware)
    
    def dispatch(self, request: Request) -> Response:
        """Dispatch a request to the appropriate handler."""
        # Process middleware first
        for middleware in self.middleware:
            response = middleware(request)
            if response is not None:
                return response
        
        # Find matching route
        for route in self.routes:
            path_params = route.match(request.method, request.path.split('?')[0])  # Remove query string
            if path_params is not None:
                try:
                    # Call handler with request and path parameters
                    if path_params:
                        response = route.handler(request, **path_params)
                    else:
                        response = route.handler(request)
                    
                    # Ensure we return a Response object
                    if not isinstance(response, Response):
                        if isinstance(response, dict):
                            response = Response.json(response)
                        elif isinstance(response, str):
                            response = Response.html(response)
                        else:
                            response = Response(str(response))
                    
                    return response
                    
                except Exception as e:
                    return Response.json(
                        {"error": "Internal server error", "message": str(e)},
                        status_code=500
                    )
        
        # No route found
        return Response.json(
            {"error": "Not found", "path": request.path},
            status_code=404
        )
    
    def get(self, pattern: str) -> Callable:
        """Decorator for GET routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('GET', pattern, handler)
            return handler
        return decorator
    
    def post(self, pattern: str) -> Callable:
        """Decorator for POST routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('POST', pattern, handler)
            return handler
        return decorator
    
    def put(self, pattern: str) -> Callable:
        """Decorator for PUT routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('PUT', pattern, handler)
            return handler
        return decorator
    
    def delete(self, pattern: str) -> Callable:
        """Decorator for DELETE routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('DELETE', pattern, handler)
            return handler
        return decorator
    
    def patch(self, pattern: str) -> Callable:
        """Decorator for PATCH routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('PATCH', pattern, handler)
            return handler
        return decorator
    
    def options(self, pattern: str) -> Callable:
        """Decorator for OPTIONS routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route('OPTIONS', pattern, handler)
            return handler
        return decorator
