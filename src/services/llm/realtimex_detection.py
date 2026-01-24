"""
RealTimeX Environment Detection
================================

Detects if the application is running within the RealTimeX desktop environment.
Used to conditionally enable RealTimeX SDK integration.

Detection criteria:
1. RTX_APP_ID environment variable is set
2. RealTimeX SDK is installed
3. RealTimeX Main App is accessible (localhost:3001)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache detection result for performance
_detection_cache: Optional[bool] = None


def should_use_realtimex_sdk(force_check: bool = False) -> bool:
    """
    Detect RealTimeX environment with caching.
    
    Args:
        force_check: Force re-check even if cached
    
    Returns:
        True if all RealTimeX conditions are met
    """
    global _detection_cache
    
    if _detection_cache is not None and not force_check:
        return _detection_cache
    
    try:
        # Check 1: RTX_APP_ID
        app_id = os.getenv("RTX_APP_ID")
        if not app_id:
            logger.debug("RealTimeX not detected: RTX_APP_ID not set")
            _detection_cache = False
            return False
        
        # Check 2: SDK installed
        try:
            import realtimex_sdk
        except ImportError:
            logger.warning(
                "RealTimeX detected (RTX_APP_ID present) but SDK not installed. "
                "Install with: pip install realtimex-sdk"
            )
            _detection_cache = False
            return False
        
        # Check 3: Main App connectivity (with timeout)
        try:
            import httpx
            response = httpx.get("http://localhost:3001/health", timeout=2.0)
            if response.status_code != 200:
                logger.warning(
                    f"RealTimeX Main App unhealthy: status={response.status_code}"
                )
                _detection_cache = False
                return False
        except Exception as e:
            logger.warning(f"Cannot reach RealTimeX Main App: {e}")
            _detection_cache = False
            return False
        
        logger.info(f"RealTimeX environment detected (app_id: {app_id})")
        _detection_cache = True
        return True
    
    except Exception as e:
        logger.error(f"RealTimeX detection error: {e}")
        _detection_cache = False
        return False


def clear_detection_cache():
    """Clear cached detection result. Useful for testing."""
    global _detection_cache
    _detection_cache = None
