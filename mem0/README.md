<a href="https://sambanova.ai/">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova Mem0 Integration

## Overview

[**Mem0**](https://docs.mem0.ai/introduction) is the memory engine that keeps conversations contextual so users never repeat themselves and your agents respond with continuity. Mem0 delivers adaptive memory engine, packaged for teams that need to run everything on their own infrastructure. You own the stack, the data, and the customizations.

## Setting up the Environment

To get started, create a virtual environment and install the required dependencies, including the Mem0 library and SambaNova model integration.

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

## Running the Mem0 script

This integration enables LLM to access persistent memory across conversations, enhancing context retention and personalization.
Run the example script with

``` bash
    python main.py
```