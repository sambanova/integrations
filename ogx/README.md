<a href="https://sambanova.ai/">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova OGX Integration

## Overview

OGX (formerly Llama Stack) is an open-source, OpenAI-compatible API server for building AI applications. It provides a standardized interface that works with any model and any infrastructure. OGX consists of two main components:

- Server – A running distribution that hosts inference providers and API adapters.
- Client – A consumer of the server's API, interacting with the hosted adapters.

> A provider is a pluggable component in OGX, such as an inference backend, a vector store, or a tool runtime. A distribution is a bundle of multiple providers deployed on the server, providing a unified interface for AI workflows.

SambaNova is included in the OGX starter distribution, which includes the following SambaNova provider:

- Inference:
    - remote::sambanova

For more details on OGX, refer to the official [documentation](https://ogx-ai.github.io/docs).

## Setting up the Environment

To get started, you need to create a virtual environment and install the OGX package.

1. Create a Virtual Environment

``` bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Dependencies

``` bash
pip install uv
uv pip install "ogx[starter]"
```

## Running the SambaNova Distribution

Before starting the server, set the required environment variables:

```bash
export OGX_PORT=8321
export SAMBANOVA_API_KEY="12345678abcdef87654321fe"  # Replace with your SambaNova Cloud API key
```

### Deploy with uv (Recommended)

```bash
uv run ogx run starter --port $OGX_PORT
```

### Deploy with Docker

To deploy using Docker, run:

```bash
docker run -it \
  -p $OGX_PORT:$OGX_PORT \
  -v ~/.ogx:/root/.ogx \
  -e SAMBANOVA_API_KEY=$SAMBANOVA_API_KEY \
  ogxai/distribution-starter \
  --port $OGX_PORT
```

### Build and deploy with Docker (custom image)

To build a custom image from the OGX repository, use `docker build` with the provided `Containerfile`:

```bash
# Clone the ogx repo first, then from its root:
docker build . \
  -f containers/Containerfile \
  --build-arg DISTRO_NAME=starter \
  --tag ogx:starter
```

Then run the custom image:

```bash
docker run -it \
  -p $OGX_PORT:$OGX_PORT \
  -v ~/.ogx:/root/.ogx \
  -e SAMBANOVA_API_KEY=$SAMBANOVA_API_KEY \
  ogx:starter \
  --port $OGX_PORT
```

## Usage

We provide a series of [notebooks](./notebooks/) that demonstrate how to use the SambaNova OGX distribution.

1. [Quickstart](./notebooks/01_Quickstart.ipynb)
    This notebook covers simple client usage, including:
    - List available models.
    - Use the inference adapter to interact with SambaNova cloud-based LLM chat models.
    - Implement a chat loop conversation using the SambaNova inference adapter.

2. [Image Chat](./notebooks/02_Image_Chat.ipynb)
    This notebook demonstrates how to use the inference adapter with SambaNova cloud-based vision models.

3. [Tool Calling](./notebooks/03_Tool_Calling.ipynb)
    This notebook demonstrates tool invocation using the inference adapter and tool runtime adapters with SambaNova cloud-based instruct models.

4. [RAG Agent](./notebooks/04_Rag_Agent.ipynb)
    This notebook provides an example of a simple Retrieval-Augmented Generation (RAG) agent using the inference adapter, Vector I/O adapters, inline embeddings, and the agent adapter.

5. [Safety](./notebooks/05_Safety.ipynb)
    This notebook shows how to evaluate user query safety and provide safeguards to the LLM response using the safety adapter.
