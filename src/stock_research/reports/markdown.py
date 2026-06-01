from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.metrics.v1 import annual_fact_rows, annual_fact_source_rows, quarterly_fact_rows
from stock_research.reports.financial_interpretation import format_financial_diagnostic_questions_zh
from stock_research.state import ResearchState, utc_now_iso


VALUATION_FORMULA_IDS = {
    "enterprise_value_v1",
    "true_yield_v1",
    "free_cash_flow_yield_v1",
    "investment_adjusted_operating_yield_v1",
    "one_dollar_test_5y_v1",
}


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _money_billions(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) / 1_000_000_000:.1f}"
    except (TypeError, ValueError):
        return ""


def _usd_billions(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"${float(value) / 1_000_000_000:.1f}B"
    except (TypeError, ValueError):
        return ""


def _currency_billions(value: Any, currency: str | None) -> str:
    if value is None:
        return ""
    label = (currency or "").upper()
    try:
        return f"{label} {float(value) / 1_000_000_000:.1f}B".strip()
    except (TypeError, ValueError):
        return ""


def _shares_billions(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) / 1_000_000_000:.2f}"
    except (TypeError, ValueError):
        return ""


def _ratio(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _percent(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return ""


def _document_inventory(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "- None"
    counts = Counter(doc.get("document_type", "unknown").split(":", 1)[0] for doc in documents)
    category_counts = Counter(doc.get("research_category", "uncategorized") for doc in documents)
    financial_ready = sum(
        1
        for doc in documents
        if doc.get("research_category")
        in {
            "KEEP_CORE_ANNUAL_REPORT",
            "KEEP_CORE_INTERIM_EARNINGS",
            "KEEP_SECONDARY_INTERIM_FINANCIAL_CONTEXT",
        }
    )
    annuals = sorted(
        [
            doc
            for doc in documents
            if str(doc.get("document_type", "")).startswith(("20-F", "10-K", "annual_report_pdf"))
        ],
        key=lambda doc: doc.get("filing_date") or "",
    )
    interims = sorted(
        [
            doc
            for doc in documents
            if str(doc.get("document_type", "")).startswith(("interim_report_pdf", "6-K"))
            and doc.get("research_category") not in {"DROP_SEC_INDEX_OR_HEADERS", "LOW_KEEP_WRAPPER_METADATA"}
        ],
        key=lambda doc: doc.get("filing_date") or "",
        reverse=True,
    )[:8]
    recent_6ks = sorted(
        [
            doc
            for doc in documents
            if str(doc.get("document_type", "")).startswith("6-K")
            and doc.get("research_category") not in {"DROP_SEC_INDEX_OR_HEADERS", "LOW_KEEP_WRAPPER_METADATA"}
        ],
        key=lambda doc: doc.get("filing_date") or "",
        reverse=True,
    )[:8]
    lines = [
        f"- Documents cached: {len(documents)} total; "
        + ", ".join(f"{form}: {count}" for form, count in sorted(counts.items())),
        f"- Financial-extraction corpus: {financial_ready} documents",
        "- Research categories: "
        + ", ".join(f"{category}: {count}" for category, count in sorted(category_counts.items())),
    ]
    if annuals:
        lines.append("- Annual reports:")
        lines.extend(
            f"  - {doc.get('filing_date')} | {doc.get('document_id')} | {doc.get('local_path')}"
            for doc in annuals
        )
    if interims:
        lines.append("- Recent interim / quarterly reports sampled:")
        lines.extend(
            f"  - {doc.get('filing_date')} | {doc.get('research_category')} | {doc.get('document_id')} | {doc.get('local_path')}"
            for doc in interims
        )
    if recent_6ks:
        lines.append("- Recent useful 6-K files sampled:")
        lines.extend(
            f"  - {doc.get('filing_date')} | {doc.get('research_category')} | {doc.get('document_id')} | {doc.get('local_path')}"
            for doc in recent_6ks
        )
    return "\n".join(lines)


def _annual_facts_table(state: ResearchState) -> str:
    rows = annual_fact_rows(state.get("extracted_facts", []))
    if not rows:
        return "- No annual fact rows extracted yet."
    lines = [
        "| Year | Revenue | Gross Profit | Operating Income | Net Income | OCF | FCF | Cash | Assets | Liabilities |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows[-10:]:
        lines.append(
            "| {year} | {revenue} | {gross_profit} | {operating_income} | {net_income} | {ocf} | {fcf} | {cash} | {assets} | {liabilities} |".format(
                year=row["year"],
                revenue=_money_billions(row.get("revenue")),
                gross_profit=_money_billions(row.get("gross_profit")),
                operating_income=_money_billions(row.get("operating_income")),
                net_income=_money_billions(row.get("net_income")),
                ocf=_money_billions(row.get("operating_cash_flow")),
                fcf=_money_billions(row.get("free_cash_flow")),
                cash=_money_billions(row.get("cash")),
                assets=_money_billions(row.get("total_assets")),
                liabilities=_money_billions(row.get("total_liabilities")),
            )
        )
    return "\n".join(lines) + "\n\nAmounts are in RMB billions unless otherwise noted."


def _quarterly_facts_table(state: ResearchState) -> str:
    rows = quarterly_fact_rows(state.get("extracted_facts", []))
    if not rows:
        return "- No quarterly fact rows extracted yet."
    lines = [
        "| Quarter | Revenue | Gross Profit | Operating Income | Net Income | OCF | Cash | Diluted Shares |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows[-16:]:
        lines.append(
            "| {quarter} | {revenue} | {gross_profit} | {operating_income} | {net_income} | {ocf} | {cash} | {shares} |".format(
                quarter=row["quarter"],
                revenue=_money_billions(row.get("revenue")),
                gross_profit=_money_billions(row.get("gross_profit")),
                operating_income=_money_billions(row.get("operating_income")),
                net_income=_money_billions(row.get("net_income")),
                ocf=_money_billions(row.get("operating_cash_flow")),
                cash=_money_billions(row.get("cash")),
                shares=_shares_billions(row.get("diluted_shares")),
            )
        )
    return (
        "\n".join(lines)
        + "\n\nAmounts are in RMB billions except diluted shares, which are in billions of ordinary shares."
    )


def _annual_source_lineage_table(state: ResearchState) -> str:
    rows = annual_fact_source_rows(state.get("extracted_facts", []))
    if not rows:
        return "- No annual source lineage available yet."
    lines = [
        "| Year | Metric | Value | Source document | Tag / method |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        value = _format_lineage_value(row.get("value"), row.get("unit"))
        source = row.get("document_id") or row.get("local_path") or ""
        tag = row.get("tag_or_method") or ""
        lines.append(
            f"| {row.get('year')} | {row.get('metric')} | {value} | `{source}` | `{tag}` |"
        )
    return "\n".join(lines)


def _format_lineage_value(value: Any, unit: Any) -> str:
    if value is None:
        return ""
    if unit == "CNY":
        return f"RMB {_money_billions(value)}B"
    if unit == "shares":
        return f"{_shares_billions(value)}B shares"
    return str(value)


def _metric_summary(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return "- No metrics calculated yet."
    lines = []
    for metric in metrics:
        formula_id = metric.get("formula_id")
        if formula_id == "financial_quality_questions_v1":
            continue
        if formula_id == "latest_interim_trend_v1":
            lines.append(
                f"- {formula_id}: {metric.get('overall_status', metric.get('status'))}"
                f" | latest period {metric.get('latest_period_end', 'n/a')}"
            )
            continue
        if formula_id == "source_of_growth_attribution_v1":
            latest_interim = metric.get("latest_interim_result") or {}
            if latest_interim.get("status") == "calculated" and not any(
                result.get("status") == "calculated" for result in metric.get("annual_results", [])
            ):
                lines.append(
                    f"- {formula_id}: latest interim {latest_interim.get('period_end')} = "
                    f"{_percent(latest_interim.get('value'))}"
                )
                continue
        annual_results = [
            result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
        ]
        if not annual_results:
            lines.append(f"- {formula_id}: {metric.get('status')}")
            continue
        latest = sorted(annual_results, key=lambda result: result.get("year", 0))[-1]
        value = latest.get("value")
        display_name = latest.get("display_name") or formula_id
        if latest.get("unit") == "CNY":
            value_text = f"RMB {_money_billions(value)}B"
        elif latest.get("unit") == "ratio":
            value_text = _percent(value) if _ratio_should_be_percent(str(formula_id)) else _ratio(value)
        else:
            value_text = str(value)
        suffix = ""
        if latest.get("as_of_date"):
            suffix = f" | market data as of {latest.get('as_of_date')}"
        if latest.get("review_required"):
            suffix += " | review required"
        lines.append(f"- {display_name} (`{formula_id}`): latest {latest.get('year')} = {value_text}{suffix}")
    return "\n".join(lines) if lines else "- No metrics calculated yet."


def _ratio_should_be_percent(formula_id: str) -> bool:
    return any(
        marker in formula_id
        for marker in ["roic", "yield", "margin", "intensity", "risk", "burden", "quality", "attribution"]
    )


def _financial_quality_questions_summary(
    state_or_metrics: ResearchState | list[dict[str, Any]],
    metrics: list[dict[str, Any]] | None = None,
) -> str:
    if isinstance(state_or_metrics, dict):
        diagnostics = state_or_metrics.get("diagnostic_findings") or {}
        metrics = metrics or state_or_metrics.get("metrics", [])
    else:
        diagnostics = {}
        metrics = state_or_metrics
    legacy_metric = _metric_by_id(metrics, "financial_quality_questions_v1")
    questions = diagnostics.get("questions") or (legacy_metric.get("questions", []) if legacy_metric else [])
    questions = sorted(questions, key=lambda question: question.get("rank", 999))
    if not questions:
        return "- No financial diagnostic rules calculated yet."
    lines = [
        "这些是由确定性财务指标规则生成的核心阅读问题。重点不是只列数字，而是解释这些数字为什么能回答对应问题。"
    ]
    if diagnostics:
        summary = diagnostics.get("summary", {})
        lines.append(
            f"诊断状态：{diagnostics.get('status')} | 已回答 {summary.get('answered', 0)}，"
            f"部分回答 {summary.get('partial', 0)}，缺失 {summary.get('missing', 0)}。"
        )
    lines.extend(["", format_financial_diagnostic_questions_zh(questions)])
    return "\n".join(lines)


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


def _valuation_metrics_for_state(state: ResearchState) -> list[dict[str, Any]]:
    valuation_metrics = state.get("valuation_metrics") or []
    if valuation_metrics:
        return valuation_metrics
    return [
        metric
        for metric in state.get("metrics", [])
        if metric.get("formula_id") in VALUATION_FORMULA_IDS
    ]


def _format_latest_question_values(values: dict[str, Any]) -> str:
    if not values:
        return ""
    parts = []
    for key, value in values.items():
        if key == "year":
            parts.append(f"year {value}")
            continue
        parts.append(f"{key}: {_format_question_value(key, value)}")
    return "; ".join(parts)


def _format_question_value(key: str, value: Any) -> str:
    if value is None:
        return "not available"
    if key in {"owner_earnings", "net_cash"}:
        return f"RMB {_money_billions(value)}B"
    if any(
        marker in key
        for marker in [
            "margin",
            "growth",
            "roic",
            "capex_to_revenue",
            "capex_to_operating_cash_flow",
            "liabilities_to_assets",
            "sbc_to_",
            "diluted_shares_yoy",
        ]
    ):
        return _percent(value)
    if key in {"cash_conversion", "cash_to_total_liabilities", "debt_to_cash", "capex_to_operating_cash_flow", "sbc_to_operating_cash_flow"}:
        return _ratio(value)
    return str(value)


def _valuation_input_summary(market_inputs: dict[str, Any]) -> str:
    if not market_inputs:
        return "- No valuation input registry loaded."
    inputs = market_inputs.get("inputs") or {}
    lines = [
        f"- Status: {market_inputs.get('status')}",
        f"- Registry: `{market_inputs.get('path')}`",
        f"- Review status: {market_inputs.get('review_status', 'unknown')}",
        f"- Input required: {market_inputs.get('input_required')}",
        f"- Review required: {market_inputs.get('review_required')}",
    ]
    missing = market_inputs.get("missing") or []
    if missing:
        lines.append("- Missing required inputs: " + ", ".join(missing))
    if inputs:
        market_cap = inputs.get("market_cap")
        market_cap_text = (
            _currency_billions(market_cap, inputs.get("currency"))
            if isinstance(market_cap, int | float)
            else str(market_cap or "")
        )
        lines.extend(
            [
                f"- As-of date: {inputs.get('as_of_date') or 'missing'}",
                f"- Source: {inputs.get('source') or 'missing'}",
                f"- Share price: {inputs.get('currency', '')} {inputs.get('share_price') or 'missing'}",
                f"- Market cap: {market_cap_text or 'missing'}",
                f"- ADS outstanding: {_shares_billions(inputs.get('ads_outstanding')) or 'missing'}",
                f"- Ordinary shares outstanding: {_shares_billions(inputs.get('ordinary_shares_outstanding')) or 'missing'}",
                f"- Ordinary shares per ADS: {inputs.get('ordinary_shares_per_ads') or 'missing'}",
                f"- USD/CNY FX: {inputs.get('usd_cny_fx') or 'not used'}",
                f"- HKD/CNY FX: {inputs.get('hkd_cny_fx') or 'not used'}",
            ]
        )
    validation = market_inputs.get("validation") or {}
    conflicts = validation.get("conflicts") or []
    warnings = validation.get("warnings") or []
    if conflicts:
        lines.append(f"- Validation conflicts: {len(conflicts)}")
        for conflict in conflicts[:3]:
            mismatch = conflict.get("mismatch_pct")
            mismatch_text = _percent(mismatch) if mismatch is not None else "unknown"
            lines.append(
                f"- Conflict: {conflict.get('type')} from {conflict.get('source')} | mismatch {mismatch_text}"
            )
    if warnings:
        lines.append("- Validation warnings: " + "; ".join(warnings[:3]))
    notes = market_inputs.get("notes")
    if notes:
        lines.append(f"- Note: {notes}")
    return "\n".join(lines)


def _verification_summary(results: list[dict[str, Any]]) -> str:
    if not results:
        return "- No verification results."
    counts = Counter(result.get("status", "unknown") for result in results)
    lines = [
        "- "
        + ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))
    ]
    material = [result for result in results if result.get("status") == "material_conflict"]
    for result in material[:5]:
        period = result.get("end_date") or result.get("instant")
        mismatch = result.get("mismatch_pct", 0)
        lines.append(
            f"- Material conflict: {result.get('metric')} | {period} | mismatch {_percent(mismatch)} | recorded for human review"
        )
    return "\n".join(lines)


def _material_event_summary(scan: dict[str, Any]) -> str:
    if not scan:
        return "- Material-event scanner has not run yet."
    lines = [
        f"- Status: {scan.get('status')}",
        f"- Documents scanned: {scan.get('scanned_document_count', 0)}",
        f"- Material events found: {scan.get('material_event_count', 0)}",
        f"- High-priority events: {scan.get('high_priority_event_count', 0)}",
    ]
    type_counts = scan.get("event_type_counts") or {}
    if type_counts:
        lines.append(
            "- Event types: "
            + ", ".join(f"{event_type}: {count}" for event_type, count in sorted(type_counts.items()))
        )
    events = scan.get("events") or []
    if not events:
        lines.append(
            "- No non-core official filing was promoted into the report. This means the scanner did not find a material accounting, auditor, financing, management, governance, dilution, acquisition, impairment, restructuring, or legal/regulatory event."
        )
        return "\n".join(lines)
    lines.extend(
        [
            "",
            "| Filing date | Event type | Severity | Document | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for event in events[:12]:
        snippet = _markdown_cell(event.get("evidence_snippet") or event.get("research_reason") or "")
        lines.append(
            "| {date} | {event_type} | {severity} | `{document}` | {snippet} |".format(
                date=_markdown_cell(event.get("filing_date")),
                event_type=_markdown_cell(event.get("event_type")),
                severity=_markdown_cell(event.get("severity")),
                document=_markdown_cell(event.get("document_id")),
                snippet=snippet[:240],
            )
        )
    return "\n".join(lines)


def _report_pack_summary(pack: dict[str, Any], path: str | None) -> str:
    if not pack:
        return "- FinancialReportPack has not been built yet."
    missing = pack.get("missing_facts") or {}
    review_flags = pack.get("human_review_flags") or []
    return "\n".join(
        [
            f"- Schema version: {pack.get('schema_version')}",
            f"- Pack path: `{path or ''}`",
            f"- Annual fact rows: {len(pack.get('annual_facts') or [])}",
            f"- Quarterly fact rows: {len(pack.get('quarterly_facts') or [])}",
            f"- Financial metric families: {len(pack.get('financial_metrics') or [])}",
            f"- Material events: {(pack.get('material_event_scan') or {}).get('material_event_count', 0)}",
            f"- Human review flags: {len(review_flags)}",
            "- Priority-A missing facts: "
            + (", ".join(str(item) for item in missing.get("priority_a", [])) or "none"),
            "- Report-control rule: the writing layer may summarize this pack but must not recalculate numbers or invent facts.",
        ]
    )


def _learning_summary(learning_context: dict[str, Any]) -> str:
    if not learning_context:
        return "- No learning-material registry loaded."
    counts = learning_context.get("status_counts", {})
    sources = learning_context.get("source_materials", [])
    lines = [
        f"- Registry: `{learning_context.get('registry_path')}`",
        f"- Source materials: {len(sources)}",
        "- Lesson statuses: "
        + (", ".join(f"{status}: {count}" for status, count in counts.items()) or "none"),
        f"- Activation rule: {learning_context.get('activation_rule')}",
    ]
    return "\n".join(lines)


def _finding_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    lines = [f"- Status: {findings.get('status', 'unknown')}"]
    analysis = findings.get("official_report_analysis") or {}
    if analysis:
        lines.append(f"- Input scope: {analysis.get('input_scope', 'unknown')}")
        latest_source = analysis.get("latest_source") or {}
        if latest_source:
            lines.append(
                f"- Latest official report used: {latest_source.get('filing_date')} | {latest_source.get('local_path')}"
            )
        subagents = analysis.get("subagent_reports") or []
        if subagents:
            lines.append("- Official-report subagents:")
            for report in subagents[:8]:
                lines.append(f"  - {report.get('name')}: {report.get('status')}")
                for finding in (report.get("findings") or [])[:2]:
                    if isinstance(finding, str):
                        lines.append(f"    - {finding}")
                    else:
                        claim = finding.get("claim") or finding.get("hypothesis") or str(finding)
                        status = finding.get("status")
                        lines.append(f"    - {claim}" + (f" | {status}" if status else ""))
        dossier_text = _official_report_dossier_main_summary(
            analysis.get("official_report_dossier") or {}
        )
        if dossier_text:
            lines.append(dossier_text)
        management_framing = _management_framing_main_summary(
            analysis.get("management_framing_analysis") or {}
        )
        if management_framing:
            lines.append(management_framing)
        operating_kpis = _operating_kpi_main_summary(
            analysis.get("operating_kpi_analysis") or {}
        )
        if operating_kpis:
            lines.append(operating_kpis)
        checklist = analysis.get("right_business_model_checklist") or []
        if checklist:
            lines.extend(
                [
                    "",
                    "### Right Business Model Checklist",
                    "",
                    "| Check | Status | Note |",
                    "| --- | --- | --- |",
                ]
            )
            for item in checklist:
                lines.append(
                    "| {item} | {status} | {note} |".format(
                        item=_markdown_cell(item.get("item")),
                        status=_markdown_cell(item.get("status")),
                        note=_markdown_cell(item.get("note")),
                    )
                )
        evidence_cards = analysis.get("evidence_cards") or []
        if evidence_cards:
            lines.extend(
                [
                    "",
                    "### Deep Official-Report Evidence Cards",
                    "",
                    "- Main-report view: compact thesis map. Full source snippets are in the data-linkage appendix.",
                    "",
                    "| Theme | Finding | Why it matters | Limitation | Source snippets |",
                    "| --- | --- | --- | --- | ---: |",
                ]
            )
            for card in evidence_cards[:10]:
                lines.append(
                    "| {theme} | {finding} | {why} | {limitation} | {evidence_count} |".format(
                        theme=_markdown_cell(card.get("theme")),
                        finding=_markdown_cell(card.get("finding")),
                        why=_markdown_cell(card.get("why_it_matters")),
                        limitation=_markdown_cell(card.get("limitation")),
                        evidence_count=len(card.get("evidence") or []),
                    )
                )
        missing = analysis.get("missing_evidence") or []
        if missing:
            lines.append("- Missing evidence:")
            for item in missing[:5]:
                lines.append(f"  - {item}")
        if analysis.get("conclusion_limit"):
            lines.append(f"- Conclusion limit: {analysis.get('conclusion_limit')}")
        return "\n".join(lines)
    evidence = findings.get("annual_report_evidence", {})
    if evidence.get("status") == "evidence_collected":
        source = evidence.get("source_document", {})
        lines.append(f"- Latest annual report used: {source.get('filing_date')} | {source.get('local_path')}")
        for topic, details in sorted(evidence.get("topics", {}).items()):
            matched = ", ".join(details.get("matched_terms", [])) or "none"
            lines.append(f"- {topic}: {details.get('total_hits', 0)} marker hits; matched terms: {matched}")
    return "\n".join(lines)


def _official_report_dossier_main_summary(dossier: dict[str, Any]) -> str:
    fields = dossier.get("fields") or []
    if not fields:
        return ""
    lines = [
        "",
        "### Official Report Dossier",
        "",
        f"- Fields: {dossier.get('field_count', len(fields))}",
        f"- Accuracy policy: {dossier.get('accuracy_policy')}",
        "",
        "| Field | Status | Summary | Source section | Evidence |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for field in fields:
        lines.append(
            "| {field} | {status} | {summary} | {section} | {evidence_count} |".format(
                field=_markdown_cell(field.get("label")),
                status=_markdown_cell(field.get("status")),
                summary=_markdown_cell(field.get("summary")),
                section=_markdown_cell(field.get("source_section")),
                evidence_count=len(field.get("evidence") or []),
            )
        )
    return "\n".join(lines)


def _operating_kpi_main_summary(analysis: dict[str, Any]) -> str:
    if not analysis:
        return ""
    latest_by_metric = analysis.get("latest_by_metric") or {}
    defined_only = analysis.get("defined_only_markers") or []
    coverage = analysis.get("metric_coverage") or []
    lines = [
        "",
        "### Official Operating KPI Extraction",
        "",
        f"- Status: {analysis.get('status')}",
        f"- Numeric KPI records: {analysis.get('record_count', 0)}",
        f"- Scope: {analysis.get('scope')}",
    ]
    if latest_by_metric:
        lines.extend(
            [
                "",
                "- Disclosure pattern: these KPIs are not all reported every year. GMV, active buyers, MAU, annual spending per active buyer, and total orders are historical Pinduoduo growth KPIs. Active merchants and transaction-services revenue per active merchant are the current merchant-focused series.",
                "",
                "| KPI | Extracted official periods | Latest period | Latest value | Unit | Source |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for metric, record in sorted(latest_by_metric.items()):
            source = (record.get("source_document") or {}).get("document_id")
            lines.append(
                "| {label} | {coverage} | {period} | {value} | {unit} | `{source}` |".format(
                    label=_markdown_cell(record.get("label") or metric),
                    coverage=_markdown_cell(_kpi_period_coverage(analysis, metric)),
                    period=_markdown_cell(record.get("period_end")),
                    value=_markdown_cell(_format_kpi_value(record)),
                    unit=_markdown_cell(record.get("unit")),
                    source=_markdown_cell(source),
                )
            )
    if coverage:
        lines.extend(
            [
                "",
                "#### Operating Metric Coverage",
                "",
                "| Metric / question | Status | Reported period coverage | Latest value | What the official reports give us | Why it matters |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for item in coverage:
            latest_record = item.get("latest_record") or {}
            coverage_metric = latest_record.get("metric")
            lines.append(
                "| {label} | {status} | {coverage} | {latest} | {note} | {why} |".format(
                    label=_markdown_cell(item.get("label")),
                    status=_markdown_cell(item.get("status")),
                    coverage=_markdown_cell(_kpi_period_coverage(analysis, coverage_metric)),
                    latest=_markdown_cell(_format_kpi_value(latest_record) if latest_record else ""),
                    note=_markdown_cell(item.get("note")),
                    why=_markdown_cell(item.get("why_it_matters")),
                )
            )
    if defined_only:
        lines.extend(["", "- Defined but not quantified in latest official report:"])
        for marker in defined_only:
            lines.append(f"  - {marker.get('label')}: {marker.get('note')}")
    if analysis.get("audit_note"):
        lines.append(f"- KPI audit note: {analysis.get('audit_note')}")
    return "\n".join(lines)


def _management_framing_main_summary(analysis: dict[str, Any]) -> str:
    if not analysis:
        return ""
    themes = analysis.get("themes") or []
    lines = [
        "",
        "### Official Management Framing",
        "",
        f"- Status: {analysis.get('status')}",
        f"- Scope: {analysis.get('scope')}",
        f"- Themes extracted: {analysis.get('theme_count', len(themes))}",
    ]
    if analysis.get("summary"):
        lines.append(f"- Summary: {analysis.get('summary')}")
    if themes:
        lines.extend(
            [
                "",
                "| Theme | Management claim | Why it matters | Accuracy limit |",
                "| --- | --- | --- | --- |",
            ]
        )
        for theme in themes:
            lines.append(
                "| {theme} | {claim} | {why} | {limit} |".format(
                    theme=_markdown_cell(theme.get("theme")),
                    claim=_markdown_cell(theme.get("management_claim") or theme.get("claim")),
                    why=_markdown_cell(theme.get("why_it_matters")),
                    limit=_markdown_cell(theme.get("accuracy_limit")),
                )
            )
    if analysis.get("audit_note"):
        lines.append(f"- Management-framing audit note: {analysis.get('audit_note')}")
    return "\n".join(lines)


def _format_kpi_value(record: dict[str, Any]) -> str:
    value = record.get("value")
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    unit = record.get("unit")
    if unit == "CNY":
        return f"RMB {numeric / 1_000_000_000:.1f}B"
    if unit in {"users", "orders", "merchants"}:
        if numeric >= 1_000_000_000:
            return f"{numeric / 1_000_000_000:.1f}B"
        return f"{numeric / 1_000_000:.1f}M"
    if unit in {"CNY_per_active_buyer", "CNY_per_active_merchant"}:
        return f"RMB {numeric:,.1f}"
    return f"{numeric:,.0f}"


def _kpi_period_coverage(analysis: dict[str, Any], metric: str | None) -> str:
    if not metric:
        return "not quantified"
    records = [
        record
        for record in analysis.get("records", [])
        if record.get("metric") == metric and record.get("period_end")
    ]
    if not records:
        return "not quantified"
    periods = sorted(str(record.get("period_end")) for record in records)
    period_types = sorted(
        {str(record.get("period_type")) for record in records if record.get("period_type")}
    )
    range_text = periods[0] if periods[0] == periods[-1] else f"{periods[0]} to {periods[-1]}"
    type_text = f"; {', '.join(period_types)}" if period_types else ""
    return f"{len(records)} records; {range_text}{type_text}"


def _external_moat_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    source_lines = findings.get("source_lines") or []
    hypotheses = findings.get("hypotheses") or []
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Registry: `{findings.get('registry_path') or 'not configured'}`",
        f"- Planned-only V1: {findings.get('planned_only', False)}",
        f"- Hypotheses to test: {len(hypotheses)}",
        f"- Source lines: {len(source_lines)}",
    ]
    if findings.get("status_counts"):
        lines.append(
            "- Source-line statuses: "
            + ", ".join(
                f"{status}: {count}" for status, count in findings.get("status_counts", {}).items()
            )
        )
    if findings.get("tier_counts"):
        lines.append(
            "- Quality-tier coverage: "
            + ", ".join(
                f"tier {tier}: {count}" for tier, count in findings.get("tier_counts", {}).items()
            )
        )
    if source_lines:
        lines.extend(
            [
                "",
                "| Source line | Tier | Role | Status |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for source_line in source_lines:
            role = str(source_line.get("validation_role", "")).replace("|", "/")
            lines.append(
                f"| {source_line.get('name')} | {source_line.get('quality_tier')} | {role} | {source_line.get('status')} |"
            )
    review_decisions = findings.get("review_needed_decisions") or []
    if review_decisions:
        lines.extend(["", "- Decisions / assumptions recorded:"])
        for decision in review_decisions:
            marker = "review" if decision.get("needs_user_review") else "noted"
            lines.append(f"  - {decision.get('decision_id')}: {marker} | {decision.get('decision')}")
    official_gaps = findings.get("official_report_gaps") or []
    if official_gaps:
        lines.extend(["", "- Official-report gaps this plan is meant to test:"])
        for gap in official_gaps[:6]:
            lines.append(f"  - {gap}")
    auditor_rules = findings.get("auditor_rules") or []
    if auditor_rules:
        lines.extend(["", "- External-source audit rules:"])
        for rule in auditor_rules[:6]:
            lines.append(f"  - {rule}")
    return "\n".join(lines)


def _public_voice_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    theme_summary = findings.get("theme_summary") or {}
    theme_counts = theme_summary.get("counts") or {}
    source_results = findings.get("source_results") or []
    stats = findings.get("collection_stats") or {}
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Registry: `{findings.get('registry_path') or 'not configured'}`",
        f"- Offline: {findings.get('offline', False)}",
        f"- Sources registered: {findings.get('source_count', 0)}",
        f"- Collectable adapters in V1: {findings.get('collectable_source_count', 0)}",
        f"- Manual/source-specific adapters pending: {findings.get('manual_or_blocked_source_count', 0)}",
        f"- Evidence items collected: {findings.get('evidence_item_count', 0)}",
    ]
    if stats:
        lines.extend(
            [
                "- Collection breadth: "
                f"{stats.get('searches_attempted', 0)} searches, "
                f"{stats.get('posts_collected', 0)} pages/posts fetched, "
                f"{stats.get('comments_seen_before_filter', 0)} public-voice items scanned, "
                f"{stats.get('comments_collected', 0)} items kept after relevance/theme filters.",
                "- Collection controls: "
                f"{stats.get('unique_posts_with_evidence', 0)} posts with usable evidence, "
                f"{stats.get('duplicate_comments_skipped', 0)} duplicate comments skipped, "
                f"{stats.get('cache_fallbacks', 0)} cache fallbacks.",
            ]
        )
    if theme_counts:
        lines.append(
            "- Theme counts: "
            + ", ".join(f"{theme}: {count}" for theme, count in sorted(theme_counts.items()))
        )
    theme_findings = findings.get("theme_findings") or []
    if theme_findings:
        lines.extend(["", "- Theme summaries:"])
        for finding in theme_findings[:7]:
            lines.append(
                f"  - {finding.get('label')}: {finding.get('summary')} | confidence: {finding.get('confidence')}"
            )
    if source_results:
        lines.extend(
            [
                "",
                "| Source | Adapter | Status | Pages/posts | Items scanned | Evidence items | Cache fallbacks |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for result in source_results:
            lines.append(
                f"| {result.get('name')} | {result.get('adapter')} | {result.get('status')} | "
                f"{result.get('posts_collected', 0)} | "
                f"{result.get('comments_seen_before_filter', 0)} | "
                f"{len(result.get('evidence_items', []))} | "
                f"{result.get('cache_fallbacks', 0)} |"
            )
    aggregate_results = [
        result for result in source_results if result.get("aggregate_summary")
    ]
    if aggregate_results:
        lines.extend(["", "- Source aggregate summaries:"])
        for result in aggregate_results:
            lines.append(f"  - {result.get('name')}: {_public_voice_aggregate_line(result.get('aggregate_summary') or {})}")
    examples = theme_summary.get("examples") or {}
    if examples:
        lines.extend(["", "- Representative public-voice excerpts:"])
        for theme, items in list(examples.items())[:6]:
            lines.append(f"  - {theme}:")
            for item in items[:2]:
                excerpt = str(item.get("excerpt") or "").replace("\n", " ")
                source = item.get("source_name") or item.get("source_id") or "source"
                evidence_type = item.get("evidence_type") or "comment"
                lines.append(f"    - [{source} / {evidence_type}] {excerpt} | {item.get('comment_url')}")
    audit_notes = findings.get("audit_notes") or []
    if audit_notes:
        lines.extend(["", "- Public-voice audit notes:"])
        for note in audit_notes[:5]:
            lines.append(f"  - {note}")
    errors = findings.get("errors") or []
    if errors:
        lines.extend(["", "- Collection errors / blocked sources:"])
        for error in errors[:5]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def _public_voice_aggregate_line(summary: dict[str, Any]) -> str:
    parts = []
    if summary.get("rating") is not None and summary.get("review_count") is not None:
        parts.append(f"rating {_ratio(summary.get('rating'))}/5 from {int(summary.get('review_count')):,} reviews")
    if summary.get("recommend_percent") is not None:
        parts.append(f"{summary.get('recommend_percent')}% recommend")
    if summary.get("positive_reviews_last_12_months_percent") is not None:
        parts.append(f"{summary.get('positive_reviews_last_12_months_percent')}% positive in last 12 months")
    counts = summary.get("category_mention_counts") or {}
    if counts:
        parts.append("category counts " + ", ".join(f"{label}={count:,}" for label, count in sorted(counts.items())))
    return "; ".join(parts) or "aggregate profile collected"


def _ir_cross_validation_summary(result: dict[str, Any]) -> str:
    if not result:
        return "- Not run."
    comparisons = result.get("comparisons", [])
    filled = result.get("filled_facts", [])
    attempts = result.get("source_attempts", [])
    status_counts = Counter(comparison.get("status", "unknown") for comparison in comparisons)
    lines = [
        f"- Status: {result.get('status')}",
        f"- Source attempts: {len(attempts)}",
        "- Comparison status counts: "
        + (", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items())) or "none"),
        f"- Missing facts filled: {len(filled)}",
    ]
    for attempt in attempts:
        lines.append(
            f"- Source attempt {attempt.get('fiscal_year')}: {attempt.get('status')} | PDF error: {attempt.get('pdf_error') or 'none'}"
        )
    for fact in filled[:8]:
        value = fact.get("value")
        value_text = f"RMB {_money_billions(value)}B" if fact.get("unit") == "CNY" else str(value)
        note = fact.get("interpretation_note")
        lines.append(
            f"- Filled {fact.get('year')} {fact.get('metric')}: {value_text}"
            + (f" | {note}" if note else "")
        )
    return "\n".join(lines)


def _open_issue_lines(state: ResearchState) -> list[str]:
    company_id = (state.get("canonical_company") or {}).get("company_id")
    if company_id == "tencent":
        lines = [
            "Tencent V1 uses Tencent IR financial-report PDFs as the official source; HKEX official cross-checking is still the next independent official-source layer.",
            "Tencent PDF extraction now reads the latest annual report's five-year summary, audited annual statement tables, and the latest mapped interim statement tables.",
            "Tencent official internal cross-checking compares overlapping PDF facts, such as financial-summary values versus audited statement-table values.",
        ]
        market_inputs = state.get("market_inputs", {})
        if market_inputs.get("status") == "input_available":
            lines.append(
                "Tencent market-price-dependent metrics use Google Finance 0700:HKG, Google Finance HKD/CNY, official issued shares, and Yahoo quote cross-checking."
            )
        else:
            lines.append("Market-price-dependent metrics for Tencent are pending validated HKD quote and HKD/CNY inputs.")
        lines.append("Third-party full financial-statement sanity checks are still pending; they should not override official Tencent/HKEX sources.")
        return lines
    discovery = state.get("source_discovery", {})
    pdd_ir_error = discovery.get("pdd_ir_error")
    lines = []
    if pdd_ir_error:
        lines.append(
            f"PDD investor relations fetch failed with: `{pdd_ir_error}`. SEC filings are the usable official source in this run."
        )
    else:
        lines.append(
            "PDD investor relations home fetch is currently unavailable in this run; SEC filings are the usable official source."
        )
    lines.extend(
        [
            "Recent direct CapEx tags are not always present, so FCF is left blank where official CapEx is unavailable.",
            "Market-price-dependent metrics use the market-data agent when quote, FX, and official share-structure inputs validate cleanly.",
        ]
    )
    return lines


def _metric_has_calculated_result(metrics: list[dict[str, Any]], formula_id: str) -> bool:
    for metric in metrics:
        if metric.get("formula_id") != formula_id:
            continue
        return any(result.get("status") == "calculated" for result in metric.get("annual_results", []))
    return False


def _right_price_line(state: ResearchState) -> str:
    valuation_metrics = _valuation_metrics_for_state(state)
    if _metric_has_calculated_result(valuation_metrics, "true_yield_v1") and _metric_has_calculated_result(
        valuation_metrics,
        "free_cash_flow_yield_v1",
    ):
        return (
            "partially evaluated; EV, owner-earnings yield, and FCF yield are calculated from current market data, "
            "while valuation-agent assumptions still require review."
        )
    if _metric_has_calculated_result(valuation_metrics, "enterprise_value_v1"):
        return (
            "partially prepared; EV is calculated, but yield metrics still need complete financial inputs "
            "and valuation-agent assumptions."
        )
    return "partially prepared; valuation awaits market data and valuation-agent assumptions."


def _right_business_model_line(state: ResearchState) -> str:
    findings = state.get("business_model_findings", {})
    external = state.get("external_moat_findings", {})
    checklist = findings.get("right_business_model_checklist") or []
    if not checklist:
        return "not evaluated yet."
    supported = [item for item in checklist if item.get("status") in {"supported", "partially_supported"}]
    hypothesis_only = [item for item in checklist if item.get("status") == "hypothesis_only"]
    external_note = ""
    if external.get("status") == "source_plan_ready_pending_collection":
        external_note = " External moat-validation sources are planned but not yet collected."
    if supported or hypothesis_only:
        return (
            "partially evaluated from official reports; business model and financial evidence are mapped, "
            "while customer, competitor, and durability validation remain missing."
            + external_note
        )
    return "prepared but not supported by available official-report evidence yet."


def _right_people_line(state: ResearchState) -> str:
    findings = state.get("leadership_findings") or {}
    if not findings:
        return "not evaluated yet."
    overall = findings.get("overall_read")
    if overall:
        return _markdown_text(overall)
    checklist = findings.get("right_people_checklist") or []
    if any(item.get("status") == "needs_review" for item in checklist):
        return "needs review; one or more governance, verification, or integrity flags remain unresolved."
    supported = [item for item in checklist if item.get("status") in {"supported", "partially_supported"}]
    if supported:
        return "partially evaluated; governance, incentives, capital allocation, communication, and execution evidence are mapped."
    return "prepared but not supported by available evidence yet."


def _data_linkage_path(state: ResearchState) -> str:
    return state.get("data_linkage_report_path") or f"{state['run_dir']}/data_linkage.md"


def _financial_results_report_path(state: ResearchState) -> str:
    return state.get("financial_results_report_path") or f"{state['run_dir']}/financial_results_report.md"


def _official_report_evidence_report_path(state: ResearchState) -> str:
    return state.get("official_report_evidence_report_path") or f"{state['run_dir']}/official_report_evidence_report.md"


def _business_model_report_path(state: ResearchState) -> str:
    return state.get("business_model_report_path") or f"{state['run_dir']}/business_model_report.md"


def _right_people_report_path(state: ResearchState) -> str:
    return state.get("right_people_report_path") or f"{state['run_dir']}/right_people_report.md"


def _right_people_chinese_report_path(state: ResearchState) -> str:
    return state.get("right_people_chinese_report_path") or f"{state['run_dir']}/right_people_report.zh.md"


def _video_manifest_path(state: ResearchState) -> str:
    return state.get("video_manifest_path") or f"{state['run_dir']}/video_manifest.json"


def _markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace("|", "/")


def _markdown_text(value: Any) -> str:
    return _markdown_cell(value).strip()


def _joined_items(items: list[Any], *, limit: int = 3) -> str:
    return "; ".join(_markdown_text(item) for item in items[:limit] if _markdown_text(item))


def _section_bullets(items: list[Any], *, limit: int = 3, empty: str = "None recorded.") -> list[str]:
    kept = [_markdown_text(item) for item in items[:limit] if _markdown_text(item)]
    if not kept:
        return [f"- {empty}"]
    return [f"- {item}" for item in kept]


def _format_report_percent(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return None


def _source_inventory_summary(source_candidates: list[dict[str, Any]]) -> str:
    if not source_candidates:
        return "- No source candidates recorded."
    tier_counts = Counter(source.get("trust_tier", "unknown") for source in source_candidates)
    status_counts = Counter(source.get("status", "unknown") for source in source_candidates)
    official_sources = [
        source.get("name")
        for source in source_candidates
        if source.get("trust_tier") == 1
    ]
    lines = [
        f"- Source candidates: {len(source_candidates)}",
        "- Trust tiers: " + ", ".join(f"tier {tier}: {count}" for tier, count in sorted(tier_counts.items(), key=lambda item: str(item[0]))),
        "- Statuses: " + ", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items())),
    ]
    if official_sources:
        lines.append("- Official source-of-record candidates: " + "; ".join(str(source) for source in official_sources))
    return "\n".join(lines)


def _source_inventory_table(source_candidates: list[dict[str, Any]]) -> str:
    if not source_candidates:
        return "- No source candidates recorded."
    lines = [
        "| Source ID | Name | Type | Tier | Status | URL | Reason |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for source in source_candidates:
        lines.append(
            "| {source_id} | {name} | {type} | {tier} | {status} | {url} | {reason} |".format(
                source_id=_markdown_cell(source.get("source_id")),
                name=_markdown_cell(source.get("name")),
                type=_markdown_cell(source.get("type")),
                tier=_markdown_cell(source.get("trust_tier")),
                status=_markdown_cell(source.get("status")),
                url=_markdown_cell(source.get("url")),
                reason=_markdown_cell(source.get("reason")),
            )
        )
    return "\n".join(lines)


def _document_linkage_table(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "- No documents recorded."
    lines = [
        "| Filing date | Report date | Type | Category | Decision | Document ID | Local path | Source URL |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for doc in sorted(documents, key=lambda item: (item.get("filing_date") or "", item.get("document_id") or "")):
        lines.append(
            "| {filing_date} | {report_date} | {doc_type} | {category} | {decision} | `{document_id}` | `{local_path}` | {source_url} |".format(
                filing_date=_markdown_cell(doc.get("filing_date")),
                report_date=_markdown_cell(doc.get("report_date")),
                doc_type=_markdown_cell(doc.get("document_type")),
                category=_markdown_cell(doc.get("research_category")),
                decision=_markdown_cell(doc.get("research_decision") or doc.get("status")),
                document_id=_markdown_cell(doc.get("document_id")),
                local_path=_markdown_cell(doc.get("local_path")),
                source_url=_markdown_cell(doc.get("source_url")),
            )
        )
    return "\n".join(lines)


def _fact_period(fact: dict[str, Any]) -> str:
    start = fact.get("start_date")
    end = fact.get("end_date")
    instant = fact.get("instant")
    if start and end:
        return f"{start} to {end}"
    return str(instant or end or "")


def _format_exact_value(value: Any, unit: Any) -> str:
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        number = f"{int(numeric):,}"
    else:
        number = f"{numeric:,.4f}".rstrip("0").rstrip(".")
    return f"{number} {unit}".strip()


def _financial_fact_lineage_table(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return "- No selected extracted facts recorded."
    lines = [
        "| Period | Period type | Metric | Value | Method / tag | Filing date | Document ID | Source URL | Fact ID |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for fact in sorted(
        facts,
        key=lambda item: (
            item.get("end_date") or item.get("instant") or "",
            item.get("period_type") or "",
            item.get("metric") or "",
            item.get("document_id") or "",
        ),
    ):
        method = fact.get("xbrl_tag") or fact.get("extraction_method")
        lines.append(
            "| {period} | {period_type} | {metric} | {value} | `{method}` | {filing_date} | `{document_id}` | {source_url} | `{fact_id}` |".format(
                period=_markdown_cell(_fact_period(fact)),
                period_type=_markdown_cell(fact.get("period_type")),
                metric=_markdown_cell(fact.get("metric")),
                value=_markdown_cell(_format_exact_value(fact.get("value"), fact.get("unit"))),
                method=_markdown_cell(method),
                filing_date=_markdown_cell(fact.get("filing_date")),
                document_id=_markdown_cell(fact.get("document_id")),
                source_url=_markdown_cell(fact.get("source_url")),
                fact_id=_markdown_cell(fact.get("fact_id")),
            )
        )
    return "\n".join(lines)


def _metric_linkage_table(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return "- No metric calculations recorded."
    lines = [
        "| Formula | Year | Status | Value | Formula / assumption | Source fact IDs |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for metric in metrics:
        formula_id = metric.get("formula_id")
        annual_results = metric.get("annual_results") or []
        if not annual_results:
            lines.append(
                f"| {_markdown_cell(formula_id)} |  | {_markdown_cell(metric.get('status'))} |  | {_markdown_cell(metric.get('note'))} |  |"
            )
            continue
        for result in annual_results:
            formula_note = result.get("formula") or result.get("assumption") or result.get("note")
            source_fact_ids = ", ".join(str(item) for item in result.get("source_fact_ids", []))
            lines.append(
                "| {formula_id} | {year} | {status} | {value} | {formula_note} | `{source_fact_ids}` |".format(
                    formula_id=_markdown_cell(formula_id),
                    year=_markdown_cell(result.get("year")),
                    status=_markdown_cell(result.get("status")),
                    value=_markdown_cell(_format_exact_value(result.get("value"), result.get("unit"))),
                    formula_note=_markdown_cell(formula_note),
                    source_fact_ids=_markdown_cell(source_fact_ids),
                )
            )
    return "\n".join(lines)


def _verification_records_table(results: list[dict[str, Any]]) -> str:
    if not results:
        return "- No verification records."
    lines = [
        "| Status | Metric | Period | Mismatch | Severity | Sources | Explanation |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for result in results:
        period = result.get("end_date") or result.get("instant")
        mismatch = result.get("mismatch_pct")
        mismatch_text = _percent(mismatch) if mismatch is not None else ""
        sources = ", ".join(str(source) for source in result.get("sources", []))
        lines.append(
            "| {status} | {metric} | {period} | {mismatch} | {severity} | `{sources}` | {explanation} |".format(
                status=_markdown_cell(result.get("status")),
                metric=_markdown_cell(result.get("metric")),
                period=_markdown_cell(period),
                mismatch=_markdown_cell(mismatch_text),
                severity=_markdown_cell(result.get("severity")),
                sources=_markdown_cell(sources),
                explanation=_markdown_cell(result.get("explanation")),
            )
        )
    return "\n".join(lines)


def _official_report_dossier_linkage_table(state: ResearchState) -> str:
    analysis = (
        (state.get("business_model_findings") or {}).get("official_report_analysis")
        or {}
    )
    dossier = analysis.get("official_report_dossier") or {}
    fields = dossier.get("fields") or []
    if not fields:
        return "- Official report dossier not available."
    lines = [
        f"- Scope: {dossier.get('scope')}",
        f"- Accuracy policy: {dossier.get('accuracy_policy')}",
        "",
        "| Field | Status | Source document | Source section | Matched terms | Evidence snippets | Accuracy note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for field in fields:
        source_document = field.get("source_document") or {}
        source_id = source_document.get("document_id") or ""
        if field.get("source_comparison"):
            source_id = f"{source_id}; {field.get('source_comparison')}"
        matched_terms = ", ".join(str(term) for term in field.get("matched_terms", []))
        evidence = "<br>".join(str(item) for item in field.get("evidence", []))
        lines.append(
            "| {field} | {status} | `{source}` | {section} | {matched_terms} | {evidence} | {accuracy_note} |".format(
                field=_markdown_cell(field.get("label")),
                status=_markdown_cell(field.get("status")),
                source=_markdown_cell(source_id),
                section=_markdown_cell(field.get("source_section")),
                matched_terms=_markdown_cell(matched_terms),
                evidence=_markdown_cell(evidence),
                accuracy_note=_markdown_cell(field.get("accuracy_note")),
            )
        )
    return "\n".join(lines)


def _management_framing_linkage_table(state: ResearchState) -> str:
    analysis = (
        (state.get("business_model_findings") or {}).get("official_report_analysis")
        or {}
    ).get("management_framing_analysis") or {}
    themes = analysis.get("themes") or []
    if not themes:
        return "- Management framing extraction not available."
    lines = [
        f"- Status: {analysis.get('status')}",
        f"- Scope: {analysis.get('scope')}",
        f"- Audit note: {analysis.get('audit_note')}",
        "",
        "| Theme | Status | Source document | Matched terms | Management claim | Evidence snippets | Accuracy limit |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for theme in themes:
        source = (theme.get("source_document") or {}).get("document_id")
        matched_terms = ", ".join(str(term) for term in theme.get("matched_terms", []))
        evidence = "<br>".join(str(item) for item in theme.get("evidence", []))
        lines.append(
            "| {theme} | {status} | `{source}` | {matched_terms} | {claim} | {evidence} | {limit} |".format(
                theme=_markdown_cell(theme.get("theme")),
                status=_markdown_cell(theme.get("status")),
                source=_markdown_cell(source),
                matched_terms=_markdown_cell(matched_terms),
                claim=_markdown_cell(theme.get("management_claim") or theme.get("claim")),
                evidence=_markdown_cell(evidence),
                limit=_markdown_cell(theme.get("accuracy_limit")),
            )
        )
    return "\n".join(lines)


def _official_evidence_cards_linkage_table(state: ResearchState) -> str:
    analysis = (
        (state.get("business_model_findings") or {}).get("official_report_analysis")
        or {}
    )
    cards = analysis.get("evidence_cards") or []
    if not cards:
        return "- Deep official-report evidence cards not available."
    lines = [
        "- Main report keeps these cards compact. This table preserves the full source-snippet trail.",
        "",
        "| Theme | Status | Source document | Matched terms | Finding | Why it matters | Evidence snippets | Limitation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for card in cards:
        source = (card.get("source_document") or {}).get("document_id")
        matched_terms = ", ".join(str(term) for term in card.get("matched_terms", []))
        evidence = "<br>".join(str(item) for item in card.get("evidence", []))
        lines.append(
            "| {theme} | {status} | `{source}` | {matched_terms} | {finding} | {why} | {evidence} | {limitation} |".format(
                theme=_markdown_cell(card.get("theme")),
                status=_markdown_cell(card.get("status")),
                source=_markdown_cell(source),
                matched_terms=_markdown_cell(matched_terms),
                finding=_markdown_cell(card.get("finding")),
                why=_markdown_cell(card.get("why_it_matters")),
                evidence=_markdown_cell(evidence),
                limitation=_markdown_cell(card.get("limitation")),
            )
        )
    return "\n".join(lines)


def _business_model_answer_linkage_table(state: ResearchState) -> str:
    deep_dive = (
        (state.get("business_model_findings") or {})
        .get("official_report_analysis", {})
        .get("business_model_deep_dive", {})
    )
    cards = deep_dive.get("answer_cards") or []
    if not cards:
        return "- Business-model answer cards not available."
    lines = [
        "- These cards are the deeper diligence answers shown in the main report. Source snippets stay here so the main report remains readable.",
        "",
        "| Question | Evidence grade | Current answer | Quantitative support | Official support | Source snippets | What could be wrong | Next tests |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for card in cards:
        lines.append(
            "| {question} | {grade} | {answer} | {quant} | {official} | {snippets} | {wrong} | {tests} |".format(
                question=_markdown_cell(card.get("question")),
                grade=_markdown_cell(card.get("evidence_grade")),
                answer=_markdown_cell(card.get("current_answer")),
                quant=_markdown_cell("<br>".join(str(item) for item in card.get("quantitative_support", []))),
                official=_markdown_cell("<br>".join(str(item) for item in card.get("official_support", []))),
                snippets=_markdown_cell("<br>".join(str(item) for item in card.get("source_evidence", []))),
                wrong=_markdown_cell("<br>".join(str(item) for item in card.get("what_could_be_wrong", []))),
                tests=_markdown_cell("<br>".join(str(item) for item in card.get("next_tests", []))),
            )
        )
    return "\n".join(lines)


def _business_model_subagent_cluster_linkage_table(state: ResearchState) -> str:
    cluster = (
        (state.get("business_model_findings") or {}).get("evidence_subagent_cluster")
        or {}
    )
    subagents = cluster.get("subagents") or []
    if not subagents:
        return "- Business-model subagent cluster not available."
    lines = [
        f"- Status: {cluster.get('status')}",
        f"- Scope: {cluster.get('scope')}",
        "",
        "| Subagent | Source family | Source quality | Status | Working level | Confidence | Evidence records | Source scope | Documents / evidence seen | Evidence highlights | Limits | Next steps |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for agent in subagents:
        source_scope = "<br>".join(str(item) for item in agent.get("source_scope", []))
        docs = agent.get("documents_seen") or {}
        docs_text = "<br>".join(f"{key}: {value}" for key, value in docs.items()) if docs else ""
        highlights = "<br>".join(str(item) for item in agent.get("evidence_highlights", []))
        limits = "<br>".join(str(item) for item in agent.get("limits", []))
        next_steps = "<br>".join(str(item) for item in agent.get("next_steps", []))
        lines.append(
            "| {name} | {family} | {tier} | {status} | {working} | {confidence} | {record_count} | {scope} | {docs} | {highlights} | {limits} | {next_steps} |".format(
                name=_markdown_cell(agent.get("name")),
                family=_markdown_cell(agent.get("source_family")),
                tier=_markdown_cell(agent.get("source_quality_tier")),
                status=_markdown_cell(agent.get("status")),
                working=_markdown_cell(agent.get("working_level")),
                confidence=_markdown_cell(agent.get("confidence")),
                record_count=_markdown_cell(agent.get("evidence_record_count", 0)),
                scope=_markdown_cell(source_scope),
                docs=_markdown_cell(docs_text),
                highlights=_markdown_cell(highlights),
                limits=_markdown_cell(limits),
                next_steps=_markdown_cell(next_steps),
            )
        )
    evidence_records = [
        (agent, record)
        for agent in subagents
        for record in (agent.get("evidence_records") or [])
    ]
    if evidence_records:
        lines.extend(
            [
                "",
                "### Business-Model Subagent Evidence Records",
                "",
                "| Subagent | Claim | Direction | Confidence | Source locator | Excerpt | Limitation |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for agent, record in evidence_records:
            lines.append(
                "| {agent} | {claim} | {direction} | {confidence} | {locator} | {excerpt} | {limitation} |".format(
                    agent=_markdown_cell(agent.get("name")),
                    claim=_markdown_cell(record.get("claim")),
                    direction=_markdown_cell(record.get("evidence_direction")),
                    confidence=_markdown_cell(record.get("confidence")),
                    locator=_markdown_cell(record.get("source_locator")),
                    excerpt=_markdown_cell(record.get("excerpt")),
                    limitation=_markdown_cell(record.get("limitation")),
                )
            )
    policy = cluster.get("orchestration_policy") or []
    if policy:
        lines.extend(["", "### Business-Model Subagent Orchestration Policy", ""])
        lines.extend(f"- {item}" for item in policy)
    schema = cluster.get("standard_output_schema") or {}
    if schema:
        lines.extend(
            [
                "",
                "### Business-Model Subagent Output Schema",
                "",
                "| Field | Rule |",
                "| --- | --- |",
            ]
        )
        for key, value in schema.items():
            lines.append(f"| {_markdown_cell(key)} | {_markdown_cell(value)} |")
    return "\n".join(lines)


def _operating_kpi_linkage_table(state: ResearchState) -> str:
    analysis = (
        (state.get("business_model_findings") or {}).get("official_report_analysis")
        or {}
    ).get("operating_kpi_analysis") or {}
    records = analysis.get("records") or []
    defined_only = analysis.get("defined_only_markers") or []
    if not records and not defined_only:
        return "- Operating KPI extraction not available."
    lines = [
        f"- Status: {analysis.get('status')}",
        f"- Scope: {analysis.get('scope')}",
        f"- Numeric KPI records: {len(records)}",
        f"- Defined-only markers: {len(defined_only)}",
        "",
    ]
    if records:
        lines.extend(
            [
                "| KPI | Period type | Period end | Value | Unit | Source document | Method | Evidence |",
                "| --- | --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for record in records:
            source = (record.get("source_document") or {}).get("document_id")
            lines.append(
                "| {label} | {period_type} | {period_end} | {value} | {unit} | `{source}` | `{method}` | {evidence} |".format(
                    label=_markdown_cell(record.get("label")),
                    period_type=_markdown_cell(record.get("period_type")),
                    period_end=_markdown_cell(record.get("period_end")),
                    value=_markdown_cell(_format_kpi_value(record)),
                    unit=_markdown_cell(record.get("unit")),
                    source=_markdown_cell(source),
                    method=_markdown_cell(record.get("extraction_method")),
                    evidence=_markdown_cell(record.get("evidence")),
                )
            )
    if defined_only:
        lines.extend(
            [
                "",
                "| Defined marker | Status | Source document | Matched terms | Note | Evidence |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for marker in defined_only:
            source = (marker.get("source_document") or {}).get("document_id")
            terms = ", ".join(str(term) for term in marker.get("matched_terms", []))
            evidence = "<br>".join(str(item) for item in marker.get("evidence", []))
            lines.append(
                "| {label} | {status} | `{source}` | {terms} | {note} | {evidence} |".format(
                    label=_markdown_cell(marker.get("label")),
                    status=_markdown_cell(marker.get("status")),
                    source=_markdown_cell(source),
                    terms=_markdown_cell(terms),
                    note=_markdown_cell(marker.get("note")),
                    evidence=_markdown_cell(evidence),
                )
            )
    coverage = analysis.get("metric_coverage") or []
    if coverage:
        lines.extend(
            [
                "",
                "### Operating Metric Coverage Notes",
                "",
                "| Metric / question | Status | Record count | Latest value | Source document | Matched terms | Note | Evidence |",
                "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
            ]
        )
        for item in coverage:
            latest_record = item.get("latest_record") or {}
            source_document = (
                (latest_record.get("source_document") or {})
                or (item.get("source_document") or {})
            )
            evidence = "<br>".join(str(snippet) for snippet in item.get("evidence", []))
            lines.append(
                "| {label} | {status} | {count} | {latest} | `{source}` | {terms} | {note} | {evidence} |".format(
                    label=_markdown_cell(item.get("label")),
                    status=_markdown_cell(item.get("status")),
                    count=_markdown_cell(item.get("record_count", 0)),
                    latest=_markdown_cell(_format_kpi_value(latest_record) if latest_record else ""),
                    source=_markdown_cell(source_document.get("document_id")),
                    terms=_markdown_cell(", ".join(str(term) for term in item.get("matched_terms", []))),
                    note=_markdown_cell(item.get("note")),
                    evidence=_markdown_cell(evidence),
                )
            )
    if analysis.get("audit_note"):
        lines.extend(["", f"- Audit note: {analysis.get('audit_note')}"])
    return "\n".join(lines)


def _public_voice_linkage_table(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Public voice evidence not run."
    items = findings.get("evidence_items") or []
    if not items:
        return "- No public voice evidence items collected."
    lines = [
        "| Source | Type | Themes | Evidence URL | Excerpt |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in items:
        themes = ", ".join(str(theme) for theme in item.get("themes", []))
        lines.append(
            "| {source} | {type} | {themes} | {url} | {excerpt} |".format(
                source=_markdown_cell(item.get("source_name") or item.get("source_id")),
                type=_markdown_cell(item.get("evidence_type") or item.get("voice_type")),
                themes=_markdown_cell(themes),
                url=_markdown_cell(item.get("comment_url") or item.get("source_url")),
                excerpt=_markdown_cell(item.get("excerpt")),
                )
            )
    return "\n".join(lines)


def _executive_transcript_linkage_table(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Executive transcript collection not run."
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Registry: `{findings.get('registry_path') or 'not configured'}`",
        f"- Transcript sources collected: {findings.get('transcript_source_count', 0)}",
        f"- Transcript segments collected: {findings.get('transcript_segment_count', 0)}",
        f"- Evidence items extracted: {findings.get('evidence_item_count', 0)}",
    ]
    question_pack = findings.get("business_model_question_pack") or {}
    if question_pack:
        lines.extend(
            [
                f"- Business-model questions configured: {_markdown_text(question_pack.get('question_count', 0))}",
                f"- Business-model question results: {_markdown_text(question_pack.get('total_question_results', 0))}",
            ]
        )
        answer_counts = question_pack.get("answer_status_counts") or {}
        if answer_counts:
            lines.append(
                "- Business-model answer statuses: "
                + ", ".join(f"{_markdown_text(status)}={_markdown_text(count)}" for status, count in sorted(answer_counts.items()))
            )
    source_results = findings.get("source_results") or []
    if source_results:
        lines.extend(
            [
                "",
                "### Executive Transcript Source Results",
                "",
                "| Source | Video UID | Platform | Adapter | Status | URL | Segments | Evidence items | Question results | Question answers | Cache paths | Errors |",
                "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for result in source_results:
            cache_paths = "<br>".join(str(path) for path in result.get("cache_paths", []))
            errors = "<br>".join(str(error) for error in result.get("errors", []))
            question_results = result.get("business_model_question_results") or []
            question_answers = sum(1 for item in question_results if item.get("answer_status") == "evidence_found")
            lines.append(
                "| {source} | {video_uid} | {platform} | {adapter} | {status} | {url} | {segments} | {items} | {questions} | {answers} | {cache} | {errors} |".format(
                    source=_markdown_cell(result.get("name") or result.get("source_id")),
                    video_uid=_markdown_cell(result.get("video_uid")),
                    platform=_markdown_cell(result.get("platform")),
                    adapter=_markdown_cell(result.get("adapter")),
                    status=_markdown_cell(result.get("status")),
                    url=_markdown_cell(result.get("url")),
                    segments=_markdown_cell(result.get("transcript_segment_count", 0)),
                    items=_markdown_cell(len(result.get("evidence_items", []))),
                    questions=_markdown_cell(len(question_results)),
                    answers=_markdown_cell(question_answers),
                    cache=_markdown_cell(cache_paths),
                    errors=_markdown_cell(errors),
                )
            )
    items = findings.get("evidence_items") or []
    if items:
        lines.extend(
            [
                "",
                "### Executive Transcript Evidence Items",
                "",
                "| Source | Video UID | Platform | Claim | Start | Matched terms | Excerpt | URL |",
                "| --- | --- | --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for item in items:
            matched = ", ".join(str(term) for term in item.get("matched_terms", []))
            lines.append(
                "| {source} | {video_uid} | {platform} | {claim} | {start} | {terms} | {excerpt} | {url} |".format(
                    source=_markdown_cell(item.get("source_name") or item.get("source_id")),
                    video_uid=_markdown_cell(item.get("video_uid")),
                    platform=_markdown_cell(item.get("platform")),
                    claim=_markdown_cell(item.get("claim")),
                    start=_markdown_cell(item.get("start_seconds")),
                    terms=_markdown_cell(matched),
                    excerpt=_markdown_cell(item.get("excerpt")),
                    url=_markdown_cell(item.get("source_url")),
                )
            )
    question_rows = []
    for result in source_results:
        for item in result.get("business_model_question_results") or []:
            question_rows.append((result, item))
    if question_rows:
        lines.extend(
            [
                "",
                "### Executive Video Business-Model Question Results",
                "",
                "| Source | Video UID | Platform | Question | Status | Evidence count | Current read |",
                "| --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for result, item in question_rows:
            lines.append(
                "| {source} | {video_uid} | {platform} | {question} | {status} | {evidence_count} | {read} |".format(
                    source=_markdown_cell(result.get("name") or result.get("source_id")),
                    video_uid=_markdown_cell(result.get("video_uid") or item.get("video_uid")),
                    platform=_markdown_cell(result.get("platform")),
                    question=_markdown_cell(item.get("question_id")),
                    status=_markdown_cell(item.get("answer_status")),
                    evidence_count=_markdown_cell(len(item.get("evidence") or [])),
                    read=_markdown_cell(item.get("current_read")),
                )
            )
    if not source_results and not items:
        lines.append("- No executive transcript sources or evidence items recorded.")
    return "\n".join(lines)


def _video_manifest_linkage(state: ResearchState) -> str:
    manifest = state.get("video_manifest") or {}
    records = manifest.get("records") or []
    if not records:
        return "- Video manifest not populated."
    lines = [
        f"- Manifest path: `{_video_manifest_path(state)}`",
        f"- Records: {manifest.get('record_count', len(records))}",
        "",
        "| Video UID | Platform | Native ID | Source IDs | Latest status | Transcript segments | Evidence items | Canonical URL |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for record in records:
        source_ids = ", ".join(str(source_id) for source_id in record.get("source_ids", []))
        lines.append(
            "| {uid} | {platform} | {native_id} | {sources} | {status} | {segments} | {items} | {url} |".format(
                uid=_markdown_cell(record.get("video_uid")),
                platform=_markdown_cell(record.get("platform")),
                native_id=_markdown_cell(record.get("native_video_id")),
                sources=_markdown_cell(source_ids),
                status=_markdown_cell(record.get("latest_collection_status")),
                segments=_markdown_cell(record.get("total_transcript_segments", 0)),
                items=_markdown_cell(record.get("total_evidence_items", 0)),
                url=_markdown_cell(record.get("canonical_url")),
            )
        )
    return "\n".join(lines)


def _official_event_question_pack_linkage(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Official event question pack not run."
    pack = findings.get("business_model_question_pack") or {}
    lines = [
        f"- Question pack status: {_markdown_text(pack.get('status', 'not available'))}",
        f"- Questions configured: {_markdown_text(pack.get('question_count', 0))}",
        f"- Source question sets: {_markdown_text(pack.get('source_question_set_count', 0))}",
        f"- Total question results: {_markdown_text(pack.get('total_question_results', 0))}",
    ]
    answer_counts = pack.get("answer_status_counts") or {}
    if answer_counts:
        lines.append(
            "- Answer statuses: "
            + ", ".join(f"{_markdown_text(status)}={_markdown_text(count)}" for status, count in sorted(answer_counts.items()))
        )
    rows = []
    for result in findings.get("source_results") or []:
        for item in result.get("business_model_question_results") or []:
            rows.append((result, item))
    if not rows:
        lines.append("- No source-level question results recorded.")
        return "\n".join(lines)
    lines.extend(
        [
            "",
            "| Source | Video UID | Period | Question | Status | Evidence count | Current read |",
            "| --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for result, item in rows:
        lines.append(
            "| {source} | {video_uid} | {period} | {question} | {status} | {evidence_count} | {read} |".format(
                source=_markdown_cell(result.get("name") or result.get("source_id")),
                video_uid=_markdown_cell(result.get("video_uid")),
                period=_markdown_cell(item.get("period") or result.get("period")),
                question=_markdown_cell(item.get("question_id")),
                status=_markdown_cell(item.get("answer_status")),
                evidence_count=_markdown_cell(len(item.get("evidence") or [])),
                read=_markdown_cell(item.get("current_read")),
            )
        )
    return "\n".join(lines)


def _customer_happiness_linkage_table(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Customer happiness synthesis not run."
    dimensions = findings.get("dimensions") or []
    if not dimensions:
        return "- No customer happiness dimensions synthesized."
    lines = [
        "| Dimension | Evidence count | Source tiers | Current read | Example sources |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for dimension in dimensions:
        tiers = ", ".join(str(tier) for tier in dimension.get("source_quality_tiers", []))
        sources = "; ".join(str(source) for source in dimension.get("source_names", []))
        lines.append(
            "| {dimension} | {count} | {tiers} | {read} | {sources} |".format(
                dimension=_markdown_cell(dimension.get("label")),
                count=_markdown_cell(dimension.get("evidence_count", 0)),
                tiers=_markdown_cell(tiers),
                read=_markdown_cell(dimension.get("current_read")),
                sources=_markdown_cell(sources),
            )
        )
    conclusion = findings.get("current_conclusion")
    if conclusion:
        lines.extend(["", f"- Conclusion: {conclusion}"])
    return "\n".join(lines)


def _right_people_linkage_table(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Right People Agent has not run."
    subagents = findings.get("subagent_reports") or []
    lines = [
        "| Subagent | Status | Source quality | Evidence records | Current read |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for subagent in subagents:
        lines.append(
            "| {name} | {status} | {quality} | {records} | {read} |".format(
                name=_markdown_cell(subagent.get("name") or subagent.get("agent_id")),
                status=_markdown_cell(subagent.get("status")),
                quality=_markdown_cell(subagent.get("source_quality")),
                records=_markdown_cell(subagent.get("evidence_records", 0)),
                read=_markdown_cell(subagent.get("current_read")),
            )
        )
    if not subagents:
        return "- No right-people subagent output."
    cards = findings.get("official_filing_evidence_cards") or []
    signals = findings.get("financial_signals") or []
    transcript = findings.get("management_transcript_signals") or {}
    framework = findings.get("evidence_framework") or {}
    decision = findings.get("right_people_decision") or {}
    scorecard = findings.get("scorecard") or {}
    lines.extend(
        [
            "",
            f"- Gate status: {decision.get('status', findings.get('status'))}",
            f"- Weighted score: {scorecard.get('weighted_score', decision.get('weighted_score', 'n/a'))}",
            f"- Evidence buckets: {len(framework.get('buckets') or [])}",
            f"- Source hierarchy tiers: {len(framework.get('source_hierarchy') or [])}",
            f"- Official filing evidence cards: {len(cards)}",
            f"- Financial signals: {len(signals)}",
            f"- Management transcript signals: {transcript.get('signal_count', 0)}",
            f"- Red flags: {len(findings.get('red_flags') or [])}",
        ]
    )
    return "\n".join(lines)


def _alternative_data_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Alternative Data Agent has not run."
    lines = [
        f"- Status: {findings.get('status')}",
        f"- Region / window: {findings.get('region')} / {findings.get('time_window')}",
        f"- Raw observations: {findings.get('raw_observation_count', 0)}",
        f"- Normalized metrics: {findings.get('normalized_metric_count', 0)}",
        f"- Text events for downstream sentiment: {findings.get('text_event_count', 0)}",
        f"- Metric summaries: {findings.get('metric_summary_count', 0)}",
        f"- Raw store: `{findings.get('raw_observation_store_path', '')}`",
        f"- Metric store: `{findings.get('metric_store_path', '')}`",
        f"- Text-event store: `{findings.get('text_event_store_path', '')}`",
    ]
    summaries = findings.get("metric_summaries") or []
    if summaries:
        lines.append("")
        lines.append("### Current Normalized Signals")
        for summary in summaries[:12]:
            pieces = [
                f"{summary.get('metric_name')}: {_format_alt_value(summary.get('current'), summary.get('unit'))}",
                f"period {summary.get('period')}",
                f"confidence {summary.get('confidence')}",
            ]
            if summary.get("change_4w") is not None:
                pieces.append(f"4w change {_percent(summary.get('change_4w'))}")
            if summary.get("z_score_52w") is not None:
                pieces.append(f"52w z-score {_ratio(summary.get('z_score_52w'))}")
            if summary.get("interpretation_hint"):
                pieces.append(f"hint {summary.get('interpretation_hint')}")
            lines.append("- " + " | ".join(pieces))
    else:
        lines.extend(
            [
                "",
                "### Connector Readiness",
                _alternative_data_connector_status(findings),
            ]
        )
    lines.extend(
        [
            "",
            "Scope limit: this agent only collects normalized evidence. It does not decide buy/sell, moat strength, sentiment, or valuation.",
        ]
    )
    return "\n".join(lines)


def _alternative_data_connector_status(findings: dict[str, Any]) -> str:
    statuses = findings.get("connector_status") or {}
    if not statuses:
        return "- No connector status recorded."
    lines = []
    for connector_id, status in sorted(statuses.items()):
        missing = ", ".join(str(item) for item in status.get("missing", [])) or "none"
        lines.append(
            f"- {connector_id}: {status.get('status')} | metrics {status.get('metrics', 0)} | text events {status.get('text_events', 0)} | missing {missing}"
        )
    return "\n".join(lines)


def _alternative_data_linkage_table(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Alternative Data Agent has not run."
    lines = [
        f"- Raw observation store: `{findings.get('raw_observation_store_path', '')}`",
        f"- Metric store: `{findings.get('metric_store_path', '')}`",
        f"- Text-event store: `{findings.get('text_event_store_path', '')}`",
        "",
        "### Connector Status",
        _alternative_data_connector_status(findings),
    ]
    metrics = findings.get("normalized_metrics") or []
    if metrics:
        lines.extend(
            [
                "",
                "### Normalized Metric Samples",
                "| Metric | Period | Value | Unit | Source | Confidence | Metadata |",
                "| --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for metric in metrics[:40]:
            lines.append(
                "| {metric} | {period} | {value} | {unit} | {source} | {confidence} | {metadata} |".format(
                    metric=_markdown_cell(metric.get("metric_name")),
                    period=_markdown_cell(metric.get("period")),
                    value=_markdown_cell(_format_alt_value(metric.get("value"), metric.get("unit"))),
                    unit=_markdown_cell(metric.get("unit")),
                    source=_markdown_cell(metric.get("source")),
                    confidence=_markdown_cell(metric.get("confidence")),
                    metadata=_markdown_cell(metric.get("metadata")),
                )
            )
    text_events = findings.get("text_events") or []
    if text_events:
        lines.extend(
            [
                "",
                "### Text Event Samples For Sentiment Agent",
                "| Source | Created at | Topic hints | Engagement | Text |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for event in text_events[:25]:
            lines.append(
                "| {source} | {created_at} | {topics} | {engagement} | {text} |".format(
                    source=_markdown_cell(event.get("source")),
                    created_at=_markdown_cell(event.get("created_at")),
                    topics=_markdown_cell(", ".join(str(item) for item in event.get("topic_hint", []))),
                    engagement=_markdown_cell(event.get("engagement")),
                    text=_markdown_cell(event.get("text")),
                )
            )
    return "\n".join(lines)


def _format_alt_value(value: Any, unit: Any) -> str:
    if value is None:
        return ""
    if unit == "ratio":
        return _percent(value)
    if unit == "currency":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _agent_reports_table(agent_reports: list[dict[str, Any]]) -> str:
    if not agent_reports:
        return "- No agent reports recorded."
    lines = [
        "| Agent | Title | Path | Created at |",
        "| --- | --- | --- | --- |",
    ]
    for report in agent_reports:
        lines.append(
            "| {agent} | {title} | `{path}` | {created_at} |".format(
                agent=_markdown_cell(report.get("agent_id")),
                title=_markdown_cell(report.get("title")),
                path=_markdown_cell(report.get("path")),
                created_at=_markdown_cell(report.get("created_at")),
            )
        )
    return "\n".join(lines)


def _audit_events_table(events: list[dict[str, Any]]) -> str:
    if not events:
        return "- No audit events recorded."
    lines = [
        "| Created at | Agent | Event | Message |",
        "| --- | --- | --- | --- |",
    ]
    for event in events:
        lines.append(
            "| {created_at} | {agent} | {event} | {message} |".format(
                created_at=_markdown_cell(event.get("created_at")),
                agent=_markdown_cell(event.get("agent_id")),
                event=_markdown_cell(event.get("event")),
                message=_markdown_cell(event.get("message")),
            )
        )
    return "\n".join(lines)


def _latest_annual_row(state: ResearchState) -> dict[str, Any]:
    rows = annual_fact_rows(state.get("extracted_facts", []))
    return rows[-1] if rows else {}


def _latest_metric_result(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") != formula_id:
            continue
        results = [
            result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
        ]
        if not results:
            return None
        return sorted(results, key=lambda result: result.get("year", 0))[-1]
    return None


def _format_metric_result(result: dict[str, Any] | None, formula_id: str) -> str:
    if not result:
        return ""
    value = result.get("value")
    unit = result.get("unit")
    if unit == "CNY":
        return f"RMB {_money_billions(value)}B"
    if unit == "ratio":
        return _percent(value) if _ratio_should_be_percent(formula_id) else _ratio(value)
    return "" if value is None else str(value)


def _latest_operating_kpi(
    state: ResearchState,
    metric: str,
) -> dict[str, Any] | None:
    analysis = (
        (state.get("business_model_findings") or {})
        .get("official_report_analysis", {})
        .get("operating_kpi_analysis", {})
    )
    return (analysis.get("latest_by_metric") or {}).get(metric)


def _report_at_a_glance(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}
    metrics = state.get("metrics", [])
    valuation_metrics = _valuation_metrics_for_state(state)
    latest = _latest_annual_row(state)
    active_merchants = _latest_operating_kpi(state, "active_merchants")
    true_yield = _format_metric_result(
        _latest_metric_result(valuation_metrics, "true_yield_v1"),
        "true_yield_v1",
    )
    fcf_yield = _format_metric_result(
        _latest_metric_result(valuation_metrics, "free_cash_flow_yield_v1"),
        "free_cash_flow_yield_v1",
    )
    investment_adjusted_yield = _latest_metric_result(
        valuation_metrics,
        "investment_adjusted_operating_yield_v1",
    )
    investment_adjusted_text = _format_investment_adjusted_yield(investment_adjusted_yield)
    roic = _format_metric_result(_latest_metric_result(metrics, "unlevered_roic_v1"), "unlevered_roic_v1")
    lines = [
        "| Item | Current read |",
        "| --- | --- |",
        f"| Company | {_markdown_cell(company.get('legal_name', state['company_query']))} |",
        f"| Listing / currency | {_markdown_cell(company.get('listing_type', 'Unknown'))}; reports in {_markdown_cell(company.get('reporting_currency', 'Unknown'))}; trades in {_markdown_cell(company.get('trading_currency', 'Unknown'))} |",
        f"| Latest annual revenue | RMB {_money_billions(latest.get('revenue'))}B ({latest.get('year', 'latest')}) |",
        f"| Latest net income / FCF | RMB {_money_billions(latest.get('net_income'))}B / RMB {_money_billions(latest.get('free_cash_flow'))}B |",
        f"| Active merchants | {_format_kpi_value(active_merchants) if active_merchants else 'not extracted'} |",
        f"| ROIC / owner earnings yield / FCF yield | {roic or 'n/a'} / {true_yield or 'n/a'} / {fcf_yield or 'n/a'} |",
        f"| Investment-adjusted operating yield | {investment_adjusted_text or 'n/a'} |",
        f"| V1 audit read | {_markdown_cell(audit_status)} |",
    ]
    return "\n".join(lines)


def _format_investment_adjusted_yield(result: dict[str, Any] | None) -> str:
    if not result:
        return ""
    owner_yield = _percent(result.get("owner_earnings_yield"))
    fcf_yield = _percent(result.get("free_cash_flow_yield"))
    operating_ev = _money_billions(result.get("operating_enterprise_value"))
    portfolio = _money_billions(result.get("investment_portfolio"))
    return f"owner earnings {owner_yield}; FCF {fcf_yield}; operating EV RMB {operating_ev}B after subtracting RMB {portfolio}B investment portfolio"


def _key_takeaways(state: ResearchState) -> str:
    metrics = state.get("metrics", [])
    valuation_metrics = _valuation_metrics_for_state(state)
    latest = _latest_annual_row(state)
    analysis = (state.get("business_model_findings") or {}).get("official_report_analysis") or {}
    framing = (analysis.get("management_framing_analysis") or {}).get("summary")
    public_voice = state.get("public_voice_findings", {})
    theme_summary = public_voice.get("theme_summary") or {}
    theme_counts = theme_summary.get("counts") or {}
    top_public_themes = sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)[:3]
    true_yield = _format_metric_result(
        _latest_metric_result(valuation_metrics, "true_yield_v1"),
        "true_yield_v1",
    )
    fcf_yield = _format_metric_result(
        _latest_metric_result(valuation_metrics, "free_cash_flow_yield_v1"),
        "free_cash_flow_yield_v1",
    )
    investment_adjusted_yield = _format_investment_adjusted_yield(
        _latest_metric_result(valuation_metrics, "investment_adjusted_operating_yield_v1")
    )
    roic = _format_metric_result(_latest_metric_result(metrics, "unlevered_roic_v1"), "unlevered_roic_v1")
    lines = []
    if framing:
        lines.append(f"- Business model: {framing}")
    if latest:
        lines.append(
            "- Financial profile: "
            f"{latest.get('year')} revenue RMB {_money_billions(latest.get('revenue'))}B, "
            f"net income RMB {_money_billions(latest.get('net_income'))}B, "
            f"FCF RMB {_money_billions(latest.get('free_cash_flow'))}B."
        )
    metric_parts = [
        part
        for part in [
            f"ROIC {roic}" if roic else "",
            f"owner earnings yield {true_yield}" if true_yield else "",
            f"FCF yield {fcf_yield}" if fcf_yield else "",
            f"investment-adjusted operating yield: {investment_adjusted_yield}" if investment_adjusted_yield else "",
        ]
        if part
    ]
    if metric_parts:
        lines.append("- Valuation snapshot: " + "; ".join(metric_parts) + ".")
    if top_public_themes:
        lines.append(
            "- Public-voice warning signs: low-confidence public evidence clusters around "
            + ", ".join(f"{theme.replace('_', ' ')} ({count})" for theme, count in top_public_themes)
            + "."
        )
    lines.append(
        "- Current conclusion: the official-report business model is understandable and financially strong, "
        "but moat durability still depends on customer evidence, merchant economics, competitor comparison, and Temu unit economics."
    )
    return "\n".join(lines)


def _business_model_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    analysis = findings.get("official_report_analysis") or {}
    if not analysis:
        return _finding_summary(findings)
    latest_source = analysis.get("latest_source") or {}
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Latest official report: {latest_source.get('filing_date')} | `{latest_source.get('document_id')}`",
        f"- Input scope: {analysis.get('input_scope', 'unknown')}",
    ]
    framing = analysis.get("management_framing_analysis") or {}
    if framing.get("summary"):
        lines.extend(["", "### Business Model Read", "", f"- {framing.get('summary')}"])
    cluster_summary = _business_model_subagent_cluster_summary(
        findings.get("evidence_subagent_cluster") or {}
    )
    if cluster_summary:
        lines.append(cluster_summary)
    deep_dive = _business_model_deep_dive_summary(analysis.get("business_model_deep_dive") or {})
    if deep_dive:
        lines.append(deep_dive)
    cards = analysis.get("evidence_cards") or []
    if cards:
        lines.extend(["", "### Thesis Map", ""])
        for card in cards[:8]:
            theme = _markdown_text(card.get("theme") or "Untitled theme")
            lines.extend(
                [
                    f"#### {theme}",
                    "",
                    f"- What it suggests: {_markdown_text(card.get('finding'))}",
                    f"- What still has to be proven: {_markdown_text(card.get('limitation'))}",
                    "",
                ]
            )
    checklist = analysis.get("right_business_model_checklist") or []
    if checklist:
        lines.extend(["", "### Right Business Model Checklist", ""])
        for item in checklist:
            lines.append(
                "- {item}: {status}. {note}".format(
                    item=_markdown_text(item.get("item")),
                    status=_markdown_text(item.get("status")),
                    note=_markdown_text(item.get("note")),
                )
            )
    operating_kpis = _operating_kpi_main_summary(analysis.get("operating_kpi_analysis") or {})
    if operating_kpis:
        lines.append(operating_kpis)
    missing = analysis.get("missing_evidence") or []
    if missing:
        lines.extend(["", "### Missing Evidence", ""])
        lines.extend(f"- {item}" for item in missing[:5])
    if analysis.get("conclusion_limit"):
        lines.append(f"- Conclusion limit: {analysis.get('conclusion_limit')}")
    return "\n".join(lines)


def _right_people_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    lines = [
        f"- Status: {_markdown_text(findings.get('status', 'unknown'))}",
        f"- Current read: {_markdown_text(findings.get('overall_read', 'not available'))}",
    ]
    coverage = findings.get("source_coverage") or {}
    if coverage:
        lines.extend(
            [
                "- Source coverage: "
                + "; ".join(
                    part
                    for part in [
                        f"annual report {coverage.get('annual_report_status')}",
                        f"official filing cards {coverage.get('official_filing_evidence_cards', 0)}",
                        f"financial signals {coverage.get('financial_signal_count', 0)}",
                        f"transcript signals {coverage.get('management_transcript_signal_count', 0)}",
                        f"red flags {coverage.get('red_flag_count', 0)}",
                    ]
                    if part
                )
            ]
        )
    subagents = findings.get("subagent_reports") or []
    if subagents:
        lines.extend(["", "### Right People Subagents", ""])
        for subagent in subagents:
            lines.extend(
                [
                    f"#### {_markdown_text(subagent.get('name') or subagent.get('agent_id'))}",
                    "",
                    f"- Status: {_markdown_text(subagent.get('status'))}",
                    f"- Current read: {_markdown_text(subagent.get('current_read'))}",
                    f"- Evidence records: {_markdown_text(subagent.get('evidence_records', 0))}",
                ]
            )
            findings_lines = subagent.get("findings") or []
            if findings_lines:
                lines.append("- Key evidence:")
                lines.extend(f"  - {_markdown_text(item)}" for item in findings_lines[:4])
            limits = subagent.get("limits") or []
            if limits:
                lines.append("- Limits:")
                lines.extend(f"  - {_markdown_text(item)}" for item in limits[:2])
            lines.append("")
    checklist = findings.get("right_people_checklist") or []
    if checklist:
        lines.extend(["### Right People Checklist", ""])
        lines.extend(["| Item | Status | Basis | Limitation |", "| --- | --- | --- | --- |"])
        for item in checklist:
            lines.append(
                "| {item} | {status} | {basis} | {limitation} |".format(
                    item=_markdown_cell(item.get("item")),
                    status=_markdown_cell(item.get("status")),
                    basis=_markdown_cell(item.get("basis")),
                    limitation=_markdown_cell(item.get("limitation")),
                )
            )
    red_flags = findings.get("red_flags") or []
    if red_flags:
        lines.extend(["", "### Review Flags", ""])
        for flag in red_flags[:8]:
            lines.append(
                f"- [{_markdown_text(flag.get('severity'))}] {_markdown_text(flag.get('flag_id'))}: {_markdown_text(flag.get('read'))}"
            )
    open_questions = findings.get("open_questions") or []
    if open_questions:
        lines.extend(["", "### Open Questions", ""])
        lines.extend(f"- {_markdown_text(question)}" for question in open_questions[:8])
    return "\n".join(lines).strip()


def _right_people_framework_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    framework = findings.get("evidence_framework") or {}
    buckets = framework.get("buckets") or []
    hierarchy = framework.get("source_hierarchy") or []
    lines = [
        f"- Core rule: {_markdown_text(framework.get('core_rule') or 'Never let a management claim masquerade as a fact.')}",
    ]
    if buckets:
        lines.extend(["", "### Evidence Buckets", ""])
        for bucket in buckets:
            lines.append(
                "- {bucket}: {definition} Use: {use}".format(
                    bucket=_markdown_text(bucket.get("bucket")),
                    definition=_markdown_text(bucket.get("definition")),
                    use=_markdown_text(bucket.get("default_use")),
                )
            )
    if hierarchy:
        lines.extend(["", "### Source Hierarchy", ""])
        for item in hierarchy:
            lines.append(
                "- {tier}: {sources}. Use: {use}".format(
                    tier=_markdown_text(item.get("tier")),
                    sources=_markdown_text(item.get("sources")),
                    use=_markdown_text(item.get("use")),
                )
            )
    return "\n".join(lines).strip()


def _right_people_decision_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    decision = findings.get("right_people_decision") or {}
    scorecard = findings.get("scorecard") or {}
    lines = [
        f"- Gate status: {_markdown_text(decision.get('status', findings.get('status')))}",
        f"- Current read: {_markdown_text(decision.get('current_read', findings.get('overall_read')))}",
        f"- Weighted score: {_markdown_text(scorecard.get('weighted_score', decision.get('weighted_score', 'n/a')))} / 100",
        f"- Confidence: {_markdown_text(decision.get('confidence', 'unknown'))}",
    ]
    unresolved = decision.get("unresolved_gate_items") or []
    if unresolved:
        lines.append("- Unresolved gate items: " + "; ".join(_markdown_text(item) for item in unresolved[:6]))
    hard = decision.get("hard_overrides") or []
    if hard:
        lines.append("- Hard overrides:")
        lines.extend(
            f"  - {_markdown_text(item.get('flag_id'))}: {_markdown_text(item.get('read'))}"
            for item in hard[:5]
        )
    dimensions = scorecard.get("dimensions") or []
    if dimensions:
        lines.extend(["", "### Scorecard", ""])
        for item in dimensions:
            lines.append(
                "- {name}: raw {raw}, weighted {points}/{weight}. {read}".format(
                    name=_markdown_text(item.get("dimension_id")),
                    raw=_markdown_text(item.get("raw_score")),
                    points=_markdown_text(item.get("weighted_points")),
                    weight=_markdown_text(item.get("weight")),
                    read=_markdown_text(item.get("current_read")),
                )
            )
    control = findings.get("control_map") or {}
    if control:
        lines.extend(["", "### Control Map", ""])
        lines.append(f"- Status: {_markdown_text(control.get('status'))}; risk level: {_markdown_text(control.get('risk_level'))}")
        lines.append(f"- Known terms: {', '.join(_markdown_text(term) for term in control.get('known_terms', [])[:8]) or 'none'}")
        for item in control.get("findings", [])[:4]:
            lines.append(f"- {_markdown_text(item)}")
    incentive = findings.get("incentive_map") or {}
    if incentive:
        lines.extend(["", "### Incentive Map", ""])
        lines.append(f"- Current read: {_markdown_text(incentive.get('current_read'))}")
        for item in (incentive.get("positive_signals") or [])[:3]:
            lines.append(f"- Positive: {_markdown_text(item)}")
        for item in (incentive.get("concerns_or_unknowns") or [])[:3]:
            lines.append(f"- Review: {_markdown_text(item)}")
    ledger = findings.get("capital_allocation_ledger") or {}
    if ledger:
        lines.extend(["", "### Capital Allocation Ledger", ""])
        lines.append(f"- Current read: {_markdown_text(ledger.get('current_read'))}")
        for row in (ledger.get("rows") or [])[-3:]:
            lines.append(
                "- {year}: revenue RMB {revenue}B, CFO RMB {cfo}B, FCF RMB {fcf}B, owner earnings proxy RMB {owner}B, ROIC {roic}, incremental ROIC {iroic}".format(
                    year=_markdown_text(row.get("year")),
                    revenue=_money_billions(row.get("revenue")),
                    cfo=_money_billions(row.get("operating_cash_flow")),
                    fcf=_money_billions(row.get("free_cash_flow")),
                    owner=_money_billions(row.get("owner_earnings_proxy")),
                    roic=_percent(row.get("roic_proxy")),
                    iroic=_percent(row.get("incremental_roic_proxy")),
                )
            )
    communication = findings.get("communication_audit") or {}
    if communication:
        lines.extend(["", "### Communication Audit", ""])
        lines.append(f"- Current read: {_markdown_text(communication.get('current_read'))}")
        for check in (communication.get("outcome_checks") or [])[:5]:
            lines.append(
                f"- {check.get('claim_theme')}: {check.get('verdict')} | {check.get('read')}"
            )
    matrix = findings.get("red_flag_matrix") or {}
    if matrix:
        lines.extend(["", "### Red-Flag Matrix", ""])
        lines.append(
            f"- Status: {_markdown_text(matrix.get('status'))}; rows: {_markdown_text(matrix.get('row_count', 0))}; hard overrides: {_markdown_text(matrix.get('hard_override_count', 0))}"
        )
        for row in (matrix.get("rows") or [])[:6]:
            lines.append(
                f"- [{_markdown_text(row.get('severity'))}] {_markdown_text(row.get('flag_id'))}: {_markdown_text(row.get('read'))}"
            )
    return "\n".join(lines).strip()


def _right_people_line_zh(state: ResearchState) -> str:
    findings = state.get("leadership_findings") or {}
    if not findings:
        return "尚未评估。"
    overall = findings.get("overall_read")
    if overall:
        return _zh_text(overall)
    checklist = findings.get("right_people_checklist") or []
    if any(item.get("status") == "needs_review" for item in checklist):
        return "需要复核；仍存在治理、核验或诚信相关的未解决事项。"
    supported = [item for item in checklist if item.get("status") in {"supported", "partially_supported"}]
    if supported:
        return "已部分评估；治理、激励、资本配置、沟通和执行证据已经被映射出来。"
    return "已准备框架，但现有证据尚不足以支持判断。"


def _right_people_chinese_framework_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- 尚未运行。"
    framework = findings.get("evidence_framework") or {}
    buckets = framework.get("buckets") or []
    hierarchy = framework.get("source_hierarchy") or []
    bucket_labels = {
        "fact": "事实",
        "management_claim": "管理层主张",
        "external_evidence": "外部证据",
        "inference": "推论",
    }
    tier_labels = {
        "high": "高",
        "medium_high": "中高",
        "medium": "中",
        "low_to_medium": "低到中",
    }
    lines = [
        "- 核心规则：不要让管理层主张伪装成事实。",
    ]
    if buckets:
        lines.extend(["", "### 证据分类", ""])
        for bucket in buckets:
            key = _markdown_text(bucket.get("bucket"))
            lines.append(
                "- {bucket}：{definition} 用途：{use}".format(
                    bucket=bucket_labels.get(key, key),
                    definition=_zh_text(bucket.get("definition")),
                    use=_zh_text(bucket.get("default_use")),
                )
            )
    if hierarchy:
        lines.extend(["", "### 来源等级", ""])
        for item in hierarchy:
            tier = _markdown_text(item.get("tier"))
            lines.append(
                "- {tier}：{sources}。用途：{use}".format(
                    tier=tier_labels.get(tier, tier),
                    sources=_zh_text(item.get("sources")),
                    use=_zh_text(item.get("use")),
                )
            )
    return "\n".join(lines).strip()


def _right_people_chinese_decision_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- 尚未运行。"
    decision = findings.get("right_people_decision") or {}
    scorecard = findings.get("scorecard") or {}
    lines = [
        f"- 门槛状态：{_status_zh(decision.get('status', findings.get('status')))}",
        f"- 当前判断：{_zh_text(decision.get('current_read', findings.get('overall_read')))}",
        f"- 加权分数：{_markdown_text(scorecard.get('weighted_score', decision.get('weighted_score', 'n/a')))} / 100",
        f"- 置信度：{_confidence_zh(decision.get('confidence', 'unknown'))}",
    ]
    unresolved = decision.get("unresolved_gate_items") or []
    if unresolved:
        lines.append("- 尚未解决的门槛项目：" + "；".join(_zh_text(item) for item in unresolved[:6]))
    hard = decision.get("hard_overrides") or []
    if hard:
        lines.append("- 硬性阻断项：")
        lines.extend(f"  - {_zh_text(item.get('flag_id'))}：{_zh_text(item.get('read'))}" for item in hard[:5])
    dimensions = scorecard.get("dimensions") or []
    if dimensions:
        lines.extend(["", "### 评分卡", ""])
        for item in dimensions:
            lines.append(
                "- {name}：原始分 {raw}，加权 {points}/{weight}。{read}".format(
                    name=_dimension_zh(item.get("dimension_id")),
                    raw=_markdown_text(item.get("raw_score")),
                    points=_markdown_text(item.get("weighted_points")),
                    weight=_markdown_text(item.get("weight")),
                    read=_zh_text(item.get("current_read")),
                )
            )
    control = findings.get("control_map") or {}
    if control:
        lines.extend(["", "### 控制权图谱", ""])
        lines.append(f"- 状态：{_status_zh(control.get('status'))}；风险等级：{_status_zh(control.get('risk_level'))}")
        lines.append(f"- 已识别关键词：{', '.join(_right_people_term_zh(term) for term in control.get('known_terms', [])[:8]) or '无'}")
        for item in control.get("findings", [])[:4]:
            lines.append(f"- {_zh_text(item)}")
    incentive = findings.get("incentive_map") or {}
    if incentive:
        lines.extend(["", "### 激励图谱", ""])
        lines.append(f"- 当前判断：{_zh_text(incentive.get('current_read'))}")
        for item in (incentive.get("positive_signals") or [])[:3]:
            lines.append(f"- 正面：{_zh_text(item)}")
        for item in (incentive.get("concerns_or_unknowns") or [])[:3]:
            lines.append(f"- 待复核：{_zh_text(item)}")
    ledger = findings.get("capital_allocation_ledger") or {}
    if ledger:
        lines.extend(["", "### 资本配置账本", ""])
        lines.append(f"- 当前判断：{_zh_text(ledger.get('current_read'))}")
        for row in (ledger.get("rows") or [])[-3:]:
            lines.append(
                "- {year}：收入 RMB {revenue}B，经营现金流 RMB {cfo}B，自由现金流 RMB {fcf}B，所有者收益近似值 RMB {owner}B，投入资本回报率近似值 {roic}，增量投入资本回报率近似值 {iroic}".format(
                    year=_markdown_text(row.get("year")),
                    revenue=_money_billions(row.get("revenue")),
                    cfo=_money_billions(row.get("operating_cash_flow")),
                    fcf=_money_billions(row.get("free_cash_flow")),
                    owner=_money_billions(row.get("owner_earnings_proxy")),
                    roic=_percent(row.get("roic_proxy")),
                    iroic=_percent(row.get("incremental_roic_proxy")),
                )
            )
    communication = findings.get("communication_audit") or {}
    if communication:
        lines.extend(["", "### 管理层沟通审计", ""])
        lines.append(f"- 当前判断：{_zh_text(communication.get('current_read'))}")
        for check in (communication.get("outcome_checks") or [])[:5]:
            lines.append(
                f"- {_zh_text(check.get('claim_theme'))}：{_status_zh(check.get('verdict'))} | {_zh_text(check.get('read'))}"
            )
    matrix = findings.get("red_flag_matrix") or {}
    if matrix:
        lines.extend(["", "### 红旗矩阵", ""])
        lines.append(
            f"- 状态：{_status_zh(matrix.get('status'))}；事项数：{_markdown_text(matrix.get('row_count', 0))}；硬性阻断：{_markdown_text(matrix.get('hard_override_count', 0))}"
        )
        for row in (matrix.get("rows") or [])[:6]:
            lines.append(
                f"- [{_severity_zh(row.get('severity'))}] {_zh_text(_red_flag_metric_zh(row.get('flag_id')))}：{_zh_text(_red_flag_metric_zh(row.get('read')))}"
            )
    return "\n".join(lines).strip()


def _right_people_chinese_evidence_dossier(findings: dict[str, Any]) -> str:
    if not findings:
        return "- 尚未运行。"
    lines = [
        "这一节故意多放一点原始材料。“正确的人”判断最怕变成抽象形容词，所以这里先展示系统读到的申报文件摘录、管理层沟通样本和财务行为结果，再把它们放回判断框架里。",
        "",
    ]
    cards = findings.get("official_filing_evidence_cards") or []
    if cards:
        lines.extend(["### 官方申报文件摘录", ""])
        for card in cards:
            group_id = _markdown_text(card.get("group_id"))
            doc = card.get("source_document") or {}
            snippets = card.get("snippets") or []
            lines.extend(
                [
                    f"#### {_right_people_card_title_zh(group_id)}",
                    "",
                    "- 来源：{filing_date} / `{document_id}`".format(
                        filing_date=_markdown_text(doc.get("filing_date") or "unknown date"),
                        document_id=_markdown_text(doc.get("document_id") or doc.get("local_path") or "unknown"),
                    ),
                    "- 为什么重要：" + _right_people_card_why_zh(group_id),
                    "- 命中关键词：" + (", ".join(_right_people_term_zh(term) for term in card.get("matched_terms", [])[:8]) or "无"),
                ]
            )
            display_snippets = [
                snippet for snippet in snippets if float(snippet.get("quality_score") or 0) >= 4
            ] or snippets[:3]
            for snippet in display_snippets[:6]:
                term = _markdown_text(snippet.get("matched_term"))
                lines.append(
                    f"- 中文证据要点（{_right_people_term_zh(term)}）："
                    + _right_people_snippet_summary_zh(term, snippet.get("text"))
                )
            lines.append("- 限制：" + _right_people_card_limit_zh(group_id))
            lines.append("")
    else:
        lines.extend(["### 官方申报文件摘录", "", "- 暂无可展示的官方申报文件证据卡。", ""])

    lines.extend(_right_people_chinese_financial_behavior_lines(findings))
    lines.extend(_right_people_chinese_transcript_lines(findings))
    lines.extend(_right_people_chinese_why_not_pass_lines(findings))
    return "\n".join(lines).strip()


def _right_people_chinese_financial_behavior_lines(findings: dict[str, Any]) -> list[str]:
    ledger = findings.get("capital_allocation_ledger") or {}
    rows = ledger.get("rows") or []
    if not rows:
        return ["### 财务行为证据", "", "- 暂无资本配置账本。", ""]
    lines = [
        "### 财务行为证据",
        "",
        "财务结果不能证明某个管理者一定优秀，但它能约束管理层叙事：如果口头上说长期主义，数字上应该逐渐体现为现金质量、增量回报、克制稀释和资本使用纪律。",
        "",
    ]
    for row in rows[-3:]:
        lines.append(
            "- {year}：收入 RMB {revenue}B，经营现金流 RMB {cfo}B，自由现金流 RMB {fcf}B，所有者收益近似值 RMB {owner}B，投入资本回报率近似值 {roic}，增量投入资本回报率近似值 {iroic}，股权激励费用 / 收入 {sbc_rev}，稀释股数增长 {dilution}。".format(
                year=_markdown_text(row.get("year")),
                revenue=_money_billions(row.get("revenue")),
                cfo=_money_billions(row.get("operating_cash_flow")),
                fcf=_money_billions(row.get("free_cash_flow")),
                owner=_money_billions(row.get("owner_earnings_proxy")),
                roic=_percent(row.get("roic_proxy")),
                iroic=_percent(row.get("incremental_roic_proxy")),
                sbc_rev=_percent(row.get("sbc_to_revenue")),
                dilution=_percent(row.get("diluted_shares_yoy")),
            )
        )
    current_read = ledger.get("current_read")
    if current_read:
        lines.append("- 当前读法：" + _zh_text(current_read))
    lines.append(
        "- 投资含义：PDD 的现金生成和轻资本特征是真实可观察的强项；但 2025 年增量投入资本回报率近似值转负、自由现金流从 2024 年高位回落，这要求我们把“管理层长期投入”与后续利润率和现金回报做承诺兑现表。"
    )
    lines.append("")
    return lines


def _right_people_chinese_transcript_lines(findings: dict[str, Any]) -> list[str]:
    signals = findings.get("management_transcript_signals") or {}
    timeline = signals.get("claim_timeline") or []
    samples = signals.get("samples") or []
    lines = [
        "### 管理层沟通证据",
        "",
        "文字稿证据只算管理层主张，不算事实。它的价值在于建立“承诺 vs 后续结果”清单：管理层反复强调什么、什么时候开始强调、之后是否被申报文件和经营结果验证。",
        "",
    ]
    if timeline:
        lines.append("- 已识别的主要沟通主题：")
        for item in timeline[:5]:
            lines.append(
                "  - {claim_id}：{count} 条；覆盖 {first} 到 {latest}。".format(
                    claim_id=_zh_text(item.get("claim_id")),
                    count=_markdown_text(item.get("count")),
                    first=_markdown_text(item.get("first_period") or "unknown"),
                    latest=_markdown_text(item.get("latest_period") or "unknown"),
                )
            )
    if samples:
        lines.append("- 中文沟通样本要点：")
        for sample in samples[:4]:
            lines.append(
                "  - {quarter} / {speaker} / {claim_id}：{summary}".format(
                    quarter=_markdown_text(sample.get("quarter")),
                    speaker=_markdown_text(sample.get("speaker")),
                    claim_id=_zh_text(sample.get("claim_id")),
                    summary=_right_people_transcript_sample_summary_zh(sample),
                )
            )
    else:
        lines.append("- 暂无 transcript 样本。")
    lines.append(
        "- 当前限制：V1 已经能收集和归类主题，但还没有逐条判断问答环节是否回避，也没有把每个承诺和后续年度 / 季度结果逐条配对。"
    )
    lines.append("")
    return lines


def _right_people_chinese_why_not_pass_lines(findings: dict[str, Any]) -> list[str]:
    decision = findings.get("right_people_decision") or {}
    unresolved = decision.get("unresolved_gate_items") or []
    lines = [
        "### 为什么当前仍然暂不通过",
        "",
    ]
    if unresolved:
        lines.append("- 未解决门槛项：" + "；".join(_dimension_zh(item) for item in unresolved[:8]) + "。")
    lines.extend(
        [
            "- 控制权：已经定位到实益所有权 / 投票权相关披露，但还没有抽成“谁有多少经济权益、谁有多少投票权、谁能控制董事会”的结构化表。",
            "- 激励：股权激励费用和稀释看起来可控，但还没有完成具名高管薪酬指标 / 薪酬与绩效一致性分析，所以不能直接说激励完全对齐每股价值。",
            "- 资本配置：现金流很强，但需要把现金用途拆成再投资、回购、分红、并购、投资资产和现金沉淀；否则无法判断管理层是否真的在提高每股内在价值。",
            "- 沟通：已有大量文字稿信号，但还没有系统识别问答回避、指标转移和承诺兑现失败。",
            "",
        ]
    )
    return lines


def _right_people_card_title_zh(group_id: str) -> str:
    return {
        "control_and_governance": "控制权与治理",
        "incentives_and_compensation": "激励与股权薪酬",
        "capital_allocation": "资本配置与现金使用",
        "integrity_red_flags": "诚信 / 治理红旗",
    }.get(group_id, group_id)


def _right_people_card_why_zh(group_id: str) -> str:
    return {
        "control_and_governance": "“正确的人”的第一问不是 CEO 说得好不好，而是谁真正控制公司、外部股东的权利是否清楚。",
        "incentives_and_compensation": "股权激励、SBC 和稀释会直接影响每股价值；好的团队应当让激励和长期每股经济结果一致。",
        "capital_allocation": "资本配置把管理层品格和能力落到行动上：保留现金、再投资、回购、分红和融资都应该服务于每股内在价值。",
        "integrity_red_flags": "审计师、重述、关联方、重大内控缺陷等词是治理风险入口；命中后需要进一步核对事实，而不是直接下结论。",
    }.get(group_id, "该证据卡用于定位“正确的人”判断所需的官方来源。")


def _right_people_card_limit_zh(group_id: str) -> str:
    return {
        "control_and_governance": "关键词命中只能说明申报文件中存在相关披露；最终需要抽取完整表格和协议条款。",
        "incentives_and_compensation": "当前证据还没有完成具名高管薪酬指标和绩效条件的逐项解析。",
        "capital_allocation": "回购、分红和现金用途需要和真实估值、现金流、投资回报一起判断。",
        "integrity_red_flags": "红旗词不是定罪；它只是要求人工进入上下文和源文件复核。",
    }.get(group_id, "该摘录用于引导复核，不是最终结论。")


def _right_people_term_zh(value: Any) -> str:
    text = _markdown_text(value)
    return {
        "VIE": "VIE / 可变利益实体",
        "variable interest entity": "可变利益实体",
        "contractual arrangements": "协议控制安排",
        "beneficial ownership": "实益所有权",
        "voting power": "投票权",
        "board of directors": "董事会",
        "directors": "董事",
        "directors and executive officers": "董事和高管",
        "share-based compensation": "股权激励费用",
        "share incentive plan": "股权激励计划",
        "restricted share units": "限制性股份单位",
        "options": "期权",
        "compensation": "薪酬 / 激励",
        "dividend": "分红",
        "repurchase": "回购",
        "investment commitments": "投资承诺",
        "reinvestment": "再投资",
        "related party": "关联方",
        "related-party": "关联方",
        "auditor": "审计师",
        "material weakness": "重大内控缺陷",
        "restatement": "重述",
        "investigation": "调查",
        "penalty": "处罚",
        "resignation": "辞任 / 离任",
    }.get(text, text)


def _right_people_snippet_summary_zh(term: Any, value: Any) -> str:
    text = _markdown_text(value)
    lower = text.lower()
    term_text = _markdown_text(term).lower()
    if not text:
        return "申报文件命中该主题，但当前没有可读摘录；需要回到源文件复核。"
    if term_text == "beneficial ownership":
        return "申报文件提供普通股实益所有权表，覆盖董事、高管，以及公司已知持有 5% 以上股份的人；下一步应抽取每个主体的经济权益和投票权。"
    if term_text == "directors and executive officers":
        return "申报文件把董事和高管作为单独披露对象；该信息应和实益所有权、股权激励、离任记录放在一起看。"
    if term_text in {"vie", "variable interest entity"}:
        if "hangzhou aimi" in lower and "86.6%" in lower:
            return "公司结构图披露 VIE 及其主要子公司；杭州埃米由陈磊和赵佳臻分别持有 86.6% 和 13.4%，并通过一系列协议安排与公司绑定。"
        return "申报文件披露存在 VIE / 可变利益实体结构；这要求把会计并表和法律所有权分开判断。"
    if term_text == "contractual arrangements":
        if "not been tested" in lower or "prc court" in lower:
            return "公司提示 VIE 协议安排在中国法律解释和执行上存在不确定性，整体尚未在中国法院测试；这会影响外部股东对底层经营实体权利的确定性。"
        return "申报文件披露协议控制安排；需要继续阅读具体协议条款、股权质押、独家购买权和违约救济。"
    if term_text == "voting power":
        return "申报文件提示新增股份可能稀释普通股持有人的投票权，并提到开曼法下普通股股东查阅股东名单或公司记录的权利有限。"
    if term_text == "board of directors":
        if "direct ownership of the vie" in lower:
            return "公司说明如果直接持有 VIE，可以通过股东权利影响 VIE 董事会；但当前结构依赖 VIE 及其股东履行协议义务。"
        return "申报文件包含董事会相关披露；需要继续映射董事独立性、委员会职责和控制人影响。"
    if term_text in {"restricted share units", "options"}:
        if "218,820,960" in text and "55,599,296" in text:
            return "截至 2025 年末，2018 年股权激励计划下仍有约 2.188 亿股期权和约 5,560 万股限制性股份单位未结；这是评估潜在稀释的重要输入。"
        if "278,720,576" in text and "55,522,388" in text:
            return "申报文件披露员工群体持有大量期权和限制性股份单位；需要和总股本、回购、稀释趋势一起看。"
        return "申报文件披露期权 / 限制性股份单位；需要抽取授予数量、行权条件、归属期和剩余池子。"
    if term_text in {"share-based compensation", "share incentive plan", "compensation"}:
        return "公司披露 2015 年和 2018 年股权激励计划，用于向员工、董事和顾问授予期权及其他奖励；股权激励费用应被当作真实每股成本处理。"
    if term_text == "repurchase":
        if "convertible bonds" in lower:
            return "申报文件中的回购语境主要是可转债回购，而不是普通股回购；资本配置分析不能把它误读成股东回购。"
        return "申报文件出现回购相关披露；需要区分普通股回购、可转债回购和其他融资活动。"
    if term_text == "investment commitments":
        return "申报文件披露重大现金需求包括资本开支、经营租赁承诺和投资承诺；这影响自由现金流可分配性。"
    if term_text == "dividend":
        return "申报文件说明控股公司向股东分红和偿债能力，可能部分依赖中国大陆子公司分红以及 VIE 支付的许可和服务费；现金可上翻能力需要单独复核。"
    if term_text in {"related party", "related-party"}:
        return "申报文件披露重大关联方余额；需要抽取关联方名称、金额、交易性质和是否为持续性安排。"
    if term_text == "auditor":
        return "摘录涉及审计委员会与独立审计师、内控、重大财务风险和关联交易审批职责；这本身不是审计师变更，但属于治理复核入口。"
    if term_text == "penalty":
        return "申报文件披露公司接受监管处罚并表示将遵守监管要求；需要进一步定位处罚原因、金额和是否影响商业模式。"
    if term_text in {"material weakness", "restatement", "investigation", "resignation"}:
        return f"申报文件出现“{_right_people_term_zh(term)}”相关词；这只是红旗入口，需要回到上下文判断是否为真实事项、否定句、风险因素或历史描述。"
    return f"申报文件出现“{_right_people_term_zh(term)}”相关披露；当前中文报告只保留要点，完整原文请回到来源文件复核。"


def _right_people_transcript_sample_summary_zh(sample: dict[str, Any]) -> str:
    claim_id = _zh_text(sample.get("claim_id"))
    excerpt = _markdown_text(sample.get("excerpt"))
    lower = excerpt.lower()
    notes: list[str] = []
    if "covid" in lower:
        notes.append("样本处于疫情冲击背景，需要把外部环境解释和公司自身执行结果分开。")
    if "convertible bonds" in lower or "capital markets" in lower:
        notes.append("样本提到资本市场活动或可转债安排，应放入资本配置台账。")
    if "investment" in lower or "long-term" in lower:
        notes.append("样本包含长期投入叙事，后续要用利润率、现金流和增量回报验证。")
    if "competition" in lower or "pressure" in lower:
        notes.append("样本涉及竞争或压力，应检查管理层是否直接解释利润率变化。")
    if not notes:
        notes.append("该样本用于建立管理层主题时间线；它只是主张证据，不是事实。")
    return " ".join(notes) + f" 归类主题：{claim_id}。"


def _report_excerpt(value: Any, *, limit: int) -> str:
    text = _markdown_text(value)
    if not text:
        return "n/a"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _right_people_chinese_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- 尚未运行。"
    lines = [
        f"- 状态：{_status_zh(findings.get('status'))}",
        f"- 当前判断：{_zh_text(findings.get('overall_read', 'not available'))}",
    ]
    coverage = findings.get("source_coverage") or {}
    if coverage:
        lines.append(
            "- 证据覆盖："
            + "；".join(
                [
                    f"年报状态 {_status_zh(coverage.get('annual_report_status'))}",
                    f"官方申报文件证据卡 {coverage.get('official_filing_evidence_cards', 0)}",
                    f"财务信号 {coverage.get('financial_signal_count', 0)}",
                    f"管理层文字稿信号 {coverage.get('management_transcript_signal_count', 0)}",
                    f"红旗 {coverage.get('red_flag_count', 0)}",
                ]
            )
        )
    subagents = findings.get("subagent_reports") or []
    if subagents:
        lines.extend(["", "### 正确的人子模块", ""])
        for subagent in subagents:
            lines.extend(
                [
                    f"#### {_subagent_name_zh(subagent.get('name') or subagent.get('agent_id'))}",
                    "",
                    f"- 状态：{_status_zh(subagent.get('status'))}",
                    f"- 当前判断：{_zh_text(subagent.get('current_read'))}",
                    f"- 证据数量：{_markdown_text(subagent.get('evidence_records', 0))}",
                ]
            )
            findings_lines = subagent.get("findings") or []
            if findings_lines:
                lines.append("- 关键证据：")
                lines.extend(
                    f"  - {_zh_text(_red_flag_metric_zh(item))}"
                    for item in findings_lines[:4]
                )
            limits = subagent.get("limits") or []
            if limits:
                lines.append("- 限制：")
                lines.extend(f"  - {_zh_text(item)}" for item in limits[:2])
            lines.append("")
    checklist = findings.get("right_people_checklist") or []
    if checklist:
        lines.extend(["### 正确的人检查清单", ""])
        lines.extend(["| 项目 | 状态 | 证据基础 | 限制 |", "| --- | --- | --- | --- |"])
        for item in checklist:
            lines.append(
                "| {item} | {status} | {basis} | {limitation} |".format(
                    item=_markdown_cell(_zh_text(item.get("item"))),
                    status=_markdown_cell(_status_zh(item.get("status"))),
                    basis=_markdown_cell(_zh_text(item.get("basis"))),
                    limitation=_markdown_cell(_zh_text(item.get("limitation"))),
                )
            )
    red_flags = findings.get("red_flags") or []
    if red_flags:
        lines.extend(["", "### 需要复核的事项", ""])
        for flag in red_flags[:8]:
            lines.append(
                f"- [{_severity_zh(flag.get('severity'))}] {_zh_text(flag.get('flag_id'))}：{_zh_text(_red_flag_metric_zh(flag.get('read')))}"
            )
    open_questions = findings.get("open_questions") or []
    if open_questions:
        lines.extend(["", "### 未解决问题", ""])
        lines.extend(f"- {_zh_text(question)}" for question in open_questions[:8])
    return "\n".join(lines).strip()


def _subagent_name_zh(value: Any) -> str:
    text = _markdown_text(value)
    return {
        "Governance / Control Reader": "治理 / 控制权阅读器",
        "Incentive Alignment Analyst": "激励一致性分析员",
        "Capital Allocation Historian": "资本配置历史分析员",
        "Management Communication Auditor": "管理层沟通审计员",
        "Execution Track Record Analyst": "执行记录分析员",
        "Integrity / Red Flag Scanner": "诚信 / 红旗扫描员",
    }.get(text, text)


def _status_zh(value: Any) -> str:
    text = _markdown_text(value)
    return {
        "evidence_collected": "已收集证据",
        "partial_v1_evidence_collected": "V1 已收集部分证据",
        "partial_pass_needs_deeper_review": "部分通过，但需要深度复核",
        "does_not_pass_pending_red_flag_review": "暂不通过，等待红旗复核",
        "passes_v1_with_open_questions": "V1 通过，但仍有开放问题",
        "does_not_pass_v1_needs_review": "V1 暂不通过，需要复核",
        "source_mapped": "已完成来源映射",
        "partial_evidence": "已有部分证据",
        "ledger_built": "已建立账本",
        "audit_seeded": "已建立审计种子",
        "review_items_found": "发现需复核事项",
        "no_review_items_promoted": "未提升出复核事项",
        "needs_review": "需要复核",
        "not_evaluated": "尚未评估",
        "unknown": "未知",
        "functional_v1_official_filing_based": "V1 可用，基于官方申报文件",
        "partially_supported": "部分支持",
        "functional_v1_transcript_based": "V1 可用，基于文字稿",
        "no_high_priority_red_flag_detected_v1": "V1 未发现高优先级红旗",
        "review_required": "需要复核",
        "supported": "支持",
    }.get(text, text)


def _confidence_zh(value: Any) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
        "unknown": "未知",
    }.get(_markdown_text(value), _markdown_text(value))


def _dimension_zh(value: Any) -> str:
    return {
        "integrity_and_candor": "诚信与坦诚",
        "incentive_alignment": "激励一致性",
        "capital_allocation": "资本配置",
        "control_and_governance": "控制权与治理",
        "execution_quality": "执行质量",
        "behavior_in_stress": "压力下的行为",
    }.get(_markdown_text(value), _markdown_text(value))


def _severity_zh(value: Any) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(_markdown_text(value), _markdown_text(value))


def _zh_text(value: Any) -> str:
    text = _markdown_text(value)
    exact = {
        "Draft pending audit review": "草稿，等待审计 / 人工复核",
        "partially_supported: V1 has official-filing, financial-outcome, and management-communication evidence, but final people judgment remains open.": "部分支持：V1 已经有官方 filing、财务结果和管理层沟通证据，但最终的 right people 判断仍然需要继续验证。",
        "partial_pass: financial outcomes and some incentive evidence are supportive, but control, pay-for-performance, communication fulfillment, and review flags are not resolved.": "部分通过：财务结果和部分激励证据是支持性的，但控制权、pay-for-performance、管理层沟通兑现情况和复核事项仍未解决。",
        "passes_v1: evidence is broadly supportive, but analyst review is still required before relying on the judgment.": "V1 通过：证据整体支持，但在依赖该判断前仍需要人工复核。",
        "does_not_pass_yet: high-severity governance, integrity, or verification flags must be resolved first.": "暂不通过：高严重性治理、诚信或核验红旗必须先解决。",
        "does_not_pass_yet: current evidence is too incomplete or cautionary to support right people.": "暂不通过：当前证据过于不完整或偏谨慎，尚不足以支持“正确的人”。",
        "Pass for V1 source discovery and first-pass official financial extraction, with material conflicts recorded for later review. This is still not a complete investment research report.": "V1 source discovery 和第一轮官方财务抽取通过；仍有重大冲突记录待后续复核。这仍然不是完整的投资研究报告。",
        "not available": "不可用",
        "Governance, board, ownership, voting-power, and VIE/control disclosures.": "治理、董事会、所有权、投票权以及 VIE / 控制权披露。",
        "Needs structured ownership/voting table before final judgment.": "最终判断前，需要结构化的所有权 / 投票权表。",
        "SBC, dilution, ownership, and share-incentive disclosures.": "股权激励费用、稀释、所有权和股权激励披露。",
        "V1 does not yet parse named-executive pay metrics or full beneficial ownership.": "V1 尚未解析具名高管薪酬指标或完整实益所有权。",
        "Cash conversion, CapEx intensity, ROIC proxy, reinvestment language, buyback/dividend terms.": "现金转化、资本开支强度、投入资本回报率近似值、再投资表述、回购 / 分红条款。",
        "Needs a 5-year cash-use bridge and promise-versus-outcome review.": "需要 5 年现金用途桥，以及管理层承诺 vs 后续结果的复核。",
        "Cached earnings-call and executive-transcript evidence.": "已缓存的业绩电话会和高管文字稿证据。",
        "V1 counts themes; it does not yet rate evasiveness or consistency in Q&A.": "V1 目前统计主题；尚未评价问答环节中是否回避问题或前后一致。",
        "Revenue growth, margin trend, cash conversion, ROIC proxy, incremental-return evidence.": "收入增长、利润率趋势、现金转化、投入资本回报率近似值和增量回报证据。",
        "Financial outcomes support management assessment but do not prove individual skill.": "财务结果可以支持管理层评估，但不能单独证明某个个人的能力。",
        "Material-event scan, official filing red-flag terms, and official-fact verification conflicts.": "重大事项扫描、官方申报文件红旗词，以及官方事实核验冲突。",
        "No red flag detected is not proof of integrity.": "没有发现红旗并不等于证明诚信没有问题。",
        "No detected red flag is not proof of integrity.": "没有发现红旗并不等于证明诚信没有问题。",
        "Voting power / beneficial ownership language exists; controller economics versus votes requires table-level extraction.": "存在投票权 / 实益所有权相关表述；控制人的经济所有权和投票权需要表格级提取。",
        "Annual report contains leadership/governance disclosure that should be mapped to named people and entities.": "年报包含领导层 / 治理披露，应映射到具体个人和实体。",
        "Official filings contain compensation / share-incentive evidence for review.": "官方申报文件包含薪酬 / 股权激励证据，可继续复核。",
        "Understand who controls the company": "理解谁实际控制公司",
        "Management incentives align with per-share value": "管理层激励是否和每股价值一致",
        "Capital allocation is rational and long-term": "资本配置是否理性且长期导向",
        "Management communication is source-checkable": "管理层沟通是否可被来源核验",
        "Execution record supports trust": "执行记录是否支持信任",
        "No unresolved severe integrity/governance red flag": "没有未解决的严重诚信 / 治理红旗",
        "What is the exact beneficial ownership and voting-power table for current insiders and major shareholders?": "当前内部人和主要股东的精确实益所有权 / 投票权表是什么？",
        "Are management incentives tied to per-share value, cash flow, ROIC, and durable growth, or mostly to scale?": "管理层激励是绑定每股价值、现金流、投入资本回报率和可持续增长，还是主要绑定规模？",
        "How much cash was used for reinvestment, buybacks, dividends, acquisitions, and investment assets over the last five years?": "过去五年现金分别用于再投资、回购、分红、并购和投资资产的金额是多少？",
        "Which management statements from earnings calls were later confirmed or contradicted by filings and financial outcomes?": "哪些业绩电话会中的管理层表述，后来被申报文件和财务结果验证或反驳？",
        "Legally filed, directly observable, audited, certified, or externally adjudicated evidence.": "依法提交、可直接观察、经审计 / 认证，或由外部监管 / 司法确认的证据。",
        "Foundation for right-people analysis.": "作为“正确的人”分析的地基。",
        "What management says it will do, why results look the way they do, or how it frames priorities.": "管理层声称将要做什么、如何解释结果、以及如何表述优先级。",
        "Hypothesis to test against later filings and outcomes.": "作为假设，必须用后续申报文件和经营结果验证。",
        "Independent validation or contradiction outside management's own story.": "来自管理层叙事之外的独立验证或反证。",
        "Corroboration or risk cue; source quality must be labeled.": "作为佐证或风险线索；必须标注来源质量。",
        "Analyst or system judgment after weighing facts, claims, and external evidence.": "在权衡事实、主张和外部证据之后形成的分析判断。",
        "Final analyst conclusion only when evidence chain is explicit.": "只有证据链清楚时，才能作为最终分析结论。",
        "10-K, 20-F, audited annual reports, proxy/DEF 14A when applicable, S-1/F-1/424B4, governance documents, definitive agreements, enforcement orders, final judgments": "10-K、20-F、经审计年报、适用时的代理声明 / DEF 14A、S-1/F-1/424B4、治理文件、正式协议、监管处罚令、最终司法判决",
        "Control, incentives, compensation, related parties, audited financial outcomes, and hard red flags.": "用于控制权、激励、薪酬、关联方、经审计财务结果和硬红旗。",
        "10-Q, 6-K, 8-K, 13D/13G, Forms 3/4/5, director/officer change filings": "10-Q、6-K、8-K、13D/13G、Forms 3/4/5、董事 / 高管变动披露",
        "Event-driven changes, ownership changes, interim financials, auditor issues, and turnover.": "用于重大事项变化、所有权变化、中期财务、审计师问题和人员变动。",
        "Earnings calls, shareholder letters, investor days, conference decks, executive interviews": "业绩电话会、股东信、投资者日、会议演示材料、高管访谈",
        "Management mindset, priorities, promises, KPI framing, and communication quality.": "用于管理层思维方式、优先级、承诺、KPI 叙事和沟通质量。",
        "Customer, supplier, merchant, employee, competitor, media, forum, app-review, and expert inputs": "客户、供应商、商家、员工、竞争对手、媒体、论坛、应用商店评论和专家输入",
        "External validation only; useful for patterns, not standalone proof.": "只用于外部验证；适合识别模式，不能单独作为证明。",
        "Mixed: strong cash-generation/capital-light signals exist, but incremental margin or incremental return concerns require review.": "混合判断：现金生成和轻资本信号较强，但增量利润率或增量回报问题需要复核。",
        "Supportive: official financial outcomes show cash generation and capital efficiency, subject to cash-use review.": "支持性：官方财务结果显示现金生成和资本效率，但仍需复核现金用途。",
        "Cautionary: capital-allocation or incremental-return signals require review.": "谨慎：资本配置或增量回报信号需要复核。",
        "Not enough capital-allocation evidence yet.": "资本配置证据还不足。",
        "SBC and dilution are measurable and currently look supportive where calculated, but true pay-for-performance alignment is not proven.": "股权激励费用和稀释已经可衡量，已计算部分目前偏支持，但真正的薪酬与绩效一致性尚未证明。",
        "Incentive alignment cannot be evaluated yet.": "激励一致性尚无法评估。",
        "Named-executive pay metrics and pay-versus-performance alignment are not yet parsed.": "具名高管薪酬指标和薪酬与绩效一致性尚未解析。",
        "Control map cannot be judged until ownership/voting evidence is extracted.": "在所有权 / 投票权证据被结构化提取前，控制权图谱不能最终判断。",
        "VIE / contractual-arrangement structure requires governance and cash-control review.": "VIE / 协议控制结构需要单独复核治理权和现金控制权。",
        "VIE or contractual-arrangement language exists; legal ownership and accounting consolidation should be separated.": "存在 VIE 或协议控制相关表述；法律所有权和会计并表应分开判断。",
        "Voting power / beneficial ownership language exists; controller economics versus votes requires table-level extraction.": "存在投票权 / 实益所有权相关表述；控制人的经济所有权和投票权需要表格级提取。",
        "Annual report contains leadership/governance disclosure that should be mapped to named people and entities.": "年报包含领导层 / 治理披露，应映射到具体个人和实体。",
        "Management-priority claims are collected and linked to first-pass outcome checks, but evasiveness and promise fulfillment are not fully scored.": "管理层优先级主张已收集，并连接到第一轮结果检查；但回避程度和承诺兑现尚未完整评分。",
        "No transcript claims available for communication audit.": "没有可用于沟通审计的 transcript 主张。",
        "Long-term investment language should be tested against later margins, cash flow, and incremental returns.": "长期投入表述应使用后续利润率、现金流和增量回报验证。",
        "Competition/pressure commentary is present; check whether management explains margin changes directly.": "存在竞争 / 压力相关评论；需要检查管理层是否直接解释利润率变化。",
        "Capital-allocation language needs a promise-versus-outcome table before it can support right people.": "资本配置表述需要承诺兑现表，才能支持“正确的人”判断。",
        "Official filings contain share-incentive / compensation disclosures for source review.": "官方申报文件包含股权激励 / 薪酬披露，可继续做来源复核。",
        "官方申报文件 contain 股权激励 / 薪酬 disclosures for 来源复核.": "官方申报文件包含股权激励 / 薪酬披露，可继续做来源复核。",
        "Review flags exist but no hard override was promoted by V1.": "存在复核事项，但 V1 没有提升出硬性阻断项。",
        "Hard override exists; right-people gate cannot pass until reviewed.": "存在硬性阻断项；复核前“正确的人”门槛不能通过。",
        "No promoted integrity/governance review flags.": "没有提升出的诚信 / 治理复核事项。",
        "integrity_and_candor": "诚信与坦诚",
        "incentive_alignment": "激励一致性",
        "capital_allocation": "资本配置",
        "control_and_governance": "控制权与治理",
        "execution_quality": "执行质量",
        "behavior_in_stress": "压力下的行为",
        "competition_and_pressure": "竞争与压力",
        "long_term_investment": "长期投入",
        "management_priorities_and_tone": "管理层优先级与语气",
        "organization_and_people": "组织与人员",
    }
    if text in exact:
        return exact[text]
    replacements = [
        ("Official filings contain governance and control evidence; V1 maps the issues but does not yet score minority-shareholder protection.", "官方申报文件包含治理和控制权证据；V1 会映射问题，但尚未给少数股东保护打分。"),
        ("SBC and dilution are measurable from official financial facts; full pay-for-performance alignment is still not proven.", "股权激励费用和稀释可以从官方财务事实中衡量；但完整的薪酬与绩效一致性尚未被证明。"),
        ("V1 connects reinvestment, cash conversion, ROIC proxy, and management capital-allocation language; causality still needs deeper review.", "V1 已把再投资、现金转化、投入资本回报率近似值和管理层资本配置表述连接起来；但因果关系还需要更深复核。"),
        ("Cached transcripts provide management-priority evidence; V1 counts and samples claims but does not yet judge evasiveness.", "已缓存文字稿提供管理层优先级证据；V1 会统计和抽样主张，但尚未判断是否回避问题。"),
        ("Financial outcomes support parts of execution quality but also show issues requiring review.", "财务结果支持部分执行质量判断，但也显示出需要复核的问题。"),
        ("No high-priority management/governance red flag was promoted by V1, but this is not a full forensic review.", "V1 没有提升出高优先级管理层 / 治理红旗，但这不是完整法证式复核。"),
        ("A term hit does not prove good or bad governance.", "关键词命中不证明治理好或坏。"),
        ("Minority-shareholder rights require document-level review of voting power, VIE, and board structure.", "少数股东权利需要逐文件复核投票权、VIE 和董事会结构。"),
        ("SBC ratio and dilution are necessary but not sufficient to prove alignment.", "股权激励费用比率和稀释是必要证据，但不足以证明激励一致。"),
        ("V1 does not yet parse named-executive compensation metrics into a pay-for-performance table.", "V1 尚未把具名高管薪酬指标解析成薪酬与绩效一致性表。"),
        ("ROIC and incremental ROIC are proxies and can be noisy for cash-heavy or investment-heavy companies.", "投入资本回报率和增量投入资本回报率是近似值；对现金很厚或投资资产很重的公司可能噪音较大。"),
        ("Management language about long-term investment must be tested against later margins, cash flow, and per-share value.", "管理层关于长期投入的表述，必须用后续利润率、现金流和每股价值验证。"),
        ("Prepared remarks are management framing.", "预先准备的发言是管理层叙事。"),
        ("Q&A tone and consistency require a later promise-versus-outcome and evasiveness review.", "问答环节的语气和一致性需要后续做承诺兑现和回避程度复核。"),
        ("Strong financial outcomes can support execution skill but cannot identify which leader created the result.", "强财务结果可以支持执行能力判断，但不能识别是哪位领导创造了结果。"),
        ("Weak margin or incremental-return signals require cause analysis before judging management quality.", "利润率或增量回报偏弱时，需要先做原因分析，再判断管理层质量。"),
        ("V1 depends on existing material-event scanning and official filing text coverage.", "V1 依赖现有重大事项扫描和官方申报文件文本覆盖。"),
        ("VIE or contractual-arrangement language exists; legal ownership and accounting consolidation should be separated.", "存在 VIE 或协议控制相关表述；法律所有权和会计并表应分开判断。"),
        ("Voting power / beneficial ownership language exists; controller economics versus votes requires table-level extraction.", "存在投票权 / 实益所有权相关表述；控制人的经济所有权和投票权需要表格级提取。"),
        ("Annual report contains leadership/governance disclosure that should be mapped to named people and entities.", "年报包含领导层 / 治理披露，应映射到具体个人和实体。"),
        ("Voting-power disclosure exists; shareholder-control rights should be reviewed.", "存在投票权披露；应复核股东控制权利。"),
        ("Official filings contain share-incentive / compensation disclosures for source review.", "官方申报文件包含股权激励 / 薪酬披露，可继续做来源复核。"),
        ("Latest SBC / revenue is", "最新股权激励费用 / 收入为"),
        ("and SBC / CFO is", "，股权激励费用 / 经营现金流为"),
        ("Latest diluted share-count growth is", "最新稀释股数增长为"),
        ("Latest annual FCF margin is", "最新年度自由现金流率为"),
        ("Latest CapEx / revenue is", "最新资本开支 / 收入为"),
        ("Latest CFO / net income is", "最新经营现金流 / 净利润为"),
        ("Latest unlevered ROIC proxy is", "最新无杠杆投入资本回报率近似值为"),
        ("Latest annual revenue growth is", "最新年度收入增长为"),
        ("Latest annual operating margin is", "最新年度经营利润率为"),
        ("Latest incremental operating margin is", "最新增量经营利润率为"),
        ("competition_and_pressure", "竞争与压力"),
        ("long_term_investment", "长期投入"),
        ("organization_and_people", "组织与人员"),
        ("management_priorities_and_tone", "管理层优先级与语气"),
        ("matched evidence items", "条匹配证据"),
        ("official_fact_material_conflict", "官方事实重大冲突"),
        ("advertising_expense conflict for", "广告费用 在"),
        ("short_term_investments conflict for", "短期投资 在"),
        ("advertising_expense", "广告费用"),
        ("short_term_investments", "短期投资"),
        ("beneficial ownership", "实益所有权"),
        ("mismatch", "差异"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    generic_replacements = [
        ("right people", "正确的人"),
        ("Right People", "正确的人"),
        ("official-filing", "官方申报文件"),
        ("official filing", "官方申报文件"),
        ("Official filing", "官方申报文件"),
        ("official filings", "官方申报文件"),
        ("Official filings", "官方申报文件"),
        ("filings", "申报文件"),
        ("filing", "申报文件"),
        ("transcripts", "文字稿"),
        ("transcript", "文字稿"),
        ("claims", "主张"),
        ("claim", "主张"),
        ("pay-for-performance", "薪酬与绩效一致性"),
        ("named-executive pay metrics", "具名高管薪酬指标"),
        ("owner earnings proxy", "所有者收益近似值"),
        ("incremental ROIC", "增量投入资本回报率"),
        ("unlevered ROIC proxy", "无杠杆投入资本回报率近似值"),
        ("ROIC proxy", "投入资本回报率近似值"),
        ("FCF margin", "自由现金流率"),
        ("CapEx", "资本开支"),
        ("CFO / net income", "经营现金流 / 净利润"),
        ("SBC / revenue", "股权激励费用 / 收入"),
        ("SBC / CFO", "股权激励费用 / 经营现金流"),
        ("SBC", "股权激励费用"),
        ("evasive", "回避"),
        ("evasiveness", "回避程度"),
        ("promise-versus-outcome", "承诺 vs 后续结果"),
        ("forensic review", "法证式复核"),
    ]
    for source, target in generic_replacements:
        text = text.replace(source, target)
    return text


def _red_flag_metric_zh(value: Any) -> str:
    text = _markdown_text(value)
    replacements = [
        ("Official filings", "官方申报文件"),
        ("Official filing", "官方申报文件"),
        ("advertising_expense", "广告费用"),
        ("short_term_investments", "短期投资"),
        (" conflict for ", " 在 "),
        ("official_fact_material_conflict", "官方事实重大冲突"),
        ("beneficial ownership", "实益所有权"),
        ("voting power", "投票权"),
        ("insiders", "内部人"),
        ("earnings calls", "业绩电话会"),
        ("earnings call", "业绩电话会"),
        ("filings", "申报文件"),
        ("filing", "申报文件"),
        ("share-incentive / compensation", "股权激励 / 薪酬"),
        ("source review", "来源复核"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _business_model_subagent_cluster_summary(cluster: dict[str, Any]) -> str:
    if not cluster:
        return ""
    subagents = cluster.get("subagents") or []
    lines = [
        "",
        "### Business Model Subagent Cluster",
        "",
        f"- Status: {cluster.get('status', 'unknown')}",
        f"- Scope: {cluster.get('scope', 'unknown')}",
    ]
    if subagents:
        lines.extend(["", "#### Subagent Blueprints", ""])
        for agent in subagents:
            name = _markdown_text(agent.get("name") or "Unnamed subagent")
            role = _markdown_text(agent.get("source_family") or agent.get("evidence_role"))
            working = _markdown_text(agent.get("working_level") or role)
            output = _markdown_text(agent.get("current_output"))
            highlights = _joined_items(agent.get("evidence_highlights") or [], limit=3)
            lines.extend(
                [
                    f"##### {name}",
                    "",
                    f"- Role: {role or 'not specified'}",
                    f"- Status: {_markdown_text(agent.get('status') or 'unknown')}",
                    f"- Working level: {working or 'not specified'}",
                    f"- Evidence records: {_markdown_text(agent.get('evidence_record_count', 0))}",
                ]
            )
            if output:
                lines.append(f"- Current read: {output}")
            if highlights:
                lines.append(f"- Evidence captured: {highlights}")
            if agent.get("subagent_id") == "official_reports_reader":
                lines.append(_official_reports_reader_material_summary(agent))
            elif agent.get("subagent_id") == "official_calls_investor_day_reader":
                lines.append(_official_management_events_summary(agent))
            lines.extend(["", "Limits:"])
            lines.extend(_section_bullets(agent.get("limits") or [], limit=3))
            lines.extend(["", "Next build:"])
            lines.extend(_section_bullets(agent.get("next_steps") or [], limit=3))
            lines.append("")
        example_lines = ["#### Evidence Examples"]
        for agent in subagents:
            records = agent.get("evidence_records") or []
            if records:
                example_lines.extend(["", f"##### {_markdown_text(agent.get('name'))}", ""])
                for record in records[:3]:
                    example_lines.append(
                        "- {claim}: {excerpt} ({confidence}; {locator})".format(
                            claim=_markdown_text(record.get("claim")),
                            excerpt=_markdown_text(record.get("excerpt")),
                            confidence=_markdown_text(record.get("confidence")),
                            locator=_markdown_text(record.get("source_locator")),
                        )
                    )
        if len(example_lines) > 1:
            lines.extend(example_lines)
    policy = cluster.get("orchestration_policy") or []
    if policy:
        lines.extend(["", "#### Orchestration Policy", ""])
        lines.extend(f"- {item}" for item in policy[:5])
    return "\n".join(lines)


def _official_reports_reader_material_summary(agent: dict[str, Any]) -> str:
    documents_seen = agent.get("documents_seen") or {}
    records = [
        record
        for record in agent.get("evidence_records", [])
        if record.get("evidence_type") == "official_interim_earnings_release_commentary"
    ]
    if not documents_seen and not records:
        return ""
    claim_counts = Counter(str(record.get("claim_id")) for record in records)
    filing_dates = sorted(
        {str(record.get("filing_date")) for record in records if record.get("filing_date")},
        reverse=True,
    )
    source_ids = []
    seen_source_ids: set[str] = set()
    for record in records:
        source_id = str(record.get("source_document_id") or "")
        if source_id and source_id not in seen_source_ids:
            seen_source_ids.add(source_id)
            source_ids.append(source_id)
    lines = [
        "",
        "Official filed-material summary:",
        "- Source-control rule: this reader only consumes filed official report documents selected by document type/category.",
        "- Included document filters: `20-F`, `10-K`, `annual_report_pdf`, and `KEEP_CORE_INTERIM_EARNINGS`.",
        "- Excluded from this reader: public voice, Reddit/forums, review sites, YouTube/Bilibili transcripts, third-party financial databases, market quote pages, and uncollected call/investor-day materials.",
        "- Included material type: annual reports plus official SEC 6-K earnings-release exhibits.",
        f"- Annual report documents available: {_markdown_text(documents_seen.get('annual_report_count', 0))}",
        f"- Official interim earnings-release documents available: {_markdown_text(documents_seen.get('official_interim_earnings_count', 0))}",
        f"- Official interim commentary records summarized: {_markdown_text(len(records))}",
    ]
    if filing_dates:
        lines.append(f"- Extracted earnings-release filing dates: {_joined_items(filing_dates, limit=6)}")
    if source_ids:
        lines.append(f"- First earnings-release source IDs: {_joined_items(source_ids, limit=4)}")
    if claim_counts:
        lines.append(
            "- Earnings-release theme coverage: "
            + "; ".join(
                f"{theme.replace('_', ' ')} {count}"
                for theme, count in sorted(claim_counts.items())
                if theme != "None"
            )
        )
    lines.extend(
        [
            "",
            "What the official interim releases add:",
            "- Management repeatedly frames the current phase as long-term investment / high-quality development rather than near-term margin maximization.",
            "- Recent releases emphasize merchant support, healthier platform ecosystem, supply-chain investment, and efficiency for merchants.",
            "- Management explicitly acknowledges intense competition, rapid external change, revenue-growth moderation, and possible pressure from sustained investments.",
            "- Customer-value language appears, but mostly at the level of consumers, quality, buyer retention, and platform ecosystem, not detailed customer-satisfaction proof.",
            "- Temu/global language in these extracted records is mostly forward-looking risk and operating-context language, not yet a full standalone Temu strategy transcript.",
            "",
            "Diligence implication:",
            "- These releases support the thesis that management is deliberately investing through a more competitive phase. They do not prove those investments have attractive returns, improve merchant profit, or deepen the moat.",
        ]
    )
    return "\n".join(lines)


def _official_management_events_summary(agent: dict[str, Any]) -> str:
    documents_seen = agent.get("documents_seen") or {}
    records = agent.get("evidence_records") or []
    highlights = [str(item) for item in agent.get("evidence_highlights") or []]
    status_lines = [
        item
        for item in highlights
        if item.startswith("Provider-chain status counts:")
        or item.startswith("Business-model question answer statuses:")
        or item.startswith("Collected transcript:")
    ]
    if not documents_seen and not records:
        return ""
    if not records:
        lines = [
            "",
            "Material summary:",
            "- Collected material type: earnings-call transcript provider-chain records and link-only transcript source candidates.",
            "- Official SEC 6-K earnings-release exhibits are routed to Official Reports Reader.",
            f"- Provider-chain registry sources: {_markdown_text(documents_seen.get('official_event_source_count', 0))}",
            f"- Alpha Vantage backfill sources: {_markdown_text(documents_seen.get('alpha_vantage_source_count', 0))}",
            f"- Local transcript intake sources: {_markdown_text(documents_seen.get('local_transcript_source_count', 0))}",
            f"- Link-only source candidates recorded: {_markdown_text(documents_seen.get('source_candidate_count', 0))}",
            f"- Business-model question-pack questions: {_markdown_text(documents_seen.get('business_model_question_count', 0))}",
            f"- Transcript question sets run: {_markdown_text(documents_seen.get('transcript_question_source_count', 0))}",
            f"- Question results recorded: {_markdown_text(documents_seen.get('transcript_question_results', 0))}",
            f"- Full call transcripts collected: {_markdown_text(documents_seen.get('call_transcript_count', 0))}",
            f"- Transcript segments collected: {_markdown_text(documents_seen.get('call_transcript_segment_count', 0))}",
            f"- Investor-day materials collected: {_markdown_text(documents_seen.get('investor_day_material_count', 0))}",
            "- Current status: provider transcripts and source candidates are captured; missing quarters require future API quota or licensed/local transcript ingestion.",
        ]
        lines.extend(f"- {line}" for line in status_lines[:8])
        return "\n".join(lines)
    claim_counts = {
        str(item.get("claim_id")): int(item.get("evidence_record_count") or 0)
        for item in agent.get("claims_tested", [])
    }
    filing_dates = sorted(
        {str(record.get("filing_date")) for record in records if record.get("filing_date")},
        reverse=True,
    )
    source_ids = []
    seen_source_ids: set[str] = set()
    for record in records:
        source_id = str(record.get("source_document_id") or "")
        if source_id and source_id not in seen_source_ids:
            seen_source_ids.add(source_id)
            source_ids.append(source_id)
    lines = [
        "",
        "Material summary:",
        "- Collected material type: official event materials outside the filed earnings-release exhibits.",
        f"- Full call transcripts collected: {_markdown_text(documents_seen.get('call_transcript_count', 0))}",
        f"- Investor-day materials collected: {_markdown_text(documents_seen.get('investor_day_material_count', 0))}",
        f"- Evidence records summarized: {_markdown_text(len(records))}",
    ]
    if filing_dates:
        lines.append(f"- Extracted filing dates: {_joined_items(filing_dates, limit=6)}")
    if source_ids:
        lines.append(f"- First source IDs: {_joined_items(source_ids, limit=4)}")
    if claim_counts:
        lines.extend(
            [
                "- Theme coverage: "
                + "; ".join(
                    f"{theme.replace('_', ' ')} {count}"
                    for theme, count in sorted(claim_counts.items())
                    if theme != "None"
                )
            ]
        )
    lines.extend(
        [
            "",
            "What the collected event materials currently suggest:",
            "- Management repeatedly frames the current phase as long-term investment / high-quality development rather than near-term margin maximization.",
            "- The material emphasizes merchant support, healthier platform ecosystem, supply-chain investment, and efficiency for merchants.",
            "- Management explicitly acknowledges intense competition, rapid external change, revenue-growth moderation, and possible pressure from sustained investments.",
            "- Customer-value language appears, but mostly at the level of consumers, quality, buyer retention, and platform ecosystem, not detailed customer-satisfaction proof.",
            "- Temu/global language in these extracted records is mostly forward-looking risk and operating-context language; it is not yet a full standalone Temu strategy transcript.",
            "",
            "Diligence implication:",
            "- These releases support the thesis that management is deliberately spending/investing through a more competitive phase. They do not prove those investments have attractive returns, improve merchant profit, or deepen the moat.",
        ]
    )
    return "\n".join(lines)


def _business_model_deep_dive_summary(deep_dive: dict[str, Any]) -> str:
    if not deep_dive:
        return ""
    lines = [
        "",
        "### Business Model Deep Dive",
        "",
        f"- Status: {deep_dive.get('status', 'unknown')}",
        f"- Scope: {deep_dive.get('scope', 'unknown')}",
    ]
    answer_cards = deep_dive.get("answer_cards") or []
    if answer_cards:
        lines.extend(["", "#### Diligence Answers", ""])
        for index, card in enumerate(answer_cards[:6], start=1):
            quantitative = "; ".join(str(item) for item in card.get("quantitative_support", [])[:7])
            wrong = "; ".join(str(item) for item in card.get("what_could_be_wrong", [])[:3])
            next_tests = "; ".join(str(item) for item in card.get("next_tests", [])[:3])
            lines.extend(
                [
                    f"**{index}. {card.get('question')}**",
                    "",
                    f"- Current answer: {card.get('current_answer')}",
                    f"- Evidence grade: {card.get('evidence_grade')}",
                ]
            )
            if quantitative:
                lines.append(f"- Quantitative support: {quantitative}")
            if wrong:
                lines.append(f"- What could be wrong: {wrong}")
            if next_tests:
                lines.append(f"- Next test: {next_tests}")
            lines.append("")
    revenue_engine = deep_dive.get("revenue_engine") or {}
    if revenue_engine:
        lines.extend(["", "#### Revenue Engine", "", f"- {revenue_engine.get('summary')}"])
        revenue_mix = revenue_engine.get("revenue_mix") or []
        if revenue_mix:
            lines.append("- Latest official revenue mix: " + "; ".join(str(item) for item in revenue_mix))
        mix_history = revenue_engine.get("revenue_mix_history") or []
        if mix_history:
            history_lines = []
            for item in mix_history[-4:]:
                year = item.get("year")
                online_share = _format_report_percent(item.get("online_marketing_share"))
                transaction_share = _format_report_percent(item.get("transaction_share"))
                if year and (online_share or transaction_share):
                    history_lines.append(
                        f"{year}: online marketing/others {online_share or 'n/a'}, transaction services {transaction_share or 'n/a'}"
                    )
            if history_lines:
                lines.append("- Recent revenue-mix history: " + "; ".join(history_lines))
        bridge = revenue_engine.get("financial_bridge") or {}
        if bridge.get("latest_snapshot"):
            lines.append("- Financial bridge: " + "; ".join(str(item) for item in bridge.get("latest_snapshot", [])[:5]))
        if bridge.get("yoy_pressure"):
            lines.append("- Latest-year pressure signals: " + "; ".join(str(item) for item in bridge.get("yoy_pressure", [])[:6]))
        findings = revenue_engine.get("findings") or []
        if findings:
            lines.extend(["", "Revenue-engine checks:"])
            for item in findings[:5]:
                claim = _markdown_text(item.get("claim"))
                why = _markdown_text(item.get("why_it_matters") or item.get("status"))
                limitation = _markdown_text(item.get("limitation"))
                lines.append(f"- {claim}")
                if why:
                    lines.append(f"  Current read: {why}")
                if limitation:
                    lines.append(f"  Limitation: {limitation}")
    unit = deep_dive.get("unit_economics") or {}
    if unit:
        lines.extend(["", "#### Unit Economics Proxies", "", f"- {unit.get('summary')}"])
        proxy_signals = unit.get("proxy_signals") or []
        if proxy_signals:
            lines.extend(["", "Unit-economics proxy cards:"])
            for signal in proxy_signals[:8]:
                name = _markdown_text(signal.get("name"))
                value = _markdown_text(signal.get("value"))
                interpretation = _markdown_text(signal.get("interpretation"))
                limitation = _markdown_text(signal.get("limitation"))
                lines.append(f"- {name}: {value}")
                if interpretation:
                    lines.append(f"  Interpretation: {interpretation}")
                if limitation:
                    lines.append(f"  Limitation: {limitation}")
        missing_unit = unit.get("missing_unit_economics") or []
        if missing_unit:
            lines.extend(["", "- Missing unit-economics evidence:"])
            lines.extend(f"  - {item}" for item in missing_unit[:5])
    moat_hypotheses = deep_dive.get("moat_hypotheses") or []
    if moat_hypotheses:
        lines.extend(
            [
                "",
                "#### Moat Hypotheses To Test",
                "",
            ]
        )
        for item in moat_hypotheses[:6]:
            missing = _joined_items(item.get("missing_tests") or [], limit=3)
            lines.append(f"- Hypothesis: {_markdown_text(item.get('hypothesis'))}")
            lines.append(f"  Official support: {_markdown_text(item.get('official_support') or item.get('status'))}")
            if item.get("financial_or_kpi_support"):
                lines.append(f"  Financial/KPI support: {_markdown_text(item.get('financial_or_kpi_support'))}")
            lines.append(f"  Current read: {_markdown_text(item.get('current_read') or 'hypothesis only')}")
            if missing:
                lines.append(f"  Missing tests: {missing}")
    anti_moat = deep_dive.get("anti_moat_tests") or []
    if anti_moat:
        lines.extend(
            [
                "",
                "#### Anti-Moat Tests",
                "",
            ]
        )
        for item in anti_moat[:6]:
            lines.append(f"- Risk: {_markdown_text(item.get('risk') or item.get('claim'))}")
            lines.append(f"  Status: {_markdown_text(item.get('status') or 'identified')}")
            if item.get("external_test_needed"):
                lines.append(f"  External test needed: {_markdown_text(item.get('external_test_needed'))}")
    return "\n".join(lines)


def _public_voice_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    theme_summary = findings.get("theme_summary") or {}
    theme_counts = theme_summary.get("counts") or {}
    stats = findings.get("collection_stats") or {}
    source_results = findings.get("source_results") or []
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Evidence items collected: {findings.get('evidence_item_count', 0)}",
    ]
    if stats:
        lines.append(
            "- Collection breadth: "
            f"{stats.get('searches_attempted', 0)} searches, "
            f"{stats.get('posts_collected', 0)} pages/posts fetched, "
            f"{stats.get('comments_seen_before_filter', 0)} public-voice items scanned, "
            f"{stats.get('comments_collected', 0)} kept."
        )
    if theme_counts:
        lines.extend(["", "### Public-Voice Theme Leads", ""])
        for theme, count in sorted(theme_counts.items(), key=lambda item: item[1], reverse=True):
            label = _markdown_text(theme.replace("_", " "))
            lines.append(
                f"- {label}: {count} evidence items. Current read: low-confidence pattern; needs stronger-source triangulation."
            )
    aggregate_results = [
        result for result in source_results if result.get("aggregate_summary")
    ]
    if aggregate_results:
        lines.extend(["", "- Aggregate review-site summaries:"])
        for result in aggregate_results:
            lines.append(f"  - {result.get('name')}: {_public_voice_aggregate_line(result.get('aggregate_summary') or {})}")
    audit_notes = findings.get("audit_notes") or []
    if audit_notes:
        lines.extend(["", "- Audit note: " + audit_notes[0]])
    return "\n".join(lines)


def _customer_happiness_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Evidence items considered: {findings.get('evidence_item_count', 0)}",
        f"- Current conclusion: {findings.get('current_conclusion', 'not available')}",
    ]
    quality_counts = findings.get("source_quality_counts") or {}
    if quality_counts:
        lines.append(
            "- Source-quality mix: "
            + ", ".join(f"tier {tier}: {count}" for tier, count in sorted(quality_counts.items()))
        )
    dimensions = findings.get("dimensions") or []
    if dimensions:
        lines.extend(["", "### Customer-Happiness Dimension Blueprints", ""])
        for dimension in sorted(dimensions, key=lambda item: int(item.get("evidence_count", 0)), reverse=True):
            label = _markdown_text(dimension.get("label") or "Unnamed dimension")
            lines.extend(
                [
                    f"#### {label}",
                    "",
                    f"- Evidence count: {_markdown_text(dimension.get('evidence_count', 0))}",
                    f"- Current read: {_markdown_text(dimension.get('current_read') or 'unknown')}",
                    f"- Confidence: {_markdown_text(dimension.get('confidence') or 'unknown')}",
                    f"- Why it matters: {_markdown_text(dimension.get('summary') or 'not available')}",
                    "",
                ]
            )
    aggregates = findings.get("aggregate_summaries") or []
    if aggregates:
        lines.extend(["", "- Aggregate source summaries:"])
        for item in aggregates:
            lines.append(
                f"  - {item.get('name')}: {_public_voice_aggregate_line(item.get('aggregate_summary') or {})}"
            )
    policy = findings.get("source_quality_policy") or []
    if policy:
        lines.extend(["", "- Source-quality policy:"])
        lines.extend(f"  - {item}" for item in policy[:3])
    return "\n".join(lines)


def _executive_transcript_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Registry: `{findings.get('registry_path') or 'not configured'}`",
        f"- Sources registered: {findings.get('source_count', 0)}",
        f"- Collectable adapters in V1: {findings.get('collectable_source_count', 0)}",
        f"- Transcript sources collected: {findings.get('transcript_source_count', 0)}",
        f"- Transcript segments collected: {findings.get('transcript_segment_count', 0)}",
        f"- Evidence items extracted: {findings.get('evidence_item_count', 0)}",
    ]
    question_pack = findings.get("business_model_question_pack") or {}
    if question_pack:
        lines.extend(
            [
                f"- Business-model questions configured: {_markdown_text(question_pack.get('question_count', 0))}",
                f"- Business-model question results: {_markdown_text(question_pack.get('total_question_results', 0))}",
            ]
        )
        answer_counts = question_pack.get("answer_status_counts") or {}
        if answer_counts:
            lines.append(
                "- Business-model answer statuses: "
                + ", ".join(f"{status}: {count}" for status, count in sorted(answer_counts.items()))
            )
    status_counts = findings.get("source_status_counts") or {}
    if status_counts:
        lines.append(
            "- Source statuses: "
            + ", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items()))
        )
    source_results = findings.get("source_results") or []
    if source_results:
        lines.extend(["", "### Executive Transcript Source Blueprints", ""])
        for result in source_results:
            source = _markdown_text(result.get("name") or result.get("source_id") or "Unnamed source")
            lines.extend(
                [
                    f"#### {source}",
                    "",
                    f"- Platform: {_markdown_text(result.get('platform') or 'unknown')}",
                    f"- Status: {_markdown_text(result.get('status') or 'unknown')}",
                    f"- Transcript segments: {_markdown_text(result.get('transcript_segment_count', 0))}",
                    f"- Evidence items: {_markdown_text(len(result.get('evidence_items', [])))}",
                    f"- Business-model question results: {_markdown_text(len(result.get('business_model_question_results') or []))}",
                    f"- Business-model question answers: {_markdown_text(sum(1 for item in (result.get('business_model_question_results') or []) if item.get('answer_status') == 'evidence_found'))}",
                    f"- Cache paths: {_markdown_text(len(result.get('cache_paths', [])))}",
                    "",
                ]
            )
    theme_summary = findings.get("theme_summary") or {}
    counts = theme_summary.get("counts") or {}
    if counts:
        lines.append(
            "- Transcript claim themes: "
            + ", ".join(f"{theme}: {count}" for theme, count in sorted(counts.items()))
        )
    examples = theme_summary.get("examples") or {}
    if examples:
        lines.extend(["", "- Transcript evidence examples:"])
        for claim_id, items in list(examples.items())[:5]:
            lines.append(f"  - {claim_id}:")
            for item in items[:2]:
                lines.append(
                    "    - {source}: {excerpt} | {url}".format(
                        source=item.get("source_name") or item.get("platform"),
                        excerpt=_markdown_cell(item.get("excerpt")),
                        url=item.get("source_url"),
                    )
                )
    audit_notes = findings.get("audit_notes") or []
    if audit_notes:
        lines.extend(["", "- Executive-transcript audit notes:"])
        lines.extend(f"  - {note}" for note in audit_notes[:4])
    errors = findings.get("errors") or []
    if errors:
        lines.extend(["", "- Collection errors / blocked sources:"])
        lines.extend(f"  - {error}" for error in errors[:5])
    return "\n".join(lines)


def _external_moat_memo_summary(findings: dict[str, Any]) -> str:
    if not findings:
        return "- Not run."
    source_lines = findings.get("source_lines") or []
    lines = [
        f"- Status: {findings.get('status', 'unknown')}",
        f"- Hypotheses to test: {len(findings.get('hypotheses', []))}",
        f"- Source lines planned: {len(source_lines)}",
    ]
    collector_groups = findings.get("collector_groups") or []
    if collector_groups:
        lines.extend(["", "### Controlled Collector Blueprints", ""])
        for group in collector_groups:
            collector = _markdown_text(group.get("collector_type") or group.get("collector_id"))
            lines.extend(
                [
                    f"#### {collector}",
                    "",
                    f"- Source line: {_markdown_text(group.get('source_line_name'))}",
                    f"- Status: {_markdown_text(group.get('status') or 'unknown')}",
                    f"- Source tier: {_markdown_text(group.get('quality_tier') or 'unknown')}",
                    f"- Collection rule: {_markdown_text(group.get('collection_rule') or 'not specified')}",
                    f"- First locator: {_markdown_text(group.get('first_locator') or 'not specified')}",
                    "",
                ]
            )
    if source_lines:
        lines.extend(["", "### Source-Line Priority", ""])
        for source_line in source_lines:
            lines.append(
                "- {name}: tier {tier}. Purpose: {role}".format(
                    name=_markdown_text(source_line.get("name")),
                    tier=_markdown_text(source_line.get("quality_tier")),
                    role=_markdown_text(source_line.get("validation_role")),
                )
            )
    gaps = findings.get("official_report_gaps") or []
    if gaps:
        lines.extend(["", "- Official-report gaps this plan is meant to test:"])
        lines.extend(f"  - {gap}" for gap in gaps[:5])
    return "\n".join(lines)


def _research_controls_summary(state: ResearchState, *, audit_status: str) -> str:
    source_candidates = state.get("source_candidates", [])
    lines = [
        "### Source Summary",
        "",
        _source_inventory_summary(source_candidates),
        "",
        "### Extraction And Verification",
        "",
        f"- Extracted facts: {len(state.get('extracted_facts', []))}",
        f"- Raw facts before deduplication: {len(state.get('raw_extracted_facts', []))}",
        f"- Method: {state.get('extraction_summary', {}).get('method', 'not run')}",
        f"- Verification records: {len(state.get('verification_results', []))}",
        "- Policy: SEC/regulator filings are the financial-report source of record; company IR may cross-validate; third-party mirrors are not allowed for financial extraction.",
        "",
        _verification_summary(state.get("verification_results", [])),
        "",
        "### Learning Materials / 学习材料",
        "",
        _learning_summary(state.get("learning_context", {})),
        "",
        "### Human Review Gates",
        "",
        "- Formula changes require approval.",
        "- Learning activation requires approval.",
        "- Material source conflicts require approval.",
        "- Low-quality sources for important claims require approval.",
        "- Important valuation assumptions require approval.",
        "",
        "### Audit Status",
        "",
        audit_status,
    ]
    return "\n".join(lines)


def build_financial_results_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}
    metrics = state.get("metrics", [])
    valuation_metrics = _valuation_metrics_for_state(state)
    operating_kpis = (
        (state.get("business_model_findings") or {})
        .get("official_report_analysis", {})
        .get("operating_kpi_analysis", {})
    )

    return f"""# Financial Results Report: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## Scope

This report is produced by the Financial Results Report Agent. It focuses on official financial results, extracted operating KPIs, financial-quality metrics, valuation metrics produced by the Valuation Agent, and source/audit controls.

It is an engineering research artifact, not an investment recommendation. Source, document, fact, formula, and evidence linkage lives in `{_data_linkage_path(state)}`.

Chinese easy-reading financial report: `{state.get('financial_easy_reading_report_path') or state['run_dir'] + '/financial_easy_reading_report.md'}`

Official report evidence report: `{_official_report_evidence_report_path(state)}`

## Financial Readout

{_report_at_a_glance(state, audit_status=audit_status)}

## Financial Quality Questions

{_financial_quality_questions_summary(state, metrics)}

## Annual Financial History

{_annual_facts_table(state)}

## Recent Quarterly Trend

{_quarterly_facts_table(state)}

## Official Operating KPIs

{_operating_kpi_main_summary(operating_kpis) if operating_kpis else "- No operating KPI extraction available yet."}

## Financial Metrics

{_metric_summary(metrics)}

## Valuation Metrics

These price-dependent metrics are produced by the Valuation Agent, not the Financial Metrics Agent.

{_metric_summary(valuation_metrics)}

## Material Event Scan

{_material_event_summary(state.get('material_event_scan', {}))}

## Financial Report Pack

{_report_pack_summary(state.get('financial_report_pack', {}), state.get('financial_report_pack_path'))}

## Market Data / Yield Inputs

{_valuation_input_summary(state.get('market_inputs', {}))}

## Extraction And Verification

- Extracted facts: {len(state.get('extracted_facts', []))}
- Raw facts before deduplication: {len(state.get('raw_extracted_facts', []))}
- Extraction method: {state.get('extraction_summary', {}).get('method', 'not run')}
- Verification records: {len(state.get('verification_results', []))}
- Policy: SEC/regulator filings are the financial-report source of record; company IR may cross-validate; third-party mirrors are not allowed for financial extraction.

{_verification_summary(state.get('verification_results', []))}

## Cross-Validation Status

{_ir_cross_validation_summary(state.get('ir_cross_validation', {}))}

## Open Financial Issues

{_bullet_list(_open_issue_lines(state))}

## Data Linkage

Detailed financial fact IDs, formulas, source documents, cross-validation records, and audit events are in `{_data_linkage_path(state)}`.
"""


def build_business_model_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}

    return f"""# Business Model / Moat Report: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## Scope

This report is produced by the Business Model Report Agent. It focuses on how the company makes money, unit-economics proxies, moat hypotheses, anti-moat risks, customer/public-voice evidence, and source-quality limits.

It is separate from the Financial Results Report at `{_financial_results_report_path(state)}`. Exact source snippets and evidence linkage are in `{_data_linkage_path(state)}`.

## Right Business Model Read

- Current read: {_right_business_model_line(state)}
- Audit status: {audit_status}

## Official Report Evidence

{_business_model_memo_summary(state.get('business_model_findings', {}))}

## External Moat Validation

{_external_moat_memo_summary(state.get('external_moat_findings', {}))}

## Customer And Public Voice Evidence

{_public_voice_memo_summary(state.get('public_voice_findings', {}))}

{_customer_happiness_memo_summary(state.get('customer_happiness_findings', {}))}

## Executive / Interview Evidence

{_executive_transcript_memo_summary(state.get('executive_transcript_findings', {}))}

## Business-Model Open Issues

{_bullet_list(_business_model_open_issue_lines(state))}

## Data Linkage

Detailed official-report dossier fields, evidence cards, operating KPIs, public-voice items, transcript evidence, and audit events are in `{_data_linkage_path(state)}`.
"""


def build_right_people_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}

    return f"""# Right People / Management Quality Report: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## Scope

This report is produced by the Right People / Management Quality Agent. It focuses on governance/control, incentive alignment, capital allocation, management communication, execution track record, and integrity/governance red flags.

It is separate from the Financial Results Report at `{_financial_results_report_path(state)}` and the Business Model Report at `{_business_model_report_path(state)}`. Exact source snippets and evidence linkage are in `{_data_linkage_path(state)}`.

## Right People Read

- Current read: {_right_people_line(state)}
- Audit status: {audit_status}

## Evidence Framework

{_right_people_framework_summary(state.get('leadership_findings', {}))}

## Right People Decision

{_right_people_decision_summary(state.get('leadership_findings', {}))}

## Management Quality Evidence

{_right_people_memo_summary(state.get('leadership_findings', {}))}

## Source Controls

- Official filings and official financial reports are the source of record for governance facts, SBC, dilution, cash use, and financial outcomes.
- Earnings calls and executive interviews are used only for management commentary, priorities, and consistency checks.
- V1 does not produce a buy/sell conclusion and does not infer personal integrity beyond source-backed evidence.

## Data Linkage

Detailed source, document, metric, transcript, red-flag, and audit-event linkage is in `{_data_linkage_path(state)}`.
"""


def build_right_people_chinese_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}

    return f"""# 正确的人 / 管理层质量报告：{company.get('legal_name', state['company_query'])}

生成时间：{utc_now_iso()}  
运行编号：`{state['run_id']}` | 市场：`{state['market']}` | 图后端：`{state.get('graph_backend', 'unknown')}`

## 范围

这份报告由“正确的人 / 管理层质量”模块生成。它关注的是治理与控制权、激励一致性、资本配置、管理层沟通、执行记录，以及诚信 / 治理红旗。

它和财务结果报告 `{_financial_results_report_path(state)}`、商业模式报告 `{_business_model_report_path(state)}` 分开。详细来源、指标、文字稿、红旗和审计线索放在 `{_data_linkage_path(state)}`。

## 正确的人当前判断

- 当前判断：{_right_people_line_zh(state)}
- 审计状态：{_zh_text(audit_status)}

## 证据分类框架

{_right_people_chinese_framework_summary(state.get('leadership_findings', {}))}

## 正确的人决策

{_right_people_chinese_decision_summary(state.get('leadership_findings', {}))}

## 关键证据摘录

{_right_people_chinese_evidence_dossier(state.get('leadership_findings', {}))}

## 管理层质量证据

{_right_people_chinese_memo_summary(state.get('leadership_findings', {}))}

## 来源控制

- 官方申报文件和官方财务报告是治理事实、股权激励费用、稀释、现金使用和财务结果的主记录来源。
- 业绩电话会和高管访谈只用于管理层评论、优先级、沟通质量和一致性检查。
- V1 不输出买卖建议，也不会在没有证据的情况下判断个人品格或诚信。

## 数据链接

详细来源、文件、指标、文字稿、红旗和审计事件链接在 `{_data_linkage_path(state)}`。
"""


def _business_model_open_issue_lines(state: ResearchState) -> list[str]:
    analysis = (state.get("business_model_findings") or {}).get("official_report_analysis") or {}
    lines = []
    missing = analysis.get("missing_evidence") or []
    lines.extend(str(item) for item in missing[:6])
    conclusion_limit = analysis.get("conclusion_limit")
    if conclusion_limit:
        lines.append(str(conclusion_limit))
    external = state.get("external_moat_findings") or {}
    if external.get("status") == "source_plan_ready_pending_collection":
        lines.append("External moat-validation sources are planned but not yet fully collected.")
    customer = state.get("customer_happiness_findings") or {}
    if customer.get("status"):
        lines.append(
            "Customer-happiness evidence is public-source lead evidence and needs stronger triangulation before final moat judgment."
        )
    if not lines:
        lines.append("No business-model open issues recorded yet.")
    return lines


def build_final_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}
    metrics = state.get("metrics", [])
    valuation_metrics = _valuation_metrics_for_state(state)

    return f"""# Stock Research Run: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## V1 Scope

This run uses the current V1 pipeline. The main report is organized as an investment-readout memo. Dedicated financial-results, official-report-evidence, business-model, and right-people reports are also generated at `{_financial_results_report_path(state)}`, `{_official_report_evidence_report_path(state)}`, `{_business_model_report_path(state)}`, and `{_right_people_report_path(state)}`. Detailed source, document, fact, formula, and evidence linkage is split into `{_data_linkage_path(state)}`.

This report is an engineering research artifact, not an investment recommendation.

## At A Glance

{_report_at_a_glance(state, audit_status=audit_status)}

## Key Takeaways

{_key_takeaways(state)}

## Right Business / People / Price Checklist

- Right business model / 正确的商业模式: {_right_business_model_line(state)}
- Right people / 正确的人和组织: {_right_people_line(state)}
- Right price / 正确的价格: {_right_price_line(state)}

## Business Model / Moat Evidence

{_business_model_memo_summary(state.get('business_model_findings', {}))}

## Financial Snapshot

### Financial Quality Questions

{_financial_quality_questions_summary(state, metrics)}

### Annual Financial History

{_annual_facts_table(state)}

### Recent Quarterly Trend

{_quarterly_facts_table(state)}

### Financial Metrics

{_metric_summary(metrics)}

### Valuation Metrics

These price-dependent metrics are produced by the Valuation Agent.

{_metric_summary(valuation_metrics)}

### Valuation Inputs

{_valuation_input_summary(state.get('market_inputs', {}))}

## Alternative Data Signals

{_alternative_data_summary(state.get('alternative_data_findings', {}))}

## External Moat Validation Sources

{_external_moat_memo_summary(state.get('external_moat_findings', {}))}

## Public Voice / Forum Evidence

{_public_voice_memo_summary(state.get('public_voice_findings', {}))}

## Customer Happiness Evidence

{_customer_happiness_memo_summary(state.get('customer_happiness_findings', {}))}

## Leadership / People Evidence

{_right_people_memo_summary(state.get('leadership_findings', {}))}

## Executive Video Transcript Evidence

{_executive_transcript_memo_summary(state.get('executive_transcript_findings', {}))}

## Research Controls

{_research_controls_summary(state, audit_status=audit_status)}

### Errors / Fallbacks

{_bullet_list([error.get('error', str(error)) for error in state.get('errors', [])])}

### Open Issues / Notes

{_bullet_list(_open_issue_lines(state))}

## Data Linkage

Full source, document, fact, formula, cross-validation, public-voice, agent, and audit-event linkage is in `{_data_linkage_path(state)}`.
"""


def build_data_linkage_report(state: ResearchState, *, audit_status: str) -> str:
    company = state.get("canonical_company") or {}
    source_candidates = state.get("source_candidates", [])
    documents = state.get("documents", [])
    metrics = state.get("metrics", [])
    valuation_metrics = _valuation_metrics_for_state(state)

    return f"""# Data Linkage: {company.get('legal_name', state['company_query'])}

## Run Metadata

- Run ID: `{state['run_id']}`
- Generated at: {utc_now_iso()}
- Main report: `{state.get('final_report_path') or f"{state['run_dir']}/final_report.md"}`
- Financial results report: `{_financial_results_report_path(state)}`
- Official report evidence report: `{_official_report_evidence_report_path(state)}`
- Business model report: `{_business_model_report_path(state)}`
- Right people report: `{_right_people_report_path(state)}`
- Chinese right people report: `{_right_people_chinese_report_path(state)}`
- Video manifest: `{_video_manifest_path(state)}`
- Company query: `{state['company_query']}`
- Market: `{state['market']}`
- Requested history: `{state['requested_years']}`
- Graph backend: `{state.get('graph_backend', 'unknown')}`
- Audit status: {audit_status}

## Purpose

This appendix preserves the audit trail behind the main research report. It is intentionally more mechanical: source hierarchy, document cache paths, selected fact IDs, extraction tags or methods, formula inputs, verification records, and qualitative-evidence links.

## Source Inventory

{_source_inventory_table(source_candidates)}

## Document Inventory

{_document_inventory(documents)}

## Document Linkage Table

{_document_linkage_table(documents)}

## Financial Extraction Summary

- Extracted facts: {len(state.get('extracted_facts', []))}
- Raw facts before deduplication: {len(state.get('raw_extracted_facts', []))}
- Method: {state.get('extraction_summary', {}).get('method', 'not run')}

## Annual Key Fact Source Lineage

{_annual_source_lineage_table(state)}

## Selected Financial Fact Linkage

{_financial_fact_lineage_table(state.get('extracted_facts', []))}

## Formula / Metric Linkage

{_metric_linkage_table(metrics + valuation_metrics)}

## IR PDF Cross-Validation Linkage

{_ir_cross_validation_summary(state.get('ir_cross_validation', {}))}

## Verification Records

{_verification_records_table(state.get('verification_results', []))}

## Market Data And Valuation Input Linkage

{_valuation_input_summary(state.get('market_inputs', {}))}

## Official Report Dossier Linkage

{_official_report_dossier_linkage_table(state)}

## Official Management Framing Linkage

{_management_framing_linkage_table(state)}

## Official Deep Evidence Card Linkage

{_official_evidence_cards_linkage_table(state)}

## Business Model Answer Linkage

{_business_model_answer_linkage_table(state)}

## Business Model Subagent Cluster Linkage

{_business_model_subagent_cluster_linkage_table(state)}

## Official Operating KPI Linkage

{_operating_kpi_linkage_table(state)}

## Alternative Data Linkage

{_alternative_data_linkage_table(state.get('alternative_data_findings', {}))}

## Public Voice Evidence Linkage

{_public_voice_linkage_table(state.get('public_voice_findings', {}))}

## Video Manifest Linkage

{_video_manifest_linkage(state)}

## Official Event Business-Model Question Pack Linkage

{_official_event_question_pack_linkage(state.get('official_event_transcript_findings', {}))}

## Executive Transcript Evidence Linkage

{_executive_transcript_linkage_table(state.get('executive_transcript_findings', {}))}

## Customer Happiness Linkage

{_customer_happiness_linkage_table(state.get('customer_happiness_findings', {}))}

## Right People Linkage

{_right_people_linkage_table(state.get('leadership_findings', {}))}

## Agent Report Linkage

{_agent_reports_table(state.get('agent_reports', []))}

## Audit Event Log

{_audit_events_table(state.get('audit_events', []))}

## Errors / Fallbacks

{_bullet_list([error.get('error', str(error)) for error in state.get('errors', [])])}
"""
