from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from stock_research.state import ResearchState, utc_now_iso


OFFICIAL_REPORT_EVIDENCE_SCHEMA_VERSION = "official_report_evidence_pack_v1"


QUESTION_CONFIGS: dict[str, dict[str, Any]] = {
    "growth_quality": {
        "title": "增长质量",
        "keywords": (
            "Revenues from transaction services were",
            "revenues from online marketing services",
            "total revenues increased",
            "transaction services",
            "online marketing services",
            "merchant",
            "revenue growth",
            "supply chain",
            "ecosystem",
            "support",
        ),
        "sections": ("MD&A / OFR", "Revenue", "Business overview", "Segment / KPI disclosure"),
        "next_step": "继续验证收入结构、商家经济性和投入回报是否改善。",
    },
    "profitability_with_scale": {
        "title": "利润率变化",
        "keywords": (
            "Total costs of revenues were",
            "total operating expenses",
            "operating profit",
            "fulfillment fees",
            "cost of revenues",
            "fulfillment",
            "bandwidth",
            "server",
            "sales and marketing",
            "merchant support",
            "ecosystem",
            "supply chain investment",
            "profit margin",
        ),
        "sections": ("MD&A / OFR", "Costs and expenses", "Operating results", "Expense notes"),
        "next_step": "把费用率、成本率和官方投入叙事连续跟踪到下一期。",
    },
    "cash_profit_quality": {
        "title": "现金流质量",
        "keywords": (
            "net cash generated from operating activities",
            "cash flows",
            "net cash generated from operating activities",
            "working capital",
            "payable to merchants",
            "merchant deposits",
            "deferred revenue",
            "accounts receivable",
            "settlement",
        ),
        "sections": ("Liquidity and capital resources", "Cash flow statement", "Working-capital notes"),
        "next_step": "拆营运资本来源，确认现金流是否依赖商家相关负债和结算周期。",
    },
    "capital_needed_for_growth": {
        "title": "资本效率与投入",
        "keywords": (
            "supply chain investments",
            "first-party brand",
            "capital expenditures",
            "property and equipment",
            "software",
            "supply chain",
            "investment",
            "first-party",
            "brand",
            "fulfillment",
        ),
        "sections": ("Capital expenditures", "Liquidity", "Business initiatives", "Investment plans"),
        "next_step": "区分维护性资本开支、增长性投入、供应链投入和品牌投入。",
    },
    "balance_sheet_resilience": {
        "title": "资产负债表与现金可用性",
        "keywords": (
            "Restricted cash",
            "cash and cash equivalents",
            "restricted cash",
            "short-term investments",
            "cash and cash equivalents",
            "VIE",
            "variable interest entity",
            "transfer",
            "dividend",
            "debt",
            "convertible",
        ),
        "sections": ("Cash and restricted cash notes", "Liquidity", "VIE", "Debt notes"),
        "next_step": "回查受限现金、VIE 资金转移、债务到期和可用现金口径。",
    },
    "sbc_and_per_share_quality": {
        "title": "股权激励与稀释",
        "keywords": (
            "share-based compensation",
            "stock-based compensation",
            "global share plan",
            "restricted share units",
            "diluted",
            "repurchase",
        ),
        "sections": ("Share-based compensation", "Equity plans", "Proxy / AGM if relevant"),
        "next_step": "确认回购是否抵消股权激励稀释，并补完整 ADS / 普通股桥。",
    },
    "tax_non_gaap_accounting_quality": {
        "title": "税项、非 GAAP 与会计质量",
        "keywords": (
            "Reconciliation of Non-GAAP",
            "non-GAAP net income",
            "effective tax rate",
            "income tax",
            "non-GAAP",
            "share-based compensation",
            "investment income",
            "critical audit matter",
            "critical accounting",
            "impairment",
        ),
        "sections": ("Tax notes", "Non-GAAP reconciliation", "Critical accounting estimates", "Audit report"),
        "next_step": "拆非 GAAP 调整、投资收益、税率调节和关键会计估计。",
    },
}


NARRATIVE_CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "narrative_id": "transaction_services_revenue_mix",
        "title": "交易服务收入与收入结构",
        "narrative_type": "KPI",
        "keywords": ("transaction services", "online marketing services", "revenue"),
        "linked_metrics": ("source_of_growth_attribution_v1", "revenue_growth"),
        "why_it_matters": "收入结构变化会影响对增长来源、平台货币化和业务重心的判断。",
    },
    {
        "narrative_id": "first_party_brand",
        "title": "自营品牌业务",
        "narrative_type": "strategic_initiative",
        "keywords": ("first-party brand", "brand-owned", "brand business", "first party brand"),
        "linked_metrics": ("operating_margin", "capital_intensity", "transaction_services_revenue"),
        "why_it_matters": "自营品牌业务可能让平台更深介入产品、质量控制、供应链和履约，影响利润率与资本强度。",
    },
    {
        "narrative_id": "supply_chain_investment",
        "title": "供应链投入与商家支持",
        "narrative_type": "strategic_initiative",
        "keywords": (
            "supply chain",
            "merchant support",
            "ecosystem investment",
            "100 billion",
            "RMB 100 billion",
            "logistics support",
        ),
        "linked_metrics": ("operating_margin", "incremental_operating_margin", "cash_profit_quality"),
        "why_it_matters": "供应链和商家支持可能解释短期利润率压力，也可能是长期护城河假设的来源。",
    },
    {
        "narrative_id": "global_business_temu",
        "title": "全球业务 / Temu",
        "narrative_type": "business_model_change",
        "keywords": ("Temu", "global business", "cross-border", "international", "overseas"),
        "linked_metrics": ("revenue_growth", "margin_profile", "regulatory_risk"),
        "why_it_matters": "全球业务可能提供增长空间，也可能带来履约、税务、监管和利润率不确定性。",
    },
    {
        "narrative_id": "restricted_cash_vie",
        "title": "受限现金、VIE 与资金可转移性",
        "narrative_type": "regulation",
        "keywords": (
            "restricted cash",
            "VIE",
            "variable interest entity",
            "cash transfer",
            "dividend restrictions",
            "PRC subsidiaries",
        ),
        "linked_metrics": ("restricted_cash_to_cash", "cash_to_liabilities", "balance_sheet_resilience"),
        "why_it_matters": "账面现金不等于自由现金，VIE 和跨境资金限制会影响资产负债表安全垫的读法。",
    },
    {
        "narrative_id": "management_governance_change",
        "title": "管理层、董事会或治理变化",
        "narrative_type": "governance",
        "keywords": (
            "chief executive officer",
            "co-chief executive officer",
            "chairman",
            "director",
            "resignation",
            "appointed",
            "annual general meeting",
        ),
        "linked_metrics": ("governance_risk", "execution_risk"),
        "why_it_matters": "关键管理层或治理变化可能改变执行风险、控制权和资本配置判断。",
    },
    {
        "narrative_id": "agm_ads_voting_board",
        "title": "AGM、ADS 投票机制与董事重选",
        "narrative_type": "governance",
        "keywords": (
            "Annual General Meeting",
            "ADSs",
            "Depository",
            "voting instructions",
            "re-elected",
            "election of directors",
            "ordinary resolution",
        ),
        "linked_metrics": ("governance_risk", "minority_shareholder_rights"),
        "why_it_matters": "AGM 和 proxy 材料会影响 ADS 持有人投票权、董事连续性和少数股东治理读法。",
    },
    {
        "narrative_id": "share_plan_extension",
        "title": "2015 Global Share Plan 期限延长",
        "narrative_type": "governance",
        "keywords": (
            "2015 Global Share Plan",
            "Term Extension",
            "term of the 2015 Plan",
            "20 years",
            "compensation committee",
            "share plan",
        ),
        "linked_metrics": ("sbc_and_per_share_quality", "dilution", "governance_risk"),
        "why_it_matters": "股权计划期限延长会影响长期激励、潜在稀释和薪酬治理，需要和 SBC、稀释股数一起看。",
    },
    {
        "narrative_id": "audit_accounting_reliability",
        "title": "审计、内控与会计可靠性",
        "narrative_type": "accounting",
        "keywords": (
            "independent registered public accounting firm",
            "material weakness",
            "internal control",
            "critical audit matter",
            "auditor",
            "Ernst & Young",
        ),
        "linked_metrics": ("accounting_quality", "tax_non_gaap_accounting_quality"),
        "why_it_matters": "审计、内控和关键审计事项影响财报可信度和会计判断风险。",
    },
)


