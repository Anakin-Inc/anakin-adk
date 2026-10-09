"""Resolve credentials and build `AsyncAnakin` clients for the tools."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anakin import AsyncAnakin

CONFIG_FILE = Path.home() / ".anakin" / "config.json"
DEFAULT_API_URL = "https://api.anakin.io/v1"


def _cli_config() -> dict[str, Any]:
    """Read ~/.anakin/config.json written by `anakin login` (anakin-cli), if present."""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


@dataclass(frozen=True)
class ClientSettings:
    """
    How tools connect to Anakin.

    Key resolution: explicit `api_key` > ANAKIN_API_KEY > ~/.anakin/config.json
    (from `anakin login`) > none (keyless tier: scrape and Wire discovery only).
    """

    api_key: str | None = None
    base_url: str | None = None
    poll_timeout: float | None = None

    def resolved_key(self) -> str | None:
        key = self.api_key or os.environ.get("ANAKIN_API_KEY") or _cli_config().get("api_key")
        return key if isinstance(key, str) and key else None

    def resolved_base_url(self) -> str:
        url = self.base_url or os.environ.get("ANAKIN_API_URL") or _cli_config().get("api_url")
        url = str(url or DEFAULT_API_URL).rstrip("/")
        return url if url.endswith("/v1") else f"{url}/v1"

    def new_client(self) -> AsyncAnakin:
        kwargs: dict[str, Any] = {
            "api_key": self.resolved_key(),
            "base_url": self.resolved_base_url(),
        }
        if self.poll_timeout is not None:
            kwargs["poll_timeout"] = self.poll_timeout
        return AsyncAnakin(**kwargs)
