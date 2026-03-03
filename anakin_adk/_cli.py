"""Internal async subprocess wrapper for anakin-cli."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from typing import Any


class AnakinCLIError(Exception):
    """Raised when anakin-cli returns an error."""


async def check_anakin_installed() -> bool:
    """Check if the anakin CLI is installed and accessible."""
    return shutil.which("anakin") is not None


async def run_anakin_command(
    args: list[str],
    *,
    output_format: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run an anakin CLI command asynchronously and return parsed output.

    Args:
        args: Command arguments (e.g. ["scrape", "https://example.com"]).
        output_format: Output format flag passed to CLI (only for commands that
            support --format, e.g. "scrape"). None means don't pass --format.
        timeout: Command timeout in seconds.

    Returns:
        Parsed output as a dictionary.

    Raises:
        AnakinCLIError: If the CLI command fails or times out.
    """
    if not await check_anakin_installed():
        raise AnakinCLIError(
            "anakin-cli is not installed. Install it with: pip install anakin-cli"
        )

    tmp_file = None
    try:
        # Create a temp file for output capture
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="anakin_")
        os.close(tmp_fd)
        tmp_file = tmp_path

        cmd = ["anakin", *args, "--output", tmp_file]
        if output_format:
            cmd.extend(["--format", output_format])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise AnakinCLIError(
                f"anakin command timed out after {timeout}s: anakin {' '.join(args)}"
            )

        if process.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            raise AnakinCLIError(f"anakin command failed: {error_msg}")

        # Read output from temp file
        if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
            with open(tmp_file, "r") as f:
                content = f.read()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"content": content, "format": "text"}

        # Fall back to stdout
        output = stdout.decode().strip() if stdout else ""
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"content": output, "format": "text"}

        return {"content": "", "format": "text"}

    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)
