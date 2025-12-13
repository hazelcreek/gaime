"""
LLM client - Provider-agnostic LLM integration using LiteLLM

Copied and adapted from backend/app/llm/client.py for TUI independence.
"""

import os
import json
import re
import logging
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


def get_provider() -> str:
    """Get configured LLM provider"""
    return os.getenv("LLM_PROVIDER", "gemini")


def get_model() -> str:
    """Get configured model name for the builder.
    
    Uses BUILDER_LLM_MODEL if set, otherwise falls back to LLM_MODEL.
    This allows using a different model for world building vs gameplay.
    """
    # Reload .env to pick up any changes
    load_dotenv(override=True)
    
    builder_model = os.getenv("BUILDER_LLM_MODEL")
    llm_model = os.getenv("LLM_MODEL")
    default_model = "gemini-2.5-pro-preview-05-06"
    
    model = builder_model or llm_model or default_model
    
    logger.debug(f"Model selection: BUILDER_LLM_MODEL={builder_model}, LLM_MODEL={llm_model}, using={model}")
    
    return model


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
    response_format: dict | None = None
) -> str:
    """
    Get completion from configured LLM provider.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model override
        temperature: Creativity (0-1)
        max_tokens: Maximum response length
        response_format: Optional format specification
    
    Returns:
        The generated text response
    """
    import litellm
    
    # Configure API keys from environment
    _configure_api_keys()
    
    model_string = model or get_model_string()
    
    logger.info(f"LLM Request: model={model_string}, temperature={temperature}, max_tokens={max_tokens}")
    
    # Build completion kwargs
    kwargs: dict[str, Any] = {
        "model": model_string,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    # Add response format if specified and supported
    if response_format:
        kwargs["response_format"] = response_format
    
    try:
        logger.debug(f"Sending request to LiteLLM...")
        response = await litellm.acompletion(**kwargs)
        
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else 'unknown'
        
        # Log usage if available
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            logger.info(f"LLM Usage: prompt_tokens={getattr(usage, 'prompt_tokens', 'N/A')}, "
                       f"completion_tokens={getattr(usage, 'completion_tokens', 'N/A')}, "
                       f"total_tokens={getattr(usage, 'total_tokens', 'N/A')}")
        
        logger.info(f"LLM Response: finish_reason={finish_reason}, content_length={len(content) if content else 0}")
        
        if finish_reason == "length":
            logger.warning(f"Response TRUNCATED due to max_tokens limit ({max_tokens}).")
        
        return content
    except Exception as e:
        logger.error(f"LLM Error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"LLM Traceback:\n{traceback.format_exc()}")
        raise


def _configure_api_keys():
    """Configure API keys for LiteLLM from environment"""
    import litellm
    
    provider = get_provider()
    
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            litellm.api_key = api_key
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
    
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = base_url


def parse_json_response(response: str | None, strict: bool = False) -> dict:
    """
    Parse a JSON response from the LLM.
    Handles markdown code blocks and other formatting.
    
    Args:
        response: The raw LLM response string
        strict: If True, raises ValueError on parse failure
    """
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
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parse failed: {e}")
        
        # Try to fix common double-escaping issues from LLMs
        # LLMs sometimes output \\" when they should output \"
        try:
            # Replace \\" with \" (fixing double-escaped quotes)
            fixed = cleaned.replace('\\\\"', '\\"')
            # Replace \\n with \n inside string values (fixing double-escaped newlines)
            # Be careful not to break actual escaped backslashes
            result = json.loads(fixed)
            logger.info("JSON parse succeeded after fixing double-escaping")
            return result
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                # Try the double-escape fix on the extracted JSON too
                try:
                    fixed = json_match.group().replace('\\\\"', '\\"')
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        
        if strict:
            snippet = cleaned[:200] + "..." if len(cleaned) > 200 else cleaned
            raise ValueError(
                f"Failed to parse JSON from LLM response. "
                f"Response preview: {snippet}"
            )
        
        # Fallback
        return {
            "narrative": cleaned,
            "state_changes": {},
            "hints": []
        }

