"""Tests for AnakinToolkit and AnakinToolset."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import anakin_adk
from anakin_adk import (
    READ_TOOLS,
    WRITE_TOOLS,
    AnakinToolkit,
    AnakinToolset,
    ScrapeWebsiteTool,
    make_tool,
)


def test_default_toolkit_is_read_only() -> None:
    tools = AnakinToolkit().get_tools()
    names = [t.name for t in tools]
    assert names == READ_TOOLS
    assert not set(names) & set(WRITE_TOOLS)
    assert {"scrape_website", "batch_scrape", "search_web", "deep_research"} <= set(names)


def test_write_tools_are_opt_in_and_confirmation_gated() -> None:
    tools = AnakinToolkit(include_write_tools=True).get_tools()
    writes = [t for t in tools if t.name in WRITE_TOOLS]
    assert len(writes) == len(WRITE_TOOLS)
    assert all(t._require_confirmation for t in writes)
    assert not any(t._require_confirmation for t in tools if t.name in READ_TOOLS)

    unattended = AnakinToolkit(include_write_tools=True, require_confirmation=False).get_tools()
    assert not any(t._require_confirmation for t in unattended)


def test_explicit_tool_selection() -> None:
    tools = AnakinToolkit(tools=["wire_discover", "wire_read_action"]).get_tools()
    assert [t.name for t in tools] == ["wire_discover", "wire_read_action"]


def test_unknown_tool_name() -> None:
    with pytest.raises(ValueError, match="Unknown Anakin tool"):
        make_tool("nope")


def test_all_tools_have_unique_valid_declarations() -> None:
    tools = AnakinToolkit(include_write_tools=True).get_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names))
    for tool in tools:
        decl = tool._get_declaration()
        assert decl is not None and decl.name == tool.name
        schema = decl.parameters_json_schema
        assert schema["type"] == "object"
        assert set(schema.get("required", [])) <= set(schema["properties"])


def test_get_tools_returns_new_instances() -> None:
    toolkit = AnakinToolkit()
    for a, b in zip(toolkit.get_tools(), toolkit.get_tools(), strict=True):
        assert a is not b


def test_backcompat_tool_classes() -> None:
    tool = ScrapeWebsiteTool(api_key="ak-x")
    assert tool.name == "scrape_website"
    assert type(tool).__name__ == "ScrapeWebsiteTool"


async def test_toolset_respects_tool_filter() -> None:
    toolset = AnakinToolset(tool_filter=["search_web", "scrape_website"])
    names = {t.name for t in await toolset.get_tools()}
    assert names == {"search_web", "scrape_website"}


def test_version_matches_pyproject() -> None:
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert match and anakin_adk.__version__ == match.group(1)
