# -*- coding: utf-8 -*-
"""
RealTimeX Embedding Adapter
============================

Provides embedding capabilities through RealTimeX SDK proxy.
Used when running as a local app within RealTimeX desktop.
"""

from typing import Any, Dict

from realtimex_sdk import LLMPermissionError, LLMProviderError

from src.logging import get_logger
from src.utils.realtimex import get_realtimex_sdk

from .base import BaseEmbeddingAdapter, EmbeddingRequest, EmbeddingResponse

logger = get_logger("RealTimeXEmbeddingAdapter")


class RealTimeXEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    Embedding adapter for RealTimeX SDK.

    Provides embeddings through the RealTimeX Main App proxy.
    No API key or base_url needed - uses RTX_APP_ID for authentication.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize RealTimeX embedding adapter.

        Args:
            config: Adapter config (SDK doesn't need api_key/base_url)
                   - model: Model name (optional, uses active provider default)
                   - dimensions: Expected embedding dimensions
        """
        # Call parent init (though most fields not needed for RealTimeX)
        super().__init__(config)

        # SDK is initialized lazily on first request
        logger.debug(
            f"RealTimeX embedding adapter configured: "
            f"model={self.model or 'default'}, dimensions={self.dimensions}"
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings via RealTimeX SDK.

        Args:
            request: EmbeddingRequest with texts

        Returns:
            EmbeddingResponse with embeddings

        Raises:
            Exception: If SDK request fails or permission denied
        """
        sdk = get_realtimex_sdk()

        # Use model from request, fallback to adapter config
        model = request.model or self.model

        logger.debug(
            f"RealTimeX embed: texts_count={len(request.texts)}, model={model or 'default'}"
        )

        try:
            # Call SDK embed function
            result = await sdk.llm.embed(input_text=request.texts, model=model)

            if not result.success:
                error_msg = result.error or "SDK request failed"
                logger.error(f"RealTimeX embed failed: {error_msg}")
                raise Exception(f"RealTimeX embedding error: {error_msg}")

            # Validate dimensions match if specified
            if self.dimensions and result.dimensions != self.dimensions:
                logger.warning(
                    f"Dimension mismatch: expected {self.dimensions}, "
                    f"got {result.dimensions} from {result.model}"
                )

            # Log success
            logger.debug(
                f"RealTimeX embed success: provider={result.provider}, "
                f"model={result.model}, dimensions={result.dimensions}, "
                f"embeddings_count={len(result.embeddings)}"
            )

            return EmbeddingResponse(
                embeddings=result.embeddings,
                model=result.model or model or "unknown",
                dimensions=result.dimensions,
                usage={},  # SDK doesn't currently expose usage metrics
            )

        except LLMPermissionError as e:
            logger.error(f"RealTimeX permission error: {e}")
            raise PermissionError(
                "RealTimeX embedding permission required. "
                "Ensure 'llm.embed' is in your SDK permissions."
            ) from e
        except LLMProviderError as e:
            logger.error(f"RealTimeX provider error: {e}")
            raise Exception(f"RealTimeX embedding provider error: {e}") from e
        except Exception as e:
            logger.error(f"RealTimeX embedding error: {e}")
            raise Exception(f"RealTimeX embedding failed: {e}") from e

    def get_model_info(self) -> Dict[str, Any]:
        """
        Return information about the configured model.

        Returns:
            Dictionary with model metadata
        """
        return {
            "provider": "realtimex",
            "model": self.model or "default",
            "dimensions": self.dimensions,
            "description": "RealTimeX SDK embedding proxy",
        }
