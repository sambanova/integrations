"""
LLM Factory - Creates LLM instances based on provider configuration.
Supports both Anthropic Claude and SambaNova models.
"""
import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langsmith.run_helpers import traceable


def create_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """
    Create an LLM instance based on provider configuration.

    Args:
        model: Model name. If not provided, uses default based on provider.
        temperature: Temperature for generation (default: 0.0)
        provider: Provider to use ('anthropic' or 'sambanova').
                 Defaults to PROVIDER env var or 'anthropic'.
        api_key: API key. If not provided, uses appropriate env var.
        max_tokens: Maximum number of tokens to generate (optional)

    Returns:
        BaseChatModel instance (either Anthropic or SambaNova)

    Raises:
        ValueError: If provider is invalid or API key is missing
    """
    # Determine provider
    if provider is None:
        provider = os.getenv("PROVIDER", "anthropic").lower()

    provider = provider.lower()

    if provider == "anthropic":
        return _create_anthropic_llm(model, temperature, api_key, max_tokens)
    elif provider == "sambanova":
        return _create_sambanova_llm(model, temperature, api_key, max_tokens)
    else:
        raise ValueError(f"Invalid provider: {provider}. Must be 'anthropic' or 'sambanova'")


def _create_anthropic_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """Create an Anthropic Claude LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required for Anthropic models. "
            "Install it with: pip install langchain-anthropic"
        )

    # Get API key - using ANTHROPIC_API_DEV_KEY to avoid Claude Code using it
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_DEV_KEY")

    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_DEV_KEY must be set in environment or passed as parameter"
        )

    # Use default model if not specified
    if model is None:
        model = "claude-sonnet-4-5-20250929"

    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
        "timeout": 30.0  # 30-second timeout for HTTP requests
    }

    # Add max_tokens if specified
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatAnthropic(**kwargs)


def _create_sambanova_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """Create a SambaNova LLM instance."""
    from sambanova_llm import create_sambanova_llm

    # Get API key
    if api_key is None:
        api_key = os.getenv("SAMBANOVA_API_KEY")

    if not api_key:
        raise ValueError(
            "SAMBANOVA_API_KEY must be set in environment or passed as parameter"
        )

    # Use default model if not specified
    if model is None:
        model = "DeepSeek-V3.1"

    return create_sambanova_llm(
        model=model,
        temperature=temperature,
        api_key=api_key,
        max_tokens=max_tokens
    )


def get_provider() -> str:
    """Get the configured provider from environment."""
    return os.getenv("PROVIDER", "anthropic").lower()


def get_model_for_role(role: str) -> str:
    """
    Get the configured model for a specific role based on the active provider.

    Args:
        role: The role name - one of 'MAIN_AGENT', 'VALIDATION', 'CYPHER_AGENT', or 'SYNTHESIS'

    Returns:
        Model name for the specified role

    Raises:
        ValueError: If role is invalid
    """
    valid_roles = ['MAIN_AGENT', 'VALIDATION', 'CYPHER_AGENT', 'SYNTHESIS']
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

    provider = get_provider()

    # Build env var name based on provider and role
    # e.g., ANTHROPIC_MAIN_AGENT_LLM or SAMBANOVA_VALIDATION_LLM
    env_var = f"{provider.upper()}_{role}_LLM"

    # Get default based on provider
    if provider == "anthropic":
        defaults = {
            "MAIN_AGENT": "claude-sonnet-4-5-20250929",
            "VALIDATION": "claude-haiku-4-5-20251001",  # Fast validation with Haiku
            "CYPHER_AGENT": "claude-sonnet-4-5-20250929",
            "SYNTHESIS": "claude-sonnet-4-5-20250929"
        }
    elif provider == "sambanova":
        defaults = {
            "MAIN_AGENT": "DeepSeek-V3.1",
            "VALIDATION": "DeepSeek-V3.1",
            "CYPHER_AGENT": "DeepSeek-V3.1",
            "SYNTHESIS": "DeepSeek-V3.1"
        }
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return os.getenv(env_var, defaults[role])


def get_main_agent_model() -> str:
    """Get the configured main agent model from environment."""
    return get_model_for_role("MAIN_AGENT")


def get_validation_model() -> str:
    """Get the configured validation model from environment."""
    return get_model_for_role("VALIDATION")


def get_cypher_agent_model() -> str:
    """Get the configured cypher agent model from environment."""
    return get_model_for_role("CYPHER_AGENT")


def get_synthesis_model() -> str:
    """Get the configured synthesis model from environment."""
    return get_model_for_role("SYNTHESIS")
