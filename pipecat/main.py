from llm import SambaNovaLLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from dotenv import load_dotenv
import os
from pipecat.pipeline.pipeline import Pipeline
from pipecat.transports.base_transport import Tra

load_dotenv()

# Configure service
service = SambaNovaLLMService(
    api_key=os.getenv('SAMBANOVA_API_KEY'),
    model='Meta-Llama-3.3-70B-Instruct',
    params=SambaNovaLLMService.InputParams(temperature=0.7, max_tokens=1024),
)

# Create context
context = OpenAILLMContext(
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant'},
        {'role': 'user', 'content': 'What is machine learning?'},
    ],
    tools=[],
)

# Use in pipeline
pipeline = Pipeline(
    [
        transport.input(),
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ]
)


def main() -> None:
    pass


if __name__ == '__main__':
    main()
