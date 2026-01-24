"""
RealTimeX SDK Status Router
============================

Provides status information about RealTimeX SDK connection and environment.
"""

from fastapi import APIRouter

from src.utils.realtimex import should_use_realtimex_sdk, get_realtimex_sdk

router = APIRouter()


@router.get("/realtimex/status")
async def get_realtimex_status():
    """
    Get RealTimeX SDK connection status.
    
    Returns:
        {
            "connected": bool,
            "mode": str | null,  # "development" or "production"
            "appId": str | null,
            "timestamp": str | null,
            "error": str | null
        }
    """
    try:
        # Check if RealTimeX is detected
        is_detected = should_use_realtimex_sdk()
        
        if not is_detected:
            return {
                "connected": False,
                "mode": None,
                "appId": None,
                "timestamp": None,
                "error": None
            }
        
        # Get SDK instance and ping (async)
        try:
            sdk = get_realtimex_sdk()
            # Use async ping() instead of ping_sync() to avoid event loop conflict
            ping_result = await sdk.ping()
            
            return {
                "connected": ping_result.get("success", False),
                "mode": ping_result.get("mode"),
                "appId": ping_result.get("appId"),
                "timestamp": ping_result.get("timestamp"),
                "error": None
            }
        except Exception as e:
            return {
                "connected": False,
                "mode": None,
                "appId": None,
                "timestamp": None,
                "error": str(e)
            }
    
    except Exception as e:
        return {
            "connected": False,
            "mode": None,
            "appId": None,
            "timestamp": None,
            "error": f"Detection failed: {str(e)}"
        }
