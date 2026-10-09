"""ADK tools for Anakin, built on the official `anakin-sdk` (AsyncAnakin).

Every tool returns ``{"status": "success", "data": ...}`` or
``{"status": "error", "error_message": ..., "hint"?: ...}`` so the model can
recover from failures instead of crashing the run.

Read tools only fetch data. Write tools (``WRITE_TOOLS``) change state on
your Anakin account or on third-party sites; they are excluded from
`AnakinToolkit` by default and ask the user for confirmation before running
(ADK tool confirmation), mirroring the Anakin MCP server.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import anakin
from anakin import AsyncAnakin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ._client import ClientSettings

# Tool results are capped so a large crawl can't blow the model's context.
DEFAULT_MAX_CHARS = 100_000

Handler = Callable[[AsyncAnakin, dict[str, Any]], Awaitable[Any]]


def _dump(data: Any) -> Any:
    if isinstance(data, list):
        return [_dump(item) for item in data]
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json", exclude_none=True)
    return data


def _cap(data: Any, max_chars: int) -> Any:
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return data
    return {
        "truncated": True,
        "note": f"Result exceeded {max_chars} characters and was cut. Narrow the request "
        "(fewer pages, include/exclude patterns, a smaller limit).",
        "content": text[:max_chars],
    }


def _hint(exc: anakin.AnakinError) -> str | None:
    if isinstance(exc, anakin.ConfigurationError):
        return "Set ANAKIN_API_KEY (free key with 300 credits: https://anakin.io/signup)."
    if isinstance(exc, anakin.WireAuthRequiredError):
        return f"The user must connect this site's account first: {exc.connect_url}"
    if isinstance(exc, anakin.WireAuthExpiredError):
        return "The saved site login expired; sign in again with wire_login or the dashboard."
    if isinstance(exc, anakin.InsufficientCreditsError):
        return f"Out of credits. {exc.signup_url or 'Top up at https://anakin.io/pricing'}"
    if isinstance(exc, anakin.JobTimeoutError):
        return (
            f"Still running server-side (job {exc.job_id}). Try again later or raise the timeout."
        )
    return None


class AnakinTool(BaseTool):
    """Base class: one Anakin operation exposed as an ADK tool."""

    #: True for tools that change state (accounts, monitors, third-party sites).
    write: bool = False

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Handler,
        write: bool = False,
        is_long_running: bool = False,
        settings: ClientSettings | None = None,
        client: AsyncAnakin | None = None,
        require_confirmation: bool | None = None,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        super().__init__(name=name, description=description, is_long_running=is_long_running)
        self._parameters = parameters
        self._handler = handler
        self.write = write
        self._settings = settings or ClientSettings()
        self._client = client
        self._require_confirmation = write if require_confirmation is None else require_confirmation
        self._max_chars = max_chars

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self._parameters,
        )

    async def check_require_confirmation(
        self, args: dict[str, Any], tool_context: ToolContext
    ) -> bool:
        return self._require_confirmation

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        if await self.check_require_confirmation(args, tool_context):
            confirmation = getattr(tool_context, "tool_confirmation", None)
            if confirmation is None:
                tool_context.request_confirmation(
                    hint=f"Approve or reject {self.name}({json.dumps(args, default=str)})."
                )
                tool_context.actions.skip_summarization = True
                return {"status": "error", "error_message": "This call needs user confirmation."}
            if not confirmation.confirmed:
                return {"status": "error", "error_message": "The user rejected this call."}

        missing = [k for k in self._parameters.get("required", []) if not args.get(k)]
        if missing:
            return {"status": "error", "error_message": f"{', '.join(missing)} is required"}

        try:
            if self._client is not None:
                result = await self._handler(self._client, args)
            else:
                async with self._settings.new_client() as client:
                    result = await self._handler(client, args)
        except anakin.AnakinError as exc:
            error: dict[str, Any] = {"status": "error", "error_message": str(exc)}
            hint = _hint(exc)
            if hint:
                error["hint"] = hint
            return error
        return {"status": "success", "data": _cap(_dump(result), self._max_chars)}


# ─── schema helpers ───────────────────────────────────────────────────────────


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _s(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "string", "description": description, **extra}


def _i(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "integer", "description": description, **extra}


def _b(description: str, default: bool = False) -> dict[str, Any]:
    return {"type": "boolean", "description": description, "default": default}


def _list(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "description": description, **extra}


_ANY_OBJECT = {"type": "object", "additionalProperties": True}
_COUNTRY = _s("Two-letter proxy country code, e.g. 'us', 'gb'. Defaults to 'us'.")
_SESSION = _s("Saved browser-session ID (from session_list) for login-protected pages.")


# ─── handlers ─────────────────────────────────────────────────────────────────


async def _scrape(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    fmt = a.get("format", "markdown")
    schema = a.get("output_schema")
    formats = {"html": ["html"], "links": ["links"], "summary": ["summary"]}.get(fmt, ["markdown"])
    doc = await c.scrape(
        a["url"],
        formats=formats,  # type: ignore[arg-type]
        country=a.get("country") or "us",
        use_browser=bool(a.get("use_browser")),
        generate_json=fmt == "json" or schema is not None,
        output_schema=schema,
        session_id=a.get("session_id"),
        poll_timeout=a.get("timeout"),
    )
    if fmt == "json" or schema is not None:
        return {"url": doc.url, "data": doc.generated_json}
    value = {"html": doc.html, "links": doc.links, "summary": doc.summary}.get(fmt, doc.markdown)
    return {
        "url": doc.url,
        fmt if fmt in {"html", "links", "summary"} else "markdown": _dump(value),
    }


async def _batch(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    urls = a["urls"]
    if len(urls) > 10:
        raise anakin.InvalidRequestError("Maximum 10 URLs allowed per batch request.")
    return await c.scrape_batch(
        urls,
        country=a.get("country") or "us",
        use_browser=bool(a.get("use_browser")),
        generate_json=bool(a.get("generate_json")),
    )


async def _search(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.search(a["query"], limit=a.get("limit", 5))


async def _research(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    timeout = min(a.get("timeout", 600), 900)
    result = await c.agentic_search(a["topic"], schema=a.get("schema"), poll_timeout=timeout)
    return result.generated_json or result


async def _map(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.map(
        a["url"],
        limit=a.get("limit", 100),
        depth=a.get("depth", 2),
        search=a.get("search"),
        include_subdomains=bool(a.get("include_subdomains")),
        use_browser=bool(a.get("use_browser")),
    )


async def _crawl(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.crawl(
        a["url"],
        max_pages=a.get("max_pages", 10),
        depth=a.get("depth", 1),
        include_patterns=a.get("include_patterns") or (),
        exclude_patterns=a.get("exclude_patterns") or (),
        country=a.get("country") or "us",
        use_browser=bool(a.get("use_browser")),
        session_id=a.get("session_id"),
    )


async def _wire_discover(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.wire.discover(
        a["q"], catalog=a.get("catalog"), auth_mode=a.get("auth_mode"), limit=a.get("limit", 5)
    )


async def _wire_catalog(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    if a.get("slug"):
        return await c.wire.catalog(a["slug"])
    catalogs = await c.wire.catalogs()
    # Hundreds of sites: return a compact index; drill in with a slug.
    return [
        {"slug": x.slug, "name": x.name, "category": x.category, "actions": x.action_count}
        for x in catalogs
    ]


async def _wire_run(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    result = await c.wire.run(
        a["action_id"],
        a.get("params") or {},
        credential_id=a.get("credential_id"),
        identity_id=a.get("identity_id"),
    )
    out: dict[str, Any] = {"data": result.data, "credits_used": result.credits_used}
    if result.files:
        out["files"] = _dump(result.files)
        out["job_id"] = result.job_id
    return out


async def _wire_identities(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.wire.identities(catalog_id=a.get("catalog_id"))


async def _wire_login(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.wire.login(
        a["catalog_slug"],
        a.get("params"),
        identity_name=a.get("identity_name"),
        source_id=a.get("source_id"),
        source_ref=a.get("source_ref"),
    )


async def _wire_build(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.wire.build(
        a["website_url"],
        a["goal"],
        actions=a.get("actions"),
        country=a.get("country"),
        visibility=a.get("visibility"),
        force=bool(a.get("force")),
    )


async def _wire_build_status(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    if a.get("id"):
        return await c.wire.get_build(a["id"])
    return await c.wire.builds(status=a.get("status"), limit=a.get("limit", 10))


async def _ai_search(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    result = await c.ai_visibility.search(
        a["query"], sources=a.get("sources"), country=a.get("country") or "us"
    )
    if not a.get("include_full_content"):
        for r in result.results:
            r.full_content = None
    return result


async def _ai_sources(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.ai_visibility.sources()


_MONITOR_KEYS = (
    "scope", "watch_mode", "watch_format", "output_schema", "ai_mode", "ai_goal", "use_browser",
    "country", "session_id", "is_active", "expires_at", "alert_webhook_url", "alert_emails",
    "max_pages", "max_depth", "include_patterns", "exclude_patterns", "wire_action_id",
    "wire_catalog_slug", "wire_credential_id", "wire_params", "wire_watch_paths",
)  # fmt: skip


async def _monitor_create(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    options = {k: a[k] for k in _MONITOR_KEYS if a.get(k) is not None}
    return await c.monitors.create(a["url"], int(a["interval_minutes"]), **options)


async def _monitor_list(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.monitors.get(a["id"]) if a.get("id") else await c.monitors.list()


async def _monitor_changes(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.monitors.changes(a["id"])


async def _monitor_control(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    action, monitor_id = a["action"], a["id"]
    if action == "pause":
        return await c.monitors.pause(monitor_id)
    if action == "resume":
        return await c.monitors.resume(monitor_id)
    if action == "run_now":
        return await c.monitors.run_now(monitor_id)
    if action == "delete":
        await c.monitors.delete(monitor_id)
        return {"deleted": monitor_id}
    raise anakin.InvalidRequestError(
        f"Unknown action {action!r}; use pause, resume, run_now or delete."
    )


async def _session_list(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    return await c.sessions.list(domain=a.get("domain"))


async def _session_delete(c: AsyncAnakin, a: dict[str, Any]) -> Any:
    await c.sessions.delete(a["id"])
    return {"deleted": a["id"]}


# ─── tool specs ───────────────────────────────────────────────────────────────

_WIRE_RUN_PARAMS = _obj(
    {
        "action_id": _s("The action to run (from wire_discover / wire_catalog)."),
        "params": {**_ANY_OBJECT, "description": "The action's input parameters (see its schema)."},
        "credential_id": _s(
            "Required when the action's auth_mode is 'required' (from wire_identities)."
        ),
        "identity_id": _s("Optional identity selector, alternative to credential_id."),
    },
    ["action_id"],
)

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "scrape_website": {
        "description": (
            "Scrape one web page and return clean markdown (default), AI-extracted JSON "
            "(format='json', optionally with output_schema), html, links or a summary. Works "
            "for articles, product pages and docs. Set use_browser for JavaScript-heavy sites. 3-15s."
        ),
        "parameters": _obj(
            {
                "url": _s("The URL of the web page to scrape."),
                "format": _s(
                    "Output format.",
                    enum=["markdown", "json", "html", "links", "summary"],
                    default="markdown",
                ),
                "output_schema": {
                    **_ANY_OBJECT,
                    "description": "JSON Schema of fields to extract.",
                },
                "use_browser": _b("Use a headless browser for JavaScript-rendered pages."),
                "country": _COUNTRY,
                "session_id": _SESSION,
                "timeout": _i("Max seconds to wait.", default=120),
            },
            ["url"],
        ),
        "handler": _scrape,
    },
    "batch_scrape": {
        "description": (
            "Scrape up to 10 web pages in parallel and return each page's markdown and status. "
            "Use for comparing products or collecting several known URLs. 5-30s."
        ),
        "parameters": _obj(
            {
                "urls": _list("URLs to scrape (max 10).", maxItems=10),
                "generate_json": _b("Also AI-extract structured JSON from each page."),
                "use_browser": _b("Use a headless browser."),
                "country": _COUNTRY,
            },
            ["urls"],
        ),
        "handler": _batch,
    },
    "search_web": {
        "description": (
            "AI web search returning result URLs, titles, snippets and dates. Use to find pages "
            "before scraping them. Instant."
        ),
        "parameters": _obj(
            {
                "query": _s("The search query in natural language."),
                "limit": _i("Max results (1-20).", default=5, minimum=1, maximum=20),
            },
            ["query"],
        ),
        "handler": _search,
    },
    "deep_research": {
        "description": (
            "Multi-source deep research: searches the web, scrapes the best sources and returns a "
            "summary plus structured_data (matching `schema` if given). Use for comparisons, market "
            "analysis or questions one page can't answer. Takes 1-5 minutes."
        ),
        "parameters": _obj(
            {
                "topic": _s("The research question or task."),
                "schema": {
                    **_ANY_OBJECT,
                    "description": "Optional JSON Schema for structured_data.",
                },
                "timeout": _i("Max seconds to wait (default 600, max 900).", default=600),
            },
            ["topic"],
        ),
        "handler": _research,
        "is_long_running": True,
    },
    "map_website": {
        "description": (
            "List the URLs on a website (internal links, optionally subdomains). Use to understand "
            "a site's structure or pick pages before crawling."
        ),
        "parameters": _obj(
            {
                "url": _s("Starting URL (usually a homepage or section root)."),
                "limit": _i("Max URLs to return (max 5000).", default=100),
                "depth": _i("Link hops to follow (1-5).", default=2),
                "search": _s("Only return URLs containing this text."),
                "include_subdomains": _b("Include subdomains."),
                "use_browser": _b("Render with a headless browser."),
            },
            ["url"],
        ),
        "handler": _map,
    },
    "crawl_website": {
        "description": (
            "Fetch markdown for many pages of a site at once (docs ingestion, RAG corpora). Scope it "
            "with include_patterns / exclude_patterns. Returns each page's markdown and status."
        ),
        "parameters": _obj(
            {
                "url": _s("Starting URL."),
                "max_pages": _i("Max pages to fetch (max 100).", default=10),
                "depth": _i("Link hops from the start URL (1-5).", default=1),
                "include_patterns": _list("Only fetch URLs matching these globs, e.g. '/blog/*'."),
                "exclude_patterns": _list("Skip URLs matching these globs."),
                "use_browser": _b("Render each page with a headless browser."),
                "country": _COUNTRY,
                "session_id": _SESSION,
            },
            ["url"],
        ),
        "handler": _crawl,
        "is_long_running": True,
    },
    "wire_discover": {
        "description": (
            "Find pre-built Wire actions for a task on a known site (Amazon, Walmart, LinkedIn, "
            "Airbnb, Zillow and hundreds more) from a natural-language intent. Returns action_ids, "
            "params, credit cost and auth needs. Prefer Wire over scraping when an action exists."
        ),
        "parameters": _obj(
            {
                "q": _s("The intent, e.g. 'top phones on walmart'."),
                "limit": _i("Max candidate actions.", default=5),
                "catalog": _s("Restrict to one site slug, e.g. 'amazon'."),
                "auth_mode": _s(
                    "Filter by auth requirement.", enum=["none", "optional", "required"]
                ),
            },
            ["q"],
        ),
        "handler": _wire_discover,
    },
    "wire_catalog": {
        "description": (
            "Browse the Wire catalog. Without a slug: every supported site with its action count. "
            "With a slug: that site's actions with exact parameter schemas, read/write type, auth "
            "mode and credit cost, plus login fields."
        ),
        "parameters": _obj({"slug": _s("Catalog slug, e.g. 'walmart'. Omit to list all sites.")}),
        "handler": _wire_catalog,
    },
    "wire_read_action": {
        "description": (
            "Run a Wire READ action (extracts data, changes nothing): search listings, get product "
            "details, read a profile. Get action_ids and params from wire_discover / wire_catalog."
        ),
        "parameters": _WIRE_RUN_PARAMS,
        "handler": _wire_run,
    },
    "wire_identities": {
        "description": (
            "List the user's saved site accounts. Each credential's id is the credential_id for "
            "actions whose auth_mode is 'required'. Check that status is 'active'."
        ),
        "parameters": _obj({"catalog_id": _s("Only identities for this catalog.")}),
        "handler": _wire_identities,
    },
    "wire_build_status": {
        "description": (
            "Check Wire build requests: pass an id for one build's status, published action_ids "
            "and skipped capabilities, or omit it to list recent builds."
        ),
        "parameters": _obj(
            {
                "id": _s("Build request id from wire_build."),
                "status": _s("List mode: filter by status."),
                "limit": _i("List mode: max builds.", default=10),
            }
        ),
        "handler": _wire_build_status,
    },
    "ai_visibility_search": {
        "description": (
            "Ask several AI answer engines (ChatGPT, Gemini, Google AI Overview, ...) the same "
            "question and compare their answers, with a synthesis of agreement and outliers. Use "
            "for brand / AI-SEO visibility checks. 1-2 minutes; billed per engine."
        ),
        "parameters": _obj(
            {
                "query": _s("The question to ask every engine (max 2000 characters)."),
                "sources": _list("Engine slugs (see ai_visibility_sources). Omit for all."),
                "country": _COUNTRY,
                "include_full_content": _b("Include each engine's raw full answer (large)."),
            },
            ["query"],
        ),
        "handler": _ai_search,
        "is_long_running": True,
    },
    "ai_visibility_sources": {
        "description": "List the AI answer engines available to ai_visibility_search.",
        "parameters": _obj({}),
        "handler": _ai_sources,
    },
    "monitor_list": {
        "description": (
            "List the user's website monitors, or pass an id for one monitor's configuration and "
            "status (next/last check, active state, credit cost)."
        ),
        "parameters": _obj({"id": _s("Monitor id; omit to list all.")}),
        "handler": _monitor_list,
    },
    "monitor_changes": {
        "description": "Get the changes a monitor has detected, newest first, with diffs and AI summaries.",
        "parameters": _obj({"id": _s("Monitor id (from monitor_list).")}, ["id"]),
        "handler": _monitor_changes,
    },
    "session_list": {
        "description": (
            "List saved browser sessions (encrypted logins created in the Anakin dashboard). Pass a "
            "session id as session_id to scrape/crawl login-protected pages."
        ),
        "parameters": _obj({"domain": _s("Filter by website domain, e.g. 'amazon.com'.")}),
        "handler": _session_list,
    },
    # ── write tools (opt-in, confirmation-gated) ─────────────────────────────
    "wire_write_action": {
        "description": (
            "Run a Wire WRITE action that changes state on a site (submit a form, add to cart, "
            "post content, update settings). Usually needs a credential_id. Never executes payments."
        ),
        "parameters": _WIRE_RUN_PARAMS,
        "handler": _wire_run,
        "write": True,
    },
    "wire_login": {
        "description": (
            "Sign in to a credentials-mode site and get a credential_id for auth-required actions. "
            "params are the catalog's login fields (see wire_catalog login_input_schema). The "
            "password is never stored."
        ),
        "parameters": _obj(
            {
                "catalog_slug": _s("The catalog to sign in to."),
                "params": {**_ANY_OBJECT, "description": "Login fields, e.g. {email, password}."},
                "identity_name": _s("Optional name for the identity."),
                "source_id": _s("Optional vault identity-source id (alternative to params)."),
                "source_ref": {
                    **_ANY_OBJECT,
                    "description": "Vault entry locator (with source_id).",
                },
            },
            ["catalog_slug"],
        ),
        "handler": _wire_login,
        "write": True,
    },
    "wire_build": {
        "description": (
            "Request new Wire actions for a site that isn't in the catalog yet. Charges credits "
            "(refunded if the build fails). Only use after wire_discover finds nothing. Track it "
            "with wire_build_status."
        ),
        "parameters": _obj(
            {
                "website_url": _s("The site to build actions for."),
                "goal": _s("What the action should do or extract. Be specific."),
                "actions": _list("Optional discrete capabilities, each built as its own action."),
                "country": _s("Optional proxy country for geo-gated sites."),
                "visibility": _s("Action visibility.", enum=["private", "public"]),
                "force": _b("Build even if similar actions exist."),
            },
            ["website_url", "goal"],
        ),
        "handler": _wire_build,
        "write": True,
    },
    "monitor_create": {
        "description": (
            "Create a scheduled monitor that checks a URL every interval_minutes (min 15) and "
            "records changes, optionally alerting a webhook or email. watch_mode 'full_page' (2 "
            "credits/check) or 'specific_data' with output_schema (3 credits/check); ai_mode adds "
            "noise filtering (+1 credit/check)."
        ),
        "parameters": _obj(
            {
                "url": _s("The URL to watch."),
                "interval_minutes": _i("Check frequency in minutes (min 15).", minimum=15),
                "scope": _s("What to monitor.", enum=["page", "site", "wire"]),
                "watch_mode": _s("Comparison mode.", enum=["full_page", "specific_data"]),
                "output_schema": {**_ANY_OBJECT, "description": "Fields to track (specific_data)."},
                "ai_mode": _b("AI meaningful-change filtering."),
                "ai_goal": _s("Which changes count, e.g. 'only when the price drops'."),
                "alert_webhook_url": _s("Webhook for change alerts."),
                "alert_emails": _s("Comma-separated alert emails."),
                "use_browser": _b("Render checks with a headless browser."),
                "country": _COUNTRY,
                "session_id": _SESSION,
                "wire_action_id": _s("Wire scope: the action to run each check."),
                "wire_params": {**_ANY_OBJECT, "description": "Wire scope: action parameters."},
            },
            ["url", "interval_minutes"],
        ),
        "handler": _monitor_create,
        "write": True,
    },
    "monitor_control": {
        "description": (
            "Control a monitor: 'pause', 'resume', 'run_now' (billed like a normal check) or "
            "'delete' (permanent)."
        ),
        "parameters": _obj(
            {
                "id": _s("Monitor id."),
                "action": _s("What to do.", enum=["pause", "resume", "run_now", "delete"]),
            },
            ["id", "action"],
        ),
        "handler": _monitor_control,
        "write": True,
    },
    "session_delete": {
        "description": "Permanently delete a saved browser session and its encrypted login data.",
        "parameters": _obj({"id": _s("Session id (from session_list).")}, ["id"]),
        "handler": _session_delete,
        "write": True,
    },
}

READ_TOOLS = [name for name, spec in TOOL_SPECS.items() if not spec.get("write")]
WRITE_TOOLS = [name for name, spec in TOOL_SPECS.items() if spec.get("write")]


def make_tool(
    name: str,
    *,
    settings: ClientSettings | None = None,
    client: AsyncAnakin | None = None,
    require_confirmation: bool | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> AnakinTool:
    """Build one Anakin tool by name (see READ_TOOLS / WRITE_TOOLS)."""
    try:
        spec = TOOL_SPECS[name]
    except KeyError:
        raise ValueError(f"Unknown Anakin tool {name!r}. Options: {sorted(TOOL_SPECS)}") from None
    return AnakinTool(
        name=name,
        description=spec["description"],
        parameters=spec["parameters"],
        handler=spec["handler"],
        write=spec.get("write", False),
        is_long_running=spec.get("is_long_running", False),
        settings=settings,
        client=client,
        require_confirmation=require_confirmation,
        max_chars=max_chars,
    )


def _named(tool_name: str, class_name: str) -> type[AnakinTool]:
    """Back-compat class for a tool (e.g. `ScrapeWebsiteTool()`), accepting the same options."""

    class _Tool(AnakinTool):
        def __init__(
            self,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
            client: AsyncAnakin | None = None,
            require_confirmation: bool | None = None,
            max_chars: int = DEFAULT_MAX_CHARS,
        ) -> None:
            spec = TOOL_SPECS[tool_name]
            super().__init__(
                name=tool_name,
                description=spec["description"],
                parameters=spec["parameters"],
                handler=spec["handler"],
                write=spec.get("write", False),
                is_long_running=spec.get("is_long_running", False),
                settings=ClientSettings(api_key=api_key, base_url=base_url),
                client=client,
                require_confirmation=require_confirmation,
                max_chars=max_chars,
            )

    _Tool.__name__ = _Tool.__qualname__ = class_name
    return _Tool


ScrapeWebsiteTool = _named("scrape_website", "ScrapeWebsiteTool")
BatchScrapeTool = _named("batch_scrape", "BatchScrapeTool")
SearchWebTool = _named("search_web", "SearchWebTool")
DeepResearchTool = _named("deep_research", "DeepResearchTool")
MapWebsiteTool = _named("map_website", "MapWebsiteTool")
CrawlWebsiteTool = _named("crawl_website", "CrawlWebsiteTool")
WireDiscoverTool = _named("wire_discover", "WireDiscoverTool")
WireCatalogTool = _named("wire_catalog", "WireCatalogTool")
WireReadActionTool = _named("wire_read_action", "WireReadActionTool")
WireWriteActionTool = _named("wire_write_action", "WireWriteActionTool")
AIVisibilitySearchTool = _named("ai_visibility_search", "AIVisibilitySearchTool")
