"""Module managing the active backend context for arbok operations."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arbok_driver.backend import Backend

_context = threading.local()


def get_active_backend() -> Backend:
    """Return the currently active backend.

    Raises:
        RuntimeError: If no backend is active (called outside a program context).
    """
    backend = getattr(_context, "backend", None)
    if backend is None:
        raise RuntimeError(
            "No active backend. arbok.* operations must be called within a "
            "program compilation or simulation context. Ensure a backend is "
            "set on your ArbokDriver instance."
        )
    return backend


def set_active_backend(backend: Backend | None) -> None:
    """Set the active backend for the current thread."""
    _context.backend = backend
