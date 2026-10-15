"""Hear a SambaNova answer while it is still being written.

SambaNova streams the reply a few tokens at a time. Each piece goes straight
into a Cartesia websocket, Cartesia streams speech back, and the speech plays
as it arrives, so you hear the start of the answer before the model has
finished writing the end of it.

    python main.py
"""

import asyncio
import contextlib
import os
import threading
import time
from typing import Any, Literal

from cartesia import AsyncCartesia
from dotenv import load_dotenv
from sambanova import AsyncSambaNova, omit
from sambanova.types.chat.completion_create_params import Message

try:
    import sounddevice as sd
except OSError as exc:  # raised on import when the PortAudio library is missing
    raise SystemExit('PortAudio is not installed. On Debian or Ubuntu: sudo apt install libportaudio2') from exc

load_dotenv()

SAMPLE_RATE = 44100
BYTES_PER_SECOND = SAMPLE_RATE * 2  # 16-bit mono

DEFAULT_MODEL = 'gpt-oss-120b'
DEFAULT_TTS_MODEL = 'sonic-2'
DEFAULT_VOICE = '6ccbfb76-1fc6-48f7-b71d-91ac6298247b'

OUTPUT_FORMAT: dict[str, Any] = {'container': 'raw', 'encoding': 'pcm_s16le', 'sample_rate': SAMPLE_RATE}

# Cartesia closes a websocket after 5 minutes without traffic. Reopen it a little before that.
IDLE_RECONNECT_S = 240
# The longest wait for the next piece of audio before a turn is given up on.
AUDIO_TIMEOUT_S = 20

# Every word the model writes is spoken, so it is asked to write for the ear.
SYSTEM_PROMPT = (
    'You are a helpful voice assistant. Everything you write is spoken aloud, so talk the way '
    'people talk: short sentences, contractions, no lists, no markdown, no emoji, no URLs. '
    'Answer in two to four sentences unless asked for more.'
)


def require_env(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value:
        raise SystemExit(f'{name} is not set. Copy .env.example to .env and add your key.')
    return value


def reasoning_effort(model: str) -> Literal['low'] | None:
    """gpt-oss models reason before they answer, and that time is silence. Keep it short."""
    return 'low' if model.startswith('gpt-oss') else None


class PcmBuffer:
    """Audio waiting to be played.

    Cartesia delivers audio faster than real time, so it queues here and the
    sound card takes exactly what it needs, from its own thread.
    """

    def __init__(self) -> None:
        self._data = bytearray()
        self._lock = threading.Lock()

    def add(self, pcm: bytes) -> None:
        with self._lock:
            self._data += pcm

    def take(self, size: int) -> bytes:
        """Exactly `size` bytes: queued audio, padded with silence if there is not enough."""
        with self._lock:
            out = bytes(self._data[:size])
            del self._data[:size]
        return out + b'\x00' * (size - len(out))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class Turn:
    """Timings for one answer, in seconds from the moment the question was sent."""

    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.first_token: float | None = None
        self.first_sound: float | None = None
        self.inference: float | None = None  # SambaNova's own time to first token, no network in it
        self.generated: float | None = None  # when the last piece of audio arrived
        self.audio_bytes = 0

    def now(self) -> float:
        return time.perf_counter() - self.started


def ms(seconds: float | None) -> str:
    return 'n/a' if seconds is None else f'{seconds * 1000:.0f} ms'


def format_report(turn: Turn) -> str:
    token = f'  first token  {ms(turn.first_token):>8}'
    if turn.inference is not None:
        token += f'   (SambaNova inference: {ms(turn.inference)})'
    lines = [token, f'  first sound  {ms(turn.first_sound):>8}   (Cartesia)']
    if turn.generated and turn.audio_bytes:
        audio = turn.audio_bytes / BYTES_PER_SECOND
        lines.append(
            f'  audio {audio:.1f} s generated in {turn.generated:.1f} s  ({audio / turn.generated:.1f}x realtime)'
        )
    return '\n'.join(lines)


class Speaker:
    """Plays queued PCM on the default output device."""

    def __init__(self) -> None:
        self.buffer = PcmBuffer()
        try:
            self._stream = sd.RawOutputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype='int16', callback=self._fill
            )
            self._stream.start()
        except sd.PortAudioError as exc:
            raise SystemExit(f'Could not open an audio output device: {exc}') from exc

    def _fill(self, outdata: Any, frames: int, time_info: Any, status: Any) -> None:
        outdata[:] = self.buffer.take(len(outdata))

    def stop(self) -> None:
        """Silence now: drop whatever has not been played yet."""
        self.buffer.clear()

    async def finish(self) -> None:
        """Wait until everything queued has been played."""
        while len(self.buffer):
            await asyncio.sleep(0.05)

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


class Voice:
    """One Cartesia websocket, opened once and reused for every answer.

    Opening it takes a second or so. Paying that once, up front, is what a real
    voice app does, so it is kept out of the per-answer timings.
    """

    def __init__(self, client: Any, model: str, voice_id: str) -> None:
        self.client = client
        self.model = model
        self.voice_id = voice_id
        self.last_used = 0.0
        self._manager: Any = None
        self._conn: Any = None

    async def connect(self) -> float:
        """Open the websocket. Returns how long the handshake took, in seconds."""
        await self.close()
        started = time.perf_counter()
        self._manager = self.client.tts.websocket_connect()
        self._conn = await self._manager.__aenter__()
        # Wall-clock time, so a laptop that slept with the app open still counts as idle.
        self.last_used = time.time()
        return time.perf_counter() - started

    async def context(self) -> Any:
        """A fresh context for one answer: everything pushed into it is spoken as one utterance."""
        if time.time() - self.last_used > IDLE_RECONNECT_S:
            await self.connect()
        self.last_used = time.time()
        return self._conn.context(
            model_id=self.model,
            voice={'mode': 'id', 'id': self.voice_id},
            output_format=OUTPUT_FORMAT,
            language='en',
            timeout=AUDIO_TIMEOUT_S,
        )

    async def close(self) -> None:
        if self._manager is not None:
            manager, self._manager, self._conn = self._manager, None, None
            await manager.__aexit__(None, None, None)


