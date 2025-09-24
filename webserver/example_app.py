"""
Example application using the web server.
"""

import json
import logging
import sys
import os

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from webserver.server import WebServer
from webserver.request import Request
from webserver.response import Response
from webserver.middleware import AuthMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create server instance
app = WebServer(host="localhost", port=8000)

# Add some middleware
auth_middleware = AuthMiddleware(protected_paths=["/api/protected"])
rate_limit_middleware = RateLimitMiddleware(max_requests=10, window_seconds=60)

app.add_middleware(auth_middleware)
app.add_middleware(rate_limit_middleware)

# In-memory data store for demo
users = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
]


# Routes
@app.get("/")
def home(request: Request) -> Response:
    """Home page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Web Server</title>
    </head>
    <body>
        <h1>Welcome to the Simple Web Server!</h1>
        <p>Available endpoints:</p>
        <ul>
            <li><a href="/api/users">GET /api/users</a> - List all users</li>
            <li><a href="/api/users/1">GET /api/users/{id}</a> - Get user by ID</li>
            <li>POST /api/users - Create new user</li>
            <li>PUT /api/users/{id} - Update user</li>
            <li>DELETE /api/users/{id} - Delete user</li>
            <li><a href="/api/protected">GET /api/protected</a> - Protected endpoint (requires auth)</li>
        </ul>
    </body>
    </html>
    """
    return Response.html(html)


@app.get("/api/users")
def get_users(request: Request) -> Response:
    """Get all users."""
    return Response.json({"users": users})


@app.get("/api/users/{user_id}")
def get_user(request: Request, user_id: str) -> Response:
    """Get a specific user by ID."""
    try:
        user_id = int(user_id)
        user = next((u for u in users if u["id"] == user_id), None)
        if user:
            return Response.json({"user": user})
        else:
            return Response.json({"error": "User not found"}, status_code=404)
    except ValueError:
        return Response.json({"error": "Invalid user ID"}, status_code=400)


@app.post("/api/users")
def create_user(request: Request) -> Response:
    """Create a new user."""
    data = request.json
    if not data or "name" not in data or "email" not in data:
        return Response.json({"error": "Name and email are required"}, status_code=400)

    # Generate new ID
    new_id = max(u["id"] for u in users) + 1 if users else 1

    new_user = {"id": new_id, "name": data["name"], "email": data["email"]}

    users.append(new_user)
    return Response.json({"user": new_user}, status_code=201)


@app.put("/api/users/{user_id}")
def update_user(request: Request, user_id: str) -> Response:
    """Update an existing user."""
    try:
        user_id = int(user_id)
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return Response.json({"error": "User not found"}, status_code=404)

        data = request.json
        if not data:
            return Response.json({"error": "No data provided"}, status_code=400)

        # Update user fields
        if "name" in data:
            user["name"] = data["name"]
        if "email" in data:
            user["email"] = data["email"]

        return Response.json({"user": user})

    except ValueError:
        return Response.json({"error": "Invalid user ID"}, status_code=400)


@app.delete("/api/users/{user_id}")
def delete_user(request: Request, user_id: str) -> Response:
    """Delete a user."""
    try:
        user_id = int(user_id)
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return Response.json({"error": "User not found"}, status_code=404)

        users.remove(user)
        return Response.json({"message": "User deleted successfully"})

    except ValueError:
        return Response.json({"error": "Invalid user ID"}, status_code=400)


@app.get("/api/protected")
def protected_endpoint(request: Request) -> Response:
    """Protected endpoint that requires authentication."""
    return Response.json({"message": "This is a protected endpoint!"})


@app.get("/health")
def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return Response.json({"status": "healthy", "server": "simple-webserver"})


def main():
    """Run the example application."""
    try:
        print("Starting server...")
        print("Visit http://localhost:8000 to see the application")
        print("Press Ctrl+C to stop the server")
        app.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        app.stop()


if __name__ == "__main__":
    main()
