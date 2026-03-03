"""AnakinToolkit — provides all Anakin tools for use with ADK agents."""

from __future__ import annotations

from google.adk.tools.base_tool import BaseTool

from .tools import BatchScrapeTool, DeepResearchTool, ScrapeWebsiteTool, SearchWebTool


class AnakinToolkit:
    """A collection of web scraping, search, and research tools powered by Anakin.

    Usage::

        from anakin_adk import AnakinToolkit
        from google.adk.agents import Agent

        agent = Agent(
            model="gemini-2.5-pro",
            name="web_researcher",
            instruction="Help users extract data from the web",
            tools=AnakinToolkit().get_tools(),
        )
    """

    def get_tools(self) -> list[BaseTool]:
        """Return all Anakin tool instances."""
        return [
            ScrapeWebsiteTool(),
            BatchScrapeTool(),
            SearchWebTool(),
            DeepResearchTool(),
        ]
