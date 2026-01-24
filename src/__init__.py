"""
RealTimeX DeepTutor
===================

Intelligent learning companion with multi-agent collaboration and LightRAG.

Core Modules:
    - agents: Multi-agent system for various learning tasks
    - api: FastAPI routers for all endpoints
    - services: LLM, Embedding, RAG, Prompt, TTS, Search services
    - knowledge: Knowledge base management
    - logging: Custom logging adapters
    - config: Configuration management
    - tools: Agent tools (RAG, web search, code execution)
    - utils: Utility functions

Usage:
    # Import as a package for integration with other services
    from src.api.main import app

    # Or use individual modules
    from src.services.rag import RAGService
    from src.agents import ChatAgent
"""

__version__ = "0.5.0.post1"
__package_name__ = "realtimex-deeptutor"

# Expose key modules for easy access
# These are imported lazily to avoid circular imports and heavy startup
__all__ = [
    "agents",
    "api",
    "services",
    "knowledge",
    "logging",
    "config",
    "tools",
    "utils",
]
