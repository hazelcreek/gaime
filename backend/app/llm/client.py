"""
LLM client - Provider-agnostic LLM integration using LiteLLM
"""

import os
import json
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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
        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        # Log error and re-raise
        print(f"LLM Error: {e}")
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


def parse_json_response(response: str | None) -> dict:
    """
    Parse a JSON response from the LLM.
    Handles markdown code blocks and other formatting.
    """
    import re
    
    # Handle None or empty response
    if response is None or not response.strip():
        raise ValueError("LLM returned empty response. Please try again.")
    
    # Remove markdown code blocks if present
    response = response.strip()
    
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]
    
    if response.endswith("```"):
        response = response[:-3]
    
    response = response.strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to extract just the narrative from truncated JSON
        # Match: "narrative": "..." (handles escaped quotes inside)
        narrative_match = re.search(r'"narrative"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', response)
        if narrative_match:
            narrative = narrative_match.group(1)
            # Unescape common JSON escapes
            narrative = narrative.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            return {
                "narrative": narrative,
                "state_changes": {},
                "hints": []
            }
        
        # Last resort: return response without JSON wrapper if it looks like raw JSON
        if response.startswith('{'):
            return {
                "narrative": "Something went wrong processing the response. Please try again.",
                "state_changes": {},
                "hints": []
            }
        
        # Return a default structure if parsing fails
        return {
            "narrative": response,
            "state_changes": {},
            "hints": []
        }

