# SambaNova + Cartesia: hear the answer while it is being written

A terminal chat where every answer is spoken. SambaNova streams the reply a few
tokens at a time, each piece goes straight into a [Cartesia](https://cartesia.ai)
websocket, and the speech plays as it arrives. You hear the start of the answer
before the model has finished writing the end of it.

No voice framework is involved: this is the handoff that frameworks such as
[Pipecat](../pipecat_integration/README.md) and [LiveKit](../livekit/README.md)
do for you, written out in one file so you can see it.

## Prerequisites

- Python 3.11 or later
- A SambaNova API key from [SambaCloud](https://cloud.sambanova.ai/apis)
- A Cartesia API key from the [Cartesia playground](https://play.cartesia.ai/keys)
- Speakers or headphones
- On Debian or Ubuntu, PortAudio: `sudo apt install libportaudio2` (macOS and Windows need nothing extra)

## Setup

```bash
git clone https://github.com/sambanova/integrations.git
cd integrations/cartesia_integration
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and add your two keys. The other settings are optional:

| Variable | Default | |
| --- | --- | --- |
| `SAMBANOVA_API_KEY` | | required |
| `CARTESIA_API_KEY` | | required |
| `SAMBANOVA_MODEL` | `gpt-oss-120b` | any [SambaCloud model](https://docs.sambanova.ai/cloud/docs/get-started/supported-models) |
| `CARTESIA_MODEL` | `sonic-2` | |
| `CARTESIA_VOICE_ID` | `6ccbfb76-1fc6-48f7-b71d-91ac6298247b` | any voice from the [Cartesia voice library](https://play.cartesia.ai/voices) |

## Run

```bash
python main.py
```

```text
Connected to Cartesia in 1125 ms. Model: gpt-oss-120b.
Type a question and press Enter. Ctrl-C stops an answer, "exit" quits.

you > why is the sky blue?

  Because of Rayleigh scattering. Sunlight hits air molecules, and the shorter blue wavelengths bounce around more than reds. That scattered blue light reaches our eyes from every direction, making the sky look blue.

  first token   1080 ms   (SambaNova inference: 422 ms)
  first sound   1370 ms   (Cartesia)
  audio 12.7 s generated in 4.0 s  (3.2x realtime)
```

- **first token**: when the first word of the answer reached your machine. In brackets is SambaNova's own
  measurement, which has no network in it; the difference is the round trip, and it varies with your
  connection.
- **first sound**: when the first audio arrived. This is how long you wait before hearing anything.
- **realtime**: seconds of speech produced per second of waiting. Above 1x, speech never runs ahead of the text.

The Cartesia connection is opened once at startup and reused, which is what a real voice app does, so its
handshake is not counted in these numbers.

## How it works

```text
you type ─► SambaNova (stream=True) ── text ──► printed
                                     └─ text ──► Cartesia websocket context ── audio ──► speakers
```

The core of `main.py`, trimmed:

```python
stream = await llm.chat.completions.create(model=model, messages=history, stream=True)
async for chunk in stream:
    text = chunk.choices[0].delta.content if chunk.choices else None
    if text:
        await ctx.push(text)          # Cartesia starts speaking from the first words
await ctx.no_more_inputs()

async for event in ctx.receive():     # runs at the same time, in its own task
    if event.type == 'chunk':
        speaker.buffer.add(event.audio)
```

A few details worth knowing:

- **Reasoning models.** `gpt-oss-120b` thinks before it answers, and that time is silence. The request sets
  `reasoning_effort='low'` for gpt-oss models, and only the answer itself (`delta.content`) is ever spoken.
  In testing, low effort brought the first word from 0.66 s to 0.55 s.
- **One context per answer.** Everything pushed into a Cartesia context is spoken as one utterance, so the
  voice stays natural across the pieces.
- **Stopping.** Ctrl-C cancels the context, so Cartesia stops generating as well as the speakers stopping,
  and the half-answer is left out of the conversation history.

## Troubleshooting

- **`PortAudio is not installed`**: on Debian or Ubuntu, `sudo apt install libportaudio2`.
- **`Could not open an audio output device`**: check that an output device is connected and selected.
  Over SSH or in a container there is usually none.
- **`SAMBANOVA_API_KEY is not set`**: create `.env` from `.env.example` in this folder and add the key.
- **`Cartesia: …`**: the message is Cartesia's. A wrong `CARTESIA_VOICE_ID` or a plan without access to
  `CARTESIA_MODEL` are the usual causes.
- **`You need to install cartesia[websockets]`**: install from `requirements.txt`, which includes that extra.
- **Silence before the first word**: try a non-reasoning model, for example
  `SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct`.
