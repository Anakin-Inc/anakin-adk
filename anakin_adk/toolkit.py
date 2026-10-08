"""AnakinToolkit / AnakinToolset: all Anakin tools for ADK agents."""

from __future__ import annotations

from collections.abc import Sequence

from anakin import AsyncAnakin
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from ._client import ClientSettings
from .tools import DEFAULT_MAX_CHARS, READ_TOOLS, WRITE_TOOLS, AnakinTool, make_tool


def _select(tools: Sequence[str] | None, include_write_tools: bool) -> list[str]:
    if tools is not None:
        return list(tools)
    return READ_TOOLS + (WRITE_TOOLS if include_write_tools else [])


class AnakinToolkit:
    """A collection of Anakin tools: scraping, search, research, Wire, monitoring, AI visibility.

    Usage::

        from anakin_adk import AnakinToolkit
        from google.adk.agents import Agent

        agent = Agent(
            model="gemini-2.5-pro",
            name="web_researcher",
            instruction="Help users extract data from the web",
            tools=AnakinToolkit().get_tools(),
        )

    Args:
        api_key: Anakin API key. Defaults to ANAKIN_API_KEY, then the key saved
            by `anakin login`. Without one, scrape and Wire discovery still work
            on the free keyless tier.
        base_url: API base URL (self-hosted AnakinScraper, tests).
        tools: Exact tool names to include (see `READ_TOOLS`, `WRITE_TOOLS`).
        include_write_tools: Also include state-changing tools (Wire write
            actions, login, builds, monitor create/control, session delete).
        require_confirmation: Ask the user before each write tool runs
            (default True). Set False only for trusted, unattended agents.
        max_chars: Cap on each tool result's size.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        tools: Sequence[str] | None = None,
        include_write_tools: bool = False,
        require_confirmation: bool = True,
        max_chars: int = DEFAULT_MAX_CHARS,
        client: AsyncAnakin | None = None,
    ) -> None:
        self._settings = ClientSettings(api_key=api_key, base_url=base_url)
        self._names = _select(tools, include_write_tools)
        self._require_confirmation = require_confirmation
        self._max_chars = max_chars
        self._client = client

    def get_tools(self) -> list[BaseTool]:
        """Return the selected Anakin tool instances."""
        tools: list[BaseTool] = []
        for name in self._names:
            tool: AnakinTool = make_tool(
                name,
                settings=self._settings,
                client=self._client,
                max_chars=self._max_chars,
            )
            if tool.write:
                tool._require_confirmation = self._require_confirmation
            tools.append(tool)
        return tools


class AnakinToolset(BaseToolset):
    """ADK-native toolset form of `AnakinToolkit`: ``Agent(tools=[AnakinToolset()])``.

    Accepts the same arguments as `AnakinToolkit`, plus ADK's `tool_filter`
    and `tool_name_prefix`.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        tools: Sequence[str] | None = None,
        include_write_tools: bool = False,
        require_confirmation: bool = True,
        max_chars: int = DEFAULT_MAX_CHARS,
        client: AsyncAnakin | None = None,
        tool_filter: list[str] | None = None,
        tool_name_prefix: str | None = None,
    ) -> None:
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._toolkit = AnakinToolkit(
            api_key=api_key,
            base_url=base_url,
            tools=tools,
            include_write_tools=include_write_tools,
            require_confirmation=require_confirmation,
            max_chars=max_chars,
            client=client,
        )

    async def get_tools(self, readonly_context: ReadonlyContext | None = None) -> list[BaseTool]:
        return [
            tool
            for tool in self._toolkit.get_tools()
            if self._is_tool_selected(tool, readonly_context)
        ]
