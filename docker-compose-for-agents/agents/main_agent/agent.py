import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .sub_agents import coder_agent

root_agent = Agent(
    model=LiteLlm(
        model=f"sambanova/{os.environ.get('SAMBANOVA_CHAT_MODEL')}",
        api_base=os.environ.get("SAMBANOVA_BASE_URL"),
        api_key=os.environ.get("SAMBANOVA_API_KEY"),
        temperature=0.0,
    ),
    name=os.environ.get("SAMBANOVA_AGENT_NAME"),
    description=os.environ.get("SAMBANOVA_AGENT_DESCRIPTION"),
    instruction=os.environ.get("SAMBANOVA_AGENT_INSTRUCTION"),
    sub_agents=[coder_agent],
)
