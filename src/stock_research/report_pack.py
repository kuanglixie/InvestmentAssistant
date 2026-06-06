from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.metrics.v1 import annual_fact_rows, quarterly_fact_rows
from stock_research.state import ResearchState, utc_now_iso


FINANCIAL_REPORT_PACK_SCHEMA_VERSION = "financial_report_pack_v1"


def build_financial_report_pack(state: ResearchState) -> dict[str, Any]:
    metrics = state.get("metrics", [])
    diagnostic_findings = state.get("diagnostic_findings") or {}
    material_event_scan = state.get("material_event_scan") or {}
    extraction_summary = state.get("extraction_summary") or {}
    annual_facts = annual_fact_rows(state.get("extracted_facts", []))
    quarterly_facts = quarterly_fact_rows(state.get("extracted_facts", []))
    human_review_flags = _human_review_flags(state)
    financial_health = _financial_health(
        annual_facts=annual_facts,
        quarterly_facts=quarterly_facts,
        diagnostic_findings=diagnostic_findings,
        material_event_scan=material_event_scan,
        human_review_flags=human_review_flags,
    )
    fact_quality_gate = extraction_summary.get("fact_quality_gate") or {}
    pack = {
        "schema_version": FINANCIAL_REPORT_PACK_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "run_id": state.get("run_id"),
        "company": state.get("canonical_company") or {},
        "market": state.get("market"),
        "source_inventory": _source_inventory(state),
        "document_inventory": _document_inventory(state.get("documents", [])),
        "annual_report_baseline": _annual_report_baseline(state),
        "fact_quality_gate": fact_quality_gate,
        "fact_extraction_summary": _fact_extraction_summary(extraction_summary),
        "fact_ledger": _fact_ledger(state.get("extracted_facts", [])),
        "canonical_metric_map": extraction_summary.get("canonical_metric_map") or {},
        "annual_statement_coverage": extraction_summary.get("annual_statement_coverage") or [],
        "annual_facts": annual_facts,
        "quarterly_facts": quarterly_facts,
        "financial_metrics": metrics,
        "latest_interim_trend": _metric_by_id(metrics, "latest_interim_trend_v1"),
        "financial_health": financial_health,
        "financial_health_status": financial_health.get("status"),
        "financial_health_score": financial_health.get("score"),
        "diagnostic_findings": diagnostic_findings,
        "layer1_question_pack_summary": (state.get("layer1_question_pack") or {}).get("summary", {}),
        "layer1_question_pack_path": state.get("layer1_question_pack_path"),
        "evidence_communication_pack_summary": (state.get("evidence_communication_pack") or {}).get("summary", {}),
        "evidence_communication_pack_path": state.get("evidence_communication_pack_path"),
        "feedback_loop_pack_summary": (state.get("feedback_loop_pack") or {}).get("summary", {}),
        "feedback_loop_pack_path": state.get("feedback_loop_pack_path"),
        "financial_investigation_notes": state.get("financial_investigation_notes")
        or {
            "status": "not_run",
            "notes": [],
            "instruction": "Use docs/financial-evidence-investigation-skill-v1.md before report writing when abnormal diagnostics need source-level explanation.",
        },
        "material_event_scan": material_event_scan,
        "verification_results": state.get("verification_results", []),
        "ir_cross_validation": state.get("ir_cross_validation", {}),
        "missing_facts": _missing_facts(extraction_summary, metrics),
        "human_review_flags": human_review_flags,
        "report_controls": {
            "source_policy": "Official regulator/exchange filings and company investor-relations documents only for financial facts.",
            "formula_policy": "Metrics come from deterministic Python formula code, not the report-writing layer.",
            "interpretation_policy": "The writing layer may summarize this pack but must not recalculate numbers or invent facts.",
            "exclusion_policy": (
                "Financial Evidence excludes market-price-dependent valuation metrics, valuation commentary, "
                "and third-party financial databases. Those belong to Valuation / Right Price or lead-generation layers."
            ),
        },
    }
    return pack


def _fact_extraction_summary(extraction_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": extraction_summary.get("method"),
        "methods_used": extraction_summary.get("methods_used", []),
        "raw_fact_count": extraction_summary.get("raw_fact_count", 0),
        "selected_fact_count": extraction_summary.get("selected_fact_count", 0),
        "counts_by_metric": extraction_summary.get("counts_by_metric", {}),
        "counts_by_period": extraction_summary.get("counts_by_period", {}),
        "coverage": extraction_summary.get("coverage", {}),
        "hard_financial_worksheet_coverage": extraction_summary.get(
            "hard_financial_worksheet_coverage",
            [],
        ),
        "review_flags": extraction_summary.get("review_flags", []),
        "disclosure_gap_registry": extraction_summary.get("disclosure_gap_registry", []),
        "extraction_errors": extraction_summary.get("extraction_errors", []),
        "notes": extraction_summary.get("notes", []),
    }


