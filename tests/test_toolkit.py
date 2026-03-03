"""Integration tests for AnakinToolkit."""

from __future__ import annotations

from anakin_adk import (
    AnakinToolkit,
    BatchScrapeTool,
    DeepResearchTool,
    ScrapeWebsiteTool,
    SearchWebTool,
    __version__,
)


class TestAnakinToolkit:
    def test_get_tools_returns_four(self):
        toolkit = AnakinToolkit()
        tools = toolkit.get_tools()
        assert len(tools) == 4

    def test_get_tools_types(self):
        toolkit = AnakinToolkit()
        tools = toolkit.get_tools()
        types = {type(t) for t in tools}
        assert types == {ScrapeWebsiteTool, BatchScrapeTool, SearchWebTool, DeepResearchTool}

    def test_all_tools_have_declarations(self):
        toolkit = AnakinToolkit()
        for tool in toolkit.get_tools():
            decl = tool._get_declaration()
            assert decl is not None, f"{tool.name} missing declaration"
            assert decl.name == tool.name

    def test_tool_names_unique(self):
        toolkit = AnakinToolkit()
        names = [t.name for t in toolkit.get_tools()]
        assert len(names) == len(set(names))

    def test_version(self):
        assert __version__ == "0.1.0"

    def test_get_tools_returns_new_instances(self):
        toolkit = AnakinToolkit()
        tools_a = toolkit.get_tools()
        tools_b = toolkit.get_tools()
        for a, b in zip(tools_a, tools_b):
            assert a is not b
