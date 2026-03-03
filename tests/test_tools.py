"""Unit tests for anakin_adk tools (all subprocess calls mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from anakin_adk.tools import (
    BatchScrapeTool,
    DeepResearchTool,
    ScrapeWebsiteTool,
    SearchWebTool,
)


@pytest.fixture
def mock_tool_context():
    return AsyncMock()


# ---------------------------------------------------------------------------
# ScrapeWebsiteTool
# ---------------------------------------------------------------------------


class TestScrapeWebsiteTool:
    def test_declaration(self):
        tool = ScrapeWebsiteTool()
        decl = tool._get_declaration()
        assert decl is not None
        assert decl.name == "scrape_website"
        assert "url" in str(decl.parameters_json_schema)

    @pytest.mark.asyncio
    async def test_missing_url(self, mock_tool_context):
        tool = ScrapeWebsiteTool()
        result = await tool.run_async(args={}, tool_context=mock_tool_context)
        assert result["status"] == "error"
        assert "url is required" in result["error_message"]

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_scrape_success(self, mock_run, mock_tool_context):
        mock_run.return_value = {"title": "Example", "content": "Hello world"}
        tool = ScrapeWebsiteTool()
        result = await tool.run_async(
            args={"url": "https://example.com"}, tool_context=mock_tool_context
        )
        assert result["status"] == "success"
        assert result["data"]["title"] == "Example"
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_scrape_with_options(self, mock_run, mock_tool_context):
        mock_run.return_value = {"content": "data"}
        tool = ScrapeWebsiteTool()
        await tool.run_async(
            args={
                "url": "https://example.com",
                "format": "markdown",
                "use_browser": True,
                "country": "us",
                "timeout": 30,
            },
            tool_context=mock_tool_context,
        )
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "scrape" in cmd
        assert "--browser" in cmd
        assert "--country" in cmd
        assert "us" in cmd

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_scrape_cli_error(self, mock_run, mock_tool_context):
        from anakin_adk._cli import AnakinCLIError

        mock_run.side_effect = AnakinCLIError("CLI not found")
        tool = ScrapeWebsiteTool()
        result = await tool.run_async(
            args={"url": "https://example.com"}, tool_context=mock_tool_context
        )
        assert result["status"] == "error"
        assert "CLI not found" in result["error_message"]


# ---------------------------------------------------------------------------
# BatchScrapeTool
# ---------------------------------------------------------------------------


class TestBatchScrapeTool:
    def test_declaration(self):
        tool = BatchScrapeTool()
        decl = tool._get_declaration()
        assert decl is not None
        assert decl.name == "batch_scrape"

    @pytest.mark.asyncio
    async def test_empty_urls(self, mock_tool_context):
        tool = BatchScrapeTool()
        result = await tool.run_async(args={"urls": []}, tool_context=mock_tool_context)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_too_many_urls(self, mock_tool_context):
        tool = BatchScrapeTool()
        urls = [f"https://example.com/{i}" for i in range(11)]
        result = await tool.run_async(args={"urls": urls}, tool_context=mock_tool_context)
        assert result["status"] == "error"
        assert "Maximum 10" in result["error_message"]

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_batch_success(self, mock_run, mock_tool_context):
        mock_run.return_value = {"results": [{"url": "https://a.com", "content": "A"}]}
        tool = BatchScrapeTool()
        result = await tool.run_async(
            args={"urls": ["https://a.com", "https://b.com"]},
            tool_context=mock_tool_context,
        )
        assert result["status"] == "success"
        mock_run.assert_awaited_once()


# ---------------------------------------------------------------------------
# SearchWebTool
# ---------------------------------------------------------------------------


class TestSearchWebTool:
    def test_declaration(self):
        tool = SearchWebTool()
        decl = tool._get_declaration()
        assert decl is not None
        assert decl.name == "search_web"

    @pytest.mark.asyncio
    async def test_missing_query(self, mock_tool_context):
        tool = SearchWebTool()
        result = await tool.run_async(args={}, tool_context=mock_tool_context)
        assert result["status"] == "error"
        assert "query is required" in result["error_message"]

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_search_success(self, mock_run, mock_tool_context):
        mock_run.return_value = {"results": [{"title": "Result 1", "url": "https://r.com"}]}
        tool = SearchWebTool()
        result = await tool.run_async(
            args={"query": "python web scraping"}, tool_context=mock_tool_context
        )
        assert result["status"] == "success"
        assert "results" in result["data"]


# ---------------------------------------------------------------------------
# DeepResearchTool
# ---------------------------------------------------------------------------


class TestDeepResearchTool:
    def test_declaration(self):
        tool = DeepResearchTool()
        decl = tool._get_declaration()
        assert decl is not None
        assert decl.name == "deep_research"

    def test_is_long_running(self):
        tool = DeepResearchTool()
        assert tool.is_long_running is True

    @pytest.mark.asyncio
    async def test_missing_topic(self, mock_tool_context):
        tool = DeepResearchTool()
        result = await tool.run_async(args={}, tool_context=mock_tool_context)
        assert result["status"] == "error"
        assert "topic is required" in result["error_message"]

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_research_success(self, mock_run, mock_tool_context):
        mock_run.return_value = {"report": "Comprehensive analysis..."}
        tool = DeepResearchTool()
        result = await tool.run_async(
            args={"topic": "AI trends 2026"}, tool_context=mock_tool_context
        )
        assert result["status"] == "success"
        assert "report" in result["data"]

    @pytest.mark.asyncio
    @patch("anakin_adk.tools.run_anakin_command")
    async def test_timeout_capped(self, mock_run, mock_tool_context):
        mock_run.return_value = {"report": "done"}
        tool = DeepResearchTool()
        await tool.run_async(
            args={"topic": "test", "timeout": 9999}, tool_context=mock_tool_context
        )
        # Timeout should be capped at 600
        call_args = mock_run.call_args
        assert call_args[1]["timeout"] == 600
