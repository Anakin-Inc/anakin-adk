---
catalog_title: Anakin
catalog_description: Scrape, crawl, search, research and run pre-built actions on hundreds of websites from your agent
catalog_icon: /adk-docs/integrations/assets/anakin.png
catalog_tags: ["data"]
---

# Anakin plugin for ADK

<div class="language-support-tag">
  <span class="lst-supported">Supported in ADK</span><span class="lst-python">Python</span>
</div>

The [Anakin ADK plugin](https://github.com/Anakin-Inc/anakin-adk) connects your
ADK agent to [Anakin](https://anakin.io), the API layer for the web. Your agent
can scrape and crawl websites, search, run deep research, call pre-built Wire
actions on hundreds of sites, monitor pages for changes, and compare what AI
answer engines say.

## Use cases

- **Web scraping and crawling**: Turn any page, or a whole site, into clean
  markdown or AI-extracted JSON, including JavaScript-heavy and login-protected
  pages.

- **Pre-built site actions (Wire)**: Get structured data from Amazon, Walmart,
  LinkedIn, Airbnb, Zillow and hundreds more without writing scrapers.

- **Search and deep research**: Find sources, or run multi-source research
  that returns a summary plus structured data.

- **Monitoring and AI visibility**: Track page changes, and see what ChatGPT,
  Gemini and Google AI Overview say about a topic or brand.

## Prerequisites

- An [Anakin API key](https://anakin.io/signup) (free tier: 300 credits).
  Scraping and Wire discovery also work without one.

## Installation

```bash
pip install anakin-adk
export ANAKIN_API_KEY="ak-..."
```

## Use with agent

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

## Available tools

Tool | Description
---- | -----------
`scrape_website` | Scrape a URL to markdown, AI-extracted JSON, html, links or a summary
`batch_scrape` | Scrape up to 10 URLs at once
`search_web` | AI web search returning titles, URLs, and snippets
`deep_research` | Multi-source research returning a summary and structured data
`map_website` | List the URLs on a website
`crawl_website` | Fetch markdown for many pages of a site
`wire_discover` | Find a pre-built Wire action by intent
`wire_catalog` | Browse supported sites and their actions
`wire_read_action` | Run a Wire read action
`wire_identities` | List saved site accounts
`wire_build_status` | Check Wire build requests
`ai_visibility_search` | Compare answers from multiple AI engines
`ai_visibility_sources` | List available AI engines
`monitor_list` | List website monitors
`monitor_changes` | Read changes a monitor detected
`session_list` | List saved browser sessions

Write tools (`wire_write_action`, `wire_login`, `wire_build`, `monitor_create`,
`monitor_control`, `session_delete`) are opt-in with
`AnakinToolset(include_write_tools=True)` and ask the user to confirm each call.

## Additional resources

- [Anakin ADK on PyPI](https://pypi.org/project/anakin-adk/)
- [Anakin ADK on GitHub](https://github.com/Anakin-Inc/anakin-adk)
- [Anakin API documentation](https://anakin.io/docs)
- [Anakin Website](https://anakin.io)
