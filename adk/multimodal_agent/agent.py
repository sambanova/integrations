from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import load_brand_colors, load_user_preferences, save_html_file, get_current_time


snova_model = LiteLlm(model='sambanova/Llama-4-Maverick-17B-128E-Instruct')

root_agent = LlmAgent(
    name='root_agent',
    model=snova_model,
    description=(
        'A multimodal agent that helps users generate complete HTML+CSS+JS webpages from UI mockups. '
        'It can optionally use tools to enrich the design based on user preferences, brand styles, or context.'
    ),
    instruction=(
        'You are a helpful assistant that receives UI mockups or layout instructions and generates complete, '
        'single-file webpages (including HTML, CSS, and JavaScript). \n'
        'Use your image understanding and reasoning skills first.\n'
        'Call tools when the layout is passed to get relevant user preferences, brand colors, '
        'or component constraints that will meaningfully improve the result.\n'
        'If the image layout is not provided by the user request it before doing any code generation\n'
        'When providing a path or url make sure to use html format like: '
        '<a href="file_url" target="_blank">abs_path</a>. \n'
        'Never include code in the conversation or in the reasoning effort, '
        'CODE ALWAYS Must be passed ONLY when using the save_html_file tool'
    ),
    tools=[load_brand_colors, load_user_preferences, get_current_time, save_html_file],
)
