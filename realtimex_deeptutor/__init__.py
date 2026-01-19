"""
RealTimeX DeepTutor Package Namespace
=====================================

This module provides a clean namespace alias for the DeepTutor package.

Import examples:
    from realtimex_deeptutor.api.routers import knowledge
    from realtimex_deeptutor.services.rag import RAGService
    from realtimex_deeptutor import __version__

This is equivalent to:
    from src.api.routers import knowledge
    from src.services.rag import RAGService
"""

import sys

# Import src and its key submodules to ensure they're in sys.modules
import src
import src.agents
import src.api
import src.api.routers
import src.config
import src.knowledge
import src.services
import src.tools
import src.utils

# Version info
__version__ = "0.5.0.post1"
__package_name__ = "realtimex-deeptutor"

# Re-export key submodules
from src import agents, api, config, knowledge, services, tools, utils

# Create aliases in sys.modules for the realtimex_deeptutor namespace
# This allows `from realtimex_deeptutor.api.routers import ...` to work
_modules_to_alias = [
    "src",
    "src.api",
    "src.api.routers",
    "src.services",
    "src.services.rag",
    "src.agents",
    "src.knowledge",
    "src.config",
    "src.tools",
    "src.utils",
]

for src_key in _modules_to_alias:
    if src_key in sys.modules:
        rt_key = src_key.replace("src", "realtimex_deeptutor", 1)
        sys.modules[rt_key] = sys.modules[src_key]

__all__ = [
    "api",
    "services",
    "agents",
    "knowledge",
    "config",
    "tools",
    "utils",
    "__version__",
    "__package_name__",
]
