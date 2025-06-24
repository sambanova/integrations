<a href="https://sambanova.ai/">
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="../../images/SambaNova-light-logo-1.png" height="60">
  <img alt="SambaNova logo" src="../../images/SambaNova-dark-logo-1.png" height="60">
</picture>
</a>

# SambaNova Financial Crews using CrewAI

Questions? Just <a href="https://discord.gg/54bNAqRw" target="_blank">message us</a> on Discord <a href="https://discord.gg/54bNAqRw" target="_blank"><img src="https://github.com/sambanova/ai-starter-kit/assets/150964187/aef53b52-1dc0-4cbf-a3be-55048675f583" alt="Discord" width="22"/></a> or <a href="https://github.com/sambanova/ai-starter-kit/issues/new/choose" target="_blank">create an issue</a> in GitHub. We're happy to help live!

Welcome to the Finance Crews project, powered by [crewAI](https://crewai.com)!

Table of Contents:

- [1. Overview](#overview)
- [2. Setup](#setup)
- [3. Installation](#installation)
- [4. The Streamlit app](#streamlit)
- [5. Understanding and monitoring your crews](#5-understanding-and-monitoring-your-crews)
  - [5.1 The RAG Crew](#51-the-rag-crew)
  - [5.2 The Web Search Crew](#52-the-web-search-crew)
  - [5.3 Monitoring your crews with Weave](#53-monitoring-your-crews-with-weave)

## 1. Overview

The Finance Crews project includes two simple templates designed to facilitate the setup of a multi-agent AI system,
leveraging the robust and adaptable framework offered by crewAI.

This project demonstrates the capabilities of Large Language Models (LLMs)
in extracting and analyzing financial information using web scraping
and Retrieval Augmented Generation (RAG).

## 2. Setup of the `.env` file

1. You need to set the environment variable `SAMBANOVA_API_KEY`: your API key for accessing the SambaNova Cloud.
You can create your API key [here](https://cloud.sambanova.ai/apis).

2. Add your `SERPER_API_KEY` after signing up at https://serper.dev/ for a free account.

3. (Optional) In order to monitor your LLM, you can create a Weights & Biases (W&B) account at https://wandb.ai and copy your `WANDB_API_KEY` key from https://wandb.ai/authorize. This must be set if `wandb login` has not been run on your machine.
    
## 3. Installation

Ensure you have Python `>=3.11 <3.13` installed on your system.
All the packages/tools are listed in the `requirements.txt` file in the project root directory.

If you want to create a Python virtual environment with its built-in module `venv`
and then install the dependencies using `pip`,
follow the steps below.

1. Install and update `pip`.

2. Install the project requirements.
```bash
cd crewai_integration/finance_crews
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Kickoff the crews.

- The RAG Crew.

  ```bash
  cd crewai_integration/finance_crews
  python crews/crew_rag/crew_rag.py
  ```

This command initializes and launches the `RAGCrew` Crew, assembling the agents and assigning them tasks as defined in the configurations in `config`.
This example, unmodified, will generate a `report.md` file as the output of a financial research and analyais in the `results` folder.
You can customise the user question in the `crew_rag.py` file, as well as replace the `sources/article.pdf` that will be used as context for Retrieval Augmented Generation (RAG).

- The Web Scraping Crew.

  ```bash
  cd crewai_integration/finance_crews
  python crews/crew_web_search/crew_web_search.py
  ```

This command initializes and launches the `WebSearchCrew` Crew, assembling the agents and assigning them tasks as defined in the configurations in `config`.
This example, unmodified, will generate a `report.md` file as the output of a financial research and analyais in the `results` folder.
You can customise the user question in the `crew_web_search.py` file.


## 4. The `Streamlit` apps
After building your virtual environment,
you can run our `streamlit` app for an interactive interface and monitoring.

Run the following commands to launch the `Streamlit` apps.

- The RAG app.

  ```bash
  streamlit run streamlit/app_rag.py --browser.gatherUsageStats false 
  ```
  or, if Streamlit does not recognize your virtual environment due to a path mismatch, run the following command:

  ```bash
  python -m streamlit run streamlit/app_rag.py --browser.gatherUsageStats false 
  ```

- The Web Search app.

  ```bash
  streamlit run streamlit/app_web_search.py --browser.gatherUsageStats false 
  ```
  or, if Streamlit does not recognize your virtual environment due to a path mismatch, run the following command:

  ```bash
  python -m streamlit run streamlit/app_web_search.py --browser.gatherUsageStats false 
  ```

## 5. Understanding and monitoring your crews
The `RAGCrew`, defined in `crew_rag.py`, and the `WebSearchCrew`, defined in `crew_web_search.py`, are both subclasses of `crewai.project.CrewBase`.
They both orchestrate two `agents` each, together with their corresponding `tasks`.

The `config/agents.yaml` files outline the capabilities and configurations of each agent in your crews.
These agents collaborate on a series of tasks, defined in the `config/tasks.yaml` files,
leveraging their collective skills to achieve complex objectives.

### 5.1 The RAG Crew

The `RAGCrew` is composed of two agents:

- A `rag_researcher`, i.e. an Expert Financial Investigator and Information Extraction Specialist,
  performing a `rag_research_task`.
  The RAG researcher uses `CrewAI Knowledge`: `crewai.knowledge.source.pdf_knowledge_source.PDFKnowledgeSource`
  and `crewai.knowledge.knowledge_config.KnowledgeConfig`.
  You can customise both the `PDFKnowledgeSource` and the `KnowledgeConfig` in the `rag_search.py` file.
  The source used for RAG is a PDF file stored in the project directory, i.e. `source/article.pdf`, but you can replace it or upload your own PDF file in the Streamlit app.
  For more information about `CrewAI Knowledge`, please refer to the [Knowledge docs](https://docs.crewai.com/concepts/knowledge).

- An `analyst`, i.e. a Financial Analyst and Solution Formulator,
  performing an `analysis` task.
  The analysis task also implements a `guardrail` to ensure that the final answer does not exceed 1000 words.

### 5.2 The Web Search Crew

The `WebSearchCrew` is composed of two agents:

- A `researcher`, i.e. a Specialized Financial Researcher,
  performing a `research_task`.
  The researcher uses `crewai_tool.SerperDevTool` from `CrewAI tools`.
  You can customise the `SerperDevTool` in the `crew_web_search.py` file.
  For more information about the `CrewAI SerperDevTool`, please refer to the [SerperDevTool docs](https://docs.crewai.com/tools/search-research/serperdevtool#google-serper-search).

- A `writer`, i.e. a Financial Reporting Writer,
  performing an `writing_task` task.
  The analysis task also implements a `guardrail` to ensure that the final answer does not exceed 10000 words.

### 5.3 Monitoring your crews with Weave
You can monitor your crews with Weave by following the corresponding project links in your terminal.
For more information on how to monitor your CrewAI crews using Weave,
please refer to the [Weave @CrewAI docs](https://docs.crewai.com/observability/weave).
