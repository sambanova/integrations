import os
import pandas as pd
from typing import Any, Iterator, Union, Dict, List
from sambanova import SambaNova
from sambanova.types.chat import ChatCompletionResponse, ChatCompletionStreamResponse

CompletionCreateParams = Dict[str, Any]

def get_config():
    # Get configuration from runtime parameters or environment variables
    try:
        # Try DataRobot runtime parameters first
        from datarobot_drum import RuntimeParameters
        return {
            "api_key": RuntimeParameters.get("SAMBANOVA_API_KEY")["apiToken"],
            "api_base": RuntimeParameters.get("SAMBANOVA_API_BASE"),
            "model":  RuntimeParameters.get("SAMBANOVA_MODEL"),
        }
    except Exception:
        # Fallback to environment variables for codespace testing
        return {
            "api_key": os.environ.get("SAMBANOVA_API_KEY", ""),
            "api_base": os.environ.get("SAMBANOVA_API_BASE", "https://api.sambanova.ai/v1"),
            "model":  os.environ.get("SAMBANOVA_MODEL", "gpt-oss-120b"),
        }


# Implement the load_model hook.
def load_model(*args, **kwargs):
    config = get_config()
    return SambaNova(
        api_key=config["api_key"],
        base_url=config["api_base"],
    )


# Load the SambaNova client
def load_client(*args, **kwargs):
    return load_model(*args, **kwargs)


# Get supported LLM models
def get_supported_llm_models(model: SambaNova) -> List[Dict[str, Any]]:
    sambanova_models = model.models.list()
    model_ids = [m.id for m in sambanova_models]
    return model_ids


# On-demand chat requests
def chat(completion_create_params: CompletionCreateParams, model: SambaNova) \
        -> Union[ChatCompletionResponse, Iterator[ChatCompletionStreamResponse], Dict]:
    """
    DataRobot chat() hook.
    completion_create_params: dict-like object with OpenAI-style parameters
    model: SambaNova client returned by load_model()
    """
    try:
        # Default model if not supplied by the Playground
        if "model" not in completion_create_params:
            completion_create_params["model"] = get_config()["model"]

        # Forward the request to SambaNova Cloud
        return model.chat.completions.create(**completion_create_params)

    except Exception as e:
        # Return a minimal ChatCompletion-like object so the Playground doesn't crash
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"Error: {e.__class__.__name__}: {e}"
                    }
                }
            ]
        }


# Batch chat requests
PROMPT_COLUMN_NAME = "promptText"
COMPLETION_COLUMN_NAME = "resultText"
ERROR_COLUMN_NAME = "error"


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []
    errors = []

    for prompt in prompts:
        try:
            # Get model config
            config = get_config()

            # Attempt to get a completion from the client
            response = model.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": f"{prompt}"},],
                max_tokens=20,
                temperature=0
            )
            # On success, append the content and a null error
            responses.append(response.choices[0].message.content or "")
            errors.append("")
        except Exception as e:
            # On failure, format the error message
            error = f"{e.__class__.__name__}: {str(e)}"
            responses.append("")
            errors.append(error)

    return pd.DataFrame({
        PROMPT_COLUMN_NAME: prompts,
        COMPLETION_COLUMN_NAME: responses,
        ERROR_COLUMN_NAME: errors
    })