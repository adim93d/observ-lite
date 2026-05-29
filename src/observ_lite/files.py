"""File helpers for append-only observ-lite logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def ensure_log_dir(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True))
        handle.write("\n")


def append_log_block(path: Path, title: str, body: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n===== {0} =====\n".format(title))
        handle.write(body.rstrip() if body else "(no output)")
        handle.write("\n")

