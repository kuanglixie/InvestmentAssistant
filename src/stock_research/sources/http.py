from __future__ import annotations

import json
import os
import time
import gzip
import zlib
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_SEC_USER_AGENT = "stock-research-system/0.1 your_email@example.com"


class FetchError(RuntimeError):
    pass


def sec_user_agent() -> str:
    return os.environ.get("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)


def fetch_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    rate_limit_seconds: float = 0.12,
) -> bytes:
    if rate_limit_seconds:
        time.sleep(rate_limit_seconds)
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            encoding = response.headers.get("Content-Encoding", "").lower()
            if encoding == "gzip":
                return gzip.decompress(data)
            if encoding == "deflate":
                return zlib.decompress(data)
            return data
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise FetchError(f"Network error while fetching {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"Timeout while fetching {url}") from exc


def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    rate_limit_seconds: float = 0.12,
) -> Any:
    data = fetch_bytes(
        url,
        headers=headers,
        timeout=timeout,
        rate_limit_seconds=rate_limit_seconds,
    )
    return json.loads(data.decode("utf-8"))


def post_json(
    url: str,
    payload: Any,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
    rate_limit_seconds: float = 0.12,
) -> Any:
    if rate_limit_seconds:
        time.sleep(rate_limit_seconds)
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            encoding = response.headers.get("Content-Encoding", "").lower()
            if encoding == "gzip":
                data = gzip.decompress(data)
            elif encoding == "deflate":
                data = zlib.decompress(data)
            return json.loads(data.decode("utf-8"))
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        detail = f": {body[:500]}" if body else ""
        raise FetchError(f"HTTP {exc.code} while posting {url}{detail}") from exc
    except URLError as exc:
        raise FetchError(f"Network error while posting {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"Timeout while posting {url}") from exc
    except json.JSONDecodeError as exc:
        raise FetchError(f"JSON decode error while posting {url}: {exc}") from exc


def write_bytes(path: str | Path, data: bytes) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def write_json(path: str | Path, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return target