def _fact_ledger(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ledger = []
    for fact in sorted(
        facts,
        key=lambda item: (
            str(item.get("period_year") or ""),
            str(item.get("period_label") or ""),
            str(item.get("canonical_metric") or item.get("metric") or ""),
            str(item.get("source_accession_number") or item.get("accession_number") or ""),
        ),
    ):
        ledger.append(
            {
                "fact_id": fact.get("fact_id"),
                "canonical_metric": fact.get("canonical_metric") or fact.get("metric"),
                "label": fact.get("label"),
                "value": fact.get("value"),
                "currency": fact.get("currency"),
                "unit": fact.get("unit"),
                "value_scale": fact.get("value_scale", 1),
                "display_unit": fact.get("display_unit"),
                "period_label": fact.get("period_label"),
                "period_type": fact.get("period_type"),
                "period_year": fact.get("period_year"),
                "start_date": fact.get("start_date"),
                "end_date": fact.get("end_date"),
                "instant": fact.get("instant"),
                "metric_family": fact.get("metric_family"),
                "financial_statement": fact.get("financial_statement"),
                "source_table": fact.get("source_table"),
                "source_document_type": fact.get("source_document_type") or fact.get("document_type"),
                "source_document": fact.get("source_document") or fact.get("downloaded_file"),
                "accession_number": fact.get("source_accession_number") or fact.get("accession_number"),
                "filing_date": fact.get("filing_date"),
                "report_date": fact.get("report_date"),
                "local_path": fact.get("local_path"),
                "xbrl_tag": fact.get("xbrl_tag"),
                "context_ref": fact.get("context_ref"),
                "confidence": fact.get("confidence"),
                "confidence_score": fact.get("confidence_score"),
                "extraction_method": fact.get("extraction_method"),
                "selection_policy": fact.get("selection_policy"),
                "formula": fact.get("formula"),
                "source_fact_ids": fact.get("source_fact_ids"),
                "adjustment_note": fact.get("adjustment_note"),
            }
        )
    return ledger


def _financial_health(
    *,
    annual_facts: list[dict[str, Any]],
    quarterly_facts: list[dict[str, Any]],
    diagnostic_findings: dict[str, Any],
    material_event_scan: dict[str, Any],
    human_review_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = sorted([row for row in annual_facts if row.get("year") is not None], key=lambda row: row.get("year", 0))
    if len(rows) < 2:
        return {
            "status": "unknown",
            "label": "证据不足",
            "score": None,
            "trend": "unknown",
            "evidence_strength": "low",
            "main_positive_evidence": "年度事实不足。",
            "main_negative_evidence": "缺少至少两个年度的可比收入、利润和现金流事实。",
            "next_verification_point": "先补齐年报 / 20-F / 10-K 的年度事实。",
            "question_status": _question_status_summary(diagnostic_findings),
        }
    latest = rows[-1]
    prior = rows[-2]
    revenue_growth = _growth(latest, prior, "revenue")
    operating_income_growth = _growth(latest, prior, "operating_income")
    net_income_growth = _growth(latest, prior, "net_income")
    operating_margin = _margin(latest, "operating_income")
    cash_conversion = _safe_divide(latest.get("operating_cash_flow"), latest.get("net_income"))
    current_ratio = _safe_divide(latest.get("current_assets"), latest.get("current_liabilities"))
    liabilities_to_assets = _safe_divide(latest.get("total_liabilities"), latest.get("total_assets"))
    warnings = [str(item.get("warning")) for item in diagnostic_findings.get("warning_flags", []) if item.get("warning")]
    high_priority_events = int(material_event_scan.get("high_priority_event_count") or 0)
    material_conflicts = [
        flag
        for flag in human_review_flags
        if flag.get("source") == "financial_verification" and flag.get("severity") == "high"
    ]

    score = 0.0
    if revenue_growth is not None:
        score += 2.0 if revenue_growth > 0 else 0.5 if revenue_growth > -0.05 else 0.0
    if operating_margin is not None:
        score += 2.0 if operating_margin > 0.10 else 1.0 if operating_margin > 0 else 0.0
    if cash_conversion is not None:
        score += 2.0 if cash_conversion >= 1.0 else 1.0 if cash_conversion >= 0.8 else 0.0
    if current_ratio is not None:
        score += 1.5 if current_ratio >= 1.5 else 0.7 if current_ratio >= 1.0 else 0.0
    if liabilities_to_assets is not None:
        score += 1.0 if liabilities_to_assets <= 0.55 else 0.4 if liabilities_to_assets <= 0.70 else 0.0
    core_warning_count = sum(1 for warning in warnings if _is_core_health_warning(warning))
    score -= min(2.0, 0.5 * core_warning_count)
    if high_priority_events:
        score -= 2.0
    if material_conflicts:
        score -= 0.5
    score = round(max(0.0, min(10.0, score)), 1)

    if high_priority_events:
        status = "deteriorating"
        trend = "deteriorating"
    elif revenue_growth is not None and revenue_growth < 0 and (operating_income_growth or 0) < 0:
        status = "deteriorating"
        trend = "deteriorating"
    elif (
        revenue_growth is not None
        and revenue_growth > 0
        and (operating_income_growth or 0) > 0
        and (net_income_growth or 0) > 0
        and cash_conversion is not None
        and cash_conversion >= 1
        and core_warning_count == 0
    ):
        status = "improving"
        trend = "improving"
    elif (
        revenue_growth is not None
        and revenue_growth > 0
        and ((operating_income_growth or 0) < 0 or (net_income_growth or 0) < 0 or core_warning_count)
    ):
        status = "mixed"
        trend = "mixed"
    else:
        status = "stable"
        trend = "stable"

    evidence_strength = "medium"
    if not quarterly_facts:
        evidence_strength = "low"
    elif not human_review_flags and material_event_scan.get("scanned_document_count", 0) > 0:
        evidence_strength = "high"

    return {
        "status": status,
        "label": _financial_health_label_zh(status, score),
        "score": score,
        "trend": trend,
        "evidence_strength": evidence_strength,
        "main_positive_evidence": (
            f"经营现金流 / 净利润 {_ratio(cash_conversion)}，广义现金与短投 {_money(_broad_liquidity(latest))}，"
            f"流动比率 {_ratio(current_ratio)}。"
        ),
        "main_negative_evidence": _main_negative_evidence_zh(
            warnings=warnings,
            operating_income_growth=operating_income_growth,
            net_income_growth=net_income_growth,
            material_conflict_count=len(material_conflicts),
            high_priority_event_count=high_priority_events,
        ),
        "next_verification_point": _next_verification_point_zh(warnings),
        "question_status": _question_status_summary(diagnostic_findings),
        "latest_annual_year": latest.get("year"),
        "latest_quarter_end": (quarterly_facts[-1] or {}).get("period_end") if quarterly_facts else None,
        "key_metrics": {
            "revenue_growth_yoy": revenue_growth,
            "operating_income_growth_yoy": operating_income_growth,
            "net_income_growth_yoy": net_income_growth,
            "operating_margin": operating_margin,
            "cash_conversion": cash_conversion,
            "current_ratio": current_ratio,
            "liabilities_to_assets": liabilities_to_assets,
        },
    }


def _financial_health_label_zh(status: str, score: float | None) -> str:
    if status == "improving":
        return "改善中"
    if status == "stable":
        return "稳定"
    if status == "deteriorating":
        return "恶化中"
    if status == "mixed":
        if score is not None and score >= 6.5:
            return "质量较高，但处于验证期"
        return "混合信号，需要验证"
    return "证据不足"


def _question_status_summary(diagnostic_findings: dict[str, Any]) -> dict[str, Any]:
    summary = diagnostic_findings.get("summary") or {}
    return {
        "answered": summary.get("answered", 0),
        "partial": summary.get("partial", 0),
        "missing": summary.get("missing", 0),
        "questions_total": summary.get("questions_total", 0),
        "warning_flags": summary.get("warning_flags", 0),
    }


def _is_core_health_warning(warning: str) -> bool:
    lower = warning.lower()
    return any(
        term in lower
        for term in [
            "incremental operating margin",
            "incremental fcf margin",
            "working-capital",
            "restricted cash",
            "investment income/loss",
        ]
    )


def _main_negative_evidence_zh(
    *,
    warnings: list[str],
    operating_income_growth: float | None,
    net_income_growth: float | None,
    material_conflict_count: int,
    high_priority_event_count: int,
) -> str:
    if high_priority_event_count:
        return f"重大事项扫描发现 {high_priority_event_count} 个高优先级事件。"
    if warnings:
        return _warning_zh(warnings[0])
    if operating_income_growth is not None and operating_income_growth < 0:
        return f"经营利润同比 {_percent(operating_income_growth)}，新增收入没有同步带来经营利润。"
    if net_income_growth is not None and net_income_growth < 0:
        return f"净利润同比 {_percent(net_income_growth)}，需要拆经营利润以下项目。"
    if material_conflict_count:
        return f"存在 {material_conflict_count} 个官方事实冲突需要人工复核。"
    return "暂未发现结构化重大反证，但仍需复核附注和重大事项。"


def _next_verification_point_zh(warnings: list[str]) -> str:
    joined = " ".join(warnings).lower()
    if "incremental operating margin" in joined:
        return "下个季度先看增量经营利润率是否从负转正，并拆费用率、商家支持和供应链投入。"
    if "working-capital" in joined:
        return "下个季度先拆营运资本，确认现金流是否依赖经营负债扩张。"
    if "restricted cash" in joined:
        return "优先回查受限现金、VIE 和资金可转移性。"
    if "investment income/loss" in joined:
        return "优先拆经营利润以下项目、投资收益和非 GAAP 调整。"
    return "下个季度先看收入增速、经营利润率、经营现金流和非 GAAP 调整是否同向改善。"


def _source_inventory(state: ResearchState) -> dict[str, Any]:
    candidates = state.get("source_candidates", [])
    approved = state.get("approved_sources", [])
    return {
        "candidate_count": len(candidates),
        "approved_count": len(approved),
        "trust_tier_counts": dict(Counter(str(source.get("trust_tier", "unknown")) for source in candidates)),
        "approved_sources": approved,
    }


def _document_inventory(documents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "document_count": len(documents),
        "document_type_counts": dict(
            Counter(str(document.get("document_type", "unknown")).split(":", 1)[0] for document in documents)
        ),
        "research_category_counts": dict(
            Counter(str(document.get("research_category", "uncategorized")) for document in documents)
        ),
        "latest_annual_report": _latest_document(
            documents,
            prefixes=("10-K", "20-F", "annual_report_pdf"),
        ),
        "latest_interim_report": _latest_document(
            documents,
            prefixes=("10-Q", "6-K", "interim_report_pdf"),
        ),
    }


def _annual_report_baseline(state: ResearchState) -> dict[str, Any]:
    documents = state.get("documents", [])
    latest_annual = _latest_document(
        documents,
        prefixes=("10-K", "20-F", "annual_report_pdf"),
    )
    diagnostics = state.get("diagnostic_findings") or {}
    answered_questions = [
        {
            "question_id": question.get("question_id"),
            "status": question.get("status"),
            "priority": question.get("priority"),
            "current_answer": question.get("current_answer"),
            "warning_flags": question.get("warning_flags", []),
            "missing": question.get("missing", []),
        }
        for question in diagnostics.get("questions", [])
    ]
    return {
        "status": "baseline_available" if latest_annual else "missing_annual_report",
        "latest_annual_report": latest_annual,
        "baseline_rule": "Annual report / 10-K / 20-F is the baseline. Interim filings can confirm or change that baseline, but cannot replace it.",
        "diagnostic_questions": answered_questions,
    }


def _missing_facts(extraction_summary: dict[str, Any], metrics: list[dict[str, Any]]) -> dict[str, Any]:
    coverage = extraction_summary.get("coverage") or {}
    metric_missing = {}
    for metric in metrics:
        missing = []
        for row in metric.get("annual_results", []):
            missing.extend(row.get("missing", []))
        if metric.get("missing"):
            missing.extend(metric.get("missing", []))
        if missing:
            metric_missing[str(metric.get("formula_id"))] = sorted({str(item) for item in missing})
    return {
        "priority_a": (coverage.get("priority_a") or {}).get("missing", []),
        "priority_b": (coverage.get("priority_b") or {}).get("missing", []),
        "by_metric_family": metric_missing,
    }


def _human_review_flags(state: ResearchState) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for flag in (state.get("extraction_summary") or {}).get("review_flags", []):
        flags.append({"source": "financial_extraction", **flag})
    for result in state.get("verification_results", []):
        if result.get("status") == "material_conflict":
            flags.append(
                {
                    "source": "financial_verification",
                    "flag_id": "official_fact_material_conflict",
                    "severity": "high",
                    "metric": result.get("metric"),
                    "period": result.get("end_date") or result.get("instant"),
                    "mismatch_pct": result.get("mismatch_pct"),
                }
            )
    for metric in state.get("metrics", []):
        formula_id = metric.get("formula_id")
        for row in metric.get("annual_results", []):
            if row.get("review_required") or row.get("limitations") or row.get("assumption") or row.get("interpretation_limit"):
                flags.append(
                    {
                        "source": "financial_metrics",
                        "flag_id": "metric_review_required",
                        "severity": "medium",
                        "formula_id": formula_id,
                        "year": row.get("year"),
                        "assumption": row.get("assumption"),
                        "limitations": row.get("limitations", []),
                        "interpretation_limit": row.get("interpretation_limit"),
                    }
                )
    for event in (state.get("material_event_scan") or {}).get("events", []):
        if event.get("severity") == "high":
            flags.append(
                {
                    "source": "material_event_scan",
                    "flag_id": "high_priority_material_event",
                    "severity": "high",
                    "event_type": event.get("event_type"),
                    "document_id": event.get("document_id"),
                    "filing_date": event.get("filing_date"),
                }
            )
    return _dedupe_flags(flags)


def _dedupe_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for flag in flags:
        key = (
            flag.get("source"),
            flag.get("flag_id"),
            flag.get("severity"),
            flag.get("metric"),
            flag.get("formula_id"),
            flag.get("event_type"),
            flag.get("period"),
            flag.get("year"),
            flag.get("document_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(flag)
    return output


def _growth(row: dict[str, Any] | None, previous: dict[str, Any] | None, key: str) -> float | None:
    current_value = _float_value((row or {}).get(key))
    previous_value = _float_value((previous or {}).get(key))
    if current_value is None or previous_value in (None, 0):
        return None
    return (current_value - previous_value) / abs(previous_value)


def _margin(row: dict[str, Any] | None, numerator_key: str) -> float | None:
    return _safe_divide((row or {}).get(numerator_key), (row or {}).get("revenue"))


def _safe_divide(numerator: Any, denominator: Any) -> float | None:
    num = _float_value(numerator)
    den = _float_value(denominator)
    if num is None or den in (None, 0):
        return None
    return num / den


def _broad_liquidity(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    values = [
        value
        for value in [
            _float_value(row.get("cash")),
            _float_value(row.get("restricted_cash")),
            _float_value(row.get("short_term_investments")),
        ]
        if value is not None
    ]
    return sum(values) if values else None


def _float_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    numeric = _float_value(value)
    if numeric is None:
        return "缺失"
    return f"RMB {numeric / 1_000_000_000:.1f}B"


def _ratio(value: Any) -> str:
    numeric = _float_value(value)
    if numeric is None:
        return "缺失"
    return f"{numeric:.2f}x"


def _percent(value: Any) -> str:
    numeric = _float_value(value)
    if numeric is None:
        return "缺失"
    return f"{numeric * 100:.1f}%"


def _warning_zh(warning: str) -> str:
    mapping = {
        "Incremental operating margin is negative.": "增量经营利润率为负，新增收入没有带来新增经营利润。",
        "Incremental FCF margin is negative.": "增量自由现金流率为负，新增收入没有带来新增自由现金流。",
        "Incremental operating margin is below latest operating margin.": "增量经营利润率低于当前经营利润率，边际盈利能力弱于存量业务。",
        "Working-capital source liabilities added more than 5% of revenue to cash-flow tailwind.": "营运资本中的现金来源负债贡献超过收入的 5%，现金流有营运资本顺风。",
        "Restricted cash exceeds 25% of cash.": "受限现金占现金比例超过 25%，账面现金不能全部视为自由现金。",
        "Investment income/loss is more than 20% of pretax income.": "投资收益/损失占税前利润比例超过 20%，净利润受非经营项目影响较大。",
    }
    return mapping.get(warning, warning)


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


def _latest_document(documents: list[dict[str, Any]], *, prefixes: tuple[str, ...]) -> dict[str, Any] | None:
    normalized_prefixes = tuple(prefix.upper() for prefix in prefixes)
    matches = []
    for document in documents:
        document_type = str(document.get("document_type", "")).upper()
        form = str(document.get("form", "")).upper()
        if document_type.startswith(normalized_prefixes) or form.startswith(normalized_prefixes):
            matches.append(document)
    if not matches:
        return None
    latest = sorted(matches, key=lambda document: document.get("filing_date") or "")[-1]
    return {
        "document_id": latest.get("document_id"),
        "document_type": latest.get("document_type"),
        "filing_date": latest.get("filing_date"),
        "report_date": latest.get("report_date"),
        "local_path": latest.get("local_path"),
        "source_url": latest.get("source_url"),
        "research_category": latest.get("research_category"),
    }
