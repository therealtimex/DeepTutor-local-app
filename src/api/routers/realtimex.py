"""
RealTimeX SDK Status Router
============================

Provides status information about RealTimeX SDK connection and environment.
"""

from fastapi import APIRouter

from src.utils.realtimex import get_realtimex_sdk, should_use_realtimex_sdk

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
                "error": None,
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
                "error": None,
            }
        except Exception as e:
            return {
                "connected": False,
                "mode": None,
                "appId": None,
                "timestamp": None,
                "error": str(e),
            }

    except Exception as e:
        return {
            "connected": False,
            "mode": None,
            "appId": None,
            "timestamp": None,
            "error": f"Detection failed: {str(e)}",
        }


@router.get("/realtimex/providers")
async def get_providers():
    """
    Get available providers from RealTimeX SDK.
    Returns empty lists if SDK not enabled, allowing frontend to use defaults.
    """
    from src.utils.realtimex import get_cached_providers

    return await get_cached_providers()


from pydantic import BaseModel


class RTXConfigApplyRequest(BaseModel):
    config_type: str  # "llm" or "embedding"
    provider: str
    model: str


@router.post("/realtimex/config/apply")
async def apply_rtx_config(request: RTXConfigApplyRequest):
    """
    Apply RTX provider selection.
    Creates/updates a special 'realtimex' config entry that signals
    the LLM service to route through SDK instead of direct API calls.
    """
    from fastapi import HTTPException

    from src.services.config.unified_config import ConfigType, get_config_manager
    from src.utils.realtimex import should_use_realtimex_sdk

    if not should_use_realtimex_sdk():
        raise HTTPException(400, "RealTimeX SDK not available")

    try:
        # Validate config type
        config_type_enum = None
        if request.config_type == "llm":
            config_type_enum = ConfigType.LLM
        elif request.config_type == "embedding":
            config_type_enum = ConfigType.EMBEDDING
        else:
            raise HTTPException(400, f"Invalid config type: {request.config_type}")

        # Store as special RTX config - the LLM service knows to use SDK
        manager = get_config_manager()
        rtx_config = {
            "id": f"rtx_{request.config_type}",
            "name": f"RealTimeX ({request.provider})",
            "provider": request.provider,
            "model": request.model,
            "source": "realtimex",  # Flag for LLM service
            "is_active": True,
        }

        # Save as active config
        manager.save_config(config_type_enum, rtx_config)
        manager.set_active_config(config_type_enum, rtx_config["id"])

        return {"success": True, "active": rtx_config}

    except Exception as e:
        raise HTTPException(500, f"Failed to apply configuration: {str(e)}")
