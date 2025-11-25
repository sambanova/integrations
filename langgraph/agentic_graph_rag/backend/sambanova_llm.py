"""
SambaNova LLM wrapper using official langchain-sambanova integration.
"""
import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel


def create_sambanova_llm(
    model: str = "Meta-Llama-3.3-70B-Instruct",
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """
    Create a SambaNova LLM instance using the official langchain-sambanova integration.

    Args:
        model: Model name (default: Meta-Llama-3.3-70B-Instruct)
        temperature: Temperature for generation (default: 0.0)
        api_key: SambaNova API key (defaults to SAMBANOVA_API_KEY env var)
        max_tokens: Maximum number of tokens to generate (optional)

    Returns:
        ChatSambaNova instance
    """
    try:
        from langchain_sambanova import ChatSambaNova
    except ImportError:
        raise ImportError(
            "langchain-sambanova is required for SambaNova models. "
            "Install it with: pip install langchain-sambanova"
        )

    # Base URL

    base_url = os.getenv("SAMBANOVA_API_BASE", default="https://api.sambanova.ai/v1") 
    
    # Get API key
    if api_key is None:
        api_key = os.getenv("SAMBANOVA_API_KEY")

    if not api_key:
        raise ValueError(
            "SAMBANOVA_API_KEY must be set in environment or passed as parameter"
        )

    # Build kwargs for ChatSambaNova
    kwargs = {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "temperature": temperature,        
        "timeout": 30,  # 30-second timeout for HTTP requests
        "max_retries": 2  # Retry up to 2 times on failure
    }

    # Add max_tokens if specified
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    # Special case for gpt-oss-120b: set reasoning_effort to "medium"
    if model == "gpt-oss-120b":
        kwargs["reasoning_effort"] = "medium"

    return ChatSambaNova(**kwargs)
