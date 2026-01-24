# -*- coding: utf-8 -*-
"""
Pipeline Factory
================

Factory for creating and managing RAG pipelines.

Note: Pipeline imports are lazy to avoid importing heavy dependencies (lightrag, llama_index, etc.)
at module load time. This allows the core services to be imported without RAG dependencies.
"""

import logging
from typing import Callable, Dict, List, Optional
import warnings

logger = logging.getLogger(__name__)

# Pipeline registry - populated lazily
_PIPELINES: Dict[str, Callable] = {}
_PIPELINES_INITIALIZED = False


def _init_pipelines():
    """Lazily initialize pipeline registry.

    Important:
    - Do NOT import optional heavy dependencies (e.g. llama_index) here.
    - Pipelines must be imported inside their factory callables, so users can
      use other providers without installing every optional dependency.
    """
    global _PIPELINES, _PIPELINES_INITIALIZED
    if _PIPELINES_INITIALIZED:
        return

    def _build_raganything(**kwargs):
        from .pipelines.raganything import RAGAnythingPipeline

        return RAGAnythingPipeline(**kwargs)

    def _build_raganything_docling(**kwargs):
        from .pipelines.raganything_docling import RAGAnythingDoclingPipeline

        return RAGAnythingDoclingPipeline(**kwargs)

    def _build_lightrag(kb_base_dir: Optional[str] = None, **kwargs):
        # LightRAGPipeline is a factory function returning a composed RAGPipeline
        from .pipelines.lightrag import LightRAGPipeline

        return LightRAGPipeline(kb_base_dir=kb_base_dir)

    def _build_realtimex(kb_base_dir: Optional[str] = None, **kwargs):
        # RealTimeX is an alias for LightRAG with RealTimeX branding
        from .pipelines.lightrag import LightRAGPipeline

        return LightRAGPipeline(kb_base_dir=kb_base_dir)

    def _build_llamaindex(**kwargs):
        # LlamaIndexPipeline depends on optional `llama_index` package.
        # Import it only when explicitly requested.
        from .pipelines.llamaindex import LlamaIndexPipeline

        return LlamaIndexPipeline(**kwargs)

    _PIPELINES.update(
        {
            "raganything": _build_raganything,  # Full multimodal: MinerU parser, deep analysis (slow, thorough)
            "raganything_docling": _build_raganything_docling,  # Docling parser: Office/HTML friendly, easier setup
            "lightrag": _build_lightrag,  # Knowledge graph: PDFParser, fast text-only (medium speed)
            "realtimex": _build_realtimex,  # RealTimeX AI powered knowledge retrieval (recommended, uses LightRAG)
            "llamaindex": _build_llamaindex,  # Vector-only: Simple chunking, fast (fastest)
        }
    )
    _PIPELINES_INITIALIZED = True


# Pipeline metadata for list_pipelines()
_PIPELINE_INFO: Dict[str, Dict[str, str]] = {
    "realtimex": {
        "id": "realtimex",
        "name": "RealTimeX",
        "description": "RealTimeX AI powered knowledge retrieval (recommended).",
        "available": True,
    },
    "lightrag": {
        "id": "lightrag",
        "name": "LightRAG",
        "description": "Lightweight knowledge graph retrieval, fast processing of text documents.",
        "available": True,
    },
}


# Try to register optional pipelines
def _register_optional_pipelines():
    """Register pipelines that have optional dependencies."""
    global _PIPELINES, _PIPELINE_INFO

    # Try RAGAnything (requires raganything package)
    try:
        from .pipelines.raganything import RAGAnythingPipeline

        _PIPELINES["raganything"] = RAGAnythingPipeline
        _PIPELINE_INFO["raganything"] = {
            "id": "raganything",
            "name": "RAG-Anything",
            "description": "Multimodal document processing with chart and formula extraction.",
            "available": True,
        }
        logger.debug("RAGAnything pipeline registered")
    except ImportError as e:
        _PIPELINE_INFO["raganything"] = {
            "id": "raganything",
            "name": "RAG-Anything",
            "description": "Multimodal document processing (requires: pip install realtimex-deeptutor[raganything])",
            "available": False,
        }
        logger.debug(f"RAGAnything not available: {e}")

    # Try LlamaIndex (requires llama-index package)
    try:
        from .pipelines import llamaindex

        _PIPELINES["llamaindex"] = llamaindex.LlamaIndexPipeline
        _PIPELINE_INFO["llamaindex"] = {
            "id": "llamaindex",
            "name": "LlamaIndex",
            "description": "Pure vector retrieval, fastest processing speed.",
            "available": True,
        }
        logger.debug("LlamaIndex pipeline registered")
    except ImportError as e:
        _PIPELINE_INFO["llamaindex"] = {
            "id": "llamaindex",
            "name": "LlamaIndex",
            "description": "Vector retrieval (requires: pip install realtimex-deeptutor[llamaindex])",
            "available": False,
        }
        logger.debug(f"LlamaIndex not available: {e}")


