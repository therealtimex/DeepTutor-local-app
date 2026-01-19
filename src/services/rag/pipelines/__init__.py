"""
Pre-configured Pipelines
========================

Ready-to-use RAG pipelines for common use cases.

LightRAG and Academic pipelines are always available.
LlamaIndex and RAGAnything require optional dependencies.
"""

# Always available pipelines
from .academic import AcademicPipeline
from .lightrag import LightRAGPipeline

__all__ = [
    "LightRAGPipeline",
    "AcademicPipeline",
]

# Optional pipelines - import only if dependencies are available
try:
    from .llamaindex import LlamaIndexPipeline
    __all__.append("LlamaIndexPipeline")
except ImportError:
    LlamaIndexPipeline = None  # type: ignore

try:
    from .raganything import RAGAnythingPipeline
    __all__.append("RAGAnythingPipeline")
except ImportError:
    RAGAnythingPipeline = None  # type: ignore

