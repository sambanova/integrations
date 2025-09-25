

# Step 1: Prerequisites
Before setting up Qwen Code, ensure you have Node.js (version 20 or higher) installed. You can install Node.js by running:

```shell
curl -qL https://www.npmjs.com/install.sh | sh
```

Then, verify your installation by running the following:

```shell
node -v
npm -v
```

# Step 2: Setting Up Qwen Code

## Step 2.1: Installation via npm
With Node.js installed, set up Qwen Code globally and check the installation version as well:

```shell
npm install -g @qwen-code/qwen-code
qwen --version
```

This code installs the Qwen Code CLI globally using Node.js's package manager. After installation, the qwen --version command checks and displays the installed version of the Qwen CLI to verify that it's correctly set up and ready to use.

Let’s run Qwen Code:

```shell
qwen
```

Click Enter to select the default theme and apply it to the user settings. Next, we need to set up the authentication.

## Step 2.2: Configuring the environment

We can now use the API key within the CLI. Return to the CLI from step 2.1 and click Enter.

Then, pass in the API key from the previous step, followed by the base URL and model name as given below:

```shell
API_KEY >SAMBANOVA_API_KEY
BASE_URL >https://api.sambanova.ai/v1
MODEL >gpt-oss-120b
```

Optionally, you can set up these variables as environment variables as well. Open a new terminal and run the following line-by-line.

```shell
export OPENAI_API_KEY="0b66a660-1f0f-4bab-8e16-45fc5122df0"6
export OPENAI_BASE_URL="https://api.sambanova.ai/v1"
export OPENAI_MODEL="DeepSeek-V3-0324"

export OPENAI_API_KEY="fw_3ZGJL9eUHcjt4WnYxMHqFqE"o
export OPENAI_BASE_URL="https://api.fireworks.ai/inference/v1"
export OPENAI_MODEL="accounts/fireworks/models/qwen3-coder-480b-a35b-instruct"
export OPENAI_MODEL="accounts/fireworks/models/deepseek-v3-0324"


export OPENAI_API_KEY="0a93167064b5bbad28e936be6da892bd7063325f726328f625bb9c339c4c39b"5
export OPENAI_BASE_URL="https://api.together.xyz/v1"
export OPENAI_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8"
export OPENAI_MODEL="deepseek-ai/DeepSeek-V3"
```

Once these environment variables are set, click Enter, and you can start experimenting with CLI.

# Step 3: Experimenting With Qwen Code CLI


In this section, I’ll walk through how I used Qwen Code CLI to interact with a real-world GitHub-hosted project. With just a few prompts, Qwen helped me understand the codebase, optimize functions, add new capabilities, automate tests, and maintain documentation.

Using thoughtfully crafted prompts, I was able to:

Analyze the codebase architecture
Optimize specific functions for memory efficiency
Automatically generate and run unit tests
Extend functionality by integrating new components
Push versioned updates to GitHub
Generate a visual flowchart of module interactions
Document all changes in a structured changelog format
Let’s dive into each of these steps.

## Exploring and understanding the codebase
Let’s begin by asking Qwen Code to explore and explain the architecture of the codebase. But, first clone the repository from GitHub and navigate into the project directory using the following command:

cmd + c to exit 

```shell
git clone https://github.com/AashiDutt/Voxtral_with_vLLM.git
cd Voxtral_with_vLLM
````


```shell
qwen
```

```shell
API_KEY >SAMBANOVA_API_KEY
BASE_URL >https://api.sambanova.ai/v1
MODEL >gpt-oss-120b
```

Here is the prompt I used to understand the cloned repository:

Prompt:  Explain the architecture of this codebase.

---
output image
----

Qwen CLI scanned files like app.py, config.py, requirements.txt, and a Colab notebook. It then returned a clear breakdown of the project’s structure along with a high-level summary of its key modules, saving me the time of manually opening and reading each file.


## Code refactoring and optimization
After understanding the architecture, I used Qwen Code CLI to analyze potential areas of improvement in the codebase.

Prompt: What parts of this module can be optimized?

---
output image
----

Qwen returned a structured list of suggestions across multiple dimensions: performance, memory efficiency, maintainability, and user experience. It didn’t just identify issues, it also proposed actionable code changes.

By following its guidance, I was able to:

Reduce memory and CPU usage
Strengthen error handling
Improve user feedback
Simplify code structure for future development
In the next step, I’ll show how I applied one of these optimizations (memory usage) and tested it using Qwen CLI itself.

## Implementing and testing the code optimization
After identifying several areas for optimization, I decided to apply one of the most impactful suggestions: improving the memory usage in the transcribe_audio function. So, I prompted Qwen CLI to target that specific file below:

Prompt: Apply memory usage optimization to the transcribe_audio function in @app.py

---
output image
----

Qwen returned a structured list of suggestions across multiple dimensions: performance, memory efficiency, maintainability, and user experience. It didn’t just identify issues, it also proposed actionable code changes.

By following its guidance, I was able to:

Reduce memory and CPU usage
Strengthen error handling
Improve user feedback
Simplify code structure for future development
In the next step, I’ll show how I applied one of these optimizations (memory usage) and tested it using Qwen CLI itself.

## Implementing and testing the code optimization
After identifying several areas for optimization, I decided to apply one of the most impactful suggestions: improving the memory usage in the transcribe_audio function. So, I prompted Qwen CLI to target that specific file below:

Prompt: Apply memory usage optimization to the transcribe_audio function in @app.py

---
output image
----

Qwen focused exclusively on app.py using its @ syntax for scoped edits. This precise targeting is useful when you want changes applied in isolation without impacting unrelated parts of the codebase. The CLI rewrote the function to:

Stream and process audio chunks instead of loading them all into memory
Reduce UI updates by refreshing the progress bar only every 10 chunks
Remove the need to precompute the total number of chunks

## Generating and running tests
Once the memory usage optimization was applied to the transcribe_audio function, I used Qwen Coder CLI to automatically generate and validate unit tests for the new implementation.

Prompt: Write a pytest unit test for the recent changes.

DOESNT WORK

## Implementing a new component
To extend the functionality of the Voxtral Audio Assistant(codebase), I prompted Qwen Code CLI to integrate support for YouTube videos.

Prompt: Extend the current example to support YouTube videos. When a user provides a YouTube URL, extract the audio from the video and pass it to the Voxtral model for processing. Keep the rest of the pipeline and components unchanged.

DOESNT WORK