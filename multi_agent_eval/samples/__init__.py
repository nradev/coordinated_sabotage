# Import sample modules to trigger registration side-effects.
from . import secretive_xor as _secretive_xor  # noqa: F401
from . import unique_digits as _unique_digits  # noqa: F401
from . import webserver as _webserver  # noqa: F401
from .registry import (
    RegisteredSample,
    get_sample,
    list_samples,
    register_sample,
)

__all__ = [
    "get_sample",
    "list_samples",
    "register_sample",
    "RegisteredSample",
]
