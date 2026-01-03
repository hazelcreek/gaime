"""
LLM client - Provider-agnostic LLM integration using LiteLLM
"""

import os
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


@dataclass
class LLMCompletionResult:
    """Result from an LLM completion call with performance metrics."""

    content: str
    duration_ms: float
    tokens_input: int | None
    tokens_output: int | None
    tokens_total: int | None


# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


def get_provider() -> str:
    """Get configured LLM provider"""
    return os.getenv("LLM_PROVIDER", "gemini")


def get_model() -> str:
    """Get configured model name"""
    return os.getenv("LLM_MODEL", "gemini-3-pro-preview")


def get_model_string() -> str:
    """Get the full model string for LiteLLM"""
    provider = get_provider()
    model = get_model()

    # LiteLLM uses prefixed model names for some providers
    if provider == "gemini":
        return f"gemini/{model}"
    elif provider == "anthropic":
        return f"anthropic/{model}"
    elif provider == "ollama":
        return f"ollama/{model}"
    else:
        # OpenAI doesn't need a prefix
        return model


async def get_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: dict | None = None,
) -> LLMCompletionResult:
    """
    Get completion from configured LLM provider.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model override
        temperature: Creativity (0-1)
        max_tokens: Maximum response length
        response_format: Optional format specification

    Returns:
        LLMCompletionResult with content and performance metrics
    """
    import litellm

    # Configure API keys from environment
    _configure_api_keys()

    model_string = model or get_model_string()

    logger.info(
        f"LLM Request: model={model_string}, temperature={temperature}, max_tokens={max_tokens}"
    )
    logger.debug(
        f"Messages: {len(messages)} messages, response_format={response_format}"
    )

    # Build completion kwargs
    kwargs: dict[str, Any] = {
        "model": model_string,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Add response format if specified and supported
    # Note: Not all models support JSON mode
    if response_format:
        kwargs["response_format"] = response_format

    try:
        logger.info("Calling LiteLLM...")
        start_time = time.perf_counter()
        response = await litellm.acompletion(**kwargs)
        duration_ms = (time.perf_counter() - start_time) * 1000

        content = response.choices[0].message.content
        finish_reason = (
            response.choices[0].finish_reason
            if hasattr(response.choices[0], "finish_reason")
            else "unknown"
        )

        # Extract token usage if available
        tokens_input = None
        tokens_output = None
        tokens_total = None
        if hasattr(response, "usage") and response.usage:
            tokens_input = getattr(response.usage, "prompt_tokens", None)
            tokens_output = getattr(response.usage, "completion_tokens", None)
            tokens_total = getattr(response.usage, "total_tokens", None)

        logger.info(
            f"LLM Response: finish_reason={finish_reason}, "
            f"content_length={len(content) if content else 0}, "
            f"duration={duration_ms:.0f}ms, "
            f"tokens={tokens_input}/{tokens_output}/{tokens_total}"
        )

        if finish_reason == "length":
            logger.warning(
                f"Response TRUNCATED due to max_tokens limit ({max_tokens}). Consider increasing max_tokens."
            )

        if not content:
            logger.warning(f"LLM returned empty content. Full response: {response}")
        else:
            # Log first 200 chars of response for debugging
            preview = content[:200] + "..." if len(content) > 200 else content
            logger.debug(f"Response preview: {preview}")

        return LLMCompletionResult(
            content=content or "",
            duration_ms=duration_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
        )
    except Exception as e:
        logger.error(f"LLM Error: {type(e).__name__}: {e}")
        raise


def _configure_api_keys():
    """Configure API keys for LiteLLM from environment"""
    import litellm

    provider = get_provider()
    logger.debug(f"Configuring API keys for provider: {provider}")

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            logger.debug(f"GEMINI_API_KEY configured (length: {len(api_key)})")
        else:
            logger.warning("GEMINI_API_KEY not found in environment")

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            litellm.api_key = api_key
            logger.debug(f"OPENAI_API_KEY configured (length: {len(api_key)})")
        else:
            logger.warning("OPENAI_API_KEY not found in environment")

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            logger.debug(f"ANTHROPIC_API_KEY configured (length: {len(api_key)})")
        else:
            logger.warning("ANTHROPIC_API_KEY not found in environment")

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = base_url
        logger.debug(f"OLLAMA_API_BASE configured: {base_url}")


def parse_json_response(response: str | None, strict: bool = False) -> dict:
    """
    Parse a JSON response from the LLM.
    Handles markdown code blocks and other formatting.

    Args:
        response: The raw LLM response string
        strict: If True, raises ValueError on parse failure instead of
                falling back to game-master defaults. Use for world builder.
    """
    import re

    # Handle None or empty response
    if response is None or not response.strip():
        raise ValueError("LLM returned empty response. Please try again.")

    # Remove markdown code blocks if present
    cleaned = response.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # In strict mode, don't fall back to game-master defaults
        if strict:
            # Include a snippet of the response for debugging
            snippet = cleaned[:200] + "..." if len(cleaned) > 200 else cleaned
            raise ValueError(
                f"Failed to parse JSON from LLM response. "
                f"The AI may have returned malformed or truncated output. "
                f"Response preview: {snippet}"
            )

        # Try to extract just the narrative from truncated JSON
        # Match: "narrative": "..." (handles escaped quotes inside)
        narrative_match = re.search(
            r'"narrative"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', cleaned
        )
        if narrative_match:
            narrative = narrative_match.group(1)
            # Unescape common JSON escapes
            narrative = (
                narrative.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            )
            return {"narrative": narrative, "state_changes": {}, "hints": []}

        # Last resort: return response without JSON wrapper if it looks like raw JSON
        if cleaned.startswith("{"):
            return {
                "narrative": "Something went wrong processing the response. Please try again.",
                "state_changes": {},
                "hints": [],
            }

        # Return a default structure if parsing fails
        return {"narrative": cleaned, "state_changes": {}, "hints": []}