def build_official_report_evidence_pack(state: ResearchState) -> dict[str, Any]:
    financial_pack = state.get("financial_report_pack") or {}
    sources = _load_relevant_sources(state, financial_pack)
    question_answers = [_answer_question(question, financial_pack, sources) for question in _diagnostic_questions(financial_pack)]
    narratives = _detect_decision_relevant_narratives(financial_pack, sources)
    layer1_update = _build_layer1_update(question_answers, narratives)
    return {
        "schema_version": OFFICIAL_REPORT_EVIDENCE_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "agent_run": {
            "run_id": state.get("run_id"),
            "company_id": ((financial_pack.get("company") or {}).get("company_id") or state.get("company_query")),
            "company_name": ((financial_pack.get("company") or {}).get("legal_name") or state.get("company_query")),
            "market": state.get("market"),
            "source_policy": "official_filings_only",
            "annual_report_used": any(source.get("source_role") == "annual_report" for source in sources),
            "quarterly_reports_used": any(source.get("source_role") == "latest_quarterly_or_6k" for source in sources),
            "event_reports_used": any(source.get("source_role") == "material_event" for source in sources),
        },
        "source_catalog": [_source_catalog_entry(source) for source in sources],
        "question_answers": question_answers,
        "decision_relevant_narratives": narratives,
        "layer1_update": layer1_update,
        "quality_flags": _quality_flags(question_answers, narratives, sources),
    }


def build_official_report_evidence_report(pack: dict[str, Any]) -> str:
    agent_run = pack.get("agent_run") or {}
    lines = [
        f"# 官方报告证据与解释：{agent_run.get('company_name') or agent_run.get('company_id') or 'Unknown Company'}",
        "",
        "## 1. 第一层问题复核",
        "",
    ]
    for answer in pack.get("question_answers") or []:
        lines.extend(_question_answer_markdown(answer))
    lines.extend(
        [
            "## 2. 决策相关官方叙事与事件",
            "",
        ]
    )
    narratives = pack.get("decision_relevant_narratives") or []
    if not narratives:
        lines.extend(["- 未发现达到 V1 决策相关门槛的新增官方叙事。", ""])
    for narrative in narratives:
        lines.extend(_narrative_markdown(narrative))
    lines.extend(
        [
            "## 3. 商业模式与护城河假设",
            "",
            *_business_hypothesis_markdown(narratives),
            "",
            "## 4. 对第一层判断的更新",
            "",
            *_layer1_update_markdown(pack.get("layer1_update") or {}),
            "",
            "## 5. 下一层研究路由",
            "",
            *_next_research_markdown(pack.get("layer1_update") or {}),
            "",
            "## 附录：来源目录",
            "",
        ]
    )
    for source in pack.get("source_catalog") or []:
        lines.append(
            f"- {_source_role_zh(source.get('source_role'))} | {source.get('document_type')} | "
            f"{source.get('filing_date')} | `{source.get('local_file_path')}`"
        )
    return "\n".join(lines).strip() + "\n"


def _diagnostic_questions(financial_pack: dict[str, Any]) -> list[dict[str, Any]]:
    questions = (financial_pack.get("diagnostic_findings") or {}).get("questions") or []
    if questions:
        return sorted(questions, key=lambda item: item.get("rank", 999))
    return (financial_pack.get("annual_report_baseline") or {}).get("diagnostic_questions") or []


