"""Shared collector contracts and helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Could not locate investment-assistant project root")


def alt_data_runtime_root() -> Path:
    return project_root() / "data" / "alternative_data"


def read_json_if_exists(path: str | Path | None, default: Any | None = None) -> Any:
    if not path:
        return default
    target = Path(path)
    if not target.exists():
        return default
    return json.loads(target.read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_jsonable(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def median(values: list[float | int | None]) -> float | None:
    clean = sorted(float(value) for value in values if value is not None)
    if not clean:
        return None
    midpoint = len(clean) // 2
    if len(clean) % 2:
        return clean[midpoint]
    return (clean[midpoint - 1] + clean[midpoint]) / 2


def rate(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def pct_gap(target: float | None, benchmark: float | None) -> float | None:
    if target is None or benchmark in (None, 0):
        return None
    return (target - benchmark) / abs(benchmark) * 100


@dataclass
class CollectorFinding:
    finding_id: str
    question: str
    summary: str
    severity: str = "medium"
    confidence: str = "medium"
    evidence: JsonDict = field(default_factory=dict)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class CollectorPack:
    collector_id: str
    company: str
    brand: str
    generated_at: datetime
    source_inputs: JsonDict
    metrics: list[JsonDict] = field(default_factory=list)
    events: list[JsonDict] = field(default_factory=list)
    findings: list[CollectorFinding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def render_pack_markdown(pack: CollectorPack, title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Collector: `{pack.collector_id}`",
        f"- Company / brand: `{pack.company}` / `{pack.brand}`",
        f"- Generated at: `{pack.generated_at.isoformat()}`",
        f"- Metrics: `{len(pack.metrics)}`",
        f"- Events: `{len(pack.events)}`",
        f"- Findings: `{len(pack.findings)}`",
        "",
        "## Findings",
        "",
    ]
    if not pack.findings:
        lines.append("- No V1 threshold findings.")
    for finding in pack.findings:
        lines.append(
            f"- `{finding.finding_id}` "
            f"(severity={finding.severity}, confidence={finding.confidence}): {finding.summary}"
        )
        lines.append(f"  Question: {finding.question}")
        if finding.next_steps:
            lines.append(f"  Next: {'; '.join(finding.next_steps)}")

    lines.extend(["", "## Metrics", ""])
    if not pack.metrics:
        lines.append("- No metrics available.")
    for metric in pack.metrics[:30]:
        lines.append(f"- {_format_metric_line(metric)}")

    lines.extend(["", "## Events", ""])
    if not pack.events:
        lines.append("- No events available.")
    for event in pack.events[:20]:
        title_value = event.get("title") or event.get("source_id") or event.get("event_id") or "event"
        topic = event.get("topic") or event.get("event_topic") or event.get("source_type") or "unknown"
        excerpt = event.get("evidence_excerpt") or event.get("excerpt") or ""
        lines.append(f"- `{topic}` {title_value}: {excerpt[:260]}")

    if pack.limitations:
        lines.extend(["", "## Limitations", ""])
        for limitation in pack.limitations:
            lines.append(f"- {limitation}")

    lines.append("")
    return "\n".join(lines)


def _format_metric_line(metric: JsonDict) -> str:
    if metric.get("comparison_id"):
        price_gap = metric.get("relative_price_gap_pct")
        delivery_gap = metric.get("delivery_gap_days")
        return (
            f"`{metric['comparison_id']}`: "
            f"price_gap={_fmt(price_gap)}%, "
            f"delivery_gap={_fmt(delivery_gap)}d, "
            f"target_price={_fmt(metric.get('target_median_price'))}, "
            f"competitor_price={_fmt(metric.get('competitor_median_price'))}"
        )
    label = metric.get("metric_name") or metric.get("event_topic") or "metric"
    value = metric.get("value")
    if value is None:
        value = metric.get("current_value")
    return f"`{label}`: {value if value is not None else 'na'}"


def _fmt(value: Any) -> str:
    if value is None:
        return "na"
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)


def severity_from_level(value: float | None, medium: float, high: float) -> str:
    if value is None:
        return "low"
    absolute = abs(value)
    if absolute >= high:
        return "high"
    if absolute >= medium:
        return "medium"
    return "low"
