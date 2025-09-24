#!/usr/bin/env python3
"""
Simple demo of the webserver functionality.
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from webserver import WebServer, Response


def create_demo_server():
    """Create a demo server with sample routes."""

    app = WebServer(host="localhost", port=8080)

    # Simple routes
    @app.get("/")
    def home(request):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebServer Demo</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { color: #007acc; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🚀 WebServer Demo</h1>
            <p>Welcome to the simple Python web server!</p>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <a href="/hello">/hello</a> - Simple greeting
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <a href="/api/status">/api/status</a> - JSON status response
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <a href="/users/123">/users/{id}</a> - Path parameter example
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <a href="/search?q=python&limit=10">/search?q=python&limit=10</a> - Query parameters
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /api/echo - Echo JSON data (use curl or Postman)
            </div>
            
            <h2>Test with curl:</h2>
            <pre>
# JSON POST request
curl -X POST http://localhost:8080/api/echo \\
     -H "Content-Type: application/json" \\
     -d '{"message": "Hello from curl!"}'

# GET with query parameters  
curl "http://localhost:8080/search?q=webserver&limit=5"
            </pre>
        </body>
        </html>
        """
        return Response.html(html)

    @app.get("/hello")
    def hello(request):
        return Response.text("Hello from the simple web server! 👋")

    @app.get("/api/status")
    def status(request):
        return Response.json({"status": "running", "server": "simple-webserver", "version": "1.0.0", "endpoints": 6})

    @app.get("/users/{user_id}")
    def get_user(request, user_id):
        try:
            user_id = int(user_id)
            return Response.json({"user_id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"})
        except ValueError:
            return Response.json({"error": "Invalid user ID"}, status_code=400)

    @app.get("/search")
    def search(request):
        query = request.query_params.get("q", "")
        limit = request.query_params.get("limit", "10")

        try:
            limit = int(limit)
        except ValueError:
            limit = 10

        # Simulate search results
        results = []
        if query:
            for i in range(min(limit, 5)):  # Max 5 fake results
                results.append(
                    {
                        "id": i + 1,
                        "title": f"Result {i + 1} for '{query}'",
                        "description": f"This is a sample search result for the query '{query}'",
                    }
                )

        return Response.json({"query": query, "limit": limit, "total": len(results), "results": results})

    @app.post("/api/echo")
    def echo(request):
        data = request.json
        if not data:
            return Response.json({"error": "No JSON data provided"}, status_code=400)

        return Response.json(
            {
                "echo": data,
                "received_at": "2024-01-01T12:00:00Z",  # Simplified timestamp
                "content_length": request.content_length,
            }
        )

    return app


def main():
    """Run the demo server."""

    print("🚀 Starting WebServer Demo...")
    print("=" * 50)

    app = create_demo_server()

    try:
        print("✅ Server starting on http://localhost:8080")
        print("📝 Visit http://localhost:8080 to see available endpoints")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)

        app.start()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        app.stop()
        print("✅ Server stopped successfully")

    except Exception as e:
        print(f"❌ Server error: {e}")
        app.stop()


if __name__ == "__main__":
    main()
