from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.metrics.v1 import annual_fact_rows, annual_fact_source_rows, quarterly_fact_rows
from stock_research.state import ResearchState, utc_now_iso


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
        annual_results = [
            result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
        ]
        if not annual_results:
            lines.append(f"- {formula_id}: {metric.get('status')}")
            continue
        latest = sorted(annual_results, key=lambda result: result.get("year", 0))[-1]
        value = latest.get("value")
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
        lines.append(f"- {formula_id}: latest {latest.get('year')} = {value_text}{suffix}")
    return "\n".join(lines) if lines else "- No metrics calculated yet."


def _ratio_should_be_percent(formula_id: str) -> bool:
    return any(marker in formula_id for marker in ["roic", "yield", "margin", "intensity", "risk", "burden"])


def _financial_quality_questions_summary(metrics: list[dict[str, Any]]) -> str:
    metric = _metric_by_id(metrics, "financial_quality_questions_v1")
    questions = sorted(metric.get("questions", []) if metric else [], key=lambda question: question.get("rank", 999))
    if not questions:
        return "- No financial quality question layer calculated yet."
    lines = [
        "These are the main questions the Financial Metrics Agent is trying to answer, ranked by value-investor usefulness."
    ]
    for question in questions:
        rank = question.get("rank", "")
        title = question.get("question", question.get("question_id", "Question"))
        latest_values = _format_latest_question_values(question.get("latest_values", {}))
        warnings = question.get("warning_flags") or []
        missing = question.get("missing") or []
        lines.extend(
            [
                "",
                f"{rank}. **{title}**",
                f"   Status: {question.get('status')} | Priority: {question.get('priority')}",
                f"   Current read: {question.get('current_answer')}",
                f"   Key metrics: {', '.join(question.get('metrics_used') or [])}",
            ]
        )
        if latest_values:
            lines.append(f"   Latest values: {latest_values}")
        if warnings:
            lines.append(f"   Warning flags: {'; '.join(warnings)}")
        if missing:
            lines.append(f"   Still missing: {', '.join(str(item) for item in missing)}")
        if question.get("interpretation_limit"):
            lines.append(f"   Limit: {question.get('interpretation_limit')}")
    return "\n".join(lines)


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


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
    metrics = state.get("metrics", [])
    if _metric_has_calculated_result(metrics, "true_yield_v1") and _metric_has_calculated_result(
        metrics,
        "free_cash_flow_yield_v1",
    ):
        return (
            "partially evaluated; EV, owner-earnings yield, and FCF yield are calculated from current market data, "
            "while valuation-agent assumptions still require review."
        )
    if _metric_has_calculated_result(metrics, "enterprise_value_v1"):
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


def _data_linkage_path(state: ResearchState) -> str:
    return state.get("data_linkage_report_path") or f"{state['run_dir']}/data_linkage.md"


def _financial_results_report_path(state: ResearchState) -> str:
    return state.get("financial_results_report_path") or f"{state['run_dir']}/financial_results_report.md"


def _business_model_report_path(state: ResearchState) -> str:
    return state.get("business_model_report_path") or f"{state['run_dir']}/business_model_report.md"


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
    latest = _latest_annual_row(state)
    active_merchants = _latest_operating_kpi(state, "active_merchants")
    true_yield = _format_metric_result(_latest_metric_result(metrics, "true_yield_v1"), "true_yield_v1")
    fcf_yield = _format_metric_result(
        _latest_metric_result(metrics, "free_cash_flow_yield_v1"),
        "free_cash_flow_yield_v1",
    )
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
        f"| V1 audit read | {_markdown_cell(audit_status)} |",
    ]
    return "\n".join(lines)


