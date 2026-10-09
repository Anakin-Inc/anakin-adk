# Changelog

## 0.2.0 (unreleased)

Rebuilt on the official [`anakin-sdk`](https://github.com/Anakin-Inc/anakin-py) (`AsyncAnakin`). `anakin-cli` is no longer required.

### Added
- 18 new tools matching the Anakin MCP server: `map_website`, `crawl_website`, `wire_discover`, `wire_catalog`, `wire_read_action`, `wire_identities`, `wire_build_status`, `ai_visibility_search`, `ai_visibility_sources`, `monitor_list`, `monitor_changes`, `session_list`, and the opt-in write tools `wire_write_action`, `wire_login`, `wire_build`, `monitor_create`, `monitor_control`, `session_delete`.
- Write tools ask the user for confirmation before running (ADK tool confirmation), unless `require_confirmation=False`.
- `AnakinToolset`, an ADK `BaseToolset` (`Agent(tools=[AnakinToolset()])`) with `tool_filter` / `tool_name_prefix`.
- `AnakinToolkit(api_key=, base_url=, tools=, include_write_tools=, require_confirmation=, max_chars=)`.
- `scrape_website`: `output_schema`, `session_id`, and the `html` / `links` / `summary` formats.
- `deep_research`: optional `schema` for structured output.
- Keyless mode: scraping and Wire discovery work without an API key.
- Errors come back with a `hint` (signup link, Wire connect URL, ...). Results are capped at `max_chars`.

### Changed
- `AnakinToolkit().get_tools()` returns all read tools (16) instead of 4. Pass `tools=[...]` to choose.
- `scrape_website` defaults to `format="markdown"` (was `"json"`, which ran AI extraction on every call). Use `format="json"` or `output_schema` for structured data.
- Credentials: `api_key` argument > `ANAKIN_API_KEY` > `~/.anakin/config.json` (from `anakin login`).
- Requires `google-adk>=1.16` and `anakin-sdk>=0.2.0`.

### Fixed
- `__version__` reported `0.1.2` while the package was `0.1.3`.
- The integrations page told users to run `anakin auth`, which doesn't exist.
- The documentation URL pointed at `docs.anakin.io`, which doesn't resolve.

### Removed
- The `anakin-cli` subprocess wrapper (`anakin_adk._cli`).

## 0.1.3 (2026-03-06)

- Fix auth docs: `anakin auth` → `anakin login --api-key`
- Add "How it works" section with architecture diagram
- Improve tool descriptions with speed estimates
- Add troubleshooting section

## 0.1.2 (2026-03-03)

- Build configuration improvements

## 0.1.1 (2026-03-03)

- Fix website URLs: useanakin.com -> anakin.io
- Add Python 3.13 classifier

## 0.1.0 (2026-03-03)

Initial release.

- `ScrapeWebsiteTool` — scrape a single URL to markdown or JSON
- `BatchScrapeTool` — scrape up to 10 URLs at once
- `SearchWebTool` — AI-powered web search
- `DeepResearchTool` — autonomous deep research
- `AnakinToolkit` — convenience class returning all 4 tools
