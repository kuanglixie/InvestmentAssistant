from __future__ import annotations

import os
import shlex
from pathlib import Path


def load_dotenv(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    env_path = Path(path)
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        value = _clean_env_value(value)
        if override or key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


def _clean_env_value(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = shlex.split(value, comments=False, posix=True)
    except ValueError:
        return value.strip("\"'")
    if len(parsed) == 1:
        return parsed[0]
    return value.strip("\"'")
