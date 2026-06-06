from __future__ import annotations

from typing import Any

from stock_research.state import ResearchState, utc_now_iso


LAYER1_QUESTION_PACK_SCHEMA_VERSION = "layer1_question_pack_v1"


def build_layer1_question_pack(state: ResearchState) -> dict[str, Any]:
    financial_pack = state.get("financial_report_pack") or {}
    metrics = _metrics_by_id(financial_pack)
    annual_rows = _annual_rows(financial_pack)
    quarterly_rows = _quarterly_rows(financial_pack)
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}
    diagnostic_findings = financial_pack.get("diagnostic_findings") or state.get("diagnostic_findings") or {}
    disclosure_gaps = (financial_pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry") or []

    standard_answers = _standard_question_answers(latest, prior, latest_quarter, metrics)
    research_questions = _research_questions(latest, prior, latest_quarter, metrics, disclosure_gaps)
    numeric_anomalies = _numeric_anomalies(latest, prior, latest_quarter, metrics)
    extractor_handoffs = _extractor_handoffs(disclosure_gaps, research_questions, numeric_anomalies)

    pack = {
        "schema_version": LAYER1_QUESTION_PACK_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "agent_run": {
            "run_id": state.get("run_id"),
            "company_id": ((financial_pack.get("company") or {}).get("company_id") or state.get("company_query")),
            "company_name": ((financial_pack.get("company") or {}).get("legal_name") or state.get("company_query")),
            "source_policy": "financial_numbers_and_diagnostic_rules_only",
            "status": "generated",
        },
        "source_financial_report_pack_path": state.get("financial_report_pack_path"),
        "standard_question_answers": standard_answers,
        "question_answers": standard_answers,
        "research_questions": research_questions,
        "numeric_anomalies": numeric_anomalies,
        "red_flags": _red_flags(diagnostic_findings),
        "hard_data_insights": _hard_data_insights(latest, prior, latest_quarter, metrics),
        "disclosure_gaps": disclosure_gaps,
        "handoff_to_evidence_communication": _evidence_handoffs(research_questions),
        "handoff_to_financial_extractor": extractor_handoffs,
        "summary": {
            "standard_question_count": len(standard_answers),
            "research_question_count": len(research_questions),
            "numeric_anomaly_count": len(numeric_anomalies),
            "disclosure_gap_count": len(disclosure_gaps),
            "financial_extractor_handoff_count": len(extractor_handoffs),
        },
    }
    return pack


def _standard_question_answers(
    latest: dict[str, Any],
    prior: dict[str, Any],
    latest_quarter: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    profit_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    cash_conversion = _latest_annual_metric(metrics, "cash_conversion_ratio_v1") or {}
    balance = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    cap_intensity = _latest_annual_metric(metrics, "capital_intensity_v1") or {}
    sbc = _latest_annual_metric(metrics, "share_based_compensation_burden_v1") or {}
    source_growth = _latest_annual_metric(metrics, "source_of_growth_attribution_v1") or {}
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}

    return [
        _std(
            "S1",
            "有没有增长？",
            "有增长，但最新年度增速明显放缓。",
            [
                _metric_sentence("最新年度收入同比", _pct(_growth(latest.get("revenue"), prior.get("revenue")))),
                _metric_sentence("最新季度收入同比", _pct(latest_quarter.get("revenue_yoy"))),
            ],
            "answered",
            ["Q1", "Q6"],
        ),
        _std(
            "S2",
            "增长来自哪里？",
            "披露口径下，增长来源具有公司特征：在线营销服务及其他与交易服务共同构成收入。",
            [
                _metric_sentence("在线营销服务及其他占最新年度收入", _pct(_safe_div(latest.get("online_marketing_services_revenue"), latest.get("revenue")))),
                _metric_sentence("交易服务占最新年度收入", _pct(_safe_div(latest.get("transaction_services_revenue"), latest.get("revenue")))),
                _metric_sentence("收入组件覆盖率", _pct(source_growth.get("value"))),
            ],
            "partial",
            ["Q6", "Q7"],
        ),
        _std(
            "S3",
            "增长有没有兑现为利润？",
            "最新年度没有充分兑现：收入增长，但经营利润和净利润回落。",
            [
                _metric_sentence("经营利润同比", _pct(_growth(latest.get("operating_income"), prior.get("operating_income")))),
                _metric_sentence("净利润同比", _pct(_growth(latest.get("net_income"), prior.get("net_income")))),
                _metric_sentence("增量经营利润率", _pct(profit_bridge.get("incremental_operating_margin"))),
            ],
            "partial",
            ["Q1", "Q2"],
        ),
        _std(
            "S4",
            "利润有没有变成现金？",
            "利润有经营现金流支撑，但现金质量需要拆营运资本桥。",
            [
                _metric_sentence("经营现金流 / 净利润", _ratio_x(cash_conversion.get("value"))),
                _metric_sentence("营运资本现金顺风 / 收入", _pct(working_capital.get("working_capital_cash_tailwind_to_revenue"))),
            ],
            "partial",
            ["Q3"],
        ),
        _std(
            "S5",
            "资产负债表能不能支撑投入期？",
            "资产负债表较强，但账面现金不能全部视为股东可用现金。",
            [
                _metric_sentence("广义现金与短投", _money(_broad_cash(latest))),
                _metric_sentence("流动比率", _ratio_x(balance.get("current_ratio"))),
                _metric_sentence("受限现金 / 现金", _pct(balance.get("restricted_cash_to_cash"))),
            ],
            "partial",
            ["Q4"],
        ),
        _std(
            "S6",
            "商业模式是否在变化？",
            "交易服务占比提升和自营品牌/供应链投入叙事提示商业模式可能变重，但财务闭环未完成。",
            [
                _metric_sentence("交易服务占最新年度收入", _pct(_safe_div(latest.get("transaction_services_revenue"), latest.get("revenue")))),
                _metric_sentence("资本开支 / 收入", _pct(cap_intensity.get("capex_to_revenue"))),
            ],
            "partial",
            ["Q5", "Q7"],
        ),
        _std(
            "S7",
            "净利润和 non-GAAP 有没有遮蔽经营质量？",
            "non-GAAP 不是当前主矛盾，但净利润需要拆经营利润以下项目。",
            [
                _metric_sentence("最新季度经营利润变化", _money(below_bridge.get("operating_income_delta"))),
                _metric_sentence("最新季度净利润变化", _money(below_bridge.get("net_income_delta"))),
            ],
            "partial",
            ["Q8"],
        ),
        _std(
            "S8",
            "股东每股价值有没有明显被稀释？",
            "SBC 和稀释暂不构成主线风险，但仍缺少完整股数和资本回报桥。",
            [
                _metric_sentence("SBC / 收入", _pct(sbc.get("sbc_to_revenue"))),
                _metric_sentence("稀释股数同比", _pct(sbc.get("diluted_shares_yoy"))),
            ],
            "partial",
            ["Q9"],
        ),
    ]


def _research_questions(
    latest: dict[str, Any],
    prior: dict[str, Any],
    latest_quarter: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
    disclosure_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    profit_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    balance = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    gap_map = {gap.get("gap_id"): gap for gap in disclosure_gaps}
    return [
        _question(
            "Q1",
            "新增收入为什么没有带来新增经营利润？",
            "partial",
            "收入仍增长，但新增收入没有转化为新增经营利润。",
            [
                _metric_sentence("收入同比", _pct(_growth(latest.get("revenue"), prior.get("revenue")))),
                _metric_sentence("经营利润同比", _pct(_growth(latest.get("operating_income"), prior.get("operating_income")))),
                _metric_sentence("增量经营利润率", _pct(profit_bridge.get("incremental_operating_margin"))),
            ],
            ["商家分群 / 单商家经济性", "广告抽佣率", "商家广告投资回报", "GMV"],
            ["growth_quality", "profitability_with_scale"],
            ["cost_of_revenue_subcomponents", "user_and_transaction_kpis"],
        ),
        _question(
            "Q2",
            "利润率压力是主动投入，还是结构性竞争压力？",
            "partial",
            "成本率和费用率同时上升，但第一层不能证明原因。",
            [
                _metric_sentence("成本率变化", f"{_pct(_cost_ratio(prior))} -> {_pct(_cost_ratio(latest))}"),
                _metric_sentence("经营利润率变化", f"{_pct(_margin(prior, 'operating_income'))} -> {_pct(_margin(latest, 'operating_income'))}"),
            ],
            ["费用化节奏", "投资回报", "履约/支付/商家支持金额"],
            ["profitability_with_scale"],
            ["cost_of_revenue_subcomponents"],
        ),
        _question(
            "Q3",
            "经营现金流质量是否依赖商家资金沉淀 / 经营负债扩张？",
            "partial",
            "经营现金流覆盖净利润，但营运资本现金顺风较明显。",
            [_metric_sentence("营运资本现金顺风 / 收入", _pct(working_capital.get("working_capital_cash_tailwind_to_revenue")))],
            ["应收、预付、存货、应付、商家保证金、递延收入完整桥"],
            ["cash_profit_quality"],
            ["working_capital_bridge"],
        ),
        _question(
            "Q4",
            "账面现金很多，但多少是真正股东可用？",
            "partial",
            "资产负债表能支撑投入期，但现金可用性要保守处理。",
            [
                _metric_sentence("广义现金与短投", _money(_broad_cash(latest))),
                _metric_sentence("受限现金 / 现金", _pct(balance.get("restricted_cash_to_cash"))),
            ],
            ["VIE 资金转移性", "受限现金性质", "12 个月刚性义务"],
            ["balance_sheet_resilience"],
            ["usable_cash_and_vie_transferability"],
        ),
        _question(
            "Q5",
            "自营品牌是否会让平台模式变重？",
            "partial",
            "管理层已有战略叙事，但第一层没有单独财务闭环。",
            [_metric_sentence("相关披露缺口", _gap_metrics(gap_map.get("first_party_brand_unit_economics")))],
            ["库存风险", "单独损益", "品牌业务 GMV / 收入 / 利润"],
            ["capital_needed_for_growth"],
            ["first_party_brand_unit_economics", "maintenance_vs_growth_capex"],
        ),
        _question(
            "Q6",
            "交易服务占比提高，到底是更强货币化，还是更高履约/治理成本？",
            "partial",
            "收入结构变化清楚，但缺少 GMV、订单、抽佣率和服务范围拆分。",
            [_metric_sentence("交易服务占收入", _pct(_safe_div(latest.get("transaction_services_revenue"), latest.get("revenue"))))],
            ["GMV", "订单", "take rate", "服务范围拆分"],
            ["growth_quality"],
            ["user_and_transaction_kpis", "cost_of_revenue_subcomponents"],
        ),
        _question(
            "Q7",
            "Temu / 全球业务是可验证增长引擎，还是仍只是战略叙事？",
            "partial",
            "官方和电话会都有全球业务叙事，但单独经济性缺失。",
            [_metric_sentence("相关披露缺口", _gap_metrics(gap_map.get("temu_standalone_economics")))],
            ["Temu 收入", "Temu 经营利润", "Temu GMV", "履约/退货成本", "地区利润率"],
            ["growth_quality"],
            ["temu_standalone_economics"],
        ),
        _question(
            "Q8",
            "净利润和 non-GAAP 是否掩盖了经营质量？",
            "partial",
            "non-GAAP 不是当前主矛盾，但经营利润以下项目需要固定拆桥。",
            [
                _metric_sentence("最新季度经营利润变化", _money(below_bridge.get("operating_income_delta"))),
                _metric_sentence("最新季度净利润变化", _money(below_bridge.get("net_income_delta"))),
            ],
            ["投资收益", "其他收益/损失", "税项", "权益法投资", "现金纳税"],
            ["tax_non_gaap_accounting_quality"],
            ["below_operating_bridge"],
        ),
        _question(
            "Q9",
            "股权激励、治理和每股价值有没有隐藏风险？",
            "partial",
            "SBC 和稀释暂未成为主线风险，但缺少完整 owner-economics 桥。",
            [],
            ["回购是否抵消 SBC", "完整 ADS / 普通股桥", "股权计划剩余额度"],
            ["sbc_and_per_share_quality"],
            ["share_count_and_capital_return_bridge"],
        ),
    ]


def _numeric_anomalies(
    latest: dict[str, Any],
    prior: dict[str, Any],
    latest_quarter: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    revenue_growth = _growth(latest.get("revenue"), prior.get("revenue"))
    op_growth = _growth(latest.get("operating_income"), prior.get("operating_income"))
    if revenue_growth is not None and revenue_growth > 0 and op_growth is not None and op_growth < 0:
        anomalies.append(
            {
                "anomaly_id": "revenue_growth_operating_income_decline",
                "severity": "high",
                "summary": "收入增长但经营利润下降。",
                "numeric_evidence": [_metric_sentence("收入同比", _pct(revenue_growth)), _metric_sentence("经营利润同比", _pct(op_growth))],
                "linked_questions": ["Q1", "Q2"],
            }
        )
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    if below_bridge.get("operating_income_delta") and below_bridge.get("net_income_delta"):
        if float(below_bridge.get("operating_income_delta") or 0) > 0 and float(below_bridge.get("net_income_delta") or 0) < 0:
            anomalies.append(
                {
                    "anomaly_id": "operating_profit_up_net_income_down",
                    "severity": "medium",
                    "summary": "最新季度经营利润改善但净利润下降。",
                    "numeric_evidence": [
                        _metric_sentence("经营利润变化", _money(below_bridge.get("operating_income_delta"))),
                        _metric_sentence("净利润变化", _money(below_bridge.get("net_income_delta"))),
                    ],
                    "linked_questions": ["Q8"],
                }
            )
    if latest_quarter.get("net_income_yoy") is not None and latest_quarter.get("net_income_yoy") < 0:
        anomalies.append(
            {
                "anomaly_id": "latest_quarter_net_income_decline",
                "severity": "medium",
                "summary": "最新季度净利润同比下降。",
                "numeric_evidence": [_metric_sentence("最新季度净利润同比", _pct(latest_quarter.get("net_income_yoy")))],
                "linked_questions": ["Q8"],
            }
        )
    return anomalies


def _hard_data_insights(
    latest: dict[str, Any],
    prior: dict[str, Any],
    latest_quarter: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    balance = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    return [
        {
            "insight_id": "cash_rich_but_availability_needs_discount",
            "summary": "现金和短投很厚，但受限现金、VIE 和资金可转移性会影响股东可用现金判断。",
            "numeric_evidence": [
                _metric_sentence("广义现金与短投", _money(_broad_cash(latest))),
                _metric_sentence("受限现金 / 现金", _pct(balance.get("restricted_cash_to_cash"))),
            ],
            "linked_questions": ["Q4"],
        },
        {
            "insight_id": "revenue_mix_has_company_specific_signal",
            "summary": "收入结构已经有公司特征，交易服务与在线营销服务及其他需要分开追踪。",
            "numeric_evidence": [
                _metric_sentence("交易服务占收入", _pct(_safe_div(latest.get("transaction_services_revenue"), latest.get("revenue")))),
                _metric_sentence("在线营销服务及其他占收入", _pct(_safe_div(latest.get("online_marketing_services_revenue"), latest.get("revenue")))),
            ],
            "linked_questions": ["Q6"],
        },
    ]


def _red_flags(diagnostic_findings: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    for flag in diagnostic_findings.get("warning_flags") or []:
        flags.append(
            {
                "flag_id": flag.get("flag_id") or flag.get("warning") or "warning",
                "severity": flag.get("severity") or "medium",
                "summary": flag.get("warning") or flag.get("message") or str(flag),
                "linked_questions": flag.get("linked_questions") or [],
            }
        )
    return flags


def _evidence_handoffs(research_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    handoffs = []
    for question in research_questions:
        handoffs.append(
            {
                "question_id": question.get("question_id"),
                "question": question.get("question"),
                "status": question.get("status"),
                "route_to": "evidence_communication_extraction",
                "official_question_ids": question.get("suggested_official_question_ids") or [],
                "still_unknown": question.get("still_unknown") or [],
            }
        )
    return handoffs


def _extractor_handoffs(
    disclosure_gaps: list[dict[str, Any]],
    research_questions: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    handoffs: list[dict[str, Any]] = []
    for gap in disclosure_gaps:
        handoffs.append(
            {
                "handoff_id": gap.get("gap_id") or "disclosure_gap",
                "priority": _gap_priority(str(gap.get("gap_id") or "")),
                "request": _gap_request(str(gap.get("gap_id") or "")),
                "missing_metrics": gap.get("missing_metrics") or [],
                "why_it_matters": gap.get("why_it_matters") or "",
                "status": gap.get("status") or "unknown",
                "linked_questions": _gap_linked_questions(str(gap.get("gap_id") or ""), research_questions),
                "source": "financial_extraction_summary.disclosure_gap_registry",
            }
        )
    if any(anomaly.get("anomaly_id") == "revenue_growth_operating_income_decline" for anomaly in anomalies):
        handoffs.append(
            {
                "handoff_id": "operating_profit_bridge_deepening",
                "priority": "P0",
                "request": "补经营利润桥和费用率完整桥。",
                "missing_metrics": ["cost_of_revenue_subcomponents", "expense_rate_bridge", "operating_profit_bridge"],
                "why_it_matters": "解释新增收入为什么没有带来新增经营利润。",
                "status": "needed",
                "linked_questions": ["Q1", "Q2"],
                "source": "layer1_numeric_anomaly",
            }
        )
    return _dedupe_handoffs(handoffs)


def _std(
    question_id: str,
    question: str,
    answer: str,
    evidence: list[str],
    status: str,
    linked_questions: list[str],
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question": question,
        "status": status,
        "short_answer": answer,
        "numeric_evidence": [item for item in evidence if item],
        "linked_research_questions": linked_questions,
    }


def _question(
    question_id: str,
    question: str,
    status: str,
    current_answer: str,
    triggers: list[str],
    unknowns: list[str],
    official_question_ids: list[str],
    extractor_needs: list[str],
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question": question,
        "status": status,
        "current_answer": current_answer,
        "financial_triggers": [item for item in triggers if item],
        "still_unknown": unknowns,
        "suggested_official_question_ids": official_question_ids,
        "handoff_to_financial_extractor": extractor_needs,
    }


def _metrics_by_id(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {metric.get("formula_id"): metric for metric in pack.get("financial_metrics") or [] if metric.get("formula_id")}


def _annual_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(pack.get("annual_facts") or [], key=lambda row: row.get("year") or 0)


def _quarterly_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(pack.get("quarterly_facts") or [], key=lambda row: str(row.get("period_end") or row.get("quarter") or ""))


def _latest_annual_metric(metrics: dict[str, dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    results = (metrics.get(formula_id) or {}).get("annual_results") or []
    return results[-1] if results else None


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    try:
        if numerator is None or denominator in (None, 0):
            return None
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _growth(current: Any, prior: Any) -> float | None:
    try:
        if current is None or prior in (None, 0):
            return None
        return float(current) / float(prior) - 1.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _margin(row: dict[str, Any], metric: str) -> float | None:
    return _safe_div(row.get(metric), row.get("revenue"))


def _cost_ratio(row: dict[str, Any]) -> float | None:
    return _safe_div(row.get("cost_of_revenue"), row.get("revenue"))


def _broad_cash(row: dict[str, Any]) -> float | None:
    values = [row.get("cash"), row.get("restricted_cash"), row.get("short_term_investments")]
    nums = [float(value) for value in values if value is not None]
    return sum(nums) if nums else None


def _money(value: Any) -> str:
    try:
        if value is None:
            return "未披露"
        return f"RMB {float(value) / 1_000_000_000:.1f}B"
    except (TypeError, ValueError):
        return str(value)


def _pct(value: Any) -> str:
    try:
        if value is None:
            return "未披露"
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _ratio_x(value: Any) -> str:
    try:
        if value is None:
            return "未披露"
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return str(value)


def _metric_sentence(label: str, value: str) -> str:
    if value in {"未披露", "None", ""}:
        return ""
    return f"{label}：{value}"


def _gap_metrics(gap: dict[str, Any] | None) -> str:
    if not gap:
        return "未披露"
    metrics = gap.get("missing_metrics") or []
    return "、".join(str(item).replace("_", " ") for item in metrics) or str(gap.get("gap_id") or "未披露")


def _gap_priority(gap_id: str) -> str:
    return {
        "cost_of_revenue_subcomponents": "P0",
        "user_and_transaction_kpis": "P0",
        "temu_standalone_economics": "P1",
        "first_party_brand_unit_economics": "P1",
        "maintenance_vs_growth_capex": "P2",
    }.get(gap_id, "P2")


def _gap_request(gap_id: str) -> str:
    return {
        "cost_of_revenue_subcomponents": "补成本细项抽取。",
        "user_and_transaction_kpis": "补用户、交易量、GMV、订单和 take-rate KPI。",
        "temu_standalone_economics": "补 Temu / 全球业务单独经济性。",
        "first_party_brand_unit_economics": "补自营品牌单位经济性和库存风险。",
        "maintenance_vs_growth_capex": "补维护性/增长性资本开支拆分。",
    }.get(gap_id, "补披露缺口对应字段。")


def _gap_linked_questions(gap_id: str, research_questions: list[dict[str, Any]]) -> list[str]:
    linked = []
    for question in research_questions:
        if gap_id in (question.get("handoff_to_financial_extractor") or []):
            linked.append(str(question.get("question_id")))
    return linked


def _dedupe_handoffs(handoffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for handoff in handoffs:
        handoff_id = str(handoff.get("handoff_id") or "")
        if not handoff_id or handoff_id in seen:
            continue
        seen.add(handoff_id)
        result.append(handoff)
    return result
