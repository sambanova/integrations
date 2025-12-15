"""
Flask server that exposes an OpenAI-compatible `/chat/completions` endpoint
backed by the SambaNova API.
"""

from flask import Flask, request, Response
from sambanova import SambaNova

app = Flask(__name__)

# Initialize the SambaNova client
# NOTE: Replace with your real API key or load it from an environment variable
client = SambaNova(api_key="YOUR_SAMBANOVA_API_KEY")


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------

def generate_streaming_response(data):
    """
    Converts a streaming response from SambaNova into
    Server-Sent Events (SSE) format.

    Each message chunk is serialized to JSON and yielded
    using the `data: <json>\n\n` format expected by clients
    that consume OpenAI-style streaming responses.

    Args:
        data: Iterable streaming response from
              `client.chat.completions.create(stream=True)`

    Yields:
        str: SSE-formatted JSON chunks
    """
    for message in data:
        json_data = message.model_dump_json()
        yield f"data: {json_data}\n\n"


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/chat/completions", methods=["POST"])
def openai_advanced_custom_llm_route():
    """
    OpenAI-compatible Chat Completions endpoint.
    
    Returns:
        Flask Response object
    """
    request_data = request.get_json()

    # Build a clean OpenAI-compatible payload for SambaNova
    openai_payload = {
        "model": request_data["model"],
        "messages": request_data["messages"],
        "temperature": request_data.get("temperature", 0),
        "max_tokens": request_data.get("max_tokens", 250),
        "stream": request_data.get("stream", False),
    }

    # Determine whether the client requested streaming
    streaming = request_data.get("stream", False)

    # Remove fields that are not supported by SambaNova
    # (often added by external tools like Vapi or middleware)
    request_data.pop("call", None)
    request_data.pop("metadata", None)

    # --------------------------------------------------------------------------
    # Streaming response (Server-Sent Events)
    # --------------------------------------------------------------------------
    if streaming:
        chat_completion_stream = client.chat.completions.create(**openai_payload)

        return Response(
            generate_streaming_response(chat_completion_stream),
            content_type="text/event-stream",
        )

    # --------------------------------------------------------------------------
    # Non-streaming response (single JSON payload)
    # --------------------------------------------------------------------------
    else:
        chat_completion = client.chat.completions.create(**openai_payload)

        return Response(
            chat_completion.model_dump_json(),
            content_type="application/json",
        )


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Run the Flask development server.

    The server will be available at:
    http://localhost:5000/chat/completions
    """
    app.run(debug=True, port=5000)
