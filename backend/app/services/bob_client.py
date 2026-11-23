"""IBM Bob Shell requests, streamed responses, and usage reporting."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from app.core.config import settings


class BobError(RuntimeError):
    pass


def cli_path() -> str | None:
    configured = Path(settings.bob_cli_path)
    return str(configured) if configured.is_file() else None


def parse_output(stdout: str) -> tuple[str, dict[str, Any]]:
    messages: list[str] = []
    result: dict[str, Any] | None = None
    limit_error = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "message" and event.get("role") == "assistant":
            if isinstance(event.get("content"), str):
                messages.append(event["content"])
        if event.get("type") == "result":
            result = event
        if event.get("type") == "error":
            limit_error = True
    if result is None or result.get("status") != "success":
        raise BobError("Check your Bob key, Bobcoin balance, and connection, then try again.")
    if limit_error:
        raise BobError("Bob reached its spend or turn limit before finishing. Try one simpler subject.")
    message = "".join(messages) or result.get("last_message", "")
    if not message.strip():
        raise BobError("Bob returned an empty response.")
    raw_stats = result.get("stats", {})
    usage = {
        "bobcoins": raw_stats.get("session_costs"),
        "total_tokens": raw_stats.get("total_tokens"),
        "input_tokens": raw_stats.get("input_tokens"),
        "output_tokens": raw_stats.get("output_tokens"),
        "tool_calls": raw_stats.get("tool_calls"),
        "duration_ms": raw_stats.get("duration_ms"),
    }
    return message, usage


def extract_json(message: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", message)
    try:
        value = json.loads(fenced[1] if fenced else message)
        if isinstance(value, dict) and ("objects" in value or "narrative" in value):
            return value
    except json.JSONDecodeError:
        pass
    raise BobError("Try again with a clearer photo or a more specific subject.")


async def run_bob(prompt: str, workspace: Path, *, images: bool = True) -> tuple[dict, dict]:
    executable = cli_path()
    key = settings.read_bob_key()
    if not key or not executable:
        raise BobError("Add bobkey.txt and run ./start-local.sh to set up Bob Shell.")
    environment = os.environ.copy()
    environment["BOB_API_KEY"] = key
    environment["BOB_LOG_LEVEL"] = "silent"
    disabled = "execute,edit,mcp,subagent,skill,mode"
    if not images:
        disabled += ",read"
    command = [
        executable, "run", "--format", "stream-json", "--mode", "agent",
        "--workspace", str(workspace), "--config-dir", str(workspace),
        "--disable-mcp", "--disable-subagents", "--disable-tool-groups", disabled,
        "--max-cost", str(settings.bob_max_cost), "--max-turns", str(settings.bob_max_turns),
        "--log-level", "silent",
    ]
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, cwd=workspace, env=environment,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(prompt.encode()), timeout=settings.bob_timeout_seconds,
        )
    except (asyncio.TimeoutError, asyncio.CancelledError):
        process.kill()
        await process.communicate()
        raise BobError("Bob took too long to respond. Try a simpler subject or one sticker at a time.") from None
    if process.returncode:
        error = stderr.decode(errors="replace").replace(key, "[redacted]")
        if "license agreement" in error.lower():
            raise BobError("Bob Shell needs its initial license setup. Run tools/node_modules/.bin/bob chat once.")
        if "team" in error.lower():
            raise BobError("This Bob key requires a team. Use an Inference-scoped key for the local Studio.")
        raise BobError("Check your API key and Bobcoin balance in IBM Bob, then try again.")
    message, usage = parse_output(stdout.decode(errors="replace"))
    # Keep provider output credential-free.
    payload = extract_json(message.replace(key, "[redacted]"))
    usage["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return payload, usage
