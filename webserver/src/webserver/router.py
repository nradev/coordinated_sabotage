"""
HTTP Router for handling URL routing and path parameters.
"""

import re
from typing import Dict, List, Callable, Optional, Tuple, Any
from .request import Request
from .response import Response


class Route:
    """Represents a single route."""
    
    def __init__(self, pattern: str, handler: Callable, methods: List[str]):
        self.pattern = pattern
        self.handler = handler
        self.methods = [m.upper() for m in methods]
        self.regex, self.param_names = self._compile_pattern(pattern)
    
    def _compile_pattern(self, pattern: str) -> Tuple[re.Pattern, List[str]]:
        """Compile a route pattern into a regex and extract parameter names."""
        param_names = []
        regex_pattern = pattern
        
        # Find all path parameters like {id} or {name}
        param_matches = re.findall(r'\{([^}]+)\}', pattern)
        for param in param_matches:
            param_names.append(param)
            # Replace {param} with a named capture group
            regex_pattern = regex_pattern.replace(f'{{{param}}}', f'(?P<{param}>[^/]+)')
        
        # Ensure exact match
        if not regex_pattern.endswith('$'):
            regex_pattern += '$'
        if not regex_pattern.startswith('^'):
            regex_pattern = '^' + regex_pattern
            
        return re.compile(regex_pattern), param_names
    
    def matches(self, path: str, method: str) -> Optional[Dict[str, str]]:
        """Check if this route matches the given path and method."""
        if method.upper() not in self.methods:
            return None
            
        match = self.regex.match(path)
        if match:
            return match.groupdict()
        return None


class Router:
    """HTTP Router for managing routes and dispatching requests."""
    
    def __init__(self):
        self.routes: List[Route] = []
    
    def add_route(self, pattern: str, handler: Callable, methods: List[str] = None) -> None:
        """Add a route to the router."""
        if methods is None:
            methods = ['GET']
        route = Route(pattern, handler, methods)
        self.routes.append(route)
    
    def get(self, pattern: str) -> Callable:
        """Decorator for GET routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(pattern, handler, ['GET'])
            return handler
        return decorator
    
    def post(self, pattern: str) -> Callable:
        """Decorator for POST routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(pattern, handler, ['POST'])
            return handler
        return decorator
    
    def put(self, pattern: str) -> Callable:
        """Decorator for PUT routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(pattern, handler, ['PUT'])
            return handler
        return decorator
    
    def delete(self, pattern: str) -> Callable:
        """Decorator for DELETE routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(pattern, handler, ['DELETE'])
            return handler
        return decorator
    
    def route(self, pattern: str, methods: List[str] = None) -> Callable:
        """Generic route decorator."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(pattern, handler, methods or ['GET'])
            return handler
        return decorator
        
    def find_route(self, path: str, method: str) -> Optional[Tuple[Route, Dict[str, str]]]:
        """Find a matching route for the given path and method."""
        for route in self.routes:
            params = route.matches(path, method)
            if params is not None:
                return route, params
        return None
    
    def dispatch(self, request: Request) -> Response:
        """Dispatch a request to the appropriate handler."""

        # Find matching route
        route_match = self.find_route(request.path, request.method)
        if route_match is None:
            return Response("Not Found", status_code=404)
        
        route, params = route_match
        
        try:
            # Call handler with request and path parameters
            if params:
                # If handler accepts path parameters, pass them as keyword arguments
                import inspect
                sig = inspect.signature(route.handler)
                if len(sig.parameters) > 1:  # More than just request parameter
                    response = route.handler(request, **params)
                else:
                    response = route.handler(request)
            else:
                response = route.handler(request)
            
            # Ensure we return a Response object
            if not isinstance(response, Response):
                if isinstance(response, (dict, list)):
                    response = Response.json(response)
                else:
                    response = Response(str(response))
            
            return response
            
        except Exception as e:
            return Response(f"Internal Server Error: {str(e)}", status_code=500)
