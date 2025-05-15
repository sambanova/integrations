#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#


from typing import List, Dict, Any, Optional

from loguru import logger  # type: ignore
from openai.types.chat import ChatCompletionMessageParam

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext  # type: ignore
from pipecat.services.openai.llm import OpenAILLMService  # type: ignore


class SambaNovaLLMService(OpenAILLMService):  # type: ignore
    """A service for interacting with SambaNova using the OpenAI-compatible interface.

    This service extends OpenAILLMService to connect to SambaNova' API endpoint while
    maintaining full compatibility with OpenAI's interface and functionality.

    Args:
        api_key (str): The API key for accessing SambaNova AI
        model (str, optional): The model identifier to use. Defaults to "Meta-Llama-3.3-70B-Instruct"
        base_url (str, optional): The base URL for SambaNova API. Defaults to "https://api.sambanova.ai/v1"
        **kwargs: Additional keyword arguments passed to OpenAILLMService
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = 'Meta-Llama-3.3-70B-Instruct',
        base_url: str = 'https://api.sambanova.ai/v1',
        **kwargs: Dict[Any, Any],
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model, **kwargs)

    def create_client(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs: Dict[Any, Any]):
        """Create OpenAI-compatible client for SambaNova API endpoint."""
        logger.debug(f'Creating SambaNova client with api {base_url}')
        return super().create_client(api_key, base_url, **kwargs)

    async def get_chat_completions(self, context: OpenAILLMContext, messages: List[ChatCompletionMessageParam]):
        """Get chat completions from SambaNova API.

        Removes OpenAI-specific parameters not supported by SambaNova.
        """
        params = {
            'model': self.model_name,
            'stream': True,
            'messages': messages,
            'tools': context.tools,
            'tool_choice': context.tool_choice,
            'frequency_penalty': self._settings['frequency_penalty'],
            'presence_penalty': self._settings['presence_penalty'],
            'temperature': self._settings['temperature'],
            'top_p': self._settings['top_p'],
            'max_tokens': self._settings['max_tokens'],
        }

        params.update(self._settings['extra'])

        chunks = await self._client.chat.completions.create(**params)
        return chunks
