"""
RealTimeX LLM Provider
======================

Provides LLM capabilities through RealTimeX SDK proxy.
Used when running as a local app within RealTimeX desktop.

This provider maps DeepTutor's LLM API to the RealTimeX SDK's ChatMessage format
and handles error translation from SDK exceptions to DeepTutor exception hierarchy.
"""

from typing import TYPE_CHECKING, AsyncGenerator, Dict, List, Optional

from src.logging import get_logger
from src.utils.realtimex import get_realtimex_sdk

from .exceptions import LLMAPIError, LLMRateLimitError, RealTimeXError, RealTimeXPermissionError

if TYPE_CHECKING:
    from realtimex_sdk import ChatMessage

logger = get_logger("RealTimeXProvider")


def _build_messages(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    messages: Optional[List[Dict[str, str]]] = None,
) -> List["ChatMessage"]:
    """
    Build ChatMessage array from DeepTutor's API parameters.

    Args:
        prompt: User message
        system_prompt: System role instruction
        messages: Optional pre-built messages array

    Returns:
        List[ChatMessage]: Messages formatted for SDK
    """
    from realtimex_sdk import ChatMessage

    if messages:
        # Convert dict format to ChatMessage objects
        return [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
    else:
        # Build from prompt and system_prompt
        return [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=prompt),
        ]


def _map_sdk_error(e: Exception) -> Exception:
    """
    Map SDK exceptions to DeepTutor exception hierarchy.

    Args:
        e: SDK exception

    Returns:
        Exception: Mapped DeepTutor exception
    """
    try:
        from realtimex_sdk import LLMPermissionError, LLMProviderError

        if isinstance(e, LLMPermissionError):
            return RealTimeXPermissionError(
                permission=e.permission, message=f"RealTimeX permission required: {e.permission}"
            )

        if isinstance(e, LLMProviderError):
            if e.code == "RATE_LIMIT":
                return LLMRateLimitError(str(e), provider="realtimex")
            if e.code in ("LLM_STREAM_ERROR", "LLM_ERROR"):
                return RealTimeXError(str(e), error_code=e.code)

            # Generic provider error
            return RealTimeXError(str(e), error_code=e.code)

    except ImportError:
        pass

    # Fallback for unknown errors
    return LLMAPIError(f"RealTimeX SDK error: {str(e)}", provider="realtimex")


async def complete(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    messages: Optional[List[Dict[str, str]]] = None,
    response_format: Optional[Dict[str, str]] = None,
    **kwargs,
) -> str:
    """
    Complete request via RealTimeX SDK.

    Maps DeepTutor's API to SDK's ChatMessage format and handles error translation.

    Args:
        prompt: User message
        system_prompt: System role instruction (default: "You are a helpful assistant.")
        model: Optional model override
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        messages: Optional pre-built messages array
        response_format: Optional response format config (e.g., {"type": "json_object"})
        **kwargs: Additional parameters (ignored for now)

    Returns:
        str: Generated completion text

    Raises:
        RealTimeXPermissionError: If permission is required/denied
        RealTimeXError: If SDK request fails
        LLMRateLimitError: If rate limited
    """
    from realtimex_sdk import ChatOptions

    sdk = get_realtimex_sdk()

    # Build messages array
    chat_messages = _build_messages(prompt, system_prompt, messages)

    # Build options
    options = ChatOptions(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,  # Pass through to SDK
    )

    # Log request
    logger.debug(
        f"RealTimeX complete: model={model or 'default'}, "
        f"temp={temperature}, max_tokens={max_tokens}, "
        f"messages_count={len(chat_messages)}, "
        f"response_format={response_format}"
    )

    try:
        response = await sdk.llm.chat(chat_messages, options)

        if not response.success:
            logger.error(f"RealTimeX request failed: {response.error}")
            raise RealTimeXError(response.error or "SDK request failed", error_code=response.code)

        # Log response metadata
        logger.debug(
            f"RealTimeX response: success={response.success}, "
            f"provider={response.provider}, model={response.model}"
        )

        if response.metrics:
            logger.debug(
                f"Tokens: {response.metrics.total_tokens} "
                f"(prompt={response.metrics.prompt_tokens}, "
                f"completion={response.metrics.completion_tokens})"
            )

        return response.content or ""

    except Exception as e:
        # Map SDK errors to DeepTutor exceptions
        mapped_error = _map_sdk_error(e)
        logger.error(f"RealTimeX error: {mapped_error}")
        raise mapped_error


async def stream(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    messages: Optional[List[Dict[str, str]]] = None,
    response_format: Optional[Dict[str, str]] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Stream response via RealTimeX SDK.

    Args:
        prompt: User message
        system_prompt: System role instruction
        model: Optional model override
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        messages: Optional pre-built messages array
        response_format: Optional response format config
        **kwargs: Additional parameters (ignored)

    Yields:
        str: Text chunks as they arrive

    Raises:
        RealTimeXPermissionError: If permission is required/denied
        RealTimeXError: If SDK request fails
        LLMRateLimitError: If rate limited
    """
    from realtimex_sdk import ChatOptions

    sdk = get_realtimex_sdk()

    # Build messages array
    chat_messages = _build_messages(prompt, system_prompt, messages)

    # Build options
    options = ChatOptions(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,  # Pass through to SDK
    )

    # Log request
    logger.debug(
        f"RealTimeX stream: model={model or 'default'}, "
        f"temp={temperature}, max_tokens={max_tokens}, "
        f"messages_count={len(chat_messages)}, "
        f"response_format={response_format}"
    )

    try:
        async for chunk in sdk.llm.chat_stream(chat_messages, options):
            if chunk.error:
                logger.error("RealTimeX stream error detected")
                raise RealTimeXError("Stream error", error_code="LLM_STREAM_ERROR")

            if chunk.text:
                yield chunk.text

    except Exception as e:
        # Map SDK errors to DeepTutor exceptions
        mapped_error = _map_sdk_error(e)
        logger.error(f"RealTimeX stream error: {mapped_error}")
        raise mapped_error
