"""
Simple web server implementation.

This package provides a lightweight HTTP server with routing capabilities.
"""

from .server import WebServer
from .router import Router
from .request import Request
from .response import Response

__version__ = "0.1.0"
__all__ = ["WebServer", "Router", "Request", "Response"]
