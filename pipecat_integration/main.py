#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

# General
import argparse
import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Pipecat
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

# If using Cartesia for TTS
from pipecat.services.cartesia.tts import CartesiaTTSService

# If using DeepGram for TTS
# from pipecat.services.deepgram.tts import DeepgramTTSService
# For function calling
from pipecat.services.llm_service import FunctionCallParams

# Transport
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketParams
from pipecat.transports.services.daily import DailyParams

# SambaNova LLM and STT
from pipecat.services.sambanova.llm import SambaNovaLLMService
from pipecat.services.sambanova.stt import SambaNovaSTTService

# Environment variables
load_dotenv(override=True)


# Define function to call
async def fetch_weather(params: FunctionCallParams) -> Any:
    """Mock function that fetches the weather forcast from an API."""

    await params.result_callback({'conditions': 'nice', 'temperature': '20 Degrees Celsius'})


# We store functions so objects (e.g. SileroVADAnalyzer) don't get instantiated.
# The function will be called when the desired transport gets selected.
transport_params = {
    'daily': lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
    ),
    'twilio': lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
    ),
    'webrtc': lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
    ),
}


async def run_example(transport: BaseTransport, _: argparse.Namespace, handle_sigint: bool) -> None:
    logger.info(f'Starting bot')

    # Speach-to-text service
    stt = SambaNovaSTTService(
        model='Whisper-Large-v3',
        api_key=os.getenv('SAMBANOVA_API_KEY'),
    )

    # Text-to-speech service
    tts = CartesiaTTSService(
        api_key=os.getenv('CARTESIA_API_KEY'),
        voice_id='71a7ad14-091c-4e8e-a314-022ece01c121',  # British Reading Lady
    )

    # Text-to-speech service (alternative)
    # tts = DeepgramTTSService(api_key=os.getenv('DEEPGRAM_API_KEY'), voice='aura-2-thalia-en', sample_rate=24000)

    # LLM service
    sambanova_api_key = os.getenv('SAMBANOVA_API_KEY')
    if isinstance(sambanova_api_key, str):
        llm = SambaNovaLLMService(
            api_key=sambanova_api_key,
            model='Llama-4-Maverick-17B-128E-Instruct',
            params=SambaNovaLLMService.InputParams(temperature=0.7, max_tokens=1024),
        )
    else:
        raise ValueError('SAMBANOVA_API_KEY is not defined.')

    # You can also register a function_name of None to get all functions
    # sent to the same callback with an additional function_name parameter
    llm.register_function('get_current_weather', fetch_weather)

    @llm.event_handler('on_function_calls_started')  # type: ignore
    async def on_function_calls_started(service, function_calls):  # noqa
        await tts.queue_frame(TTSSpeakFrame('Let me check on that.'))

    # Define weather function using standardized schema
    weather_function = FunctionSchema(
        name='get_current_weather',
        description='Get the current weather',
        properties={
            'location': {
                'type': 'string',
                'description': 'The city and state.',
            },
            'format': {
                'type': 'string',
                'enum': ['celsius', 'fahrenheit'],
                'description': "The temperature unit to use. Infer this from the user's location.",
            },
        },
        required=['location', 'format'],
    )

    # Create tools schema
    tools = ToolsSchema(standard_tools=[weather_function])

    # Define system message
    messages = [
        {
            'role': 'system',
            'content': (
                'You are a helpful Large Language Model assistant participating in a WebRTC call. '
                'You are an expert in meteorology and weather forecasting. '
                'Your goal is to demonstrate your weather forecasting capabilities in a succinct and clear manner. '
                'Please introduce yourself to the user shortly, and invite them '
                'to ask about the weather in any city and country, '
                'as well as their preferred temperature unit, Celsius or Fahrenheit. '
                'Then wait for their question. '
                'When responding, elaborate in a conversational, creative, and helpful way. '
                'Your output will be converted to audio, so do not include any special characters in your answers. '
                'Once you have given your final answer, please stop unless the user asks another question.'
            ),
        },
    ]
    # Create context with system message and tools
    context = OpenAILLMContext(messages, tools)

    # Context aggregator
    context_aggregator = llm.create_context_aggregator(context)

    # Set up pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # Create and configure task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler('on_client_connected')  # type: ignore
    async def on_client_connected(transport, client):  # noqa
        logger.info(f'Client connected')
        # Kick off the conversation.
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler('on_client_disconnected')  # type: ignore
    async def on_client_disconnected(transport, client):  # noqa
        logger.info(f'Client disconnected')
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint)

    await runner.run(task)


if __name__ == '__main__':
    from pipecat.examples.run import main

    main(run_example, transport_params=transport_params)
