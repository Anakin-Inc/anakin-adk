# anakin-adk

Google ADK tools for web scraping, search, and research — powered by [Anakin](https://anakin.io).

Give your Gemini agents the ability to scrape websites, search the web, and run deep research — all through a simple toolkit that plugs into Google's [Agent Development Kit](https://google.github.io/adk-docs/).

## Installation

```bash
pip install anakin-adk
```

You also need the Anakin CLI installed and authenticated:

```bash
pip install anakin-cli
anakin login --api-key "ask_your-key-here"
```

Get your API key by signing up at [anakin.io/signup](https://anakin.io/signup) — then grab the key (starts with `ask_`) from your dashboard. Verify with:

```bash
anakin status
```

## Quick start

```python
from anakin_adk import AnakinToolkit
from google.adk.agents import Agent

agent = Agent(
    model="gemini-2.5-pro",
    name="web_researcher",
    instruction="Help users extract data from the web",
    tools=AnakinToolkit().get_tools(),
)
```

Run with the ADK dev UI:

```bash
adk web
```

## How it works

```
Your ADK Agent (Gemini)
        │
        ▼
   anakin-adk          ← this package: exposes tools to ADK
        │
        ▼
   anakin-cli           ← local CLI that talks to the Anakin API
        │
        ▼
   Anakin Cloud API     ← handles scraping, search, and research
```

1. Your Gemini agent decides to call a tool (e.g. `scrape_website`).
2. `anakin-adk` translates the call into an `anakin-cli` command.
3. The CLI sends the request to the Anakin cloud API, which handles proxy rotation, browser rendering, and anti-detection.
4. Results come back as clean markdown or structured JSON, ready for the agent to use.

## Available tools

| Tool | Description | Speed |
|------|-------------|-------|
| `scrape_website` | Scrape a single URL and return clean markdown or structured JSON. Supports headless browser for JS-heavy sites, geo-targeted proxies (207 countries), and AI extraction. | 3–15s |
| `batch_scrape` | Scrape up to 10 URLs at once and return combined results. | 5–30s |
| `search_web` | AI-powered web search returning titles, URLs, and snippets with citations. | Instant |
| `deep_research` | Autonomous multi-stage research — searches, scrapes, and synthesizes a comprehensive report. | 1–5 min |

## Using individual tools

You can pick only the tools you need:

```python
from anakin_adk import ScrapeWebsiteTool, SearchWebTool
from google.adk.agents import Agent

agent = Agent(
    model="gemini-2.5-pro",
    name="search_and_scrape",
    instruction="Search the web and scrape relevant pages",
    tools=[SearchWebTool(), ScrapeWebsiteTool()],
)
```

## Examples

See the [`examples/`](examples/) directory:

- **`basic_scraping.py`** — Simple scrape agent
- **`research_agent.py`** — Deep research agent
- **`search_and_scrape.py`** — Multi-step: search then scrape

## Troubleshooting

| Error | Cause |
|-------|-------|
| `401 Unauthorized` | Invalid or missing API key. Run `anakin login --api-key "ask_..."` |
| `402 Payment Required` | Free tier exceeded — upgrade your plan at anakin.io |
| `429 Too Many Requests` | Rate limited — slow down or upgrade |
| `anakin: command not found` | CLI not installed. Run `pip install anakin-cli` |

For JS-heavy sites that return empty content, try setting `use_browser=true` in the `scrape_website` tool.

Check your auth status anytime with `anakin status`.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check anakin_adk/
```

## License

MIT
