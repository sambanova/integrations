"""Hear a SambaNova answer while it is still being written.

SambaNova streams the reply a few tokens at a time. Each piece goes straight
into a Cartesia websocket, Cartesia streams speech back, and the speech plays
as it arrives, so you hear the start of the answer before the model has
finished writing the end of it.

    python main.py
"""

import os
import threading
import time
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

SAMPLE_RATE = 44100
BYTES_PER_SECOND = SAMPLE_RATE * 2  # 16-bit mono

DEFAULT_MODEL = 'gpt-oss-120b'
DEFAULT_TTS_MODEL = 'sonic-2'
DEFAULT_VOICE = '6ccbfb76-1fc6-48f7-b71d-91ac6298247b'

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