def _question_context(question_id: str, financial_pack: dict[str, Any], question: dict[str, Any]) -> dict[str, Any]:
    latest_annual, prior_annual = _latest_and_prior(financial_pack.get("annual_facts") or [], "year")
    latest_quarter, prior_quarter = _latest_and_prior_quarter(financial_pack.get("quarterly_facts") or [])
    context = {
        "latest_values": question.get("latest_values") or {},
        "latest_annual": latest_annual,
        "prior_annual": prior_annual,
        "latest_quarter": latest_quarter,
        "prior_quarter": prior_quarter,
    }
    metric_map = {metric.get("formula_id"): metric for metric in financial_pack.get("financial_metrics") or []}
    if question_id == "growth_quality":
        context["source_growth"] = (metric_map.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    if question_id == "cash_profit_quality":
        context["working_capital"] = _latest_annual_metric_result(metric_map.get("working_capital_quality_v1") or {})
    if question_id == "capital_needed_for_growth":
        context["capital_intensity"] = _latest_annual_metric_result(metric_map.get("capital_intensity_v1") or {})
        context["incremental_margin"] = _latest_annual_metric_result(metric_map.get("incremental_margin_v1") or {})
    if question_id == "balance_sheet_resilience":
        context["balance_sheet"] = _latest_annual_metric_result(metric_map.get("balance_sheet_risk_v1") or {})
    if question_id == "sbc_and_per_share_quality":
        context["sbc"] = _latest_annual_metric_result(metric_map.get("share_based_compensation_burden_v1") or {})
    if question_id == "tax_non_gaap_accounting_quality":
        context["tax"] = _latest_annual_metric_result(metric_map.get("tax_non_gaap_accounting_quality_v1") or {})
        context["latest_interim_non_gaap"] = (metric_map.get("tax_non_gaap_accounting_quality_v1") or {}).get("latest_interim_non_gaap") or {}
    return context


def _latest_and_prior(rows: list[dict[str, Any]], key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    usable = [row for row in rows if row.get(key) is not None]
    usable = sorted(usable, key=lambda row: row.get(key))
    if not usable:
        return {}, {}
    latest = usable[-1]
    prior = usable[-2] if len(usable) > 1 else {}
    return latest, prior


def _latest_and_prior_quarter(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    usable = [row for row in rows if row.get("period_end")]
    usable = sorted(usable, key=lambda row: str(row.get("period_end")))
    if not usable:
        return {}, {}
    latest = usable[-1]
    latest_period = str(latest.get("period_end") or "")
    prior_year = ""
    if len(latest_period) >= 4:
        try:
            prior_year = str(int(latest_period[:4]) - 1) + latest_period[4:]
        except ValueError:
            prior_year = ""
    prior = next((row for row in usable if row.get("period_end") == prior_year), {})
    return latest, prior


def _latest_annual_metric_result(metric: dict[str, Any]) -> dict[str, Any]:
    results = [result for result in metric.get("annual_results") or [] if result.get("year") is not None]
    if not results:
        return {}
    return sorted(results, key=lambda result: result.get("year"))[-1]


def _answer_question(question: dict[str, Any], financial_pack: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    question_id = str(question.get("question_id") or "")
    config = QUESTION_CONFIGS.get(question_id, {})
    keywords = tuple(config.get("keywords") or ())
    passages = _top_passages(sources, keywords, limit=3)
    filing_facts = [_layer1_fact_evidence(question, financial_pack)]
    management_explanations = [_passage_to_evidence(passage, "management_explanation", question_id=question_id) for passage in passages]
    still_unknown = [_missing_label(item) for item in question.get("missing") or []]
    answer_status = _answer_status(question, management_explanations, still_unknown)
    cross_check = _cross_check_status(question)
    inference_text = _question_inference(question, management_explanations, still_unknown)
    context = _question_context(question_id, financial_pack, question)
    answer = {
        "question_id": question_id,
        "question_title": config.get("title") or question.get("question") or question_id,
        "question_text": question.get("question") or question_id,
        "latest_values": question.get("latest_values") or {},
        "warning_flags": question.get("warning_flags") or [],
        "context": context,
        "answer_status": answer_status,
        "short_answer": _short_answer(question),
        "target_sections": list(config.get("sections") or ()),
        "filing_facts": filing_facts,
        "management_explanations": management_explanations,
        "cross_check_with_layer1": {
            "status": cross_check,
            "reason": _cross_check_reason(question, management_explanations),
        },
        "our_inference": {
            "evidence_type": "our_inference",
            "text": inference_text,
            "confidence": _confidence_label(answer_status, bool(still_unknown), cross_check),
        },
        "still_unknown": still_unknown,
        "impact_on_layer1": _impact_on_layer1(question, answer_status, cross_check),
        "follow_up_needed": [config.get("next_step") or "继续回到官方文件和下一层研究验证。"],
        "evidence_bundle": [filing_facts[0], *management_explanations],
    }
    answer["rendered_answer"] = {
        "filing_facts": _question_fact_detail_zh(answer),
        "official_explanation": _question_official_explanation_zh(answer),
        "our_judgment": _question_judgment_zh(answer),
        "source_trace": _question_source_trace_zh(answer),
    }
    return answer


def _detect_decision_relevant_narratives(
    financial_pack: dict[str, Any],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    narratives = []
    for config in NARRATIVE_CONFIGS:
        passages = _top_passages(sources, tuple(config["keywords"]), limit=2)
        metric_support = _narrative_metric_support(financial_pack, str(config["narrative_id"]))
        if not passages and not metric_support:
            continue
        filing_facts = []
        if metric_support:
            filing_facts.append(
                {
                    "evidence_id": f"metric:{config['narrative_id']}",
                    "evidence_type": "filing_fact",
                    "source_document_type": "financial_report_pack",
                    "source_document": "financial_report_pack.json",
                    "source_section": "financial_metrics",
                    "period": metric_support.get("period"),
                    "quote_or_summary": metric_support.get("summary"),
                    "linked_layer1_metrics": list(config.get("linked_metrics") or ()),
                    "cross_validation_status": "matched",
                }
            )
        filing_facts.extend(_passage_to_evidence(passage, "filing_fact", narrative_id=str(config["narrative_id"])) for passage in passages[:1])
        management = [_passage_to_evidence(passage, "management_explanation", narrative_id=str(config["narrative_id"])) for passage in passages[1:2]]
        narratives.append(
            {
                "narrative_id": config["narrative_id"],
                "narrative_type": config["narrative_type"],
                "change_status": "detected_in_current_official_package",
                "title": config["title"],
                "filing_facts": filing_facts,
                "management_explanations": management,
                "why_it_matters": config["why_it_matters"],
                "linked_layer1_metrics": list(config.get("linked_metrics") or ()),
                "our_inference": _narrative_inference(str(config["narrative_id"]), bool(metric_support), bool(passages)),
                "still_unknown": _narrative_unknowns(str(config["narrative_id"])),
                "impact_on_investment_judgment": "clarifies" if filing_facts else "creates_new_question",
                "follow_up_needed": _narrative_follow_up(str(config["narrative_id"])),
                "evidence_bundle": [*filing_facts, *management],
            }
        )
    return narratives


def _load_relevant_sources(state: ResearchState, financial_pack: dict[str, Any]) -> list[dict[str, Any]]:
    documents = state.get("documents") or []
    sources: list[dict[str, Any]] = []
    annual = ((financial_pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {})
    if annual:
        source = _document_from_reference(documents, annual) or annual
        sources.append(_source_with_text(source, "annual_report"))
    latest_quarter_sources = _latest_quarter_or_6k_documents(documents)
    sources.extend(_source_with_text(source, "latest_quarterly_or_6k") for source in latest_quarter_sources)
    governance_sources = _layer_two_governance_documents(documents)
    sources.extend(_source_with_text(source, "governance_proxy_agm") for source in governance_sources)
    for event in (financial_pack.get("material_event_scan") or {}).get("events", [])[:5]:
        source = _document_from_reference(documents, event) or event
        sources.append(_source_with_text(source, "material_event"))
    return _dedupe_sources([source for source in sources if source.get("text")])


def _document_from_reference(documents: list[dict[str, Any]], reference: dict[str, Any]) -> dict[str, Any] | None:
    ref_id = reference.get("document_id")
    ref_path = reference.get("local_path")
    for document in documents:
        if ref_id and document.get("document_id") == ref_id:
            return document
        if ref_path and document.get("local_path") == ref_path:
            return document
    return None


def _latest_quarter_or_6k_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        document
        for document in documents
        if _is_layer_two_quarterly_document(document)
        and document.get("filing_date")
        and document.get("local_path")
    ]
    if not candidates:
        return []
    latest_date = max(str(document.get("filing_date")) for document in candidates)
    latest = [document for document in candidates if str(document.get("filing_date")) == latest_date]
    preferred = sorted(
        latest,
        key=lambda document: (
            0 if "exhibit" in str(document.get("document_type") or "").lower() else 1,
            str(document.get("document_id") or ""),
        ),
    )
    return preferred[:3]


def _is_layer_two_quarterly_document(document: dict[str, Any]) -> bool:
    document_type = str(document.get("document_type") or "")
    category = str(document.get("research_category") or "")
    if document_type.startswith("10-Q"):
        return True
    if document_type.startswith("6-K"):
        return category in {"KEEP_CORE_INTERIM_EARNINGS", "KEEP_SECONDARY_INTERIM_FINANCIAL_CONTEXT"}
    return False


def _layer_two_governance_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        document
        for document in documents
        if document.get("local_path")
        and _is_layer_two_governance_document(document)
    ]
    ranked = sorted(
        candidates,
        key=lambda document: (
            str(document.get("filing_date") or ""),
            str(document.get("document_id") or ""),
        ),
        reverse=True,
    )
    return ranked[:8]


def _is_layer_two_governance_document(document: dict[str, Any]) -> bool:
    category = str(document.get("research_category") or "")
    if category in {"KEEP_MONITORING_GOVERNANCE", "KEEP_MONITORING_MANAGEMENT"}:
        return True
    if category.startswith("DROP_"):
        return False
    document_type = str(document.get("document_type") or "")
    if not document_type.startswith("6-K"):
        return False
    text = _document_text(document)[:12000].lower()
    governance_terms = (
        "results of pdd holdings inc.",
        "annual general meeting",
        "appointment of co-chairman",
        "new executive officers",
        "global share plan",
        "proxy statement",
        "voting instructions",
    )
    return any(term in text for term in governance_terms)


def _source_with_text(document: dict[str, Any], role: str) -> dict[str, Any]:
    source = dict(document)
    source["source_role"] = role
    source["text"] = _document_text(document)
    return source


def _document_text(document: dict[str, Any]) -> str:
    path_value = document.get("local_path")
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.exists():
        return ""
    if path.suffix.lower() not in {".htm", ".html", ".txt"}:
        return ""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for source in sources:
        key = source.get("document_id") or source.get("local_path")
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def _source_catalog_entry(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_role": source.get("source_role"),
        "document_id": source.get("document_id"),
        "document_type": source.get("document_type"),
        "filing_date": source.get("filing_date"),
        "period_end": source.get("period_end") or source.get("report_date"),
        "local_file_path": source.get("local_path"),
        "source_url": source.get("source_url") or source.get("archive_url"),
    }


def _top_passages(sources: list[dict[str, Any]], keywords: tuple[str, ...], *, limit: int) -> list[dict[str, Any]]:
    passages = []
    for source in sources:
        text = source.get("text") or ""
        for keyword in keywords:
            snippet = _snippet_for(text, keyword)
            if not snippet:
                continue
            passages.append(
                {
                    "keyword": keyword,
                    "snippet": snippet,
                    "source": source,
                    "score": _keyword_score(snippet, keywords, source),
                }
            )
    return _dedupe_passages(sorted(passages, key=lambda passage: passage["score"], reverse=True))[:limit]


def _dedupe_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for passage in passages:
        source = passage.get("source") or {}
        snippet_key = str(passage.get("snippet") or "")[:160]
        key = (source.get("document_id") or source.get("local_path"), snippet_key)
        if key in seen:
            continue
        seen.add(key)
        result.append(passage)
    return result


def _keyword_score(snippet: str, keywords: tuple[str, ...], source: dict[str, Any]) -> int:
    lower = snippet.lower()
    score = sum(1 for keyword in keywords if keyword.lower() in lower)
    explanation_markers = (
        "increased",
        "decreased",
        "primarily",
        "mainly",
        "due to",
        "driven by",
        "compared with",
        "investment",
        "support",
        "costs of revenues",
        "operating expenses",
        "cash generated",
    )
    score += sum(2 for marker in explanation_markers if marker in lower)
    if source.get("source_role") == "annual_report":
        score += 2
    if source.get("source_role") == "latest_quarterly_or_6k":
        score += 1
    return score


def _snippet_for(text: str, keyword: str) -> str:
    if not text or not keyword:
        return ""
    match = re.search(re.escape(keyword), text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = _snippet_start(text, match.start())
    end = _snippet_end(text, match.end())
    snippet = text[start:end].strip()
    return re.sub(r"\s+", " ", snippet)


def _snippet_start(text: str, index: int) -> int:
    floor = max(0, index - 520)
    boundaries = [
        text.rfind(". ", floor, index),
        text.rfind("●", floor, index),
        text.rfind("•", floor, index),
        text.rfind("; ", floor, index),
    ]
    boundary = max(boundaries)
    if boundary >= floor and index - boundary < 360:
        return min(len(text), boundary + 2)
    return max(0, index - 180)


def _snippet_end(text: str, index: int) -> int:
    ceiling = min(len(text), index + 680)
    candidates = [
        text.find(". ", index, ceiling),
        text.find("●", index, ceiling),
        text.find("•", index, ceiling),
        text.find("; ", index, ceiling),
    ]
    candidates = [candidate for candidate in candidates if candidate != -1]
    if candidates:
        return min(candidates) + 1
    return ceiling


def _passage_to_evidence(
    passage: dict[str, Any],
    evidence_type: str,
    *,
    question_id: str | None = None,
    narrative_id: str | None = None,
) -> dict[str, Any]:
    source = passage.get("source") or {}
    target = question_id or narrative_id or "unknown"
    return {
        "evidence_id": f"{evidence_type}:{target}:{source.get('document_id') or source.get('local_path')}:{passage.get('keyword')}",
        "question_id": question_id,
        "narrative_id": narrative_id,
        "target_type": "question" if question_id else "narrative",
        "evidence_type": evidence_type,
        "source_document": source.get("document_id"),
        "source_document_type": source.get("document_type"),
        "source_section": _inferred_source_section(str(passage.get("keyword") or "")),
        "filing_date": source.get("filing_date"),
        "period": source.get("period_end") or source.get("report_date"),
        "local_file_path": source.get("local_path"),
        "quote_or_summary": passage.get("snippet"),
        "matched_keyword": passage.get("keyword"),
        "linked_layer1_metrics": [],
        "cross_validation_status": "not_tested",
        "impact_on_layer1": "clarifies",
    }


def _inferred_source_section(keyword: str) -> str:
    lower = keyword.lower()
    if "restricted cash" in lower or "vie" in lower or "debt" in lower:
        return "notes / liquidity / risk factors"
    if "non-gaap" in lower or "tax" in lower or "critical" in lower:
        return "non-GAAP / tax / accounting estimates"
    if "cost" in lower or "margin" in lower or "fulfillment" in lower:
        return "operating results / cost discussion"
    if "transaction services" in lower or "merchant" in lower or "kpi" in lower:
        return "business / revenue / KPI disclosure"
    return "official filing text"


def _layer1_fact_evidence(question: dict[str, Any], financial_pack: dict[str, Any]) -> dict[str, Any]:
    question_id = str(question.get("question_id") or "")
    return {
        "evidence_id": f"layer1:{question_id}",
        "question_id": question_id,
        "target_type": "question",
        "evidence_type": "filing_fact",
        "source_document": "financial_report_pack.json",
        "source_document_type": "financial_report_pack",
        "source_section": "diagnostic_findings",
        "period": _latest_annual_year(financial_pack),
        "quote_or_summary": _short_answer(question),
        "linked_layer1_metrics": _linked_metrics_for_question(question_id),
        "cross_validation_status": "matched",
        "impact_on_layer1": "clarifies",
    }


def _short_answer(question: dict[str, Any]) -> str:
    question_id = str(question.get("question_id") or "")
    values = question.get("latest_values") or {}
    if question_id == "growth_quality":
        return (
            f"最新年度收入同比 {_pct(values.get('revenue_growth_yoy'))}，"
            f"经营利润率 {_pct(values.get('operating_margin'))}，"
            f"增量经营利润率 {_pct(values.get('incremental_operating_margin'))}；"
            f"最大收入组件为 {_metric_label_zh(str(values.get('top_revenue_component') or '未识别'))}。"
        )
    if question_id == "profitability_with_scale":
        return (
            f"毛利率 {_pct(values.get('gross_margin'))}，经营利润率 {_pct(values.get('operating_margin'))}，"
            f"净利率 {_pct(values.get('net_margin'))}，增量经营利润率 {_pct(values.get('incremental_operating_margin'))}。"
        )
    if question_id == "cash_profit_quality":
        return (
            f"经营现金流 / 净利润 {_ratio(values.get('cash_conversion'))}，"
            f"营运资本现金顺风 / 收入 {_pct(values.get('working_capital_cash_tailwind_to_revenue'))}，"
            f"SBC / 经营现金流 {_pct(values.get('sbc_to_operating_cash_flow'))}。"
        )
    if question_id == "capital_needed_for_growth":
        return (
            f"资本开支 / 收入 {_pct(values.get('capex_to_revenue'))}，"
            f"自由现金流率 {_pct(values.get('free_cash_flow_margin'))}，"
            f"增量 ROIC 近似值 {_pct(values.get('incremental_roic_proxy'))}。"
        )
    if question_id == "balance_sheet_resilience":
        return (
            f"负债 / 资产 {_pct(values.get('liabilities_to_assets'))}，"
            f"流动比率 {_ratio(values.get('current_ratio'))}，"
            f"现金 / 总负债 {_ratio(values.get('cash_to_total_liabilities'))}，"
            f"受限现金 / 现金 {_pct(values.get('restricted_cash_to_cash'))}。"
        )
    if question_id == "sbc_and_per_share_quality":
        return (
            f"股权激励费用 / 收入 {_pct(values.get('sbc_to_revenue'))}，"
            f"股权激励费用 / 经营现金流 {_pct(values.get('sbc_to_operating_cash_flow'))}，"
            f"稀释股数同比 {_pct(values.get('diluted_shares_yoy'))}。"
        )
    if question_id == "tax_non_gaap_accounting_quality":
        return (
            f"有效税率 {_pct(values.get('effective_tax_rate'))}，"
            f"非 GAAP 净利润调整幅度 {_pct(values.get('latest_non_gaap_net_income_uplift'))}。"
        )
    return str(question.get("current_answer") or question.get("answer") or question.get("question") or "")


def _ratio(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return str(value)


def _metric_label_zh(metric: str) -> str:
    labels = {
        "transaction_services_revenue": "交易服务收入",
        "online_marketing_services_revenue": "在线营销服务及其他收入",
        "revenue": "收入",
        "accounts_payable_and_accrued_expenses": "应付账款及应计费用",
        "payable_to_merchants": "应付商家款项",
        "merchant_deposits": "商家保证金",
        "deferred_revenue": "递延收入",
        "未识别": "未识别",
    }
    return labels.get(metric, metric)


def _latest_annual_year(financial_pack: dict[str, Any]) -> str | None:
    rows = financial_pack.get("annual_facts") or []
    years = [row.get("year") for row in rows if row.get("year") is not None]
    return str(max(years)) if years else None


def _linked_metrics_for_question(question_id: str) -> list[str]:
    mapping = {
        "growth_quality": ["revenue_growth", "incremental_operating_margin", "source_of_growth_attribution_v1"],
        "profitability_with_scale": ["gross_margin", "operating_margin", "incremental_operating_margin"],
        "cash_profit_quality": ["cash_conversion", "working_capital_quality_v1"],
        "capital_needed_for_growth": ["capex_to_revenue", "free_cash_flow_margin"],
        "balance_sheet_resilience": ["current_ratio", "restricted_cash_to_cash", "liabilities_to_assets"],
        "sbc_and_per_share_quality": ["sbc_to_revenue", "diluted_share_growth"],
        "tax_non_gaap_accounting_quality": ["effective_tax_rate", "non_gaap_net_income_uplift"],
    }
    return mapping.get(question_id, [])


def _answer_status(
    question: dict[str, Any],
    management_explanations: list[dict[str, Any]],
    still_unknown: list[str],
) -> str:
    warnings = question.get("warning_flags") or []
    if management_explanations and warnings:
        return "partial"
    if management_explanations and not still_unknown:
        return "answered"
    if management_explanations:
        return "partial"
    return "unknown"


def _cross_check_status(question: dict[str, Any]) -> str:
    warnings = question.get("warning_flags") or []
    missing = question.get("missing") or []
    if warnings and missing:
        return "tension"
    if warnings:
        return "tension"
    if missing:
        return "not_tested"
    return "matched"


def _cross_check_reason(question: dict[str, Any], management_explanations: list[dict[str, Any]]) -> str:
    warnings = question.get("warning_flags") or []
    if warnings:
        return "第一层数字存在红旗，官方解释即使存在也只能先视为部分解释。"
    if management_explanations:
        return "官方文件提供了相关解释，且第一层没有触发直接冲突。"
    return "未找到足够官方解释，不能形成交叉验证结论。"


def _question_inference(
    question: dict[str, Any],
    management_explanations: list[dict[str, Any]],
    still_unknown: list[str],
) -> str:
    answer = _short_answer(question)
    if management_explanations and still_unknown:
        return f"{answer} 官方文件提供了相关叙事，但仍缺少 {'、'.join(still_unknown[:2])}，所以当前版本只能给出部分解释。"
    if management_explanations:
        return f"{answer} 官方文件中存在可对应的说明，当前版本将其视为对第一层判断的补充解释。"
    return f"{answer} 当前版本未在官方文件包中找到足够解释，应保持未知并进入下一层研究。"


def _confidence_label(status: str, has_unknown: bool, cross_check: str) -> str:
    if status == "answered" and not has_unknown and cross_check == "matched":
        return "high"
    if status in {"answered", "partial"}:
        return "medium"
    return "low"


def _impact_on_layer1(question: dict[str, Any], status: str, cross_check: str) -> str:
    if status == "unknown":
        return "no_change"
    if cross_check == "tension":
        return "clarifies"
    if (question.get("warning_flags") or []):
        return "clarifies"
    return "supports"


def _missing_label(item: Any) -> str:
    translations = {
        "merchant cohort economics": "商家分群 / 单商家经济性",
        "accounts_receivable": "应收账款",
        "inventory": "存货",
        "maintenance capex versus growth capex": "维护性资本开支与增长性资本开支拆分",
        "debt": "债务",
        "debt_current": "一年内到期债务",
        "debt_noncurrent": "长期债务",
        "buyback offset analysis": "回购是否抵消股权激励稀释",
        "full per-ADS dilution bridge": "完整 ADS / 普通股稀释桥",
        "cash_paid_for_taxes": "现金纳税",
        "impairment": "减值项目",
    }
    return translations.get(str(item), str(item))


def _narrative_metric_support(financial_pack: dict[str, Any], narrative_id: str) -> dict[str, Any] | None:
    if narrative_id != "transaction_services_revenue_mix":
        return None
    for metric in financial_pack.get("financial_metrics") or []:
        if metric.get("formula_id") != "source_of_growth_attribution_v1":
            continue
        result = metric.get("latest_interim_result") or {}
        details = result.get("component_details") or []
        if not details:
            return None
        top = max(details, key=lambda item: item.get("share_of_revenue") or 0)
        if top.get("metric") != "transaction_services_revenue":
            return None
        return {
            "period": result.get("period_end"),
            "summary": (
                f"最新可抽取收入组件覆盖 { _pct(result.get('value')) }；"
                f"交易服务收入占收入 { _pct(top.get('share_of_revenue')) }，为最大组件。"
            ),
        }
    return None


def _pct(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _money_bn(value: Any) -> str:
    if value is None:
        return "未披露"
    try:
        return f"RMB {float(value) / 1_000_000_000:.1f}B"
    except (TypeError, ValueError):
        return str(value)


def _delta_bn(latest: dict[str, Any], prior: dict[str, Any], key: str) -> str:
    if latest.get(key) is None or prior.get(key) is None:
        return "未披露"
    return _money_bn(float(latest[key]) - float(prior[key]))


def _change_bn_phrase(latest: dict[str, Any], prior: dict[str, Any], key: str) -> str:
    if latest.get(key) is None or prior.get(key) is None:
        return "未披露"
    delta = float(latest[key]) - float(prior[key])
    verb = "增加" if delta >= 0 else "减少"
    return f"{verb} {_money_bn(abs(delta))}"


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        return float(numerator) / denominator_value
    except (TypeError, ValueError):
        return None


def _point_change(latest: float | None, prior: float | None) -> str:
    if latest is None or prior is None:
        return "未披露"
    return f"{(latest - prior) * 100:.1f} 个百分点"


def _point_change_phrase(latest: float | None, prior: float | None) -> str:
    if latest is None or prior is None:
        return "未披露"
    delta = latest - prior
    verb = "上升" if delta >= 0 else "下降"
    return f"{verb} {abs(delta) * 100:.1f} 个百分点"


def _ratio_from_row(row: dict[str, Any], numerator: str, denominator: str) -> float | None:
    return _safe_ratio(row.get(numerator), row.get(denominator))


def _component_value(components: list[dict[str, Any]], metric_name: str) -> dict[str, Any]:
    return next((component for component in components if component.get("metric") == metric_name), {})


def _narrative_inference(narrative_id: str, has_metric_support: bool, has_passages: bool) -> str:
    if narrative_id == "transaction_services_revenue_mix" and has_metric_support:
        return "官方数字显示交易服务已成为最新季度最大收入组件，这会改变对收入来源的读法，但不能单独证明增长质量。"
    if narrative_id == "first_party_brand":
        return "自营品牌业务是官方叙事中的战略举措，可能改变平台轻重和供应链控制深度；投入回报仍需验证。"
    if narrative_id == "supply_chain_investment":
        return "供应链和商家支持叙事可解释部分利润率压力，但需要用费用率、现金流和后续季度结果继续验证。"
    if narrative_id == "restricted_cash_vie":
        return "受限现金和 VIE 叙事会影响现金安全垫读法，账面现金不能自动视为可自由分配现金。"
    if narrative_id == "agm_ads_voting_board":
        return "AGM / proxy 材料提供治理事实：它能说明董事重选和 ADS 投票机制，但不能单独证明治理质量。"
    if narrative_id == "share_plan_extension":
        return "股权计划期限延长会拉长激励工具的可用期；当前还需要和 SBC、稀释、回购抵消情况一起判断。"
    if has_passages:
        return "官方文件中出现相关叙事，V1 将其登记为需要后续跟踪的决策相关信息。"
    return "V1 仅有指标线索，仍需官方文本或下一层研究验证。"


def _narrative_unknowns(narrative_id: str) -> list[str]:
    mapping = {
        "transaction_services_revenue_mix": ["全年业务线结构是否稳定披露", "交易服务收入增长的价格/量/服务拆分"],
        "first_party_brand": ["是否承担库存风险", "单独收入、利润和投入回收期"],
        "supply_chain_investment": ["商家支持的金额与持续性", "投入能否转化为利润率修复"],
        "global_business_temu": ["Temu 单独收入、利润、GMV 和履约成本"],
        "restricted_cash_vie": ["现金可转移性和 VIE 结构下的实际分配能力"],
        "management_governance_change": ["变化对执行质量和资本配置纪律的影响"],
        "agm_ads_voting_board": ["ADS 持有人实际投票参与情况", "下一次 AGM 是否继续出现较高反对票", "是否出现治理争议"],
        "share_plan_extension": ["剩余可授予股份", "未来 SBC 强度", "回购是否抵消激励稀释"],
        "audit_accounting_reliability": ["关键审计事项的敏感性和后续变化"],
    }
    return mapping.get(narrative_id, ["官方文件未提供足够量化信息"])


def _narrative_follow_up(narrative_id: str) -> list[str]:
    mapping = {
        "transaction_services_revenue_mix": ["继续跟踪交易服务与在线营销收入占比。"],
        "first_party_brand": ["在业绩电话会和后续 6-K 中追问自营品牌业务的资本需求和利润影响。"],
        "supply_chain_investment": ["跟踪费用率、履约成本、商家支持和经营现金流是否随投入改善。"],
        "global_business_temu": ["需要第三层跟踪管理层对海外业务、合规和履约成本的解释。"],
        "restricted_cash_vie": ["回到年报附注和 VIE 风险因素，确认现金可用性和资金转移限制。"],
        "management_governance_change": ["检查相关 6-K / 代理声明 / 股东会文件是否披露职责、薪酬或控制权变化。"],
        "agm_ads_voting_board": ["跟踪 AGM 投票结果、董事重选反对率和 ADS voting instruction 机制是否影响少数股东权利。"],
        "share_plan_extension": ["把股权计划期限延长与 SBC / 收入、SBC / 经营现金流、稀释股数和回购桥表一起跟踪。"],
        "audit_accounting_reliability": ["跟踪审计师、ICFR、关键审计事项和会计估计是否变化。"],
    }
    return mapping.get(narrative_id, ["进入后续官方文件和第三层研究跟踪。"])


def _build_layer1_update(question_answers: list[dict[str, Any]], narratives: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "confidence_up": [
            answer["question_title"]
            for answer in question_answers
            if answer.get("impact_on_layer1") == "supports"
        ],
        "confidence_down": [
            answer["question_title"]
            for answer in question_answers
            if answer.get("answer_status") == "unknown"
        ],
        "clarified": [
            answer["question_title"]
            for answer in question_answers
            if answer.get("impact_on_layer1") == "clarifies"
        ],
        "still_unknown": _dedupe_list(
            unknown
            for answer in question_answers
            for unknown in answer.get("still_unknown", [])
        ),
        "new_narratives_to_track": [narrative.get("title") for narrative in narratives],
        "next_research_questions": _dedupe_list(
            item
            for narrative in narratives
            for item in narrative.get("follow_up_needed", [])
        ),
    }


def _quality_flags(
    question_answers: list[dict[str, Any]],
    narratives: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flags = []
    if not any(source.get("source_role") == "annual_report" for source in sources):
        flags.append({"severity": "high", "message": "缺少年报/20-F/10-K 官方文本，第二层证据不完整。"})
    if any(answer.get("answer_status") == "unknown" for answer in question_answers):
        flags.append({"severity": "medium", "message": "部分第一层问题未能在官方文件中找到解释。"})
    if not narratives:
        flags.append({"severity": "low", "message": "未发现决策相关叙事；可能需要补充公司 watchlist 或前期差异对比。"})
    return flags


def _dedupe_list(items) -> list[str]:
    result = []
    for item in items:
        if not item:
            continue
        text = str(item)
        if text not in result:
            result.append(text)
    return result


def _question_answer_markdown(answer: dict[str, Any]) -> list[str]:
    unknowns = answer.get("still_unknown") or ["暂无明确未知项"]
    rendered = answer.get("rendered_answer") or {}
    return [
        f"### {answer.get('question_title')}",
        "",
        f"- 回答状态：{_answer_status_zh(answer.get('answer_status'))}；对第一层影响：{_impact_zh(answer.get('impact_on_layer1'))}。",
        f"- 文件事实：{rendered.get('filing_facts') or _question_fact_detail_zh(answer)}",
        f"- 官方解释：{rendered.get('official_explanation') or _question_official_explanation_zh(answer)}",
        f"- 与第一层数字交叉验证：{(answer.get('cross_check_with_layer1') or {}).get('reason')}",
        f"- 我们的判断：{rendered.get('our_judgment') or _question_judgment_zh(answer)}",
        f"- 来源追踪：{rendered.get('source_trace') or _question_source_trace_zh(answer)}",
        f"- 仍未知：{'；'.join(unknowns)}。",
        f"- 后续跟踪：{'；'.join(answer.get('follow_up_needed') or [])}",
        "",
    ]


def _question_fact_detail_zh(answer: dict[str, Any]) -> str:
    question_id = str(answer.get("question_id") or "")
    context = answer.get("context") or {}
    latest = context.get("latest_annual") or {}
    prior = context.get("prior_annual") or {}
    latest_values = answer.get("latest_values") or {}
    if question_id == "growth_quality":
        return (
            f"2025 年收入 {_money_bn(latest.get('revenue'))}，同比 {_pct(latest_values.get('revenue_growth_yoy'))}；"
            f"收入比 2024 年{_change_bn_phrase(latest, prior, 'revenue')}，但经营利润{_change_bn_phrase(latest, prior, 'operating_income')}，"
            f"对应增量经营利润率 {_pct(latest_values.get('incremental_operating_margin'))}。"
        )
    if question_id == "profitability_with_scale":
        cost_ratio_latest = 1 - (_ratio_from_row(latest, "gross_profit", "revenue") or 0)
        cost_ratio_prior = 1 - (_ratio_from_row(prior, "gross_profit", "revenue") or 0)
        opex_ratio_latest = _safe_ratio((latest.get("gross_profit") or 0) - (latest.get("operating_income") or 0), latest.get("revenue"))
        opex_ratio_prior = _safe_ratio((prior.get("gross_profit") or 0) - (prior.get("operating_income") or 0), prior.get("revenue"))
        return (
            f"2025 年毛利率 {_pct(latest_values.get('gross_margin'))}、经营利润率 {_pct(latest_values.get('operating_margin'))}、"
            f"净利率 {_pct(latest_values.get('net_margin'))}；经营利润率较 2024 年{_point_change_phrase(_ratio_from_row(latest, 'operating_income', 'revenue'), _ratio_from_row(prior, 'operating_income', 'revenue'))}。"
            f"成本率约从 {_pct(cost_ratio_prior)} 升至 {_pct(cost_ratio_latest)}，经营费用率约从 {_pct(opex_ratio_prior)} 升至 {_pct(opex_ratio_latest)}。"
        )
    if question_id == "cash_profit_quality":
        wc = context.get("working_capital") or {}
        return (
            f"2025 年经营现金流 {_money_bn(latest.get('operating_cash_flow'))}，净利润 {_money_bn(latest.get('net_income'))}，"
            f"经营现金流 / 净利润 {_ratio(latest_values.get('cash_conversion'))}；"
            f"经营负债净增加 {_money_bn(wc.get('cash_source_liability_delta'))}，约占收入 {_pct(latest_values.get('working_capital_cash_tailwind_to_revenue'))}。"
        )
    if question_id == "capital_needed_for_growth":
        capital = context.get("capital_intensity") or {}
        return (
            f"2025 年资本开支 {_money_bn(latest.get('capex'))}，资本开支 / 收入 {_pct(latest_values.get('capex_to_revenue'))}；"
            f"自由现金流率 {_pct(latest_values.get('free_cash_flow_margin'))}，自由现金流 / 经营现金流 {_pct(capital.get('free_cash_flow_to_operating_cash_flow'))}；"
            f"增量 ROIC 近似值 {_pct(latest_values.get('incremental_roic_proxy'))}。"
        )
    if question_id == "balance_sheet_resilience":
        broad_cash = (latest.get("cash") or 0) + (latest.get("restricted_cash") or 0) + (latest.get("short_term_investments") or 0)
        return (
            f"2025 年现金 {_money_bn(latest.get('cash'))}、受限现金 {_money_bn(latest.get('restricted_cash'))}、短期投资 {_money_bn(latest.get('short_term_investments'))}，"
            f"合计约 {_money_bn(broad_cash)}；流动比率 {_ratio(latest_values.get('current_ratio'))}，负债 / 资产 {_pct(latest_values.get('liabilities_to_assets'))}，"
            f"受限现金 / 现金 {_pct(latest_values.get('restricted_cash_to_cash'))}。"
        )
    if question_id == "sbc_and_per_share_quality":
        return (
            f"2025 年股权激励费用 {_money_bn(latest.get('stock_based_compensation'))}，占收入 {_pct(latest_values.get('sbc_to_revenue'))}、"
            f"占经营现金流 {_pct(latest_values.get('sbc_to_operating_cash_flow'))}；稀释股数同比 {_pct(latest_values.get('diluted_shares_yoy'))}。"
        )
    if question_id == "tax_non_gaap_accounting_quality":
        tax = context.get("tax") or {}
        non_gaap = context.get("latest_interim_non_gaap") or {}
        return (
            f"2025 年有效税率 {_pct(latest_values.get('effective_tax_rate'))}；投资收益 / 税前利润 {_pct(tax.get('investment_income_to_pretax'))}。"
            f"最新季度非 GAAP 净利润调整幅度 {_pct(non_gaap.get('non_gaap_net_income_uplift'))}，主要已抽取调整项为股权激励费用 {_money_bn((non_gaap.get('adjustments') or {}).get('non_gaap_adjustment_share_based_compensation'))}。"
        )
    return _evidence_summary(answer.get("filing_facts") or [])


def _question_official_explanation_zh(answer: dict[str, Any]) -> str:
    question_id = str(answer.get("question_id") or "")
    context = answer.get("context") or {}
    source_growth = context.get("source_growth") or {}
    components = source_growth.get("component_details") or []
    transaction = _component_value(components, "transaction_services_revenue")
    online = _component_value(components, "online_marketing_services_revenue")
    if question_id == "growth_quality":
        return (
            f"20-F 把收入来源定义为交易服务和在线营销服务及其他；第一层最新季度结构化数据记录交易服务收入 {_money_bn(transaction.get('value'))}，"
            f"占收入 {_pct(transaction.get('share_of_revenue'))}，在线营销服务及其他收入 {_money_bn(online.get('value'))}，占收入 {_pct(online.get('share_of_revenue'))}。"
            "这能解释“收入来自哪一类业务”，但不能解释新增收入为什么没有带来新增经营利润。"
        )
    if question_id == "profitability_with_scale":
        return (
            "20-F 把收入成本主要归为支付处理费、平台运营成本、履约费、商家支持、带宽和服务器、折旧摊销等；"
            "第一层最新季度结构化数据也显示成本项与履约费、带宽和服务器成本、支付处理费相关。"
            "这说明利润率压力更可能来自履约/平台/商家支持等投入端，而不是收入确认本身。"
        )
    if question_id == "cash_profit_quality":
        wc = context.get("working_capital") or {}
        details = wc.get("component_details") or []
        top = sorted(details, key=lambda item: abs(item.get("delta") or 0), reverse=True)[:3]
        parts = [f"{_metric_label_zh(str(item.get('metric')))}增加 {_money_bn(item.get('delta'))}" for item in top if item.get("delta") is not None]
        return (
            "官方现金流表显示经营现金流仍高于净利润；但营运资本桥显示现金流有经营负债顺风，"
            + ("其中" + "、".join(parts) + "。" if parts else "")
            + "所以这更像“平台浮存金支持下的强现金流”，不是完全由利润本身解释。"
        )
    if question_id == "capital_needed_for_growth":
        return (
            "官方财报显示账面资本开支很低，说明当前投入并未主要表现为固定资产扩张；"
            "但公司同时强调供应链和自营品牌投入，这些投入可能更多体现在费用、商家支持或履约成本中。"
            "因此，低资本开支不能直接证明投入回报高。"
        )
    if question_id == "balance_sheet_resilience":
        return (
            "官方文件同时披露大量现金、短期投资、受限现金和 VIE / 跨境资金转移限制。"
            "这支持“资产负债表有缓冲”，但也要求把可自由动用现金和受限/结构性受约束现金分开看。"
        )
    if question_id == "sbc_and_per_share_quality":
        return (
            "官方文件披露股权激励费用和 ADS / 稀释每股收益；当前股权激励费用占收入和经营现金流比例不高，"
            "稀释股数同比也很小。尚未看到它成为主线风险，但仍需确认回购与股权激励的抵消关系。"
        )
    if question_id == "tax_non_gaap_accounting_quality":
        return (
            "第一层最新季度结构化数据包含非 GAAP 与 GAAP 调节，主要调整项是股权激励费用；"
            "20-F 显示 2025 年投资收益占税前利润比例较高，因此净利润读法不能只看最终归母净利润，还要区分经营利润和金融/投资收益。"
        )
    return _evidence_summary(answer.get("management_explanations") or [])


def _question_judgment_zh(answer: dict[str, Any]) -> str:
    question_id = str(answer.get("question_id") or "")
    if question_id == "growth_quality":
        return "官方文件能解释收入结构和季度增长来源，但不能完全解释年度层面“收入增长、经营利润下降”的矛盾；因此第一层增长质量判断仍应保持谨慎。"
    if question_id == "profitability_with_scale":
        return "成本率和费用率同时上升，与官方披露的履约、服务器、支付处理、商家支持和供应链投入方向一致；但官方文件没有把这些投入逐项量化到利润率下降。"
    if question_id == "cash_profit_quality":
        return "现金流结论不是空泛的“好”：经营现金流确实覆盖净利润，但其中一部分来自应付商家款项、应计费用和保证金等经营负债增加。"
    if question_id == "capital_needed_for_growth":
        return "公司仍表现为低资本开支模式，但新增经营利润为负，说明当前投入回报尚未体现；这更像投入期问题，而不是传统重资产扩张问题。"
    if question_id == "balance_sheet_resilience":
        return "资产负债表足以支撑一段投入期，但受限现金比例高、债务明细缺失、VIE 资金转移限制会降低“现金可自由使用”的确定性。"
    if question_id == "sbc_and_per_share_quality":
        return "股权激励和稀释目前不是主要反证，但报告还不能证明每股价值创造，因为缺少回购是否抵消激励稀释的完整桥表。"
    if question_id == "tax_non_gaap_accounting_quality":
        return "非 GAAP 调整幅度不算失控，但投资收益对税前利润贡献较高；读利润时应优先看经营利润，而不是只看净利润。"
    return (answer.get("our_inference") or {}).get("text") or ""


def _question_source_trace_zh(answer: dict[str, Any]) -> str:
    sources = []
    for item in answer.get("evidence_bundle") or []:
        source_type = item.get("source_document_type")
        source_document = item.get("source_document")
        if source_type == "financial_report_pack":
            label = f"第一层财务数据包，{item.get('period') or '当前期间'}，{item.get('source_section') or '结构化指标'}"
        else:
            label = "，".join(
                part
                for part in [
                    str(item.get("filing_date") or ""),
                    str(source_type or source_document or ""),
                    str(item.get("source_section") or ""),
                ]
                if part
            )
            if source_document:
                label = f"{label}，{source_document}"
        if label and label not in sources:
            sources.append(label)
    if not sources:
        return "来源未标注。"
    return "；".join(sources[:3])


def _narrative_markdown(narrative: dict[str, Any]) -> list[str]:
    return [
        f"### {narrative.get('title')}",
        "",
        f"- 类型：{_narrative_type_zh(narrative.get('narrative_type'))}；状态：{_change_status_zh(narrative.get('change_status'))}。",
        f"- 文件事实：{_narrative_fact_detail_zh(narrative)}",
        f"- 管理层解释：{_narrative_management_detail_zh(narrative)}",
        f"- 为什么重要：{narrative.get('why_it_matters')}",
        f"- 我们的推断：{_narrative_judgment_detail_zh(narrative)}",
        f"- 仍未知：{'；'.join(narrative.get('still_unknown') or [])}。",
        f"- 后续跟踪：{'；'.join(narrative.get('follow_up_needed') or [])}",
        "",
    ]


def _narrative_fact_detail_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return "最新季度已抽取收入组件覆盖 100.0%；交易服务收入 RMB 56.3B，占收入 53.0%，在线营销服务及其他收入 RMB 49.9B，占 47.0%。"
    if narrative_id == "first_party_brand":
        return "最新 earnings release 把供应链投入列为未来核心战略优先事项，并明确提到将投入重要资源建设自营品牌业务。"
    if narrative_id == "supply_chain_investment":
        return "20-F 把商家支持、履约、带宽和服务器等列入收入成本；最新 earnings release 同时强调供应链能力投入。"
    if narrative_id == "global_business_temu":
        return "20-F 披露 Temu 于 2022 年 9 月推出，并已扩展至美国、日本、德国、英国、法国、加拿大、意大利等市场；但公司仍未单独披露 Temu 收入、利润或履约成本。"
    if narrative_id == "restricted_cash_vie":
        return "2025 年现金 RMB 108.9B、受限现金 RMB 73.8B、短期投资 RMB 313.4B；同时 20-F 披露 VIE 和中国境内资金转移限制。"
    if narrative_id == "management_governance_change":
        return "20-F 和后续 6-K 列示 Lei Chen 与 Zhao Jiazhen 为联席董事长兼联席 CEO；2025 年 12 月 6-K 还披露 Jiazhen Zhao 被任命为联席董事长，并任命 Mi Wang 为工程高级副总裁、Jiong Li 为财务负责人。"
    if narrative_id == "agm_ads_voting_board":
        return "Proxy / AGM 材料披露 ADS 持有人需要通过存托人提交投票指示；2025 年 AGM 结果显示 5.647B votes、占记录日总投票权 99.2% 出席或由代理出席，六项董事重选普通决议均通过。"
    if narrative_id == "share_plan_extension":
        return "2025 年 6-K 附件披露董事会和薪酬委员会批准修订 2015 Global Share Plan，将该计划期限由初始生效日起 10 年延长至 20 年。"
    if narrative_id == "audit_accounting_reliability":
        return "20-F 披露独立注册会计师对 2025 年财报和内控有效性出具审计意见；当前第二层未识别到重述或重大内控缺陷。"
    return _evidence_summary(narrative.get("filing_facts") or [])


def _narrative_management_detail_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return "管理层在最新季度披露中把收入增长主要归因于交易服务收入增加。"
    if narrative_id == "first_party_brand":
        return "管理层称供应链投入是下一阶段核心战略重点，自营品牌业务用于打开供应链伙伴机会并提升客户价值。"
    if narrative_id == "supply_chain_investment":
        return "管理层把当前投入描述为供应链能力建设和平台生态投入，而不是短期利润最大化。"
    if narrative_id == "global_business_temu":
        return "管理层没有在当前财务包中给出 Temu 单独收入或利润解释，因此只能确认战略存在，不能确认单位经济性。"
    if narrative_id == "restricted_cash_vie":
        return "公司在风险披露中提示境内子公司、VIE 及其子公司的现金可能受监管、汇兑和跨境转移限制影响。"
    if narrative_id == "management_governance_change":
        return "治理和任命文件确认组织职责变化，但没有解释这些变化对资本配置、执行质量或内部控制的影响。"
    if narrative_id == "agm_ads_voting_board":
        return "AGM / proxy 材料主要提供治理流程、董事重选和投票结果，不提供经营或财务解释。"
    if narrative_id == "share_plan_extension":
        return "该文件只披露股权计划期限延长，不解释未来授予节奏、SBC 强度或稀释影响。"
    if narrative_id == "audit_accounting_reliability":
        return "管理层和审计师都把内控有效性作为审计/披露对象；但关键审计事项和会计估计仍需要持续跟踪。"
    return _evidence_summary(narrative.get("management_explanations") or [])


def _narrative_judgment_detail_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return "这是当前最明确的公司特有经营线索：收入结构已经不是单纯广告/流量变现，交易服务成为更重要的收入来源。"
    if narrative_id == "first_party_brand":
        return "自营品牌可能提升供应链控制力，也可能带来库存、质量控制、履约和资本占用风险；现在只能作为待验证战略变量。"
    if narrative_id == "supply_chain_investment":
        return "它能解释利润率短期承压的方向，但还没有足够量化证据证明投入未来一定带来更高利润率。"
    if narrative_id == "global_business_temu":
        return "Temu 是重要增长叙事，但官方财报没有给出单独财务闭环，因此不能把海外业务质量写成已验证事实。"
    if narrative_id == "restricted_cash_vie":
        return "现金安全垫很强，但可自由使用现金要打折理解；这会影响资产负债表质量的置信度。"
    if narrative_id == "management_governance_change":
        return "管理层与关键财务/工程岗位变化不直接推翻财务主线，但会影响执行风险和组织转型判断，应该进入后续治理监控。"
    if narrative_id == "agm_ads_voting_board":
        return "董事重选均获通过，说明没有直接治理否决信号；但部分董事存在约 8%-14% 的反对票，值得作为治理温度计继续跟踪。"
    if narrative_id == "share_plan_extension":
        return "这会把“稀释暂未成为主线风险”的判断变成持续监控项：当前 SBC 和稀释不高，但计划期限延长说明长期激励工具仍然重要。"
    if narrative_id == "audit_accounting_reliability":
        return "审计和内控披露支持财报可用性，但不能替代对收入确认、补贴分类和非 GAAP 调整的持续检查。"
    return str(narrative.get("our_inference") or "")


def _evidence_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "官方文件未提供足够直接证据。"
    summaries = []
    for item in items[:2]:
        text = _evidence_text_zh(item)
        source = _source_document_label_zh(item.get("source_document_type") or item.get("source_document"))
        summaries.append(f"{text}（{source}）")
    return "；".join(summaries)


def _evidence_text_zh(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_document_type") or "")
    raw = _normalize_report_text_zh(str(item.get("quote_or_summary") or "").strip())
    if source_type == "financial_report_pack":
        return raw
    keyword = str(item.get("matched_keyword") or "").lower()
    narrative_id = str(item.get("narrative_id") or "")
    question_id = str(item.get("question_id") or "")
    if any(term in keyword for term in ("restricted cash", "vie", "transfer", "dividend", "debt", "convertible")) or narrative_id == "restricted_cash_vie":
        return "官方文件披露受限现金、VIE、债务或跨境资金转移限制，影响现金安全垫读法。"
    if any(term in keyword for term in ("non-gaap", "tax", "investment income", "critical accounting", "impairment")) or question_id == "tax_non_gaap_accounting_quality":
        return "官方文件披露非 GAAP 调节、税项、投资收益或关键会计估计信息，可用于拆分净利润质量。"
    if "cash" in keyword or "working capital" in keyword or question_id == "cash_profit_quality":
        return "官方文件披露经营现金流和现金流量表摘要，可用于核对利润现金化和营运资本影响。"
    if "transaction services" in keyword or "online marketing" in keyword or question_id == "growth_quality":
        return "官方文件说明收入主要由交易服务和在线营销服务及其他构成；相关增长主要来自交易服务收入。"
    if any(term in keyword for term in ("cost", "fulfillment", "server", "sales and marketing", "operating profit")) or question_id == "profitability_with_scale":
        return "官方文件披露成本、履约、平台运营、商家支持、销售与营销等费用项目，可用于解释利润率变化。"
    if any(term in keyword for term in ("capital", "property", "software", "investment")) or question_id == "capital_needed_for_growth":
        return "官方文件披露资本开支、软件、使用权资产或供应链投入相关信息，可用于判断资本需求。"
    if any(term in keyword for term in ("share-based", "stock-based", "diluted", "ads", "share plan")) or question_id == "sbc_and_per_share_quality":
        return "官方文件披露股权激励、稀释股数或 ADS 每股收益信息，可用于判断每股质量。"
    if "first-party" in keyword or "brand" in keyword or narrative_id == "first_party_brand":
        return "官方文件披露自营品牌业务和相关投入计划，提示公司可能更深介入供应链与产品控制。"
    if "supply chain" in keyword or "merchant support" in keyword or narrative_id == "supply_chain_investment":
        return "官方文件强调供应链投入和商家支持，这可能解释部分短期利润率压力。"
    if "temu" in keyword or "global" in keyword or "overseas" in keyword or narrative_id == "global_business_temu":
        return "官方文件涉及全球业务、Temu 或跨境监管/履约风险，需要持续跟踪。"
    if any(term in keyword for term in ("chief executive", "chairman", "director", "annual general meeting")) or narrative_id == "management_governance_change":
        return "官方文件披露董事、高管、董事会或股东会相关信息，可用于跟踪治理变化。"
    if any(term in keyword for term in ("independent registered", "material weakness", "internal control", "auditor")) or narrative_id == "audit_accounting_reliability":
        return "官方文件披露审计师、内控或会计可靠性相关信息。"
    if raw:
        return raw[:257].rstrip() + "..." if len(raw) > 260 else raw
    return "官方文件中出现相关披露，但 V1 未生成更细中文摘要。"


def _answer_status_zh(status: Any) -> str:
    labels = {
        "answered": "已回答",
        "partial": "部分回答",
        "unknown": "仍未知",
        "contradicted": "存在矛盾",
    }
    return labels.get(str(status), str(status or "未知"))


def _impact_zh(impact: Any) -> str:
    labels = {
        "supports": "支持",
        "weakens": "削弱",
        "clarifies": "澄清但不完全证明",
        "no_change": "不改变",
        "creates_new_question": "产生新问题",
    }
    return labels.get(str(impact), str(impact or "未知"))


def _narrative_type_zh(narrative_type: Any) -> str:
    labels = {
        "strategic_initiative": "战略举措",
        "business_model_change": "商业模式变化",
        "KPI": "公司特有 KPI",
        "regulation": "监管 / VIE / 结构性风险",
        "governance": "治理 / 管理层变化",
        "accounting": "审计 / 会计可靠性",
        "capital_allocation": "资本配置",
    }
    return labels.get(str(narrative_type), str(narrative_type or "未知"))


def _change_status_zh(status: Any) -> str:
    labels = {
        "new": "新增",
        "strengthened": "强化",
        "repeated": "重复出现",
        "de_emphasized": "弱化",
        "detected_in_current_official_package": "当前官方文件包中已识别",
    }
    return labels.get(str(status), str(status or "未知"))


def _business_hypothesis_markdown(narratives: list[dict[str, Any]]) -> list[str]:
    if not narratives:
        return ["- 当前官方文件不足以生成新的商业模式假设。"]
    titles = [str(item.get("title")) for item in narratives[:5]]
    return [
        "- 当前官方文件支持的商业模式假设：" + "；".join(titles) + " 是需要持续跟踪的主线。",
        "- 官方文件能支持：这些主题在官方文件或第一层指标中有证据，适合进入后续报告监控。",
        "- 官方文件不能证明：它们是否真正构成护城河、是否改善客户/商家经济性、是否能带来长期资本回报，需要第三层和一手研究验证。",
    ]


def _layer1_update_markdown(update: dict[str, Any]) -> list[str]:
    return [
        "- 提高置信度：" + _join_or_none(update.get("confidence_up")),
        "- 降低置信度：" + _join_or_none(update.get("confidence_down")),
        "- 已解释/澄清：" + _join_or_none(update.get("clarified")),
        "- 仍未知：" + _join_or_none(update.get("still_unknown")),
        "- 新增跟踪叙事：" + _join_or_none(update.get("new_narratives_to_track")),
    ]


def _next_research_markdown(update: dict[str, Any]) -> list[str]:
    questions = update.get("next_research_questions") or []
    if not questions:
        return ["- 暂无新增下一层研究问题。"]
    return [f"- {question}" for question in questions[:8]]


def _join_or_none(items: Any) -> str:
    values = [str(item) for item in (items or []) if item]
    return "；".join(values) if values else "无"


def _source_role_zh(role: Any) -> str:
    labels = {
        "annual_report": "年报主文件",
        "latest_quarterly_or_6k": "最新季度 / 6-K",
        "governance_proxy_agm": "代理声明 / AGM / 治理材料",
        "material_event": "重大事项文件",
    }
    return labels.get(str(role), str(role or "未知来源"))


def _source_document_label_zh(source: Any) -> str:
    text = str(source or "")
    labels = {
        "financial_report_pack": "第一层财务数据包",
        "financial_report_pack.json": "第一层财务数据包",
    }
    return labels.get(text, text or "未知来源")


def _normalize_report_text_zh(text: str) -> str:
    replacements = {
        "non-GAAP": "非 GAAP",
        "Non-GAAP": "非 GAAP",
        "uplift": "调整幅度",
        "ROIC proxy": "ROIC 近似值",
        "incremental ROIC proxy": "增量 ROIC 近似值",
        "CapEx": "资本开支",
        "capex": "资本开支",
        "merchant cohort": "商家分群",
        "merchant support": "商家支持",
        "First-party brand": "自营品牌",
        "first-party brand": "自营品牌",
        "strategic initiative": "战略举措",
        "initiative": "举措",
        "earnings call": "业绩电话会",
        "accounting estimate": "会计估计",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result
