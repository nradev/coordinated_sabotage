"""
Middleware system for the web server.
"""

from typing import Optional, List, Dict, Any
from .request import Request
from .response import Response
import time
import logging


class Middleware:
    """Base middleware class."""

    def __call__(self, request: Request) -> Optional[Response]:
        """Process the request. Return None to continue, or Response to short-circuit."""
        return None

