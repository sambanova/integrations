<a href="https://sambanova.ai/">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova Composio Integration

## Overview

[**Composio**](https://docs.composio.dev/docs/welcome) Composio is a developer-oriented integration platform for AI agents and large language model (LLM) applications. It acts as a bridge between AI systems and real-world tools/services (like Slack, GitHub, Gmail, CRMs, web search and productivity apps, etc.), so those agents can authentically interact and take action across apps without you building every integration yourself.

## Setting up the Environment

To get started, create a virtual environment and install the required dependencies, including the Composio library and SambaNova model integration.

1. Create a Virtual Environment
Run the following commands to set up a virtual environment:

> Use python 3.9 or higher

``` bash
    python -m venv .venv
    source .venv/bin/activate
```

2. Install Dependencies
Once the environment is activated, install the necessary packages:

``` bash
    pip install -r requirements.txt
```

3. Set your SambaCloud API Key
Generate your SambaCloud API key [here](https://cloud.sambanova.ai/apis) and set it in the [`./.env`](./.env) 

``` bash
    SAMBANOVA_API_KEY=<Your SAMBANOVA api key>
```

## Running the Composio script

This integration enables LLM to access web search tool.
Run the example script with

``` bash
    python main.py
```

## Customization
For more example refer to the [official Composio documentation](https://docs.composio.dev/docs/).