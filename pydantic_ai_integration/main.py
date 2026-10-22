"""A trip-briefing agent built with Pydantic AI on SambaCloud.

Ask about a city and the agent looks it up, fetches a live forecast, and answers with a
validated `TripBrief` object instead of free text. Follow-up questions keep the conversation,
so "and what should I pack?" knows which city you meant.

    python main.py                                  # interactive
    python main.py "I'm flying to Lisbon tomorrow"  # one question, then exit

Weather and geocoding come from Open-Meteo (https://open-meteo.com), which needs no API key.
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ToolCallPart

load_dotenv()

DEFAULT_MODEL = 'MiniMax-M3'
GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
# Five days, so a question asked on a Thursday about "this weekend" is covered.
FORECAST_DAYS = 5

# WMO weather interpretation codes, the full set Open-Meteo documents, so the model gets words, not numbers.
WEATHER_CODES = {
    0: 'clear sky',
    1: 'mainly clear',
    2: 'partly cloudy',
    3: 'overcast',
    45: 'fog',
    48: 'fog with rime',
    51: 'light drizzle',
    53: 'drizzle',
    55: 'heavy drizzle',
    56: 'light freezing drizzle',
    57: 'heavy freezing drizzle',
    61: 'light rain',
    63: 'rain',
    65: 'heavy rain',
    66: 'light freezing rain',
    67: 'heavy freezing rain',
    71: 'light snow',
    73: 'snow',
    75: 'heavy snow',
    77: 'snow grains',
    80: 'light rain showers',
    81: 'rain showers',
    82: 'violent rain showers',
    85: 'light snow showers',
    86: 'heavy snow showers',
    95: 'thunderstorm',
    96: 'thunderstorm with light hail',
    97: 'heavy thunderstorm',
    99: 'thunderstorm with heavy hail',
}

# Not strftime('%A'), which follows the locale: the weekday fix below relies on these exact names.
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

INSTRUCTIONS = (
    'You are a travel assistant. For any question about a place, call find_city first, then get_forecast '
    'with the coordinates and timezone it returns. Never guess the weather or the local time: use the tools. '
    'Put a direct answer to the latest question in `answer`, in one to three sentences.'
)


@dataclass
class Deps:
    """Shared by every tool call in a run. The agent never sees it; tools reach it through `ctx.deps`."""

    http: httpx.AsyncClient


class City(BaseModel):
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class DayForecast(BaseModel):
    day: date
    weekday: str
    conditions: str
    min_c: float
    max_c: float
    # Open-Meteo returns null when it has no estimate for a day.
    rain_chance_pct: Annotated[int, Field(ge=0, le=100)] | None


class Forecast(BaseModel):
    """What get_forecast returns. A typed model, like City, rather than a raw dict."""

    local_time: datetime
    conditions: str
    temperature_c: float
    wind_kmh: float
    next_days: list[DayForecast]


class TripBrief(BaseModel):
    """The agent's output. Pydantic AI validates the model's answer against this before returning it."""

    city: str
    country: str
    local_time: datetime = Field(description='Local date and time at the destination, as reported by get_forecast')
    current_conditions: str
    current_temperature_c: float
    next_days: list[DayForecast]
    # Enforced, not just described: a list of the wrong length goes back to the model as a retry.
    packing_tips: list[str] = Field(min_length=2, max_length=4, description='Two to four short, practical items')
    answer: str = Field(description='A direct answer to the latest question')


def require_env(name: str) -> None:
    """Exit with a hint if a required variable is unset. The SambaNova provider reads the value itself."""
    if not os.getenv(name, '').strip():
        raise SystemExit(f'{name} is not set. Copy .env.example to .env and add your key.')


async def find_city(ctx: RunContext[Deps], name: str) -> City:
    """Look up a city by name and return its country, coordinates and timezone."""
    response = await ctx.deps.http.get(GEOCODING_URL, params={'name': name, 'count': 1})
    response.raise_for_status()
    results = response.json().get('results')
    if not results:
        # ModelRetry sends the message back to the model, which can try another spelling.
        raise ModelRetry(f'No city called {name!r}. Try the English name, without the country.')
    place = results[0]
    return City(
        name=place['name'],
        country=place.get('country', ''),
        latitude=place['latitude'],
        longitude=place['longitude'],
        timezone=place['timezone'],
    )


async def get_forecast(ctx: RunContext[Deps], latitude: float, longitude: float, timezone: str) -> Forecast:
    """Current weather, local time and a five-day forecast for a location, starting today."""
    params: dict[str, str | float | int] = {
        'latitude': latitude,
        'longitude': longitude,
        'timezone': timezone,
        'current': 'temperature_2m,weather_code,wind_speed_10m',
        'daily': 'weather_code,temperature_2m_min,temperature_2m_max,precipitation_probability_max',
        'forecast_days': FORECAST_DAYS,
    }
    response = await ctx.deps.http.get(FORECAST_URL, params=params)
    response.raise_for_status()
    data = response.json()
    current, daily = data['current'], data['daily']
    return Forecast(
        local_time=current['time'],
        conditions=WEATHER_CODES.get(current['weather_code'], 'unknown'),
        temperature_c=current['temperature_2m'],
        wind_kmh=current['wind_speed_10m'],
        next_days=[
            DayForecast(
                day=day,
                # Given, not left to the model: asked about "this weekend" with bare dates, it guessed
                # the weekdays and got them wrong.
                weekday=WEEKDAYS[date.fromisoformat(day).weekday()],
                conditions=WEATHER_CODES.get(code, 'unknown'),
                min_c=low,
                max_c=high,
                rain_chance_pct=rain,
            )
            for day, code, low, high, rain in zip(
                daily['time'],
                daily['weather_code'],
                daily['temperature_2m_min'],
                daily['temperature_2m_max'],
                daily['precipitation_probability_max'],
                strict=True,
            )
        ],
    )


def build_agent(model: str) -> Agent[Deps, TripBrief]:
    # The `sambanova:` prefix selects Pydantic AI's built-in SambaNova provider, which reads
    # SAMBANOVA_API_KEY and sends requests to https://api.sambanova.ai/v1.
    # The tools are passed as a list rather than with @agent.tool: CI type-checks without pydantic_ai
    # installed, and mypy --strict rejects a decorator it cannot see the types of.
    # retries=2 gives the model two more tries after a ModelRetry, e.g. to fix a misspelled city.
    agent: Agent[Deps, TripBrief] = Agent(
        f'sambanova:{model}',
        deps_type=Deps,
        output_type=TripBrief,
        instructions=INSTRUCTIONS,
        tools=[find_city, get_forecast],
        retries=2,
    )
    return agent


def print_brief(brief: TripBrief, tools_used: list[str], seconds: float) -> None:
    print(f'\n  {brief.city}, {brief.country}  |  local time {brief.local_time:%Y-%m-%d %H:%M}')
    print(f'  now: {brief.current_conditions}, {brief.current_temperature_c:.0f}°C')
    for day in brief.next_days:
        temps = f'{day.min_c:.0f} to {day.max_c:.0f}°C'
        rain = 'n/a' if day.rain_chance_pct is None else f'{day.rain_chance_pct}%'
        print(f'  {day.weekday[:3]} {day.day}: {day.conditions}, {temps}, rain {rain}')
    print('  pack: ' + '; '.join(brief.packing_tips))
    print(f'\n  {brief.answer}\n')
    print(f'  tools: {", ".join(tools_used) or "none"}  |  {seconds:.1f} s\n')


def tools_called(messages: list[ModelMessage]) -> list[str]:
    """The tools the model called in this turn, in order. `final_result` is how the TripBrief itself comes back."""
    return [
        part.tool_name
        for message in messages
        for part in message.parts
        if isinstance(part, ToolCallPart) and part.tool_name != 'final_result'
    ]


async def ask(agent: Agent[Deps, TripBrief], deps: Deps, question: str, history: list[ModelMessage]) -> None:
    started = time.perf_counter()
    try:
        result = await agent.run(question, deps=deps, message_history=history)
    except (ModelHTTPError, UnexpectedModelBehavior) as exc:
        print(f'\n  error: {exc}\n')
        return
    except httpx.HTTPError as exc:
        # An Open-Meteo 429/5xx, timeout or dropped connection, raised inside a tool. Report it and keep the
        # session alive; the question can simply be asked again.
        print(f'\n  error: weather service request failed: {exc!r}\n')
        return
    print_brief(result.output, tools_called(result.new_messages()), time.perf_counter() - started)
    # Carry the whole conversation into the next turn, so follow-ups know which city is meant.
    history[:] = result.all_messages()


async def main() -> None:
    require_env('SAMBANOVA_API_KEY')
    # `or`, not a getenv default: a blank `SAMBANOVA_MODEL=` in .env would otherwise give the model string `sambanova:`.
    model = os.getenv('SAMBANOVA_MODEL', '').strip() or DEFAULT_MODEL
    agent = build_agent(model)
    history: list[ModelMessage] = []

    async with httpx.AsyncClient(timeout=30) as http:
        deps = Deps(http=http)
        if len(sys.argv) > 1:
            await ask(agent, deps, ' '.join(sys.argv[1:]), history)
            return

        print(f'Trip briefing on SambaCloud. Model: {model}. Type "exit" to quit.\n')
        while True:
            try:
                question = input('you > ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if question.lower() in {'exit', 'quit'}:
                return
            if question:
                await ask(agent, deps, question, history)


if __name__ == '__main__':
    asyncio.run(main())
