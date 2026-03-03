# anakin-adk

Google ADK tools for web scraping, search, and research — powered by [Anakin](https://anakin.io).

## Installation

```bash
pip install anakin-adk
```

You also need the Anakin CLI installed and authenticated:

```bash
pip install anakin-cli
anakin auth
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

## Available tools

| Tool | Description |
|------|-------------|
| `scrape_website` | Scrape a single URL and return clean markdown or structured JSON |
| `batch_scrape` | Scrape up to 10 URLs at once and return combined results |
| `search_web` | AI-powered web search returning titles, URLs, and snippets |
| `deep_research` | Autonomous deep research that explores the web and returns a comprehensive report |

## Using individual tools

You can also use tools individually:

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

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check anakin_adk/
```

## License

MIT
