"""Runtime configuration for observ-lite."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_LOG_DIR = "/var/log/observ-lite"
DEFAULT_COMMAND_TIMEOUT = 8
DEFAULT_MAX_OUTPUT_CHARS = 20000


@dataclass(frozen=True)
class Config:
    log_dir: Path
    command_timeout: int
    max_output_chars: int


def _env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def load_config() -> Config:
    return Config(
        log_dir=Path(os.environ.get("OBSERV_LITE_LOG_DIR", DEFAULT_LOG_DIR)),
        command_timeout=_env_int("OBSERV_LITE_COMMAND_TIMEOUT", DEFAULT_COMMAND_TIMEOUT),
        max_output_chars=_env_int(
            "OBSERV_LITE_MAX_OUTPUT_CHARS",
            DEFAULT_MAX_OUTPUT_CHARS,
        ),
    )

