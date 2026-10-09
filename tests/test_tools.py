"""Tool behaviour tests. Anakin's HTTP API is mocked with respx; no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from anakin_adk import AnakinToolkit, make_tool
from anakin_adk._client import ClientSettings

BASE = "https://api.anakin.io/v1"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANAKIN_API_KEY", "ak-test")
    monkeypatch.delenv("ANAKIN_API_URL", raising=False)
    monkeypatch.setattr("anakin_adk._client.CONFIG_FILE", tmp_path / "config.json")
    import anakin._http as http

    monkeypatch.setattr(http, "DEFAULT_POLL_INTERVAL", 0.001)


@pytest.fixture
def ctx() -> MagicMock:
    context = MagicMock()
    context.tool_confirmation = None
    return context


async def call(name: str, args: dict[str, Any], ctx: MagicMock, **kw: Any) -> dict[str, Any]:
    tool = make_tool(name, **kw)
    result: dict[str, Any] = await tool.run_async(args=args, tool_context=ctx)
    return result


def _json(request: httpx.Request) -> Any:
    return json.loads(request.content)


# ─── validation & errors ──────────────────────────────────────────────────────


async def test_missing_required_arg(ctx: MagicMock) -> None:
    result = await call("scrape_website", {}, ctx)
    assert result == {"status": "error", "error_message": "url is required"}


@respx.mock
async def test_api_error_becomes_error_result_with_hint(ctx: MagicMock) -> None:
    respx.post(f"{BASE}/wire/task").mock(
        return_value=httpx.Response(
            401,
            json={
                "status": "error",
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Needs LinkedIn",
                    "connect_url": "/c",
                },
            },
        )
    )
    result = await call("wire_read_action", {"action_id": "li"}, ctx)
    assert result["status"] == "error"
    assert "Needs LinkedIn" in result["error_message"]
    assert result["hint"].endswith("https://anakin.io/c")


async def test_keyless_keyed_tool_returns_signup_hint(
    ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANAKIN_API_KEY")
    result = await call("crawl_website", {"url": "https://e.com"}, ctx)
    assert result["status"] == "error"
    assert "anakin.io/signup" in result["hint"]


# ─── scrape ───────────────────────────────────────────────────────────────────


@respx.mock
async def test_scrape_markdown(ctx: MagicMock) -> None:
    respx.post(f"{BASE}/url-scraper").mock(
        return_value=httpx.Response(202, json={"jobId": "j", "status": "pending"})
    )
    respx.get(f"{BASE}/url-scraper/j").mock(
        return_value=httpx.Response(
            200, json={"id": "j", "status": "completed", "markdown": "# Hi"}
        )
    )
    result = await call("scrape_website", {"url": "https://e.com"}, ctx)
    assert result == {"status": "success", "data": {"url": "https://e.com", "markdown": "# Hi"}}


@respx.mock
async def test_scrape_json_with_schema(ctx: MagicMock) -> None:
    sent: dict[str, Any] = {}

    def submit(request: httpx.Request) -> httpx.Response:
        sent.update(_json(request))
        return httpx.Response(202, json={"jobId": "j", "status": "pending"})

    respx.post(f"{BASE}/url-scraper").mock(side_effect=submit)
    respx.get(f"{BASE}/url-scraper/j").mock(
        return_value=httpx.Response(
            200, json={"id": "j", "status": "completed", "generatedJson": {"p": 1}}
        )
    )
    result = await call(
        "scrape_website",
        {
            "url": "https://e.com",
            "output_schema": {"type": "object"},
            "use_browser": True,
            "country": "gb",
        },
        ctx,
    )
    assert sent["outputSchema"] == {"type": "object"}
    assert sent["useBrowser"] is True and sent["country"] == "gb"
    assert result["data"]["data"] == {"p": 1}


@respx.mock
async def test_keyless_scrape_works(ctx: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANAKIN_API_KEY")
    route = respx.post(f"{BASE}/url-scraper/scrape").mock(
        return_value=httpx.Response(200, json={"markdown": "free"})
    )
    result = await call("scrape_website", {"url": "https://e.com"}, ctx)
    assert result["data"]["markdown"] == "free"
    assert "X-API-Key" not in route.calls.last.request.headers


async def test_batch_rejects_more_than_ten(ctx: MagicMock) -> None:
    result = await call("batch_scrape", {"urls": [f"https://e.com/{i}" for i in range(11)]}, ctx)
    assert result["status"] == "error"
    assert "Maximum 10 URLs" in result["error_message"]


@respx.mock
async def test_large_results_are_capped(ctx: MagicMock) -> None:
    respx.post(f"{BASE}/url-scraper").mock(
        return_value=httpx.Response(202, json={"jobId": "j", "status": "pending"})
    )
    respx.get(f"{BASE}/url-scraper/j").mock(
        return_value=httpx.Response(
            200, json={"id": "j", "status": "completed", "markdown": "x" * 5000}
        )
    )
    result = await call("scrape_website", {"url": "https://e.com"}, ctx, max_chars=1000)
    assert result["data"]["truncated"] is True
    assert len(result["data"]["content"]) == 1000


# ─── search / research / crawl ────────────────────────────────────────────────


@respx.mock
async def test_search(ctx: MagicMock) -> None:
    respx.post(f"{BASE}/search").mock(
        return_value=httpx.Response(
            200, json={"id": "s", "results": [{"url": "https://a.com", "title": "A"}]}
        )
    )
    result = await call("search_web", {"query": "q", "limit": 3}, ctx)
    assert result["data"]["results"][0]["title"] == "A"


@respx.mock
async def test_deep_research_returns_generated_json(ctx: MagicMock) -> None:
    respx.post(f"{BASE}/agentic-search").mock(
        return_value=httpx.Response(202, json={"job_id": "a", "status": "pending"})
    )
    respx.get(f"{BASE}/agentic-search/a").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "a",
                "status": "completed",
                "generatedJson": {"summary": "S", "structured_data": {"x": 1}},
            },
        )
    )
    result = await call("deep_research", {"topic": "t"}, ctx)
    assert result["data"] == {"summary": "S", "structured_data": {"x": 1}}


@respx.mock
async def test_crawl_patterns(ctx: MagicMock) -> None:
    sent: dict[str, Any] = {}

    def submit(request: httpx.Request) -> httpx.Response:
        sent.update(_json(request))
        return httpx.Response(202, json={"jobId": "c", "status": "pending"})

    respx.post(f"{BASE}/crawl").mock(side_effect=submit)
    respx.get(f"{BASE}/crawl/c").mock(
        return_value=httpx.Response(200, json={"id": "c", "status": "completed", "results": []})
    )
    result = await call(
        "crawl_website", {"url": "https://e.com", "include_patterns": ["/docs/*"]}, ctx
    )
    assert result["status"] == "success"
    assert sent["includePatterns"] == ["/docs/*"]


# ─── wire ─────────────────────────────────────────────────────────────────────


@respx.mock
async def test_wire_discover_and_catalog_index(ctx: MagicMock) -> None:
    respx.get(f"{BASE}/wire/resolve").mock(
        return_value=httpx.Response(
            200, json={"results": [{"action_id": "hn_stories", "catalog": "hackernews"}]}
        )
    )
    respx.get(f"{BASE}/wire/catalog").mock(
        return_value=httpx.Response(
            200,
            json={
                "catalog": [
                    {
                        "id": "1",
                        "slug": "hackernews",
                        "name": "HN",
                        "category": "news",
                        "action_count": 4,
                    }
                ]
            },
        )
    )
    found = await call("wire_discover", {"q": "hn"}, ctx)
    assert found["data"][0]["catalog_slug"] == "hackernews"
    index = await call("wire_catalog", {}, ctx)
    assert index["data"] == [{"slug": "hackernews", "name": "HN", "category": "news", "actions": 4}]


@respx.mock
async def test_wire_read_action(ctx: MagicMock) -> None:
    sent: dict[str, Any] = {}

    def submit(request: httpx.Request) -> httpx.Response:
        sent.update(_json(request))
        return httpx.Response(202, json={"status": "processing", "job_id": "w"})

    respx.post(f"{BASE}/wire/task").mock(side_effect=submit)
    respx.get(f"{BASE}/wire/jobs/w").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "data": [{"t": 1}], "credits_used": 2}
        )
    )
    result = await call(
        "wire_read_action", {"action_id": "hn_stories", "params": {"limit": 1}}, ctx
    )
    assert sent == {"action_id": "hn_stories", "params": {"limit": 1}}
    assert result["data"] == {"data": [{"t": 1}], "credits_used": 2}


# ─── write tools: confirmation gate ───────────────────────────────────────────


@respx.mock
async def test_write_tool_requests_confirmation_first(ctx: MagicMock) -> None:
    route = respx.post(f"{BASE}/monitors")
    result = await call("monitor_create", {"url": "https://e.com", "interval_minutes": 60}, ctx)
    assert result["status"] == "error"
    assert "confirmation" in result["error_message"]
    ctx.request_confirmation.assert_called_once()
    assert not route.called


@respx.mock
async def test_write_tool_runs_once_confirmed(ctx: MagicMock) -> None:
    ctx.tool_confirmation = MagicMock(confirmed=True)
    sent: dict[str, Any] = {}

    def create(request: httpx.Request) -> httpx.Response:
        sent.update(_json(request))
        return httpx.Response(201, json={"id": "m1", "url": "https://e.com"})

    respx.post(f"{BASE}/monitors").mock(side_effect=create)
    result = await call(
        "monitor_create",
        {
            "url": "https://e.com",
            "interval_minutes": 60,
            "ai_mode": True,
            "watch_mode": "full_page",
        },
        ctx,
    )
    assert result["status"] == "success"
    assert sent == {
        "url": "https://e.com",
        "intervalMinutes": 60,
        "aiMode": True,
        "watchMode": "full_page",
    }


async def test_write_tool_rejected(ctx: MagicMock) -> None:
    ctx.tool_confirmation = MagicMock(confirmed=False)
    result = await call("session_delete", {"id": "s1"}, ctx)
    assert result["error_message"] == "The user rejected this call."


@respx.mock
async def test_write_tool_without_confirmation_when_disabled(ctx: MagicMock) -> None:
    respx.delete(f"{BASE}/monitors/m1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    tool = AnakinToolkit(
        tools=["monitor_control"], include_write_tools=True, require_confirmation=False
    ).get_tools()[0]
    result = await tool.run_async(args={"id": "m1", "action": "delete"}, tool_context=ctx)
    assert result == {"status": "success", "data": {"deleted": "m1"}}


# ─── credentials ──────────────────────────────────────────────────────────────


def test_settings_fall_back_to_cli_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANAKIN_API_KEY")
    config = tmp_path / "config.json"
    config.write_text('{"api_key": "ak-from-cli", "api_url": "http://localhost:8080"}')
    monkeypatch.setattr("anakin_adk._client.CONFIG_FILE", config)
    settings = ClientSettings()
    assert settings.resolved_key() == "ak-from-cli"
    assert settings.resolved_base_url() == "http://localhost:8080/v1"
    assert ClientSettings(api_key="ak-explicit").resolved_key() == "ak-explicit"
