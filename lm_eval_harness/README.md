# LM Evaluation Harness @SambaNova

This document demonstrates how to use [LM Evaluation Harness]([https://weave-docs.wandb.ai/](https://github.com/EleutherAI/lm-evaluation-harness)) with [SambaNova](https://sambanova.ai/) as your fastest LLM provider of choice for open source models.  

`lm-evaluation-harness` is a unified evaluation framework developed by EleutherAI for testing generative language models on a large number of different evaluation tasks.

Features:

- Over 60 standard academic benchmarks for LLMs, with hundreds of subtasks and variants implemented.
- Support for commercial APIs
- Support for local models and benchmarks.
- Evaluation with publicly available prompts ensures reproducibility and comparability between papers.
- Easy support for custom prompts and evaluation metrics.

## Pre-requisites: 
1. Create a [SambaNova Cloud](https://cloud.sambanova.ai/) account and get an API key.

2. Clone the `lm-evaluation-harness` repo:
```bash
git clone https://github.com/EleutherAI/lm-eval-harness.git
cd lm-evaluation-harness
```   

3. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  
```

4. Install dependencies:
```bash
pip install -e .
pip install -e ."[api]"
pip install tqdm
```

**Note**: Additional Python packages may be required depending on the selected benchmark or task. If you encounter errors related to missing libraries, install them manually.

## Running the notebook

1. Copy the notebook `quickstart_eval.ipynb` into the cloned directory:
```bash
mv /path/to/quickstart_eval.ipynb lm-evaluation-harness/
cd lm-evaluation-harness
```
   
2. Open the notebook.

3. Add your SambaNova API key in the following cell:
```bash
os.environ["OPENAI_API_KEY"] = "your-sambanova-api-key"
```

4. Specify the task and model in the `tasks` and `model_args` arguments, respectively. For example, `gsm8k` (a math benchmark) and the `Meta-Llama-3.1-8B-Instruct` model are used here:
```bash
results = lm_eval.simple_evaluate(
    model="openai-chat-completions",
    model_args="model=Meta-Llama-3.1-8B-Instruct,base_url=https://api.sambanova.ai/v1/chat/completions",
    tasks="gsm8k", 
    apply_chat_template=True,
    log_samples=True,
    limit=5
)
```

5. Run the notebook.

