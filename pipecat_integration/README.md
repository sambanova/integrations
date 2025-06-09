<a href="https://sambanova.ai/">
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova Financial Agent using CrewAI (Financial Flow)
======================

Questions? Just <a href="https://discord.gg/54bNAqRw" target="_blank">message us</a> on Discord <a href="https://discord.gg/54bNAqRw" target="_blank"><img src="https://github.com/sambanova/ai-starter-kit/assets/150964187/aef53b52-1dc0-4cbf-a3be-55048675f583" alt="Discord" width="22"/></a> or <a href="https://github.com/sambanova/ai-starter-kit/issues/new/choose" target="_blank">create an issue</a> in GitHub. We're happy to help live!

Welcome to the the Pipecat @SambaNova integration!

Table of Contents:

- [1. Overview](#overview)
- [2. Setup](#setup)
- [3. Installation](#installation)

## 1. Overview
[Pipecat](https://www.pipecat.ai/) is a framework for building voice-enabled, real-time, multimodal AI applications.

Pipecat is an open source Python framework that handles the complex orchestration of AI services, network transport, audio processing, and multimodal interactions. “Multimodal” means you can use any combination of audio, video, images, and/or text in your interactions. And “real-time” means that things are happening quickly enough that it feels conversational—a “back-and-forth” with a bot, not submitting a query and waiting for results.

The flow of interactions in a Pipecat application is typically straightforward:

- The bot says something.
- The user says something.
- The bot says something.
- The user says something.

This continues until the conversation naturally ends. While this flow seems simple, making it feel natural requires sophisticated real-time processing.

For more details, please refer to the [Pipecat docs](https://docs.pipecat.ai/getting-started/overview).

## 2. Setup

1. LLM service and STT service.
    Add your `SAMBANOVA_API_KEY` to the `.env` file.

2. TTS service.
    You can choose between [Cartesia](https://cartesia.ai/) and [DeepGram](https://deepgram.com/) as your TTS provider.
    - For Cartesia, add your `CARTESIA_API_KEY` and your `CARTESIA_VOICE_ID` to the `.env` file.
    - For DeepGram, add your `DEEPGRAM_API_KEY` to the `.env` file.

3. Transport.
    xxx.
    
## 3. Installation

Ensure you have Python `>=3.11 <3.13` installed on your system.
All the packages/tools are listed in the `requirements.txt` file in the project root directory.

If you want to create a Python virtual environment with its built-in module `venv`
and then install the dependencies using `pip`,
follow the steps below.

1. Install and update `pip`.

```bash
cd integrations/financial_agent_crewai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the `main.py` file with transport option `webrtc`:

```bash
cd integrations/pipecat_integration
python main.py --transport webrtc
```

This command xxx.
https://docs.pipecat.ai/getting-started/quickstart

## 4. References
For more details, please refer to the [Sambanova @Pipecat docs](xxx).
