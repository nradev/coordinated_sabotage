#!/usr/bin/env python3
"""
Simple demo script for the webserver.
"""

import os
import sys

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from webserver import WebServer, Response, LoggingMiddleware, CORSMiddleware


def create_demo_server():
    """Create a simple demo server."""
    app = WebServer(host="localhost", port=8080)
    
    # Add CORS middleware
    app.add_middleware(CORSMiddleware())
    
    @app.get("/")
    def home(request):
        """Home page."""
        return Response.html("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Demo Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>🚀 Demo Web Server</h1>
            <p>This is a simple demonstration of the web server.</p>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <strong>GET /</strong> - This home page
            </div>
            
            <div class="endpoint">
                <strong>GET /api/hello</strong> - Simple JSON response
            </div>
            
            <div class="endpoint">
                <strong>GET /api/users/{id}</strong> - Get user by ID
            </div>
            
            <div class="endpoint">
                <strong>POST /api/echo</strong> - Echo back JSON data
            </div>
            
            <h2>Test Commands:</h2>
            <pre>
# Test JSON endpoint
curl http://localhost:8080/api/hello

# Test path parameters
curl http://localhost:8080/api/users/123

# Test POST with JSON
curl -X POST http://localhost:8080/api/echo \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello, World!"}'
            </pre>
        </body>
        </html>
        """)
    
    @app.get("/api/hello")
    def hello(request):
        """Simple JSON response."""
        return Response.json({
            "message": "Hello from the demo server!",
            "server": "simple-webserver",
            "version": "0.1.0"
        })
    
    @app.get("/api/users/{user_id}")
    def get_user(request, user_id):
        """Get user by ID."""
        try:
            user_id = int(user_id)
            return Response.json({
                "user_id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com"
            })
        except ValueError:
            return Response.json(
                {"error": "Invalid user ID"}, 
                status_code=400
            )
    
    @app.post("/api/echo")
    def echo(request):
        """Echo back the JSON data."""
        data = request.json
        if not data:
            return Response.json(
                {"error": "JSON body required"}, 
                status_code=400
            )
        
        return Response.json({
            "echo": data,
            "received_at": "2024-01-01T00:00:00Z",
            "content_length": request.content_length
        })
    
    return app


def main():
    """Run the demo server."""
    print("🚀 Starting Demo Web Server...")
    print("=" * 40)
    
    app = create_demo_server()
    
    print(f"✅ Server configured with {len(app.router.middleware)} middleware components")
    print("🌐 Server starting on http://localhost:8080")
    print("📝 Visit http://localhost:8080 to see the demo page")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 40)
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")


if __name__ == "__main__":
    main()
