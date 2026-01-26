"""
Command-line interface for DeepTutor.

Provides entry points for:
- Full-stack startup (backend + frontend)
- Backend-only mode (future)
- Frontend-only mode (future)
- Config management (future)
"""

from .start import main as start_main

__all__ = ["start_main"]
