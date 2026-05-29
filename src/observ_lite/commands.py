"""Safe helpers for running optional system commands."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, Optional, Sequence


CommandResult = Dict[str, Any]


def command_available(command: str) -> bool:
    """Return whether a command is available on PATH."""
    return shutil.which(command) is not None


def truncate_text(text: str, max_chars: int) -> str:
    """Limit text size while making truncation explicit."""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    suffix = "\n...[truncated]..."
    if max_chars <= len(suffix):
        return text[:max_chars]
    return text[: max_chars - len(suffix)] + suffix


def run_command(
    args: Sequence[str],
    timeout: int,
    max_output_chars: int,
    input_text: Optional[str] = None,
) -> CommandResult:
    """Run a command without raising on failure.

    Every external command used by the collector should go through this helper.
    The returned dict is intentionally JSON-serializable.
    """
    args_list = list(args)
    if not args_list:
        return {
            "ok": False,
            "returncode": None,
            "output": "",
            "error": "empty command",
        }

    executable = args_list[0]
    if "/" not in executable and not command_available(executable):
        return {
            "ok": False,
            "returncode": None,
            "output": "",
            "error": "command not found: {0}".format(executable),
            "command": args_list,
        }

    try:
        completed = subprocess.run(
            args_list,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "ok": False,
            "returncode": None,
            "output": truncate_text(stdout, max_output_chars),
            "error": truncate_text(
                "command timed out after {0}s\n{1}".format(timeout, stderr).strip(),
                max_output_chars,
            ),
            "command": args_list,
        }
    except OSError as exc:
        return {
            "ok": False,
            "returncode": None,
            "output": "",
            "error": str(exc),
            "command": args_list,
        }

    output = completed.stdout or ""
    error = completed.stderr or ""

    if len(output) > max_output_chars:
        output = truncate_text(output, max_output_chars)
        error = "stdout exceeded output limit; stderr omitted"
    else:
        remaining = max_output_chars - len(output)
        error = truncate_text(error, remaining) if error else ""

    result: CommandResult = {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "output": output,
        "command": args_list,
    }
    if error or completed.returncode != 0:
        result["error"] = error
    return result

