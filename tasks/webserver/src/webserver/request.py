"""
HTTP Request handling.
"""

from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse
import json


class Request:
    """Represents an HTTP request."""

    def __init__(
        self, method: str, path: str, headers: Dict[str, str], body: bytes = b""
    ):
        self.method = method.upper()
        self.path = path
        self.headers = headers
        self.body = body
        self._query_params: Optional[Dict[str, Any]] = None
        self._json_data: Optional[Dict[str, Any]] = None

    @property
    def query_params(self) -> Dict[str, Any]:
        """Parse and return query parameters from the URL."""
        if self._query_params is None:
            parsed_url = urlparse(self.path)
            self._query_params = {}
            if parsed_url.query:
                parsed = parse_qs(parsed_url.query)
                # Flatten single-item lists
                for key, value_list in parsed.items():
                    if len(value_list) == 1:
                        self._query_params[key] = value_list[0]
                    else:
                        self._query_params[key] = value_list
        return self._query_params

    @property
    def json(self) -> Optional[Dict[str, Any]]:
        """Parse and return JSON data from request body."""
        if self._json_data is None and self.body:
            content_type = self.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    self._json_data = json.loads(self.body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._json_data = None
        return self._json_data

    @property
    def content_length(self) -> int:
        """Return the content length of the request body."""
        return len(self.body)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a header value by name (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self.headers.items():
            if key.lower() == name_lower:
                return value
        return default

    def __repr__(self) -> str:
        return f"Request(method='{self.method}', path='{self.path}')"