async def answer(
    llm: AsyncSambaNova, voice: Voice, speaker: Speaker, history: list[Message], model: str
) -> tuple[str, Turn]:
    """Stream one answer from SambaNova into Cartesia and play it as it arrives."""
    turn = Turn()
    ctx = await voice.context()
    reply: list[str] = []
    speaking: asyncio.Task[None] | None = None

    async def speak() -> None:
        try:
            async for event in ctx.receive():
                if event.type == 'chunk' and event.audio:
                    if turn.first_sound is None:
                        turn.first_sound = turn.now()
                    turn.audio_bytes += len(event.audio)
                    speaker.buffer.add(event.audio)
                elif event.type == 'error':
                    raise RuntimeError(f'Cartesia: {event.message or event.title or "unknown error"}')
        except TimeoutError:
            raise RuntimeError(f'Cartesia sent no audio for {AUDIO_TIMEOUT_S} s. Reconnecting for the next question.')
        turn.generated = turn.now()

    try:
        effort = reasoning_effort(model)
        stream = await llm.chat.completions.create(
            model=model, messages=history, stream=True, reasoning_effort=effort if effort else omit
        )
        async for chunk in stream:
            # The stream ends with a frame that has no choices, carrying SambaNova's own timings.
            if chunk.usage is not None and chunk.usage.time_to_first_token is not None:
                turn.inference = chunk.usage.time_to_first_token
            if not chunk.choices:
                continue
            # Only the answer is spoken. A reasoning model's thinking arrives in another field.
            text = chunk.choices[0].delta.content
            if not text:
                continue
            if speaking is None:
                turn.first_token = turn.now()
                print('\n  ', end='')
                speaking = asyncio.create_task(speak())
            print(text, end='', flush=True)
            reply.append(text)
            await ctx.push(text)
        if speaking is not None:
            await ctx.no_more_inputs()
            await speaking
    except BaseException as exc:
        # Stopped, or something failed: stop Cartesia generating and drop unplayed audio.
        if speaking is not None:
            speaking.cancel()
        with contextlib.suppress(Exception):
            await ctx.cancel()
        speaker.stop()
        if not isinstance(exc, asyncio.CancelledError):
            voice.last_used = 0.0  # the socket may be dead: start the next answer on a fresh one
        raise
    return ''.join(reply), turn


async def ask(
    llm: AsyncSambaNova, voice: Voice, speaker: Speaker, history: list[Message], model: str, question: str
) -> Turn | None:
    """One question and answer. History only keeps answers that completed."""
    history.append({'role': 'user', 'content': question})
    try:
        reply, turn = await answer(llm, voice, speaker, history, model)
    except BaseException:
        history.pop()
        raise
    if not reply:
        history.pop()
        return None
    history.append({'role': 'assistant', 'content': reply})
    return turn


def describe(exc: BaseException) -> str:
    """An error as one line, never blank: some exceptions carry no message."""
    return str(exc) or type(exc).__name__


async def open_voice(voice: Voice) -> float:
    try:
        return await voice.connect()
    except Exception as exc:
        raise SystemExit(f'Could not connect to Cartesia: {describe(exc)}') from exc


def main() -> None:
    llm = AsyncSambaNova(api_key=require_env('SAMBANOVA_API_KEY'))
    voice = Voice(
        AsyncCartesia(api_key=require_env('CARTESIA_API_KEY')),
        os.getenv('CARTESIA_MODEL') or DEFAULT_TTS_MODEL,
        os.getenv('CARTESIA_VOICE_ID') or DEFAULT_VOICE,
    )
    model = os.getenv('SAMBANOVA_MODEL') or DEFAULT_MODEL
    speaker = Speaker()
    history: list[Message] = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    # A Runner rather than asyncio.run: Ctrl-C then cancels only the answer in
    # progress, and the Cartesia websocket stays open between questions.
    with asyncio.Runner() as runner:
        try:
            took = runner.run(open_voice(voice))
            print(f'Connected to Cartesia in {ms(took)}. Model: {model}.')
            print('Type a question and press Enter. Ctrl-C stops an answer, "exit" quits.')
            while True:
                try:
                    question = input('\nyou > ').strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if question.lower() in ('exit', 'quit'):
                    break
                if not question:
                    continue
                try:
                    turn = runner.run(ask(llm, voice, speaker, history, model, question))
                    if turn is None:
                        print('  (no answer came back, try asking again)')
                        continue
                    print('\n\n' + format_report(turn))
                    runner.run(speaker.finish())
                except KeyboardInterrupt:
                    speaker.stop()
                    print('\n  (stopped)')
                except Exception as exc:
                    print(f'\n  ! {describe(exc)}')
        finally:
            runner.run(voice.close())
            speaker.close()


if __name__ == '__main__':
    main()
