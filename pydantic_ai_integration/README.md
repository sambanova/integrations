# SambaNova + Pydantic AI: a trip-briefing agent with typed output

A terminal travel assistant built with [Pydantic AI](https://pydantic.dev/docs/ai/) on SambaCloud. Ask about a city
and the agent looks it up, fetches a live forecast, and answers with a validated `TripBrief` object instead of free
text. Follow-up questions keep the conversation, so "what should I pack?" knows which city you meant.

The [Pydantic AI integration guide](https://docs.sambanova.ai/docs/en/integrations/pydantic-ai) covers the basics
one snippet at a time: Pydantic AI's built-in SambaNova provider, structured output, tool calling and streaming. This
app builds on the first three and adds what the guide doesn't show: two tools the model chains together, typed tool
results, dependency injection, retries, and multi-turn history.

## Prerequisites

- Python 3.11 or later
- A SambaNova API key from [SambaCloud](https://cloud.sambanova.ai/apis)

Weather and geocoding come from [Open-Meteo](https://open-meteo.com), which needs no API key.

## Setup

```bash
git clone https://github.com/sambanova/integrations.git
cd integrations/pydantic_ai_integration
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and add your key. The model is optional:

| Variable | Default | |
| --- | --- | --- |
| `SAMBANOVA_API_KEY` | | required |
| `SAMBANOVA_MODEL` | `MiniMax-M3` | any [SambaCloud model](https://docs.sambanova.ai/docs/en/models/sambacloud-models) that supports function calling |

## Run

```bash
python main.py                                     # interactive
python main.py "Do I need an umbrella in Lisbon?"  # one question, then exit
```

Pydantic AI prints a startup banner to standard error first. Set `PYDANTIC_AI_NO_BANNER=1` to turn it off.

```text
Trip briefing on SambaCloud. Model: MiniMax-M3. Type "exit" to quit.

you > I'm flying to Lisbon tomorrow. Do I need an umbrella?

  Lisbon, Portugal  |  local time 2026-10-22 17:15
  now: mainly clear, 18°C
  Thu 2026-10-22: overcast, 8 to 20°C, rain 0%
  Fri 2026-10-23: overcast, 12 to 22°C, rain 3%
  Sat 2026-10-24: overcast, 9 to 22°C, rain 0%
  Sun 2026-10-25: overcast, 11 to 23°C, rain 0%
  Mon 2026-10-26: fog, 13 to 22°C, rain 0%
  pack: Light jacket for cool mornings and evenings (9–13 °C); Layers for changing between overcast days and clearer spells; Comfortable walking shoes for Lisbon's hilly streets

  You can probably leave the umbrella at home — Lisbon is overcast but dry over the next few days, with rain chances near 0% and mild temperatures in the low 20s °C. A light jacket for the cooler mornings and evenings (around 9–13 °C) would be more useful than an umbrella.

  tools: find_city, get_forecast  |  21.3 s

you > What about Kyoto this weekend?

  Kyoto, Japan  |  local time 2026-10-23 01:15
  now: overcast, 14°C
  Fri 2026-10-23: light drizzle, 12 to 21°C, rain 75%
  Sat 2026-10-24: rain, 18 to 20°C, rain 96%
  Sun 2026-10-25: rain, 19 to 22°C, rain 77%
  Mon 2026-10-26: rain showers, 18 to 23°C, rain 73%
  Tue 2026-10-27: rain showers, 15 to 26°C, rain 73%
  pack: Compact umbrella — rain is very likely all weekend; Waterproof jacket or raincoat; Waterproof shoes for temple visits and wet streets; Light layers for mild 18–22 °C temperatures

  Yes, definitely pack an umbrella — Kyoto is in for a wet weekend, with rain chances of 96% on Saturday and 77% on Sunday, plus light drizzle starting Friday. Temperatures will sit around 18–22 °C, so a waterproof layer and waterproof shoes are also wise.

  tools: find_city, get_forecast  |  20.0 s

you > What should I pack for Kyoto?

  Kyoto, Japan  |  local time 2026-10-23 01:15
  now: overcast, 14°C
  Fri 2026-10-23: light drizzle, 12 to 21°C, rain 75%
  Sat 2026-10-24: rain, 18 to 20°C, rain 96%
  Sun 2026-10-25: rain, 19 to 22°C, rain 77%
  Mon 2026-10-26: rain showers, 18 to 23°C, rain 73%
  Tue 2026-10-27: rain showers, 15 to 26°C, rain 73%
  pack: Compact umbrella — rain is very likely all weekend; Waterproof jacket or raincoat; Waterproof shoes for temple visits and wet streets; Light layers for mild 18–22 °C temperatures

  For Kyoto this weekend, pack a compact umbrella and a waterproof jacket — rain is very likely (96% chance Saturday, 77% Sunday). Waterproof shoes are a smart call for temple hopping on wet streets, and bring light layers for mild 18–22 °C temperatures.

  tools: none  |  15.4 s

```

- **tools**: the tools the model called this turn. The third question needed none: the Kyoto forecast was already
  in the conversation history.
- Most of each turn's time, typically 15 to 40 seconds, is `MiniMax-M3` reasoning before it calls a tool. A model
  without a reasoning phase, such as `Meta-Llama-3.3-70B-Instruct`, answers the same question in a few seconds.

## How it works

```text
question ─► Agent("sambanova:MiniMax-M3") ─► find_city ──► Open-Meteo geocoding
                    ▲                    └─► get_forecast ─► Open-Meteo forecast
                    │                    └─► final_result ─► TripBrief (validated) ─► printed
                    └── message_history: the whole conversation, sent again on the next turn
```

The core of `main.py`, trimmed:

```python
class DayForecast(BaseModel):
    day: date
    weekday: str
    conditions: str
    min_c: float
    max_c: float
    rain_chance_pct: Annotated[int, Field(ge=0, le=100)] | None


class TripBrief(BaseModel):
    city: str
    country: str
    local_time: datetime
    current_conditions: str
    current_temperature_c: float
    next_days: list[DayForecast]
    packing_tips: list[str] = Field(min_length=2, max_length=4)
    answer: str


async def find_city(ctx: RunContext[Deps], name: str) -> City:
    """Look up a city by name and return its country, coordinates and timezone."""
    response = await ctx.deps.http.get(GEOCODING_URL, params={'name': name, 'count': 1})
    if not response.json().get('results'):
        raise ModelRetry(f'No city called {name!r}. Try the English name, without the country.')
    ...


agent: Agent[Deps, TripBrief] = Agent(
    'sambanova:MiniMax-M3',
    deps_type=Deps,
    output_type=TripBrief,
    instructions=INSTRUCTIONS,
    tools=[find_city, get_forecast],
    retries=2,
)

result = await agent.run(question, deps=Deps(http=client), message_history=history)
history = result.all_messages()
```

A few details worth knowing:

- **The SambaNova provider.** `sambanova:` selects Pydantic AI's built-in
  [SambaNova provider](https://pydantic.dev/docs/ai/models/compatible-apis/#sambanova), which reads
  `SAMBANOVA_API_KEY` and calls `https://api.sambanova.ai/v1`. Nothing is configured by hand.
- **Validation checks shape, not truth.** `TripBrief` rejects a rain chance outside 0 to 100, a date that isn't a
  date, or the wrong number of packing tips, and the error goes back to the model as a retry. It cannot check that
  the numbers the model copied into `TripBrief` match what `get_forecast` returned. Tools return typed models
  (`City`, `Forecast`) so there is less raw data for the model to re-copy.
- **Structured output is a tool call.** Pydantic AI sends `TripBrief`'s JSON schema as a tool named
  `final_result` and validates the arguments the model calls it with. That is why the model must support function
  calling, and why `final_result` is left out of the `tools` line.
- **Dependencies.** One `httpx.AsyncClient` is shared by every tool call through `ctx.deps`. The model never sees
  it; it only sees the tools' parameters.
- **Retries.** When the city isn't found, `ModelRetry` sends the message back to the model, which tries another
  spelling. `retries=2` allows two more attempts before the run fails.
- **Weekdays are computed, not inferred.** The forecast returns each day's weekday. Given bare dates and asked
  on a Thursday about "this weekend", the model called Friday "Saturday" and Saturday "Sunday".
- **Tools are passed as a list**, not with `@agent.tool`. Both work in Pydantic AI; the list keeps
  `mypy --strict` passing when `pydantic_ai` is not installed, as in this repository's CI.

## Troubleshooting

- **`SAMBANOVA_API_KEY is not set`**: create `.env` from `.env.example` in this folder and add the key.
- **`error: status_code: 401 ... invalid_api_key`**: the key in `.env` is wrong or revoked. Create a new one in
  [SambaCloud](https://cloud.sambanova.ai/apis).
- **`error: weather service request failed: ...`**: Open-Meteo was unreachable, timed out or returned an error
  such as a 429. The session keeps running; ask again.
- **`error: Tool 'find_city' exceeded max retries count of 2`**: the place doesn't exist in Open-Meteo's geocoder,
  even after the model tried other spellings. Ask with a city name in English.
- **`UserError: Native structured output is not supported by this model`**: you changed `output_type` to
  `NativeOutput(TripBrief)`. Keep the plain `TripBrief`; the default mode uses a tool call.
- **An older `pydantic-ai-slim` was installed**: Pydantic AI 2.59 needs Python 3.11 or later. On Python 3.10, `pip`
  installs an older release without an error. Check with `pip show pydantic-ai-slim` and recreate the virtual
  environment on Python 3.11 or later.
- **Each answer takes 15 to 40 seconds**: that is `MiniMax-M3` reasoning. Set
  `SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct` for faster, shorter answers.
