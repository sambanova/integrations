import os

from langchain_sambanova import SambaNovaEmbeddings # type: ignore
from sambanova import SambaNova # type: ignore

from mem0 import Memory # type: ignore

# --- Environment Variables ---
os.environ.setdefault('OPENAI_API_KEY', 'your-openai-key')  # Used for vectordb llm
os.environ.setdefault('SAMBANOVA_API_KEY', 'your-openai-key')

embeddings = SambaNovaEmbeddings(model='E5-Mistral-7B-Instruct')


# --- Initialize Clients ---
client = SambaNova(
    api_key=os.environ['SAMBANOVA_API_KEY'],
)

config = {
    'embedder': {'provider': 'langchain', 'config': {'model': embeddings}},
    'vector_store': {
        'provider': 'qdrant',
        'config': {
            'embedding_model_dims': '4096',
        },
    },
}

memory = Memory.from_config(config)


def chat_with_memories(message: str, user_id: str = 'default_user') -> str:
    """
    Chat with the model using persistent memory.
    Retrieves relevant memories, includes them in the system prompt,
    generates a response, and stores new memories.
    """

    # Retrieve relevant memories
    relevant = memory.search(query=message, user_id=user_id, limit=3)
    results = relevant.get('results', [])

    memories_str = '\n'.join(f"- {entry['memory']}" for entry in results) if results else 'No relevant memories yet.'

    # Build system prompt
    system_prompt = (
        'You are a helpful AI assistant. Use the memories below only if relevant.\n\n' f'User Memories:\n{memories_str}'
    )

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message},
    ]

    # Generate response
    response = client.chat.completions.create(model='gpt-oss-120b', messages=messages)
    assistant_reply = response.choices[0].message.content

    # Save conversation into memory
    memory.add(
        [
            {'role': 'user', 'content': message},
            {'role': 'assistant', 'content': assistant_reply},
        ],
        user_id=user_id,
    )

    return assistant_reply # type: ignore


def main() -> None:
    """Simple REPL chat loop."""
    print("Chat with AI memory system (type 'exit' to quit)\n")

    while True:
        user_input = input('You: ').strip()
        if user_input.lower() == 'exit':
            print('Goodbye!')
            break

        response = chat_with_memories(user_input)
        print(f'AI: {response}\n')


if __name__ == '__main__':
    main()
