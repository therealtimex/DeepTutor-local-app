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