# Register optional pipelines at module load
_register_optional_pipelines()


def get_pipeline(name: str = "realtimex", kb_base_dir: Optional[str] = None, **kwargs):
    """
    Get a pre-configured pipeline by name.

    Args:
        name: Pipeline name (raganything, raganything_docling, lightrag, realtimex, llamaindex)
              Default is 'realtimex' (recommended, always available).
        kb_base_dir: Base directory for knowledge bases (passed to all pipelines)
        **kwargs: Additional arguments passed to pipeline constructor

    Returns:
        Pipeline instance

    Raises:
        ValueError: If pipeline name is not found or not available
    """
    _init_pipelines()
    if name not in _PIPELINES:
        available = list(_PIPELINES.keys())
        # Check if it's a known but unavailable pipeline
        if name in _PIPELINE_INFO:
            info = _PIPELINE_INFO[name]
            raise ValueError(
                f"Pipeline '{name}' is not available. {info['description']}. "
                f"Available pipelines: {available}"
            )
        raise ValueError(f"Unknown pipeline: {name}. Available: {available}")

    factory = _PIPELINES[name]

    try:
        # Handle different pipeline types:
        # - lightrag, realtimex: callable that accepts kb_base_dir and returns a composed RAGPipeline
        # - llamaindex, raganything, raganything_docling: callables that instantiate class-based pipelines
        if name in ("lightrag", "realtimex"):
            return factory(kb_base_dir=kb_base_dir, **kwargs)

        if kb_base_dir:
            kwargs["kb_base_dir"] = kb_base_dir
        return factory(**kwargs)
    except ImportError as e:
        # Common case: user didn't install optional RAG backend deps (e.g. llama_index).
        raise ValueError(
            f"Pipeline '{name}' is not available because an optional dependency is missing: {e}. "
            f"Please install the required dependency for '{name}', or switch provider to 'realtimex'/'lightrag'."
        ) from e


def list_pipelines(include_unavailable: bool = False) -> List[Dict[str, str]]:
    """
    List available pipelines.

    Args:
        include_unavailable: If True, also include pipelines that aren't installed

    Returns:
        List of pipeline info dictionaries
    """
    return [
        {
            "id": "realtimex",
            "name": "RealTimeX",
            "description": "RealTimeX AI powered knowledge retrieval (recommended).",
        },
        {
            "id": "lightrag",
            "name": "LightRAG",
            "description": "Lightweight knowledge graph retrieval, fast processing of text documents.",
        },
        {
            "id": "raganything",
            "name": "RAG-Anything (MinerU)",
            "description": "Multimodal document processing with MinerU parser. Best for academic PDFs with complex equations and formulas.",
        },
        {
            "id": "raganything_docling",
            "name": "RAG-Anything (Docling)",
            "description": "Multimodal document processing with Docling parser. Better for Office documents (.docx, .pptx) and HTML. Easier to install.",
        },
        {
            "id": "llamaindex",
            "name": "LlamaIndex",
            "description": "Pure vector retrieval, fastest processing speed.",
        },
    ]


def register_pipeline(name: str, factory: Callable):
    """
    Register a custom pipeline.

    Args:
        name: Pipeline name
        factory: Factory function or class that creates the pipeline
    """
    _init_pipelines()
    _PIPELINES[name] = factory


def has_pipeline(name: str) -> bool:
    """
    Check if a pipeline exists.

    Args:
        name: Pipeline name

    Returns:
        True if pipeline exists
    """
    _init_pipelines()
    return name in _PIPELINES


# Backward compatibility with old plugin API
def get_plugin(name: str) -> Dict[str, Callable]:
    """
    DEPRECATED: Use get_pipeline() instead.

    Get a plugin by name (maps to pipeline API).
    """
    warnings.warn(
        "get_plugin() is deprecated, use get_pipeline() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    pipeline = get_pipeline(name)
    return {
        "initialize": pipeline.initialize,
        "search": pipeline.search,
        "delete": getattr(pipeline, "delete", lambda kb: True),
    }


def list_plugins() -> List[Dict[str, str]]:
    """
    DEPRECATED: Use list_pipelines() instead.
    """
    warnings.warn(
        "list_plugins() is deprecated, use list_pipelines() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return list_pipelines()


def has_plugin(name: str) -> bool:
    """
    DEPRECATED: Use has_pipeline() instead.
    """
    warnings.warn(
        "has_plugin() is deprecated, use has_pipeline() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return has_pipeline(name)
