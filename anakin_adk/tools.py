"""ADK tool implementations wrapping anakin-cli commands."""

from __future__ import annotations

from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ._cli import AnakinCLIError, run_anakin_command


class ScrapeWebsiteTool(BaseTool):
    """Scrape a single URL and return clean, structured content."""

    def __init__(self) -> None:
        super().__init__(
            name="scrape_website",
            description=(
                "Scrape a single web page and return its content as clean markdown or "
                "structured JSON. Use for extracting articles, product pages, docs, etc."
            ),
        )

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the web page to scrape.",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format for the scraped content.",
                        "enum": ["markdown", "json"],
                        "default": "json",
                    },
                    "use_browser": {
                        "type": "boolean",
                        "description": (
                            "Use a headless browser for JavaScript-rendered pages."
                        ),
                        "default": False,
                    },
                    "country": {
                        "type": "string",
                        "description": (
                            "Two-letter country code for geo-targeted scraping "
                            "(e.g. 'us', 'gb')."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds for the scrape operation.",
                        "default": 60,
                    },
                },
                "required": ["url"],
            },
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        url = args.get("url")
        if not url:
            return {"status": "error", "error_message": "url is required"}

        cmd = ["scrape", url]

        fmt = args.get("format", "json")

        if args.get("use_browser"):
            cmd.append("--browser")

        country = args.get("country")
        if country:
            cmd.extend(["--country", country])

        timeout = args.get("timeout", 60)

        try:
            result = await run_anakin_command(cmd, output_format=fmt, timeout=timeout)
            return {"status": "success", "data": result}
        except AnakinCLIError as e:
            return {"status": "error", "error_message": str(e)}


class BatchScrapeTool(BaseTool):
    """Scrape multiple URLs at once (up to 10) and return combined results."""

    def __init__(self) -> None:
        super().__init__(
            name="batch_scrape",
            description=(
                "Scrape up to 10 web pages at once and return combined results. "
                "Use for comparing products, collecting articles, or gathering data "
                "from multiple sources."
            ),
        )

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to scrape (max 10).",
                        "maxItems": 10,
                    },
                },
                "required": ["urls"],
            },
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        urls = args.get("urls", [])
        if not urls:
            return {"status": "error", "error_message": "urls list is required"}

        if len(urls) > 10:
            return {
                "status": "error",
                "error_message": "Maximum 10 URLs allowed per batch request.",
            }

        cmd = ["scrape-batch", *urls]

        try:
            result = await run_anakin_command(cmd, timeout=120)
            return {"status": "success", "data": result}
        except AnakinCLIError as e:
            return {"status": "error", "error_message": str(e)}


class SearchWebTool(BaseTool):
    """Run an AI-powered web search and return relevant results."""

    def __init__(self) -> None:
        super().__init__(
            name="search_web",
            description=(
                "Run an AI-powered web search and return relevant results with "
                "titles, URLs, and snippets. Use for finding pages, answering "
                "questions, or discovering sources on a topic."
            ),
        )

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                },
                "required": ["query"],
            },
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        query = args.get("query")
        if not query:
            return {"status": "error", "error_message": "query is required"}

        cmd = ["search", query]

        try:
            result = await run_anakin_command(cmd, timeout=30)
            return {"status": "success", "data": result}
        except AnakinCLIError as e:
            return {"status": "error", "error_message": str(e)}


class DeepResearchTool(BaseTool):
    """Run a deep agentic research task that autonomously explores the web."""

    def __init__(self) -> None:
        super().__init__(
            name="deep_research",
            description=(
                "Run a deep agentic research task that autonomously explores "
                "the web and returns a comprehensive report. Use for comparisons, "
                "market analysis, technical deep-dives, or questions requiring "
                "multiple sources. Takes 1-5 minutes."
            ),
            is_long_running=True,
        )

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic or question.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 300, max 600).",
                        "default": 300,
                    },
                },
                "required": ["topic"],
            },
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        topic = args.get("topic")
        if not topic:
            return {"status": "error", "error_message": "topic is required"}

        timeout = min(args.get("timeout", 300), 600)
        cmd = ["research", topic]

        try:
            result = await run_anakin_command(cmd, timeout=timeout)
            return {"status": "success", "data": result}
        except AnakinCLIError as e:
            return {"status": "error", "error_message": str(e)}
