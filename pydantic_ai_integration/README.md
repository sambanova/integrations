# SambaNova + Pydantic AI: a trip-briefing agent with typed output

A terminal travel assistant built with [Pydantic AI](https://pydantic.dev/docs/ai/) on SambaCloud. Ask about a city
and the agent looks it up, fetches a live forecast, and answers with a validated `TripBrief` object instead of free
text. Follow-up questions keep the conversation, so "what should I pack?" knows which city you meant.

It puts the pieces the [Pydantic AI integration guide](https://docs.sambanova.ai/docs/en/integrations/pydantic-ai)
shows one at a time into one app: Pydantic AI's built-in SambaNova provider, structured output, two tools the model
chains together, dependency injection, retries, and multi-turn history.

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

  Lisbon, Portugal  |  local time 2026-10-22T16:00
  now: mainly clear, 19°C
  Thu 2026-10-22: overcast, 8 to 20°C, rain 0%
  Fri 2026-10-23: overcast, 13 to 22°C, rain 3%
  Sat 2026-10-24: overcast, 9 to 23°C, rain 0%
  Sun 2026-10-25: overcast, 11 to 24°C, rain 0%
  Mon 2026-10-26: fog, 13 to 24°C, rain 0%
  pack: Light jacket or cardigan for cooler mornings (around 12–13°C); Comfortable walking shoes for cobblestone streets; Sunglasses for breaks in the overcast sky

  No umbrella needed — Lisbon is overcast but dry tomorrow (Friday), with only a 3% chance of rain and a pleasant high of 22°C. Pack a light layer for the cooler morning low around 13°C.

  tools: find_city, get_forecast  |  21.6 s

you > What about Kyoto this weekend?

  Kyoto, Japan  |  local time 2026-10-23T00:00
  now: overcast, 14°C
  Fri 2026-10-23: light drizzle, 12 to 21°C, rain 73%
  Sat 2026-10-24: rain, 18 to 20°C, rain 100%
  Sun 2026-10-25: rain, 19 to 22°C, rain 73%
  Mon 2026-10-26: rain showers, 18 to 23°C, rain 76%
  Tue 2026-10-27: rain showers, 15 to 26°C, rain 71%
  pack: Compact umbrella and a waterproof jacket; Waterproof shoes for temple gardens and wet streets; Light layers for mild 18–22°C days

  Yes, definitely pack an umbrella — Kyoto is in for a wet weekend, with rain likely both Saturday (100% chance) and Sunday (73% chance), and highs only around 20–22°C. Bring a waterproof jacket and shoes suitable for rainy temple walks.

  tools: find_city, get_forecast  |  21.0 s

you > What should I pack for Kyoto?

  Kyoto, Japan  |  local time 2026-10-23T00:00
  now: overcast, 14°C
  Fri 2026-10-23: light drizzle, 12 to 21°C, rain 73%
  Sat 2026-10-24: rain, 18 to 20°C, rain 100%
  Sun 2026-10-25: rain, 19 to 22°C, rain 73%
  Mon 2026-10-26: rain showers, 18 to 23°C, rain 76%
  Tue 2026-10-27: rain showers, 15 to 26°C, rain 71%
  pack: Compact umbrella and a waterproof jacket; Waterproof shoes for temple gardens and wet streets; Light layers for mild 18–22°C days; Bag cover or dry sack for electronics and documents

  Pack a compact umbrella and a waterproof jacket — rain is expected all weekend (100% chance Saturday, 73% Sunday). Bring waterproof shoes for wet temple paths, light layers for mild 18–22°C days, and a small bag cover to protect your belongings.

  tools: none  |  17.1 s
```

- **tools**: the tools the model called this turn. The third question needed none: the Kyoto forecast was already
  in the conversation history.
- Most of each turn's time is `MiniMax-M3` reasoning before it calls a tool. A model without a reasoning phase,
  such as `Meta-Llama-3.3-70B-Instruct`, answers the same question in a few seconds.

## How it works

```text
question ─► Agent("sambanova:MiniMax-M3") ─► find_city ──► Open-Meteo geocoding
                    ▲                    └─► get_forecast ─► Open-Meteo forecast
                    │                    └─► final_result ─► TripBrief (validated) ─► printed
                    └── message_history: the whole conversation, sent again on the next turn
```

The core of `main.py`, trimmed:

```python
class TripBrief(BaseModel):
    city: str
    country: str
    local_time: str
    current_conditions: str
    current_temperature_c: float
    next_days: list[DayForecast]
    packing_tips: list[str]
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
- **`error: Tool 'find_city' exceeded max retries count of 2`**: the place doesn't exist in Open-Meteo's geocoder,
  even after the model tried other spellings. Ask with a city name in English.
- **`UserError: Native structured output is not supported by this model`**: you changed `output_type` to
  `NativeOutput(TripBrief)`. Keep the plain `TripBrief`; the default mode uses a tool call.
- **An older `pydantic-ai-slim` was installed**: Pydantic AI 2.59 needs Python 3.11 or later. On Python 3.10, `pip`
  installs an older release without an error. Check with `pip show pydantic-ai-slim` and recreate the virtual
  environment on Python 3.11 or later.
- **Each answer takes about 20 seconds**: that is `MiniMax-M3` reasoning. Set
  `SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct` for faster, shorter answers.
