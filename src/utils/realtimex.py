# -*- coding: utf-8 -*-
"""
RealTimeX SDK Utilities
========================

Utilities for RealTimeX SDK integration.
Provides unified SDK instance management and environment detection.
"""

import logging
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from realtimex_sdk import RealtimeXSDK

# Global SDK instance (lazy-initialized, singleton)
_sdk_instance: Optional["RealtimeXSDK"] = None


def get_realtimex_sdk() -> "RealtimeXSDK":
    """
    Get or create the shared RealTimeX SDK instance.

    This is the single source of truth for SDK instances across DeepTutor.
    All permissions required by the application are specified here.

    Returns:
        RealtimeXSDK: Initialized SDK instance with all required permissions

    Raises:
        ImportError: If realtimex-sdk is not installed
    """
    global _sdk_instance

    if _sdk_instance is None:
        try:
            from realtimex_sdk import RealtimeXSDK, SDKConfig

            # Specify ALL permissions needed by DeepTutor
            _sdk_instance = RealtimeXSDK(
                config=SDKConfig(
                    permissions=[
                        "llm.chat",  # For LLM completions
                        "llm.providers",  # For listing available providers
                        "llm.embed",  # For embeddings
                    ]
                )
            )
            logger.info("RealTimeX SDK initialized with all required permissions")
        except ImportError as e:
            logger.error("RealTimeX SDK not installed. Install with: pip install realtimex-sdk")
            raise ImportError(
                "realtimex-sdk is required for RealTimeX integration. "
                "Install with: pip install realtimex-sdk"
            ) from e

    return _sdk_instance


# Cache for detection result
_detection_cache: Optional[bool] = None


def should_use_realtimex_sdk(force_check: bool = False) -> bool:
    """
    Detect if DeepTutor is running in RealTimeX environment.

    Performs a 3-stage check with result caching:
    1. RTX_APP_ID environment variable is set
    2. RealtimeX SDK is installed (importable)
    3. RealTimeX Main App is accessible (via SDK ping)

    Args:
        force_check: Force re-check even if cached

    Returns:
        True if all RealTimeX conditions are met
    """
    global _detection_cache

    if _detection_cache is not None and not force_check:
        return _detection_cache

    try:
        import os

        # Check 1: RTX_APP_ID environment variable
        app_id = os.getenv("RTX_APP_ID")
        if not app_id:
            logger.debug("RealTimeX not detected: RTX_APP_ID not set")
            _detection_cache = False
            return False

        # Check 2: SDK installed
        try:
            import realtimex_sdk  # noqa: F401
        except ImportError:
            logger.warning(
                "RealTimeX detected (RTX_APP_ID present) but SDK not installed. "
                "Install with: pip install realtimex-sdk"
            )
            _detection_cache = False
            return False

        # Check 3: Main App connectivity via SDK ping
        try:
            sdk = get_realtimex_sdk()
            result = sdk.ping_sync()

            if not result.get("success"):
                logger.warning(f"RealTimeX ping failed: {result}")
                _detection_cache = False
                return False

            # Log successful detection with mode info
            mode = result.get("mode", "unknown")
            logger.info(f"RealTimeX environment detected (app_id: {app_id}, mode: {mode})")
            _detection_cache = True
            return True

        except Exception as e:
            logger.warning(f"RealTimeX Main App not accessible: {e}")
            _detection_cache = False
            return False

    except Exception as e:
        logger.error(f"RealTimeX detection error: {e}")
        _detection_cache = False
        return False


# Cache for providers list
_providers_cache: Optional[dict] = None
_providers_cache_time: float = 0
PROVIDERS_CACHE_TTL = 300  # 5 minutes


async def get_cached_providers() -> dict:
    """
    Get available providers from RealTimeX SDK with backend caching.

    Returns:
        Dict with 'llm' and 'embedding' provider lists.
        Returns empty lists if SDK not enabled.
    """
    global _providers_cache, _providers_cache_time

    import time

    if not should_use_realtimex_sdk():
        return {"rtx_enabled": False, "llm": [], "embedding": []}

    # Check cache validity
    if _providers_cache and (time.time() - _providers_cache_time) < PROVIDERS_CACHE_TTL:
        return _providers_cache

    # Fetch fresh data from SDK
    try:
        sdk = get_realtimex_sdk()

        # Fetch both in parallel (conceptually, though await is sequential here)
        # In a real async environment we might use asyncio.gather, but sequential is safe
        llm_result = await sdk.llm.chat_providers()
        embed_result = await sdk.llm.embed_providers()

        def serialize_provider(p):
            return {
                "provider": p.provider,
                "models": [{"id": m.id, "name": m.name} for m in p.models],
            }

        _providers_cache = {
            "rtx_enabled": True,
            "llm": [serialize_provider(p) for p in llm_result.providers],
            "embedding": [serialize_provider(p) for p in embed_result.providers],
        }
        _providers_cache_time = time.time()

        return _providers_cache

    except Exception as e:
        logger.warning(f"Failed to fetch RTX providers: {e}")
        # Return empty but enabled structure on error to allow retry
        return {"rtx_enabled": True, "llm": [], "embedding": [], "error": str(e)}


def invalidate_providers_cache():
    """Invalidate the providers cache (e.g. on reconnection)."""
    global _providers_cache, _providers_cache_time
    _providers_cache = None
    _providers_cache_time = 0


# =============================================================================
# RTX Active Config Storage
# =============================================================================
# Stores the user's selected provider/model for LLM and Embedding when using RTX.
# This is persisted to disk so selections survive restarts.

import json
from pathlib import Path

# Storage path for RTX active config
_RTX_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "user" / "settings"
_RTX_CONFIG_FILE = _RTX_CONFIG_DIR / "rtx_active.json"


def _load_rtx_active_config() -> dict:
    """Load RTX active config from disk."""
    try:
        if _RTX_CONFIG_FILE.exists():
            with open(_RTX_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load RTX active config: {e}")
    return {}


def _save_rtx_active_config(config: dict) -> bool:
    """Save RTX active config to disk."""
    try:
        _RTX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_RTX_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save RTX active config: {e}")
        return False


def get_rtx_active_config(config_type: str) -> Optional[dict]:
    """
    Get the active RTX config for a specific config type.

    Args:
        config_type: "llm" or "embedding"

    Returns:
        Dict with provider, model, or None if not configured
    """
    if not should_use_realtimex_sdk():
        return None

    data = _load_rtx_active_config()
    return data.get(config_type)


def set_rtx_active_config(config_type: str, provider: str, model: str) -> bool:
    """
    Set the active RTX config for a specific config type.

    Args:
        config_type: "llm" or "embedding"
        provider: Provider name (e.g., "openai")
        model: Model ID (e.g., "gpt-4o")

    Returns:
        True if saved successfully
    """
    data = _load_rtx_active_config()
    data[config_type] = {
        "provider": provider,
        "model": model,
    }
    return _save_rtx_active_config(data)


def clear_rtx_active_config(config_type: str) -> bool:
    """
    Clear the active RTX config for a specific config type.

    Args:
        config_type: "llm" or "embedding"

    Returns:
        True if cleared successfully
    """
    data = _load_rtx_active_config()
    if config_type in data:
        del data[config_type]
        return _save_rtx_active_config(data)
    return True
