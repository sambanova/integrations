"""
Test script to verify the configured LLM provider and API key are working.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from llm_factory import create_llm, get_provider, get_main_agent_model


def test_provider():
    """Test the configured LLM provider with a simple prompt."""
    provider = get_provider()
    model = get_main_agent_model()

    print(f"Testing LLM provider...")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")

    try:
        llm = create_llm(model=model)
        response = llm.invoke("1+1=")
        answer = response.content.strip()
        print(f"✓ API key is valid. Response to '1+1=': {answer}")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease check:")
        print(f"1. PROVIDER is set correctly in .env (current: '{provider}')")
        if provider == "anthropic":
            print("2. ANTHROPIC_API_DEV_KEY is set to a valid key in .env")
        else:
            print("2. SAMBANOVA_API_KEY is set to a valid key in .env")
        return False


if __name__ == "__main__":
    success = test_provider()
    sys.exit(0 if success else 1)
