<a href="https://sambanova.ai/">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova Llama Stack Integration

## Overview

Llama Stack is a framework that standardizes core building blocks to simplify AI application development. It integrates best practices across the Llama ecosystem, making it easier to build and deploy AI solutions efficiently. Llama Stack consists of two main components:

- Server – A running distribution of Llama Stack that hosts various adaptors.
- Client – A consumer of the server's API, interacting with the hosted adaptors.

> An adaptor is a provider component in Llama Stack, such as an inference model, a safety guardrails model, or an agent. A distribution is a bundle of multiple adaptors deployed on the server, providing a unified interface for AI workflows.

SambaNova is included in Llama-stack Starter distribution, which includes the following sambanova adaptors:

- Inference:
    - remote::sambanova
- Safety:
    - remote::sambanova

For more details on Llama Stack, refer to the official [documentation](https://llama-stack.readthedocs.io/en/latest/index.html).

## Setting up the Environment

To get started, you need to create a virtual environment and install the base Llama Stack framework. This will allow you to build the distribution template and integrate SambaNova's adaptors.

1. Create a Virtual Environment
Run the following commands to set up a virtual environment:

``` bash
    python -m venv .venv
    source .venv/bin/activate
```

2. Install Dependencies
Once the environment is activated, install the necessary packages:

``` bash
    pip install uv
    pip install llama-stack
```

## Building the SambaNova Distribution

After the environment is set, you can build the distribution.

Create the Llama Stack Directory

```bash
mkdir -p ~/.llama
```

You can build the SambaNova Llama Stack distribution using either a virtual environment (**venv**), a conda environmnet, or a Docker image.  

### Build with Docker (Recommended)

You can skip this step if you want to use the default starter docker images

If you want to  re-build the distribution as a Docker container, use the following command:  

```bash
llama stack build --template starter --image-type container  
```

After the build process is complete, verify that the image was created by listing available Docker images:  

```bash
docker image list
```

Example Output:

``` bash
REPOSITORY                        TAG       IMAGE ID       CREATED          SIZE
distribution-starter            0.2.14     4f70c8f71a21   5 minutes ago    2.4GB
```

### Build with venv

To build the distribution within the currently activated virtual environment, run:

```bash
llama stack build --template starter --image-type venv
```

### Build with conda

To build the distribution in a conda environment, run:

``` bash
llama stack build --template starter --image-type conda
```

## Running the SambaNova Distribution

After the distribution has been built, the Llama Stack server can be deployed.

Before deploying the distribution, set the required environment variables:

```bash
export LLAMA_STACK_PORT=8321
export ENABLE_SAMBANOVA=sambanova
export SAMBANOVA_API_KEY="12345678abcdef87654321fe"  # Replace with your SambaNova Cloud API key
```

### Deploy with Docker  (Recommended)

To deploy using Docker, run:

```bash
docker run -it \
  -p $LLAMA_STACK_PORT:$LLAMA_STACK_PORT \
  -v ~/.llama:/root/.llama \
  llamastack/distribution-starter \ # optionally change this to match the tag of your built image
  --port $LLAMA_STACK_PORT \
  --env SAMBANOVA_API_KEY=$SAMBANOVA_API_KEY
```

### Deploy with venv

Run the following command to start the distribution using a virtual environment:

``` bash
llama stack run --image-type venv ~/.llama/distributions/starter/starter-run.yaml \
    --port $LLAMA_STACK_PORT \
    --env SAMBANOVA_API_KEY=$SAMBANOVA_API_KEY
```

### Deploy with Conda

For Conda-based deployment, use:

```bash
llama stack run --image-type conda ~/.llama/distributions/starter/starter-run.yaml \
    --port $LLAMA_STACK_PORT \
    --env SAMBANOVA_API_KEY=$SAMBANOVA_API_KEY
```

## Usage:

We provide a series of [notebooks](./notebooks/) that demonstrate how to use the SambaNova Llama Stack distribution.

1. [Quickstart](./notebooks/01_Quickstart.ipynb)
    This notebook covers a simple client usage, including the following points:
    - List available models.
    - Use the inference adaptor to interact with the Sambanova cloud-based LLM chat models.
    - Implement a chat loop conversation using the SambaNova inference adaptor.

2. [Image Chat](./notebooks/02_Image_Chat.ipynb)
    This notebook demonstrates how to use the inference adaptor to interact with the SambaNova cloud-based vision models.

3. [Tool Calling](./notebooks/03_Tool_Calling.ipynb)
    This notebook demonstrates tool invocation using the inference adaptor and the tool runtime adaptors with the SambaNova cloud-based instruct models.

4. [RAG Agent](./notebooks/04_Rag_Agent.ipynb)
    This notebook provides an example of a simple Retrieval-Augmented Generation (RAG) agent using the inference adaptor, Vector I/O adaptors, inline embeddings, and the agent adaptor.

5. [Safety](./notebooks/05_Safety.ipynb)
    This notebooks shows how to evaluate the safety of the user query and how to provide safeguards to the LLM response using the safety adaptor.
