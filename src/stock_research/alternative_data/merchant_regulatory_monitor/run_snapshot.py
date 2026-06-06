"""CLI entrypoint for merchant and regulatory alternative-data snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from .normalizer import build_summary, normalize_cpsc_recalls, normalize_text_record


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Could not locate investment-assistant project root")


def config_root() -> Path:
    return project_root() / "config" / "alternative_data" / "merchant_regulatory_monitor"


def runtime_root() -> Path:
    return project_root() / "data" / "alternative_data" / "merchant_regulatory_monitor"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-plan", default=str(config_root() / "source_plan.v1.json"))
    parser.add_argument("--merchant-text-json", action="append", default=[], help="JSON list/object of text records.")
    parser.add_argument("--merchant-html-file", action="append", default=[], help="Local seller/policy HTML file to strip into text.")
    parser.add_argument("--merchant-url", action="append", default=[], help="Live public merchant/policy URL to fetch as text.")
    parser.add_argument("--regulatory-url", action="append", default=[], help="Live official regulatory URL to fetch as text.")
    parser.add_argument("--cpsc-json", action="append", default=[], help="CPSC recall API-style JSON payload.")
    parser.add_argument("--fetch-cpsc-query", action="append", default=[], help="Live CPSC recall query term, for example Temu.")
    parser.add_argument("--query-term", action="append", default=["temu", "pdd", "pinduoduo"])
    parser.add_argument("--request-timeout", type=float, default=20.0)
    parser.add_argument("--output-dir", default=str(runtime_root() / "latest"))
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_plan = _read_json(Path(args.source_plan)) if args.source_plan else {}
    events = []

    for path in args.merchant_text_json:
        records = _records_from_payload(_read_json(Path(path)))
        for record in records:
            events.extend(normalize_text_record(record))

    for path in args.merchant_html_file:
        events.extend(normalize_text_record(_text_record_from_html_file(Path(path))))

    for url in args.merchant_url:
        events.extend(
            normalize_text_record(
                _fetch_text_record(
                    url,
                    source_group="merchant_platform_policy",
                    source_type="public_html_live",
                    timeout=args.request_timeout,
                )
            )
        )

    for url in args.regulatory_url:
        events.extend(
            normalize_text_record(
                _fetch_text_record(
                    url,
                    source_group="regulatory_consumer_protection",
                    source_type="official_public_page_live",
                    timeout=args.request_timeout,
                )
            )
        )

    for path in args.cpsc_json:
        events.extend(normalize_cpsc_recalls(_read_json(Path(path)), query_terms=args.query_term))

    for query in args.fetch_cpsc_query:
        payload = _fetch_json(_cpsc_url(source_plan, query), args.request_timeout)
        events.extend(normalize_cpsc_recalls(payload, query_terms=[query, *args.query_term]))

    summary = build_summary(events)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "merchant_regulatory_events.json", [event.model_dump(mode="json") for event in events])
    _write_json(output_dir / "merchant_regulatory_summary.json", summary.model_dump(mode="json"))
    (output_dir / "merchant_regulatory_summary.md").write_text(_render_markdown(summary, source_plan), encoding="utf-8")
    return {
        "status": "complete",
        "events": len(events),
        "high_severity_events": summary.high_severity_count,
        "source_plan": str(args.source_plan),
        "output_dir": str(output_dir),
    }


def main(argv: list[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, indent=2))
    return 0


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        records = payload.get("records") or payload.get("merchant_text_records") or []
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _cpsc_url(source_plan: dict[str, Any], query: str) -> str:
    for source in source_plan.get("sources", []):
        if isinstance(source, dict) and source.get("source_id") == "cpsc_recalls_api":
            template = source.get("url_template")
            if template:
                return str(template).format(query=quote_plus(query))
    return f"https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallTitle={quote_plus(query)}"


def _fetch_json(url: str, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": "investment-assistant/0.1", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body.decode("utf-8", errors="replace"))


def _fetch_text_record(url: str, source_group: str, source_type: str, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "investment-assistant/0.1", "Accept": "text/html, text/plain;q=0.9"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        final_url = response.geturl()
    html = body.decode("utf-8", errors="replace")
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return {
        "source_id": _source_id_from_url(final_url or url),
        "source_group": source_group,
        "source_type": source_type,
        "url": final_url or url,
        "title": parser.title or _source_id_from_url(final_url or url),
        "text": parser.text,
    }


def _text_record_from_html_file(path: Path) -> dict[str, Any]:
    html = path.read_text(encoding="utf-8", errors="replace")
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return {
        "source_id": path.stem,
        "source_group": "merchant_platform_policy",
        "source_type": "public_html_file",
        "title": parser.title or path.stem,
        "text": parser.text,
    }


def _source_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}".strip("/") or "source"
    return "".join(character if character.isalnum() else "_" for character in raw.lower()).strip("_")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._parts: list[str] = []

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip()).strip()

    @property
    def text(self) -> str:
        return " ".join(part.strip() for part in self._parts if part.strip()).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        self._parts.append(data)


def _render_markdown(summary, source_plan: dict[str, Any]) -> str:
    source_count = len(source_plan.get("sources", [])) if isinstance(source_plan, dict) else 0
    lines = [
        "# Temu Merchant / Regulatory Monitor",
        "",
        f"- Generated at: `{summary.generated_at.isoformat()}`",
        f"- Events: `{summary.event_count}`",
        f"- High severity events: `{summary.high_severity_count}`",
        f"- Sources in plan: `{source_count}`",
        "",
        "## Investment Questions",
        "",
    ]
    for question in summary.investment_questions:
        lines.append(f"- {question}")

    lines.extend(["", "## Topic Counts", ""])
    for topic, count in sorted(summary.topic_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{topic}`: {count}")
    if not summary.topic_counts:
        lines.append("- No topic events were emitted.")

    lines.extend(["", "## Top Events", ""])
    for event in summary.top_events:
        lines.append(f"- `{event.severity}` `{event.source_group}` `{event.topic}`: {event.title} - {event.evidence_excerpt}")
    if not summary.top_events:
        lines.append("- No events.")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
