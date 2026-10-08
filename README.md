# anakin-adk

Google ADK tools for [Anakin](https://anakin.io): give your Gemini agents the web. Scrape and crawl sites, search, run deep research, call pre-built **Wire** actions on hundreds of sites (Amazon, Walmart, LinkedIn, Airbnb, Zillow, ...), monitor pages for changes, and compare what AI engines say, all from Google's [Agent Development Kit](https://google.github.io/adk-docs/).

Built on the official [`anakin-sdk`](https://github.com/Anakin-Inc/anakin-py): no CLI or subprocess required.

## Installation

```bash
pip install anakin-adk
export ANAKIN_API_KEY="ak-..."   # free key with 300 credits: https://anakin.io/signup
```

No key yet? `scrape_website`, `wire_discover` and `wire_catalog` work on the free keyless tier. A key saved with `anakin login` (from [anakin-cli](https://github.com/Anakin-Inc/anakin-cli)) is picked up automatically.

## Quick start

```python
from anakin_adk import AnakinToolset
from google.adk.agents import Agent

agent = Agent(
    model="gemini-2.5-pro",
    name="web_researcher",
    instruction="Help users extract data from the web",
    tools=[AnakinToolset()],
)
```

Run with the ADK dev UI:

```bash
adk web
```

`AnakinToolkit().get_tools()` returns the same tools as a plain list, if you prefer.

## How it works

```
Your ADK Agent (Gemini)
        │
        ▼
   anakin-adk        ← this package: ADK tools
        │
        ▼
   anakin-sdk        ← official async Python client (retries, polling, typed errors)
        │
        ▼
   Anakin API        ← proxies, browser rendering, anti-detection, Wire actions
```

Every tool returns `{"status": "success", "data": ...}` or `{"status": "error", "error_message": ..., "hint": ...}`, so the agent can recover (e.g. the hint carries the link to connect a site account). Results are capped at 100,000 characters (`max_chars`) so a big crawl can't flood the context.

## Available tools

Read tools (included by default):

| Tool | What it does | Speed |
|------|-------------|-------|
| `scrape_website` | One URL as markdown, AI-extracted JSON (`output_schema`), html, links or summary. Headless browser, 207 proxy countries, saved login sessions. | 3–15s |
| `batch_scrape` | Up to 10 URLs in parallel | 5–30s |
| `search_web` | AI web search: URLs, titles, snippets | Instant |
| `deep_research` | Multi-source research: summary + structured data | 1–5 min |
| `map_website` | List a site's URLs | Seconds |
| `crawl_website` | Markdown for many pages (include/exclude patterns) | 10s–minutes |
| `wire_discover` | Find a pre-built Wire action by intent | Instant |
| `wire_catalog` | Browse supported sites, or one site's actions and params | Instant |
| `wire_read_action` | Run a Wire read action (search listings, product details, profiles) | 3–30s |
| `wire_identities` | Saved site accounts and their `credential_id`s | Instant |
| `wire_build_status` | Status of Wire build requests | Instant |
| `ai_visibility_search` | Ask ChatGPT, Gemini, Google AI Overview (and more) the same question and compare | 1–2 min |
| `ai_visibility_sources` | Available AI engines | Instant |
| `monitor_list` / `monitor_changes` | Website monitors and the changes they detected | Instant |
| `session_list` | Saved browser login sessions | Instant |

Write tools (opt-in with `include_write_tools=True`; they change state, so each call **asks the user to confirm** via ADK tool confirmation):

| Tool | What it does |
|------|-------------|
| `wire_write_action` | Run a Wire action that changes something on a site (submit a form, post, update settings) |
| `wire_login` | Sign in to a site and get a `credential_id` (password never stored) |
| `wire_build` | Request new Wire actions for a site not in the catalog (charges credits) |
| `monitor_create` / `monitor_control` | Create, pause, resume, run or delete a monitor |
| `session_delete` | Delete a saved browser session |

```python
AnakinToolset(include_write_tools=True)  # confirm each write
AnakinToolset(
    include_write_tools=True, require_confirmation=False
)  # trusted, unattended agents only
```

## Choosing tools

Fewer tools means faster, more accurate tool selection. Pick only what your agent needs:

```python
from anakin_adk import AnakinToolset, ScrapeWebsiteTool, SearchWebTool

AnakinToolset(tools=["wire_discover", "wire_catalog", "wire_read_action"])  # a Wire agent
AnakinToolset(tool_filter=["search_web", "scrape_website"])  # ADK-style filter
tools = [SearchWebTool(), ScrapeWebsiteTool()]  # individual classes
```

## Configuration

```python
AnakinToolset(
    api_key="ak-...",  # default: ANAKIN_API_KEY, then ~/.anakin/config.json
    base_url="http://localhost:8080",  # self-hosted AnakinScraper (default: hosted API)
    max_chars=100_000,  # cap on each tool result
)
```

## Examples

See [`examples/`](examples/):

- **`basic_scraping.py`**: simple scrape agent
- **`search_and_scrape.py`**: search, then scrape the best results
- **`research_agent.py`**: deep research agent
- **`wire_agent.py`**: discover and run Wire actions on real sites

## Troubleshooting

| Error / hint | Cause |
|-------|-------|
| `needs an Anakin API key` | The tool needs a key: set `ANAKIN_API_KEY` ([free key](https://anakin.io/signup)) |
| `401` | Invalid key |
| `402` | Out of credits (or the keyless tier is unavailable): the hint has a link |
| Wire `AUTH_REQUIRED` | The user must connect that site's account: the hint has the URL |
| `This call needs user confirmation` | A write tool is waiting for the user to approve it in your ADK UI |

For JS-heavy sites that return empty content, set `use_browser=true` on `scrape_website`.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

## License

MIT
