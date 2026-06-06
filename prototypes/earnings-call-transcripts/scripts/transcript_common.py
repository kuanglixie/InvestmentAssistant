#!/usr/bin/env python3
"""Shared helpers for earnings-call transcript sourcing prototypes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"


class TranscriptError(RuntimeError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def prototype_root() -> Path:
    return Path(__file__).resolve().parents[1]


def artifact_root() -> Path:
    return project_root() / "artifacts" / "earnings-call-transcripts"


def load_dotenv() -> None:
    for env_path in (project_root() / ".env", prototype_root() / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def parse_quarter(quarter: str) -> tuple[int | None, str | None]:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", quarter.upper())
    if not match:
        return None, None
    return int(match.group(1)), match.group(2)


def stable_id(symbol: str, quarter: str, provider: str, source_type: str) -> str:
    key = f"{symbol.upper()}:{quarter.upper()}:{provider}:{source_type}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def safe_slug(value: str) -> str:
    value = value or "transcript"
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:100] or "transcript"


def make_run_dir(symbol: str, quarter: str, provider: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = artifact_root() / f"{safe_slug(symbol.upper())}-{quarter.upper()}-{safe_slug(provider)}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def fetch_json(url: str, params: dict[str, str], timeout: int) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise TranscriptError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise TranscriptError(f"Network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise TranscriptError("Response was not JSON.") from exc


def alpha_vantage_key(demo: bool) -> str:
    if demo:
        return "demo"
    load_dotenv()
    key = os.environ.get("ALPHA_VANTAGE_API_KEY") or os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key:
        raise TranscriptError("Set ALPHA_VANTAGE_API_KEY, or pass --demo for IBM demo testing.")
    return key


def sanitize_secret_text(text: str) -> str:
    load_dotenv()
    sanitized = text
    for name, value in os.environ.items():
        if not value or len(value) < 8:
            continue
        if any(token in name.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            sanitized = sanitized.replace(value, "REDACTED")
    sanitized = re.sub(r"(API key as )\S+", r"\1REDACTED", sanitized, flags=re.IGNORECASE)
    return sanitized


def is_alpha_vantage_miss(payload: dict[str, Any]) -> str | None:
    for key in ("Information", "Error Message", "Note"):
        if key in payload:
            return sanitize_secret_text(str(payload[key]))
    transcript = payload.get("transcript")
    if not isinstance(transcript, list) or not transcript:
        return "No transcript list returned."
    return None


def normalize_alpha_vantage(symbol: str, quarter: str, payload: dict[str, Any]) -> dict[str, Any]:
    fiscal_year, fiscal_quarter = parse_quarter(quarter)
    blocks = payload.get("transcript") or []
    paragraphs: list[str] = []

    for block in blocks:
        speaker = (block.get("speaker") or "").strip()
        title = (block.get("title") or "").strip()
        content = (block.get("content") or "").strip()
        if not content:
            continue
        label = speaker
        if title and title != speaker:
            label = f"{speaker} ({title})" if speaker else title
        paragraphs.append(f"{label}: {content}" if label else content)

    transcript_text = "\n\n".join(paragraphs)
    return {
        "id": stable_id(symbol, quarter, "alpha_vantage", "third_party_api"),
        "ticker": symbol.upper(),
        "company_name": None,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "quarter": quarter.upper(),
        "call_date": None,
        "provider": "alpha_vantage",
        "source_url": build_alpha_vantage_url(symbol, quarter, "REDACTED"),
        "source_type": "third_party_api",
        "transcript_text": transcript_text,
        "raw_json": payload,
        "is_official": False,
        "is_machine_generated": False,
        "confidence": "medium",
        "can_store": None,
        "can_redistribute": False,
        "license_notes": "Review Alpha Vantage terms for your intended storage and redistribution use before production.",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def build_alpha_vantage_url(symbol: str, quarter: str, apikey: str) -> str:
    query = urllib.parse.urlencode(
        {
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": symbol.upper(),
            "quarter": quarter.upper(),
            "apikey": apikey,
        }
    )
    return f"{ALPHA_VANTAGE_URL}?{query}"


def normalize_local_transcript(
    symbol: str,
    quarter: str,
    company_name: str | None,
    text: str,
    provider: str,
    source_url: str | None,
    source_type: str,
    confidence: str,
    is_official: bool,
    is_machine_generated: bool,
    can_store: bool | None,
    can_redistribute: bool | None,
    license_notes: str | None,
) -> dict[str, Any]:
    fiscal_year, fiscal_quarter = parse_quarter(quarter)
    return {
        "id": stable_id(symbol, quarter, provider, source_type),
        "ticker": symbol.upper(),
        "company_name": company_name,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "quarter": quarter.upper(),
        "call_date": None,
        "provider": provider,
        "source_url": source_url,
        "source_type": source_type,
        "transcript_text": text.strip(),
        "raw_json": None,
        "is_official": is_official,
        "is_machine_generated": is_machine_generated,
        "confidence": confidence,
        "can_store": can_store,
        "can_redistribute": can_redistribute,
        "license_notes": license_notes,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def record_to_markdown(record: dict[str, Any]) -> str:
    lines = [
        f"# {record['ticker']} {record['quarter']} Earnings Call Transcript",
        "",
        f"- Provider: `{record['provider']}`",
        f"- Source type: `{record['source_type']}`",
        f"- Confidence: `{record.get('confidence')}`",
        f"- Official: `{record.get('is_official')}`",
        f"- Machine generated: `{record.get('is_machine_generated')}`",
        f"- Can store: `{record.get('can_store')}`",
        f"- Can redistribute: `{record.get('can_redistribute')}`",
        f"- License notes: {record.get('license_notes') or ''}",
        "",
        "## Transcript",
        "",
        record.get("transcript_text", ""),
        "",
    ]
    return "\n".join(lines)


def write_record(run_dir: Path, record: dict[str, Any]) -> None:
    safe_record = dict(record)
    safe_record["raw_json"] = record.get("raw_json")
    (run_dir / "record.json").write_text(json.dumps(safe_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "transcript.md").write_text(record_to_markdown(record), encoding="utf-8")
    if record.get("raw_json") is not None:
        (run_dir / "raw.json").write_text(json.dumps(record["raw_json"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_next_steps(run_dir: Path, symbol: str, quarter: str, reason: str) -> None:
    content = f"""# Next Steps: {symbol.upper()} {quarter.upper()}

Automated Alpha Vantage fetch did not produce a transcript.

Reason:

```text
{reason}
```

Fallback path:

1. Check company IR for official webcast/audio/transcript.
2. Check manual validation sources such as StockAnalysis, Motley Fool, Seeking Alpha, or Quartr.
3. If only official audio exists and use is permitted, transcribe it with the `webcast-transcripts` prototype.
4. Ingest the resulting text with `ingest_local_transcript.py`, preserving source type and license notes.
"""
    (run_dir / "next_steps.md").write_text(content, encoding="utf-8")


def add_common_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--quarter", required=True, help="YYYYQn format, e.g. 2024Q1.")
    parser.add_argument("--timeout", type=int, default=30)


def print_error(exc: Exception) -> int:
    print(f"error: {sanitize_secret_text(str(exc))}", file=sys.stderr)
    return 2