def _key_takeaways(state: ResearchState) -> str:
    metrics = state.get("metrics", [])
    latest = _latest_annual_row(state)
    analysis = (state.get("business_model_findings") or {}).get("official_report_analysis") or {}
    framing = (analysis.get("management_framing_analysis") or {}).get("summary")
    public_voice = state.get("public_voice_findings", {})
    theme_summary = public_voice.get("theme_summary") or {}
    theme_counts = theme_summary.get("counts") or {}
    top_public_themes = sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)[:3]
    true_yield = _format_metric_result(_latest_metric_result(metrics, "true_yield_v1"), "true_yield_v1")
    fcf_yield = _format_metric_result(
        _latest_metric_result(metrics, "free_cash_flow_yield_v1"),
        "free_cash_flow_yield_v1",
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
    metric_parts = [part for part in [f"ROIC {roic}" if roic else "", f"owner earnings yield {true_yield}" if true_yield else "", f"FCF yield {fcf_yield}" if fcf_yield else ""] if part]
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
        "- Policy: Official filings and company IR are source of record; third-party databases are sanity checks only.",
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
    operating_kpis = (
        (state.get("business_model_findings") or {})
        .get("official_report_analysis", {})
        .get("operating_kpi_analysis", {})
    )

    return f"""# Financial Results Report: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## Scope

This report is produced by the Financial Results Report Agent. It focuses on official financial results, extracted operating KPIs, calculated metrics, valuation inputs needed by yield-style metrics, and source/audit controls.

It is an engineering research artifact, not an investment recommendation. Source, document, fact, formula, and evidence linkage lives in `{_data_linkage_path(state)}`.

## Financial Readout

{_report_at_a_glance(state, audit_status=audit_status)}

## Financial Quality Questions

{_financial_quality_questions_summary(metrics)}

## Annual Financial History

{_annual_facts_table(state)}

## Recent Quarterly Trend

{_quarterly_facts_table(state)}

## Official Operating KPIs

{_operating_kpi_main_summary(operating_kpis) if operating_kpis else "- No operating KPI extraction available yet."}

## Calculated Metrics

{_metric_summary(metrics)}

## Market Data / Yield Inputs

{_valuation_input_summary(state.get('market_inputs', {}))}

## Extraction And Verification

- Extracted facts: {len(state.get('extracted_facts', []))}
- Raw facts before deduplication: {len(state.get('raw_extracted_facts', []))}
- Extraction method: {state.get('extraction_summary', {}).get('method', 'not run')}
- Verification records: {len(state.get('verification_results', []))}
- Policy: official filings and company IR are source of record; third-party data can only sanity-check.

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

    return f"""# Stock Research Run: {company.get('legal_name', state['company_query'])}

Generated at: {utc_now_iso()}  
Run ID: `{state['run_id']}` | Market: `{state['market']}` | Graph backend: `{state.get('graph_backend', 'unknown')}`

## V1 Scope

This run uses the current V1 pipeline. The main report is organized as an investment-readout memo. Dedicated financial-results and business-model reports are also generated at `{_financial_results_report_path(state)}` and `{_business_model_report_path(state)}`. Detailed source, document, fact, formula, and evidence linkage is split into `{_data_linkage_path(state)}`.

This report is an engineering research artifact, not an investment recommendation.

## At A Glance

{_report_at_a_glance(state, audit_status=audit_status)}

## Key Takeaways

{_key_takeaways(state)}

## Right Business / People / Price Checklist

- Right business model / 正确的商业模式: {_right_business_model_line(state)}
- Right people / 正确的人和组织: not evaluated yet.
- Right price / 正确的价格: {_right_price_line(state)}

## Business Model / Moat Evidence

{_business_model_memo_summary(state.get('business_model_findings', {}))}

## Financial Snapshot

### Financial Quality Questions

{_financial_quality_questions_summary(metrics)}

### Annual Financial History

{_annual_facts_table(state)}

### Recent Quarterly Trend

{_quarterly_facts_table(state)}

### Metrics

{_metric_summary(metrics)}

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

{_finding_summary(state.get('leadership_findings', {}))}

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

    return f"""# Data Linkage: {company.get('legal_name', state['company_query'])}

## Run Metadata

- Run ID: `{state['run_id']}`
- Generated at: {utc_now_iso()}
- Main report: `{state.get('final_report_path') or f"{state['run_dir']}/final_report.md"}`
- Financial results report: `{_financial_results_report_path(state)}`
- Business model report: `{_business_model_report_path(state)}`
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

{_metric_linkage_table(metrics)}

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

## Agent Report Linkage

{_agent_reports_table(state.get('agent_reports', []))}

## Audit Event Log

{_audit_events_table(state.get('audit_events', []))}

## Errors / Fallbacks

{_bullet_list([error.get('error', str(error)) for error in state.get('errors', [])])}
"""
