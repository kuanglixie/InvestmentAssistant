from __future__ import annotations

import re
from collections import Counter
from typing import Any

from stock_research.state import ResearchState, utc_now_iso


QUESTION_TEXT = {
    "Q1": "How does the company make money?",
    "Q2": "Who pays, who uses, and who supplies?",
    "Q3": "Why do customers pay?",
    "Q4": "What drives revenue growth?",
    "Q5": "What drives margins and cost structure?",
    "Q6": "Is the model recurring, transactional, cyclical, or subsidy-driven?",
    "Q7": "What are the fragile points?",
    "Q8": "What does Financial Evidence confirm or contradict?",
    "Q9": "What should other agents investigate?",
}

BMQ_TEXT = {
    "BMQ-01": "What are the company's revenue streams, and how large are they?",
    "BMQ-02": "Who is the payer, user, and supplier for each revenue stream?",
    "BMQ-03": "What exactly does the company sell?",
    "BMQ-04": "What is the pricing, fee, take-rate, or billing mechanism?",
    "BMQ-05": "When is revenue recognized, and what are the key performance obligations?",
    "BMQ-06": "Is revenue reported gross or net, and what is the principal-agent basis?",
    "BMQ-07": "Does segment disclosure align with the business model?",
    "BMQ-08": "What disclosed operating metrics can anchor unit economics?",
    "BMQ-09": "What unit-economics proxies are available when direct unit economics are not disclosed?",
    "BMQ-10": "How is the cost structure layered?",
    "BMQ-11": "What drives gross margin, operating margin, and segment margin?",
    "BMQ-12": "What drives growth?",
    "BMQ-13": "Does the model depend on subsidies, incentives, marketing, or one-time tailwinds?",
    "BMQ-14": "Do operating leverage, cash conversion, working capital, and capex support the business narrative?",
    "BMQ-15": "Does SBC or dilution make the economics look better than they are?",
    "BMQ-16": "What are the most fragile points in the model?",
    "BMQ-17": "Which core questions are unknown, under-disclosed, or contradictory?",
    "BMQ-18": "What should downstream agents investigate next?",
}

BMQ_ZH_TEXT = {
    "BMQ-01": "公司的收入流是什么，各自大概有多大？",
    "BMQ-02": "每条收入流中，谁付款、谁使用、谁供给？",
    "BMQ-03": "公司到底卖的是什么？",
    "BMQ-04": "定价、收费、take-rate 或 billing 机制是什么？",
    "BMQ-05": "收入何时确认，关键履约义务是什么？",
    "BMQ-06": "收入是按 gross 还是 net 列报，principal-agent 依据是什么？",
    "BMQ-07": "分部披露是否和商业模式相匹配？",
    "BMQ-08": "有哪些披露的运营指标可以锚定单位经济？",
    "BMQ-09": "如果公司不披露直接单位经济，有哪些代理指标可以使用？",
    "BMQ-10": "成本结构如何分层？",
    "BMQ-11": "毛利率、经营利润率和分部利润率由什么驱动？",
    "BMQ-12": "增长由什么驱动？",
    "BMQ-13": "模型是否依赖补贴、激励、营销投入或一次性顺风？",
    "BMQ-14": "经营杠杆、现金转化、营运资本和资本开支是否支持商业叙事？",
    "BMQ-15": "SBC 或摊薄是否让经济性看起来比实际更好？",
    "BMQ-16": "模型最脆弱的点在哪里？",
    "BMQ-17": "哪些核心问题未知、披露不足或互相矛盾？",
    "BMQ-18": "下游 agent 下一步应该调查什么？",
}


def build_business_model_evidence_pack(state: ResearchState) -> dict[str, Any]:
    """Build a fixed-question business-model evidence pack from existing state.

    This is intentionally deterministic for the MVP. It synthesizes current
    official-report, financial-pack, transcript, and source-coverage artifacts;
    it does not ask an LLM to fill evidence gaps.
    """

    company = _company_payload(state.get("canonical_company") or {}, state)
    findings = state.get("business_model_findings") or {}
    analysis = findings.get("official_report_analysis") or {}
    field_by_id = _dossier_fields_by_id(analysis)
    card_by_id = _deep_dive_cards_by_id(analysis)
    financial_pack = state.get("financial_report_pack") or {}
    official_events = state.get("official_event_transcript_findings") or {}
    executive = state.get("executive_transcript_findings") or {}
    source_coverage = findings.get("source_coverage") or {}

    questions = [
        _question_q1(field_by_id, card_by_id),
        _question_q2(field_by_id, analysis),
        _question_q3(field_by_id, card_by_id, executive),
        _question_q4(field_by_id, card_by_id, financial_pack, official_events),
        _question_q5(field_by_id, card_by_id, financial_pack, official_events),
        _question_q6(field_by_id, card_by_id, financial_pack, official_events),
        _question_q7(field_by_id, card_by_id, findings, financial_pack),
        _question_q8(financial_pack, card_by_id),
        _question_q9(findings, financial_pack, source_coverage),
    ]

    financial_cross_check = _financial_cross_check(financial_pack)
    fragility_points = _fragility_points(field_by_id, card_by_id, findings, financial_pack)
    questions_for_other_agents = _questions_for_other_agents(findings, financial_pack, source_coverage)

    confidence_counts = Counter(question.get("confidence", "unknown") for question in questions)
    summary = {
        "one_sentence_business_model": (
            "PDD is best read as a merchant-funded demand aggregation and commerce-services platform: "
            "buyers use Pinduoduo and Temu for value-for-money shopping, while merchants fund online "
            "marketing and transaction-related services."
        ),
        "business_model_quality": _business_model_quality(financial_pack, field_by_id),
        "confidence": _overall_confidence(confidence_counts, field_by_id, financial_pack),
        "reason": (
            "The core revenue mechanics are directly supported by official filings and company-level "
            "financials, but segment/geography economics, Pinduoduo versus Temu split, and merchant ROI "
            "remain insufficiently disclosed."
        ),
    }

    return {
        "company": company,
        "agent": "business_model_evidence_agent",
        "version": "0.1",
        "generated_at": utc_now_iso(),
        "source_policy": {
            "core_claim_rule": "Core business-model claims require official filing, revenue recognition, segment disclosure, product/pricing, or similarly high-reliability evidence.",
            "management_claim_rule": "Earnings calls and executive interviews are treated as management claims or framing, not proof.",
            "financial_number_rule": "Financial Evidence Agent output is the source of record for calculated financial cross-checks in this pack.",
            "no_buy_sell_hold_rule": "This agent does not output Buy, Sell, or Hold.",
        },
        "summary": summary,
        "questions": questions,
        "financial_cross_check": financial_cross_check,
        "fragility_points": fragility_points,
        "questions_for_other_agents": questions_for_other_agents,
        "source_coverage": _source_coverage_snapshot(source_coverage, field_by_id, financial_pack),
        "open_issues": _open_issues(findings, financial_pack),
    }


def build_business_model_evidence_report(pack: dict[str, Any]) -> str:
    company = pack.get("company") or {}
    summary = pack.get("summary") or {}
    questions = pack.get("questions") or []
    by_id = {question.get("question_id"): question for question in questions}

    return f"""# Business Model Evidence Report: {company.get('name') or company.get('ticker') or 'Unknown Company'}

Generated at: {pack.get('generated_at')}

Agent: `{pack.get('agent')}` | Version: `{pack.get('version')}`  
Scope: business-model evidence and preliminary diagnosis only. This report does not make Buy / Sell / Hold recommendations.

## 1. One-Sentence Business Model

{summary.get('one_sentence_business_model', '')}

## 2. How Does the Company Make Money?

{_question_markdown(by_id.get('Q1'))}

## 3. Who Pays, Who Uses, Who Supplies?

{_question_markdown(by_id.get('Q2'))}

## 4. Why Do Customers Pay?

{_question_markdown(by_id.get('Q3'))}

## 5. What Drives Revenue Growth?

{_question_markdown(by_id.get('Q4'))}

## 6. What Drives Margins and Cost Structure?

{_question_markdown(by_id.get('Q5'))}

## 7. Recurring, Transactional, Cyclical, or Subsidy-Driven?

{_question_markdown(by_id.get('Q6'))}

## 8. Fragile Points

{_fragility_table(pack.get('fragility_points') or [])}

## 9. Financial Evidence Cross-Check

{_financial_cross_check_markdown(pack.get('financial_cross_check') or {})}

## 10. Questions for Other Agents

{_other_agent_questions_markdown(pack.get('questions_for_other_agents') or {})}

## 11. Overall Business Model Quality

Rating: {summary.get('business_model_quality', 'uncertain')}

Confidence: {summary.get('confidence', 'low')}

Reason:
{summary.get('reason', '')}

## 12. Source Coverage And Open Issues

{_source_coverage_markdown(pack.get('source_coverage') or {})}

### Open Issues

{_bullet_list(pack.get('open_issues') or [])}
"""


def build_business_model_unit_economics_pack(
    state: ResearchState,
    evidence_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the target Business Model & Unit Economics workpaper.

    V1 is an adapter over the existing fixed-question Business Model Evidence
    Agent. It preserves the old Q1-Q9 artifact while producing the new Layer-2
    workpaper shape with BMQ-01 through BMQ-18, evidence cards, unknowns, and
    downstream handoffs.
    """

    evidence_pack = evidence_pack or state.get("business_model_evidence_pack") or build_business_model_evidence_pack(state)
    company = evidence_pack.get("company") or _company_payload(state.get("canonical_company") or {}, state)
    question_by_id = {
        str(question.get("question_id")): question
        for question in evidence_pack.get("questions", [])
        if isinstance(question, dict) and question.get("question_id")
    }
    source_inventory, evidence_cards, evidence_card_ids_by_question = _bmue_evidence_registry(evidence_pack)
    financial_pack = state.get("financial_report_pack") or {}
    source_coverage = evidence_pack.get("source_coverage") or {}
    question_answers = _bmue_question_answers(question_by_id, evidence_card_ids_by_question, evidence_pack, financial_pack)
    unknowns = _bmue_unknowns(question_answers, evidence_pack, source_coverage, financial_pack)
    contradictions = _bmue_contradictions(evidence_pack)
    cross_checks = _bmue_cross_checks(evidence_pack, financial_pack, evidence_card_ids_by_question)
    handoff = _bmue_handoff(evidence_pack, evidence_card_ids_by_question)

    return {
        "schema_version": "business_model_unit_economics_workpaper_v0.1",
        "workpaper_type": "business_model_unit_economics",
        "agent": {
            "name": "business_model_unit_economics_workpaper_agent",
            "version": "0.1",
            "run_id": state.get("run_id"),
            "base_artifact": "business_model_evidence_agent_v0.1",
        },
        "company": {
            "issuer_name": company.get("name") or "",
            "primary_ticker": company.get("ticker") or "",
            "market": company.get("market") or "",
            "accounting_framework": _accounting_framework(state),
            "sector_family": _sector_family(state),
            "model_family": _model_family(question_by_id, evidence_pack),
        },
        "scope": {
            "as_of_date": (evidence_pack.get("generated_at") or utc_now_iso())[:10],
            "fiscal_period": _fiscal_period(financial_pack),
            "currency": _reporting_currency(financial_pack),
            "lookback_years": "all_available",
            "included_source_ids": [source.get("source_id") for source in source_inventory],
            "source_policy": "question-led workpaper generated from official filings, financial evidence, management communication, and source-coverage registry; weak evidence is marked partial or unknown.",
        },
        "summary": {
            "preliminary_read": (evidence_pack.get("summary") or {}).get("one_sentence_business_model", ""),
            "confidence": (evidence_pack.get("summary") or {}).get("confidence", "low"),
            "coverage": _bmue_coverage_status(question_answers),
            "boundary": "Evidence workpaper only. No Buy/Sell/Hold, target price, or final Right Business judgment.",
        },
        "source_inventory": source_inventory,
        "question_answers": question_answers,
        "revenue_streams": _bmue_revenue_streams(question_by_id, evidence_card_ids_by_question),
        "party_map": _bmue_party_map(question_by_id, evidence_card_ids_by_question),
        "offer_map": _bmue_offer_map(question_by_id, evidence_card_ids_by_question),
        "pricing_map": _bmue_pricing_map(evidence_card_ids_by_question),
        "revenue_recognition": _bmue_revenue_recognition(question_by_id, evidence_card_ids_by_question),
        "gross_net_treatment": _bmue_gross_net_treatment(evidence_card_ids_by_question),
        "segment_alignment": _bmue_segment_alignment(evidence_pack, evidence_card_ids_by_question),
        "disclosed_operating_metrics": _bmue_disclosed_operating_metrics(question_by_id, evidence_card_ids_by_question),
        "unit_economics_proxies": _bmue_unit_economics_proxies(question_by_id, evidence_card_ids_by_question),
        "cost_structure": _bmue_cost_structure(question_by_id, evidence_card_ids_by_question),
        "margin_drivers": _bmue_margin_drivers(question_by_id, evidence_card_ids_by_question),
        "growth_drivers": _bmue_growth_drivers(question_by_id, evidence_card_ids_by_question),
        "subsidy_dependencies": _bmue_subsidy_dependencies(question_by_id, evidence_card_ids_by_question),
        "fragile_points": _bmue_fragile_points(evidence_pack, evidence_card_ids_by_question),
        "cross_checks": cross_checks,
        "evidence_cards": evidence_cards,
        "contradictions": contradictions,
        "handoff": handoff,
        "unknowns": unknowns,
        "quality_flags": _bmue_quality_flags(question_answers, unknowns, contradictions, evidence_pack),
        "render_manifest": {
            "default_report_order": list(BMQ_TEXT),
            "summary_card_ids": evidence_card_ids_by_question.get("Q1", [])[:3]
            + evidence_card_ids_by_question.get("Q8", [])[:3],
        },
        "legacy_business_model_evidence": {
            "agent": evidence_pack.get("agent"),
            "version": evidence_pack.get("version"),
            "question_count": len(evidence_pack.get("questions", [])),
        },
    }


def build_business_model_unit_economics_report(pack: dict[str, Any]) -> str:
    company = pack.get("company") or {}
    summary = pack.get("summary") or {}
    answers = pack.get("question_answers") or []
    answer_by_id = {answer.get("question_id"): answer for answer in answers}
    return f"""# Business Model & Unit Economics Workpaper: {company.get('issuer_name') or company.get('primary_ticker') or 'Unknown Company'}

Generated at: {(pack.get('scope') or {}).get('as_of_date')}

Agent: `{(pack.get('agent') or {}).get('name')}` | Version: `{(pack.get('agent') or {}).get('version')}`  
Scope: evidence workpaper only. This report does not make Buy / Sell / Hold recommendations, target-price calls, or final Right Business judgments.

## 1. Preliminary Read

{summary.get('preliminary_read', '')}

- Confidence: {summary.get('confidence', 'low')}
- Coverage: {summary.get('coverage', 'unknown')}

## 2. Question Overview

{_bmue_question_overview_table(answers)}

## 3. Revenue Architecture

{_bmue_revenue_stream_table(pack.get('revenue_streams') or [])}

## 4. Payer / User / Supplier Map

{_bmue_party_table(pack.get('party_map') or [])}

## 5. Product, Pricing, Revenue Recognition, Gross / Net

### Offer Map

{_bmue_simple_object_table(pack.get('offer_map') or [], ["offer_id", "offer", "evidence_card_ids"])}

### Pricing / Fee / Take-Rate

{_bmue_simple_object_table(pack.get('pricing_map') or [], ["pricing_id", "mechanism", "status", "evidence_card_ids"])}

### Revenue Recognition

{_bmue_simple_object_table(pack.get('revenue_recognition') or [], ["recognition_id", "timing", "performance_obligation", "evidence_card_ids"])}

### Gross / Net Treatment

{_bmue_simple_object_table(pack.get('gross_net_treatment') or [], ["treatment_id", "treatment", "basis", "status"])}

## 6. Unit Economics, Costs, Margins, Growth

### Unit-Economics Proxies

{_bmue_simple_object_table(pack.get('unit_economics_proxies') or [], ["proxy_id", "metric_name", "quality", "interpretation_limit"])}

### Cost Structure

{_bmue_simple_object_table(pack.get('cost_structure') or [], ["bucket_id", "bucket_name", "fixed_or_variable", "evidence_card_ids"])}

### Margin Drivers

{_bmue_simple_object_table(pack.get('margin_drivers') or [], ["driver_id", "driver_text", "direction", "evidence_card_ids"])}

### Growth Drivers

{_bmue_simple_object_table(pack.get('growth_drivers') or [], ["driver_id", "driver_text", "driver_type", "durability"])}

## 7. Financial Cross-Checks

{_bmue_simple_object_table(pack.get('cross_checks') or [], ["check_id", "check_type", "result", "claim_tested"])}

## 8. Subsidy Dependence And Fragile Points

### Subsidy / Incentive Dependency

{_bmue_simple_object_table(pack.get('subsidy_dependencies') or [], ["dependency_id", "instrument", "severity", "status"])}

### Fragile Points

{_bmue_simple_object_table(pack.get('fragile_points') or [], ["fragile_id", "point", "severity", "monitoring_metric"])}

## 9. Unknowns And Contradictions

### Unknowns

{_bmue_simple_object_table(pack.get('unknowns') or [], ["unknown_id", "question_id", "reason", "needed_source"])}

### Contradictions

{_bmue_simple_object_table(pack.get('contradictions') or [], ["contradiction_id", "resolution_status", "resolution_note"])}

## 10. Downstream Handoff

{_bmue_handoff_markdown(pack.get('handoff') or [])}

## 11. Evidence Card Index

{_bmue_evidence_card_index(pack.get('evidence_cards') or [])}

## 12. Quality Flags

{_bullet_list(pack.get('quality_flags') or [])}
"""


def build_business_model_unit_economics_chinese_report(pack: dict[str, Any]) -> str:
    company = pack.get("company") or {}
    summary = pack.get("summary") or {}
    answers = pack.get("question_answers") or []
    return f"""# 商业模式与单位经济底稿：{company.get('issuer_name') or company.get('primary_ticker') or '未知公司'}

生成时间：{(pack.get('scope') or {}).get('as_of_date')}

Agent：`{(pack.get('agent') or {}).get('name')}` | 版本：`{(pack.get('agent') or {}).get('version')}`  
范围：这是证据底稿，不输出 Buy / Sell / Hold，不给目标价，也不直接给最终 Right Business 判断。

说明：source id、evidence card id、citation 和原始证据摘录保留英文或原始语言，方便回到源文件复核。

## 1. 初步读法

{_bmue_zh_preliminary_read(summary, company)}

- 信心：{_bmue_zh_status(summary.get('confidence', 'low'))}
- 覆盖度：{_bmue_zh_status(summary.get('coverage', 'unknown'))}

## 2. 问题总览

{_bmue_zh_question_overview_table(answers)}

## 3. 收入结构

{_bmue_zh_revenue_stream_table(pack.get('revenue_streams') or [])}

## 4. 付款方 / 使用者 / 供给方地图

{_bmue_zh_party_table(pack.get('party_map') or [])}

## 5. 产品、定价、收入确认、Gross / Net

### 产品 / 服务地图

{_bmue_zh_simple_object_table(pack.get('offer_map') or [], [("offer_id", "ID"), ("offer", "产品/服务"), ("evidence_card_ids", "证据卡")])}

### 定价 / 费率 / Take-Rate

{_bmue_zh_simple_object_table(pack.get('pricing_map') or [], [("pricing_id", "ID"), ("mechanism", "机制"), ("status", "状态"), ("evidence_card_ids", "证据卡")])}

### 收入确认

{_bmue_zh_simple_object_table(pack.get('revenue_recognition') or [], [("recognition_id", "ID"), ("timing", "确认时点"), ("performance_obligation", "履约义务"), ("evidence_card_ids", "证据卡")])}

### Gross / Net 列报

{_bmue_zh_simple_object_table(pack.get('gross_net_treatment') or [], [("treatment_id", "ID"), ("treatment", "列报方式"), ("basis", "依据"), ("status", "状态")])}

## 6. 单位经济、成本、利润率、增长

### 单位经济代理指标

{_bmue_zh_simple_object_table(pack.get('unit_economics_proxies') or [], [("proxy_id", "ID"), ("metric_name", "指标"), ("quality", "质量"), ("interpretation_limit", "解释边界")])}

### 成本结构

{_bmue_zh_simple_object_table(pack.get('cost_structure') or [], [("bucket_id", "ID"), ("bucket_name", "成本桶"), ("fixed_or_variable", "固定/可变"), ("evidence_card_ids", "证据卡")])}

### 利润率驱动

{_bmue_zh_simple_object_table(pack.get('margin_drivers') or [], [("driver_id", "ID"), ("driver_text", "驱动因素"), ("direction", "方向"), ("evidence_card_ids", "证据卡")])}

### 增长驱动

{_bmue_zh_simple_object_table(pack.get('growth_drivers') or [], [("driver_id", "ID"), ("driver_text", "驱动因素"), ("driver_type", "类型"), ("durability", "持续性")])}

## 7. 财务交叉验证

{_bmue_zh_simple_object_table(pack.get('cross_checks') or [], [("check_id", "ID"), ("check_type", "检查类型"), ("result", "结果"), ("claim_tested", "被检验的主张")])}

## 8. 补贴依赖与脆弱点

### 补贴 / 激励依赖

{_bmue_zh_simple_object_table(pack.get('subsidy_dependencies') or [], [("dependency_id", "ID"), ("instrument", "工具"), ("severity", "严重性"), ("status", "状态")])}

### 脆弱点

{_bmue_zh_simple_object_table(pack.get('fragile_points') or [], [("fragile_id", "ID"), ("point", "脆弱点"), ("severity", "严重性"), ("monitoring_metric", "后续跟踪指标")])}

## 9. 未知项与矛盾

### 未知项

{_bmue_zh_simple_object_table(pack.get('unknowns') or [], [("unknown_id", "ID"), ("question_id", "对应问题"), ("reason", "原因"), ("needed_source", "需要的来源")])}

### 矛盾 / 张力

{_bmue_zh_simple_object_table(pack.get('contradictions') or [], [("contradiction_id", "ID"), ("resolution_status", "解决状态"), ("resolution_note", "说明")])}

## 10. 下游交接

{_bmue_zh_handoff_markdown(pack.get('handoff') or [])}

## 11. Evidence Card 索引

{_bmue_zh_evidence_card_index(pack.get('evidence_cards') or [])}

## 12. 质量标记

{_bmue_zh_bullet_list(pack.get('quality_flags') or [])}
"""


def _question_q1(field_by_id: dict[str, dict[str, Any]], card_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    revenue = field_by_id.get("revenue_model", {})
    economic_engine = card_by_id.get("economic_engine", {})
    revenue_quality = card_by_id.get("revenue_quality", {})
    finding = _first_non_empty(
        economic_engine.get("current_answer"),
        revenue.get("summary"),
        "Revenue model not sufficiently disclosed by current evidence.",
    )
    evidence = [
        _evidence_from_dossier_field(
            revenue,
            claim="Revenue primarily comes from transaction services and online marketing services/others provided to third-party merchants.",
            source_type="revenue_recognition_note",
            reliability="high",
        ),
        *_evidence_from_card(economic_engine, source_type="official_filing", reliability="high"),
        *_evidence_from_card(revenue_quality, source_type="financial_evidence_agent_output", reliability="high"),
    ]
    return _question("Q1", finding, _clean_evidence(evidence), confidence="high", open_issues=[])


def _question_q2(field_by_id: dict[str, dict[str, Any]], analysis: dict[str, Any]) -> dict[str, Any]:
    customers = field_by_id.get("customer_groups", {})
    suppliers = field_by_id.get("supplier_or_partner_dependencies", {})
    kpi = ((analysis.get("operating_kpi_analysis") or {}).get("latest_by_metric") or {}).get("active_merchants")
    finding = (
        "The filing identifies buyers/consumers and merchants as the key platform participants. "
        "The economic payer is mainly the merchant/customer of PDD's platform services, while the end user is the buyer. "
        "Supply depends on third-party merchants and, for Temu, logistics and fulfillment partners."
    )
    evidence = [
        _evidence_from_dossier_field(customers, source_type="official_filing", reliability="high"),
        _evidence_from_dossier_field(suppliers, source_type="official_filing", reliability="high"),
        _evidence_from_operating_kpi(
            kpi,
            claim="PDD reported 16.8 million active merchants as of 2025-12-31.",
        ),
    ]
    return _question(
        "Q2",
        finding,
        _clean_evidence(evidence),
        confidence="medium",
        open_issues=["Current evidence does not fully separate Pinduoduo domestic merchants from Temu cross-border merchants."],
    )


def _question_q3(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    executive: dict[str, Any],
) -> dict[str, Any]:
    management = field_by_id.get("management_framing", {})
    customer_value = card_by_id.get("customer_value", {})
    interview_item = _first_transcript_question_item(executive, "customer_value_proposition")
    finding = _first_non_empty(
        customer_value.get("current_answer"),
        "The official customer proposition is value-for-money selection, broad choice, and interactive shopping.",
    )
    evidence = [
        _evidence_from_dossier_field(
            management,
            claim="Management frames the platform around value-for-money shopping and a buyer-merchant flywheel.",
            source_type="management_communication",
            reliability="medium",
        ),
        *_evidence_from_card(customer_value, source_type="official_filing", reliability="high"),
        _evidence_from_question_item(interview_item, source_type="management_communication", reliability="medium"),
    ]
    return _question(
        "Q3",
        finding,
        _clean_evidence(evidence),
        confidence="medium",
        open_issues=["Official evidence does not prove current customer love, retention, trust, or Temu customer experience quality."],
    )


def _question_q4(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    financial_pack: dict[str, Any],
    official_events: dict[str, Any],
) -> dict[str, Any]:
    revenue_quality = card_by_id.get("revenue_quality", {})
    revenue_engine = _first_transcript_question_item(official_events, "revenue_engine")
    temu_global = _first_transcript_question_item(official_events, "temu_global_model")
    growth_diag = _diagnostic_question(financial_pack, "growth_quality")
    finding = _first_non_empty(
        revenue_quality.get("current_answer"),
        growth_diag.get("current_answer"),
        "Revenue growth drivers are only partially disclosed.",
    )
    evidence = [
        *_evidence_from_card(revenue_quality, source_type="official_filing", reliability="high"),
        _evidence_from_diagnostic(growth_diag, reliability="high"),
        _evidence_from_question_item(revenue_engine, source_type="management_communication", reliability="medium"),
        _evidence_from_question_item(temu_global, source_type="management_communication", reliability="medium"),
        _evidence_from_dossier_field(field_by_id.get("segment_structure", {}), source_type="segment_disclosure", reliability="high"),
    ]
    return _question(
        "Q4",
        finding,
        _clean_evidence(evidence),
        confidence="medium",
        open_issues=[
            "Segment/product/geography/take-rate facts remain missing or partial.",
            "PDD does not fully disclose Pinduoduo versus Temu economics.",
        ],
    )


def _question_q5(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    financial_pack: dict[str, Any],
    official_events: dict[str, Any],
) -> dict[str, Any]:
    unit = card_by_id.get("unit_economics", {})
    cost = field_by_id.get("cost_and_capital_drivers", {})
    profitability = _diagnostic_question(financial_pack, "profitability_with_scale")
    cost_structure = _first_transcript_question_item(official_events, "cost_structure_and_margin_drivers")
    finding = _first_non_empty(
        unit.get("current_answer"),
        profitability.get("current_answer"),
        "Margin and cost structure evidence is incomplete.",
    )
    evidence = [
        _evidence_from_dossier_field(cost, source_type="official_filing", reliability="high"),
        *_evidence_from_card(unit, source_type="financial_evidence_agent_output", reliability="high"),
        _evidence_from_diagnostic(profitability, reliability="high"),
        _evidence_from_question_item(cost_structure, source_type="management_communication", reliability="medium"),
    ]
    return _question(
        "Q5",
        finding,
        _clean_evidence(evidence),
        confidence="medium",
        open_issues=["Need to separate strategic investment from structural margin deterioration, especially around Temu and merchant support."],
    )


def _question_q6(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    financial_pack: dict[str, Any],
    official_events: dict[str, Any],
) -> dict[str, Any]:
    revenue = field_by_id.get("revenue_model", {})
    investment = _first_transcript_question_item(official_events, "investment_phase_and_costs")
    cash_quality = _diagnostic_question(financial_pack, "cash_profit_quality")
    finding = (
        "The model is primarily transactional and merchant-funded, with repeat behavior implied by marketplace scale but not fully proven by current KPIs. "
        "It is not a subscription model. Growth may be investment- or subsidy-influenced when management emphasizes merchant support, supply-chain investment, and margin pressure."
    )
    evidence = [
        _evidence_from_dossier_field(revenue, source_type="revenue_recognition_note", reliability="high"),
        _evidence_from_question_item(investment, source_type="management_communication", reliability="medium"),
        _evidence_from_diagnostic(cash_quality, reliability="high"),
        *_evidence_from_card(card_by_id.get("customer_value", {}), source_type="official_filing", reliability="high"),
    ]
    return _question(
        "Q6",
        finding,
        _clean_evidence(evidence),
        confidence="medium",
        open_issues=["Current filings no longer provide a complete recent buyer/order/retention KPI set."],
    )


def _question_q7(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    findings: dict[str, Any],
    financial_pack: dict[str, Any],
) -> dict[str, Any]:
    anti = card_by_id.get("anti_moat", {})
    risk = field_by_id.get("risk_factor_map", {})
    missing = findings.get("missing_evidence") or []
    deterioration = _diagnostic_question(financial_pack, "growth_quality")
    finding = _first_non_empty(
        anti.get("current_answer"),
        "Main fragility points are merchant economics, Pinduoduo versus Temu disclosure, quality/trust, competition, and regulatory/trade exposure.",
    )
    evidence = [
        _evidence_from_dossier_field(risk, source_type="official_filing", reliability="high"),
        *_evidence_from_card(anti, source_type="financial_evidence_agent_output", reliability="high"),
        _evidence_from_diagnostic(deterioration, reliability="high"),
        _synthetic_evidence(
            claim="Official report analysis records missing evidence around customer happiness, merchant profitability, Pinduoduo versus Temu economics, and competitor evidence.",
            source_name="Business Model / Moat Agent missing-evidence list",
            source_type="internal_agent_output",
            reliability="medium",
            citation="business_model_findings.missing_evidence",
            excerpt="; ".join(str(item) for item in missing[:4]),
        ),
    ]
    return _question("Q7", finding, _clean_evidence(evidence), confidence="medium", open_issues=list(missing[:4]))


def _question_q8(financial_pack: dict[str, Any], card_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cross = _financial_cross_check(financial_pack)
    finding = (
        "Financial evidence confirms company-level cash generation and capital-light characteristics, but contradicts a simple operating-leverage story in 2025: "
        "revenue grew while operating income, net income, free cash flow, operating margin, and ROIC weakened."
    )
    evidence = [
        _evidence_from_financial_health(financial_pack.get("financial_health") or {}),
        _evidence_from_diagnostic(_diagnostic_question(financial_pack, "growth_quality"), reliability="high"),
        _evidence_from_diagnostic(_diagnostic_question(financial_pack, "capital_needed_for_growth"), reliability="high"),
        *_evidence_from_card(card_by_id.get("unit_economics", {}), source_type="financial_evidence_agent_output", reliability="high"),
    ]
    open_issues = []
    open_issues.extend(cross.get("needs_investigation") or [])
    return _question("Q8", finding, _clean_evidence(evidence), confidence="high", open_issues=open_issues[:5])


def _question_q9(
    findings: dict[str, Any],
    financial_pack: dict[str, Any],
    source_coverage: dict[str, Any],
) -> dict[str, Any]:
    questions = _questions_for_other_agents(findings, financial_pack, source_coverage)
    flat = [question for items in questions.values() for question in items]
    evidence = [
        _synthetic_evidence(
            claim="Downstream questions were generated from missing evidence, source coverage gaps, and financial cross-check warnings.",
            source_name="Business Model Evidence Agent",
            source_type="internal_agent_output",
            reliability="medium",
            citation="questions_for_other_agents",
            excerpt="; ".join(flat[:5]),
        )
    ]
    return _question(
        "Q9",
        "Other agents should investigate the specific unproven assumptions behind the model: moat durability, growth runway, risk, valuation sensitivity, and management consistency.",
        _clean_evidence(evidence),
        confidence="high",
        open_issues=flat[:8],
    )


def _question(
    question_id: str,
    finding: str,
    evidence: list[dict[str, Any]],
    *,
    confidence: str,
    open_issues: list[str],
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question": QUESTION_TEXT[question_id],
        "finding": _trim(finding, limit=1200),
        "confidence": confidence,
        "evidence": evidence,
        "open_issues": open_issues,
    }


def _company_payload(company: dict[str, Any], state: ResearchState) -> dict[str, Any]:
    tickers = company.get("tickers") or []
    ticker = ""
    if tickers and isinstance(tickers[0], dict):
        ticker = str(tickers[0].get("symbol") or "")
    return {
        "name": company.get("legal_name") or state.get("company_query") or "",
        "ticker": ticker,
        "market": company.get("market") or state.get("market") or "",
    }


def _dossier_fields_by_id(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dossier = analysis.get("official_report_dossier") or {}
    return {
        str(field.get("field_id")): field
        for field in dossier.get("fields", [])
        if isinstance(field, dict) and field.get("field_id")
    }


def _deep_dive_cards_by_id(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    deep = analysis.get("business_model_deep_dive") or {}
    return {
        str(card.get("question_id")): card
        for card in deep.get("answer_cards", [])
        if isinstance(card, dict) and card.get("question_id")
    }


def _diagnostic_question(financial_pack: dict[str, Any], question_id: str) -> dict[str, Any]:
    diagnostics = financial_pack.get("diagnostic_findings") or {}
    for question in diagnostics.get("questions", []):
        if question.get("question_id") == question_id:
            return question
    return {}


def _evidence_from_dossier_field(
    field: dict[str, Any],
    *,
    claim: str | None = None,
    source_type: str,
    reliability: str,
) -> dict[str, Any]:
    if not field:
        return {}
    source_document = field.get("source_document") or {}
    status = field.get("status")
    excerpt = ""
    evidence = field.get("evidence") or []
    if evidence:
        excerpt = str(evidence[0])
    elif status == "not_disclosed":
        excerpt = str(field.get("summary") or "")
    return {
        "claim": claim or str(field.get("summary") or ""),
        "source_name": source_document.get("document_id") or "official report dossier",
        "source_type": source_type,
        "reliability": reliability,
        "citation": _citation(source_document, field.get("source_section")),
        "excerpt": _trim(excerpt),
        "status": status,
    }


def _evidence_from_card(card: dict[str, Any], *, source_type: str, reliability: str) -> list[dict[str, Any]]:
    if not card:
        return []
    items = []
    for claim in (card.get("official_support") or [])[:2]:
        items.append(
            _synthetic_evidence(
                claim=str(claim),
                source_name=_card_source_name(card),
                source_type=source_type,
                reliability=reliability,
                citation=_card_citation(card),
                excerpt=_first_evidence_excerpt(card),
            )
        )
    for claim in (card.get("quantitative_support") or [])[:3]:
        items.append(
            _synthetic_evidence(
                claim=str(claim),
                source_name="Financial Evidence Agent output",
                source_type="financial_evidence_agent_output",
                reliability="high",
                citation=f"business_model_deep_dive.answer_cards.{card.get('question_id')}.quantitative_support",
                excerpt=str(claim),
            )
        )
    return items


def _evidence_from_operating_kpi(kpi: dict[str, Any] | None, *, claim: str) -> dict[str, Any]:
    if not kpi:
        return {}
    source_document = kpi.get("source_document") or {}
    return {
        "claim": claim,
        "source_name": source_document.get("document_id") or "official operating KPI extraction",
        "source_type": "official_filing",
        "reliability": "high",
        "citation": _citation(source_document, "operating KPI extraction"),
        "excerpt": _trim(kpi.get("evidence")),
    }


def _evidence_from_diagnostic(question: dict[str, Any], *, reliability: str) -> dict[str, Any]:
    if not question:
        return {}
    return {
        "claim": str(question.get("current_answer") or ""),
        "source_name": "Financial Evidence Agent output",
        "source_type": "financial_evidence_agent_output",
        "reliability": reliability,
        "citation": f"financial_report_pack.diagnostic_findings.questions.{question.get('question_id')}",
        "excerpt": _trim("; ".join(str(flag) for flag in question.get("warning_flags", [])[:3]) or question.get("interpretation_limit")),
        "status": question.get("status"),
    }


def _evidence_from_financial_health(financial_health: dict[str, Any]) -> dict[str, Any]:
    if not financial_health:
        return {}
    return {
        "claim": (
            f"Financial health status is {financial_health.get('status')}; "
            f"positive evidence: {financial_health.get('main_positive_evidence')}; "
            f"negative evidence: {financial_health.get('main_negative_evidence')}."
        ),
        "source_name": "Financial Evidence Agent output",
        "source_type": "financial_evidence_agent_output",
        "reliability": "high",
        "citation": "financial_report_pack.financial_health",
        "excerpt": _trim(financial_health.get("next_verification_point")),
    }


def _evidence_from_question_item(
    item: dict[str, Any] | None,
    *,
    source_type: str,
    reliability: str,
) -> dict[str, Any]:
    if not item:
        return {}
    evidence = item.get("evidence") or []
    excerpt = ""
    if evidence and isinstance(evidence[0], dict):
        excerpt = str(evidence[0].get("excerpt") or "")
    return {
        "claim": str(item.get("current_read") or item.get("question") or ""),
        "source_name": item.get("source_name") or item.get("source_id") or "transcript question pack",
        "source_type": source_type,
        "reliability": reliability,
        "citation": item.get("source_url") or f"{item.get('source_id')}.{item.get('question_id')}",
        "excerpt": _trim(excerpt),
        "answer_status": item.get("answer_status"),
    }


def _first_transcript_question_item(findings: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    evidence_matches: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
    fallback_matches: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
    for result_index, result in enumerate(findings.get("source_results") or []):
        for item in result.get("business_model_question_results") or []:
            if item.get("question_id") == question_id and item.get("answer_status") == "evidence_found":
                evidence_matches.append((_question_item_sort_key(item, result, result_index), item))
            elif item.get("question_id") == question_id:
                fallback_matches.append((_question_item_sort_key(item, result, result_index), item))
    if evidence_matches:
        return max(evidence_matches, key=lambda pair: pair[0])[1]
    if fallback_matches:
        return max(fallback_matches, key=lambda pair: pair[0])[1]
    return None


def _question_item_sort_key(item: dict[str, Any], result: dict[str, Any], result_index: int) -> tuple[int, int, int]:
    period = str(item.get("period") or result.get("period") or result.get("quarter") or result.get("source_id") or "")
    match = re.search(r"(20\d{2})\s*[Qq]\s*([1-4])", period)
    if not match:
        match = re.search(r"(20\d{2})[Qq]([1-4])", period)
    if match:
        return (int(match.group(1)), int(match.group(2)), result_index)
    return (0, 0, result_index)


def _synthetic_evidence(
    *,
    claim: str,
    source_name: str,
    source_type: str,
    reliability: str,
    citation: str,
    excerpt: str,
) -> dict[str, Any]:
    return {
        "claim": _trim(claim, limit=600),
        "source_name": source_name,
        "source_type": source_type,
        "reliability": reliability,
        "citation": citation,
        "excerpt": _trim(excerpt),
    }


def _financial_cross_check(financial_pack: dict[str, Any]) -> dict[str, list[str]]:
    health = financial_pack.get("financial_health") or {}
    growth_quality = _diagnostic_question(financial_pack, "growth_quality")
    profitability = _diagnostic_question(financial_pack, "profitability_with_scale")
    capital = _diagnostic_question(financial_pack, "capital_needed_for_growth")
    cash = _diagnostic_question(financial_pack, "cash_profit_quality")
    missing = financial_pack.get("missing_facts") or {}
    missing_growth = ((missing.get("by_metric_family") or {}).get("source_of_growth_attribution_v1") or [])
    return {
        "confirmed_by_financials": [
            str(cash.get("current_answer") or "Cash conversion evidence is available."),
            str(capital.get("current_answer") or "Capital intensity evidence is available."),
            str(health.get("main_positive_evidence") or ""),
        ],
        "contradicted_by_financials": [
            str(growth_quality.get("current_answer") or ""),
            str(profitability.get("current_answer") or ""),
            str(health.get("main_negative_evidence") or ""),
        ],
        "needs_investigation": [
            "Explain why 2025 revenue growth did not translate into higher operating income or FCF.",
            "Separate strategic investment from structural margin pressure.",
            "Tie revenue component growth to merchant ROI, take rate, ad load, and Temu mix.",
            *[str(item) for item in missing_growth],
        ],
    }


def _fragility_points(
    field_by_id: dict[str, dict[str, Any]],
    card_by_id: dict[str, dict[str, Any]],
    findings: dict[str, Any],
    financial_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    anti = card_by_id.get("anti_moat", {})
    risk = field_by_id.get("risk_factor_map", {})
    segment = field_by_id.get("segment_structure", {})
    health = financial_pack.get("financial_health") or {}
    return [
        {
            "risk": "Merchant economics may be fragile after ads, fees, discounts, logistics, returns, and platform rules.",
            "evidence": _trim("; ".join(str(item) for item in findings.get("missing_evidence", []) if "Merchant" in str(item)) or anti.get("current_answer")),
            "source_type": "official_filing_plus_internal_gap",
            "severity": "high",
        },
        {
            "risk": "Pinduoduo versus Temu economics are not fully separated.",
            "evidence": _trim(segment.get("summary") or "Segment structure not disclosed or not found by V1 reader."),
            "source_type": "segment_disclosure",
            "severity": "high",
        },
        {
            "risk": "Operating leverage claim is under pressure in 2025.",
            "evidence": _trim(health.get("main_negative_evidence") or ""),
            "source_type": "financial_evidence_agent_output",
            "severity": "medium",
        },
        {
            "risk": "Quality, counterfeit, logistics, regulation, trade, and consumer-protection risks can damage the low-price model.",
            "evidence": _trim(risk.get("summary") or anti.get("current_answer")),
            "source_type": "official_filing",
            "severity": "medium",
        },
    ]


def _questions_for_other_agents(
    findings: dict[str, Any],
    financial_pack: dict[str, Any],
    source_coverage: dict[str, Any],
) -> dict[str, list[str]]:
    missing = [str(item) for item in findings.get("missing_evidence", [])]
    connected = [
        f"{gap.get('group_id')}: {gap.get('status')}"
        for gap in source_coverage.get("top_connected_gaps", [])[:4]
    ]
    health = financial_pack.get("financial_health") or {}
    return {
        "moat_agent": [
            "Is the buyer-merchant flywheel observable outside management language?",
            "Do competitors show grudging respect or copy-resistant disadvantages versus PDD/Temu?",
            "Can merchant ROI remain attractive after platform fees, advertising, logistics, returns, and price pressure?",
        ],
        "growth_runway_agent": [
            "How much growth is domestic Pinduoduo versus Temu/global expansion?",
            "Which driver matters most now: merchant count, revenue per merchant, ad load, take rate, geography, or new products?",
            *missing[:2],
        ],
        "risk_agent": [
            "What regulatory, trade, tariff, consumer-protection, and platform-governance risks could impair the model?",
            "Does low-price growth depend on subsidies or merchant margin compression?",
            *connected[:2],
        ],
        "valuation_agent": [
            "What valuation sensitivity follows from lower 2025 operating margin and ROIC?",
            "What normalized FCF margin should be used if current investment pressure persists?",
            str(health.get("next_verification_point") or "Track next-quarter incremental operating margin."),
        ],
        "management_agent": [
            "Is management's long-term investment explanation consistent with financial outcomes?",
            "Does management answer merchant economics, Temu disclosure, and margin-pressure questions directly?",
            "Do executive interviews clarify business-model philosophy without being over-weighted as evidence?",
        ],
    }


def _source_coverage_snapshot(
    source_coverage: dict[str, Any],
    field_by_id: dict[str, dict[str, Any]],
    financial_pack: dict[str, Any],
) -> dict[str, Any]:
    section_status = {
        "revenue_recognition_notes": _coverage_status(field_by_id.get("revenue_model")),
        "segment_geography_disclosure": _coverage_status(field_by_id.get("segment_structure")),
        "financial_evidence_agent_output": "covered" if financial_pack.get("schema_version") else "missing",
    }
    return {
        "status": source_coverage.get("status") or "not_available",
        "registry_path": source_coverage.get("registry_path"),
        "source_group_count": source_coverage.get("source_group_count", 0),
        "source_target_count": source_coverage.get("source_target_count", 0),
        "p0_source_status": section_status,
        "top_connected_gaps": source_coverage.get("top_connected_gaps", [])[:6],
    }


def _coverage_status(field: dict[str, Any] | None) -> str:
    if not field:
        return "missing"
    if field.get("status") == "not_disclosed":
        return "partial_or_missing"
    if field.get("status"):
        return "covered"
    return "missing"


def _open_issues(findings: dict[str, Any], financial_pack: dict[str, Any]) -> list[str]:
    issues = [str(item) for item in findings.get("missing_evidence", [])]
    missing = financial_pack.get("missing_facts") or {}
    for item in ((missing.get("by_metric_family") or {}).get("source_of_growth_attribution_v1") or []):
        issues.append(str(item))
    issues.append("Gemini/YouTube management-interview understanding adapter is planned but not yet connected as source-of-record evidence.")
    return list(dict.fromkeys([issue for issue in issues if issue]))


def _business_model_quality(financial_pack: dict[str, Any], field_by_id: dict[str, dict[str, Any]]) -> str:
    health_status = financial_pack.get("financial_health_status")
    segment_status = (field_by_id.get("segment_structure") or {}).get("status")
    if health_status == "mixed" or segment_status == "not_disclosed":
        return "medium"
    if health_status in {"deteriorating", "unknown"}:
        return "uncertain"
    return "medium"


def _overall_confidence(
    confidence_counts: Counter[str],
    field_by_id: dict[str, dict[str, Any]],
    financial_pack: dict[str, Any],
) -> str:
    if not financial_pack.get("schema_version"):
        return "low"
    if (field_by_id.get("segment_structure") or {}).get("status") == "not_disclosed":
        return "medium"
    if confidence_counts.get("low"):
        return "medium"
    return "high"


def _clean_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    seen = set()
    for item in items:
        if not item or not item.get("claim"):
            continue
        key = (item.get("claim"), item.get("citation"))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned[:8]


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value:
            return str(value)
    return ""


def _citation(source_document: dict[str, Any], section: Any = None) -> str:
    parts = []
    if source_document.get("source_url"):
        parts.append(str(source_document.get("source_url")))
    elif source_document.get("document_id"):
        parts.append(str(source_document.get("document_id")))
    if section:
        parts.append(str(section))
    return " | ".join(parts)


def _card_source_name(card: dict[str, Any]) -> str:
    source_document = card.get("source_document") or {}
    return source_document.get("document_id") or "Business Model Deep Dive"


def _card_citation(card: dict[str, Any]) -> str:
    source_document = card.get("source_document") or {}
    return _citation(source_document, f"business_model_deep_dive.{card.get('question_id')}")


def _first_evidence_excerpt(card: dict[str, Any]) -> str:
    evidence = card.get("source_evidence") or []
    if evidence:
        return str(evidence[0])
    return str(card.get("current_answer") or "")


def _trim(value: Any, *, limit: int = 480) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _question_markdown(question: dict[str, Any] | None) -> str:
    if not question:
        return "- Not available."
    return "\n".join(
        [
            "### Finding",
            "",
            str(question.get("finding") or ""),
            "",
            f"Confidence: {question.get('confidence', 'unknown')}",
            "",
            "### Evidence",
            "",
            _evidence_table(question.get("evidence") or []),
            "",
            "### Open Issues",
            "",
            _bullet_list(question.get("open_issues") or []),
        ]
    )


def _evidence_table(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "- No evidence recorded."
    rows = ["| Claim | Source | Source Type | Reliability | Citation |", "|---|---|---|---|---|"]
    for item in evidence:
        rows.append(
            "| {claim} | {source} | {source_type} | {reliability} | {citation} |".format(
                claim=_md_cell(item.get("claim")),
                source=_md_cell(item.get("source_name")),
                source_type=_md_cell(item.get("source_type")),
                reliability=_md_cell(item.get("reliability")),
                citation=_md_cell(item.get("citation")),
            )
        )
    return "\n".join(rows)


def _fragility_table(points: list[dict[str, Any]]) -> str:
    if not points:
        return "- No fragility points recorded."
    rows = ["| Fragile Point | Why It Matters / Evidence | Source Type | Severity |", "|---|---|---|---|"]
    for point in points:
        rows.append(
            "| {risk} | {evidence} | {source_type} | {severity} |".format(
                risk=_md_cell(point.get("risk")),
                evidence=_md_cell(point.get("evidence")),
                source_type=_md_cell(point.get("source_type")),
                severity=_md_cell(point.get("severity")),
            )
        )
    return "\n".join(rows)


def _financial_cross_check_markdown(cross_check: dict[str, Any]) -> str:
    return "\n".join(
        [
            "### Confirmed by Financials",
            "",
            _bullet_list(cross_check.get("confirmed_by_financials") or []),
            "",
            "### Contradicted by Financials",
            "",
            _bullet_list(cross_check.get("contradicted_by_financials") or []),
            "",
            "### Needs Further Investigation",
            "",
            _bullet_list(cross_check.get("needs_investigation") or []),
        ]
    )


def _other_agent_questions_markdown(questions: dict[str, list[str]]) -> str:
    if not questions:
        return "- No downstream questions recorded."
    sections = []
    for agent, items in questions.items():
        sections.extend([f"### {agent}", "", _bullet_list(items), ""])
    return "\n".join(sections).strip()


def _source_coverage_markdown(coverage: dict[str, Any]) -> str:
    p0 = coverage.get("p0_source_status") or {}
    rows = ["| Source | Status |", "|---|---|"]
    for source, status in p0.items():
        rows.append(f"| {_md_cell(source)} | {_md_cell(status)} |")
    lines = [
        f"- Registry: `{coverage.get('registry_path')}`",
        f"- Source groups: {coverage.get('source_group_count', 0)}",
        f"- Source targets: {coverage.get('source_target_count', 0)}",
        "",
        "\n".join(rows),
    ]
    gaps = coverage.get("top_connected_gaps") or []
    if gaps:
        lines.extend(["", "### Connected Source Gaps", ""])
        lines.extend(
            f"- {gap.get('group_id')}: {gap.get('priority')} | {gap.get('status')} | targets={gap.get('source_target_count', 0)}"
            for gap in gaps
        )
    return "\n".join(lines)


def _bullet_list(items: list[Any]) -> str:
    clean = [str(item) for item in items if item]
    if not clean:
        return "- None"
    return "\n".join(f"- {item}" for item in clean)


def _md_cell(value: Any) -> str:
    text = _trim(value, limit=240)
    return text.replace("|", "\\|").replace("\n", " ")


def _accounting_framework(state: ResearchState) -> str:
    company = state.get("canonical_company") or {}
    if (company.get("company_id") or "").lower() == "pdd":
        return "US_GAAP"
    return "unknown"


def _sector_family(state: ResearchState) -> str:
    company_id = ((state.get("canonical_company") or {}).get("company_id") or state.get("company_query") or "").lower()
    if company_id in {"pdd", "amazon", "alibaba", "jd", "meli"}:
        return "marketplace"
    if company_id in {"google", "googl", "meta", "tencent"}:
        return "advertising_and_platform"
    return "unknown"


def _model_family(question_by_id: dict[str, dict[str, Any]], evidence_pack: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            str((evidence_pack.get("summary") or {}).get("one_sentence_business_model") or ""),
            *(str(question.get("finding") or "") for question in question_by_id.values()),
        ]
    ).lower()
    families = []
    if any(term in text for term in ["merchant", "marketplace", "commerce", "transaction"]):
        families.append("marketplace")
    if any(term in text for term in ["online marketing", "advertising", "ad load"]):
        families.append("advertising_platform")
    if "subscription" in text and not any(term in text for term in ["not a subscription", "not subscription"]):
        families.append("subscription")
    if not families:
        families.append("unknown")
    return list(dict.fromkeys(families))


def _fiscal_period(financial_pack: dict[str, Any]) -> str:
    for key in ("annual_period_end", "latest_period_end", "period_end"):
        if financial_pack.get(key):
            return str(financial_pack.get(key))
    return "all_available"


def _reporting_currency(financial_pack: dict[str, Any]) -> str:
    for key in ("reporting_currency", "currency", "presentation_currency"):
        if financial_pack.get(key):
            return str(financial_pack.get(key))
    return "unknown"


def _bmue_evidence_registry(evidence_pack: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[str]]]:
    source_lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    evidence_cards: list[dict[str, Any]] = []
    card_ids_by_question: dict[str, list[str]] = {}
    source_counter = 1
    card_counter = 1
    for question in evidence_pack.get("questions") or []:
        qid = str(question.get("question_id") or "")
        for item in question.get("evidence") or []:
            source_key = (
                str(item.get("source_name") or "unknown_source"),
                str(item.get("source_type") or "unknown"),
                str(item.get("citation") or ""),
            )
            source = source_lookup.get(source_key)
            if source is None:
                source_id = f"BMUE-SRC-{source_counter:03d}"
                source_counter += 1
                source = {
                    "source_id": source_id,
                    "source_name": source_key[0],
                    "source_scope": _bmue_source_scope(item.get("source_type")),
                    "document_type": str(item.get("source_type") or "unknown"),
                    "title": source_key[0],
                    "issuer_or_publisher": source_key[0],
                    "reliability": item.get("reliability") or "unknown",
                    "citation": source_key[2],
                    "observed_at": evidence_pack.get("generated_at") or utc_now_iso(),
                    "collection_status": "available",
                    "notes": "",
                }
                source_lookup[source_key] = source
            card_id = f"BMUE-EV-{card_counter:03d}"
            card_counter += 1
            evidence_cards.append(
                {
                    "card_id": card_id,
                    "claim_text": _trim(item.get("claim"), limit=900),
                    "claim_normalized": _trim(item.get("claim"), limit=240),
                    "importance": _bmue_importance(qid, item),
                    "assertion_class": _bmue_assertion_class(item.get("source_type")),
                    "source_scope": source["source_scope"],
                    "audited_scope": _bmue_audited_scope(item.get("source_type")),
                    "support_level": "direct" if item.get("source_type") != "internal_agent_output" else "corroborative",
                    "question_ids": [qid],
                    "basis_card_ids": [],
                    "evidence": [
                        {
                            "source_id": source["source_id"],
                            "locator": item.get("citation") or "",
                            "excerpt": _trim(item.get("excerpt"), limit=900),
                            "structured_fact": None,
                            "period_covered": None,
                        }
                    ],
                    "confidence": _bmue_confidence_score(item.get("reliability")),
                    "status": item.get("status") or item.get("answer_status"),
                }
            )
            card_ids_by_question.setdefault(qid, []).append(card_id)
    return list(source_lookup.values()), evidence_cards, card_ids_by_question


def _bmue_source_scope(source_type: Any) -> str:
    mapping = {
        "official_filing": "filed_narrative",
        "revenue_recognition_note": "filed_financial_note",
        "segment_disclosure": "filed_financial_note",
        "financial_evidence_agent_output": "system_generated",
        "management_communication": "furnished_or_transcript_management_claim",
        "product_page": "company_live_page",
        "pricing_page": "company_live_page",
        "internal_agent_output": "system_generated",
    }
    return mapping.get(str(source_type or ""), "unknown")


def _bmue_assertion_class(source_type: Any) -> str:
    mapping = {
        "official_filing": "filing_fact",
        "revenue_recognition_note": "revenue_recognition_fact",
        "segment_disclosure": "filing_fact",
        "financial_evidence_agent_output": "calculated_metric",
        "management_communication": "management_claim",
        "product_page": "product_fact",
        "pricing_page": "pricing_fee_policy_fact",
        "internal_agent_output": "system_inference",
    }
    return mapping.get(str(source_type or ""), "unknown")


def _bmue_audited_scope(source_type: Any) -> str:
    if source_type in {"revenue_recognition_note", "segment_disclosure"}:
        return "audited_or_filed_note"
    if source_type == "official_filing":
        return "filed_narrative"
    if source_type == "financial_evidence_agent_output":
        return "computed_from_financial_pack"
    if source_type == "management_communication":
        return "furnished_or_transcript"
    if source_type in {"product_page", "pricing_page"}:
        return "live_page"
    if source_type == "internal_agent_output":
        return "inferred"
    return "unknown"


def _bmue_importance(question_id: str, evidence: dict[str, Any]) -> str:
    if question_id in {"Q1", "Q2", "Q5", "Q8"}:
        return "high"
    if evidence.get("reliability") == "high":
        return "high"
    return "medium"


def _bmue_confidence_score(reliability: Any) -> float:
    value = str(reliability or "").lower()
    if value == "high":
        return 0.9
    if value in {"medium_high", "medium"}:
        return 0.7
    if value in {"low_medium", "medium_or_low"}:
        return 0.5
    return 0.35


def _bmue_question_answers(
    question_by_id: dict[str, dict[str, Any]],
    card_ids: dict[str, list[str]],
    evidence_pack: dict[str, Any],
    financial_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    mappings = {
        "BMQ-01": ("Q1", "revenue_streams"),
        "BMQ-02": ("Q2", "party_map"),
        "BMQ-03": ("Q1", "offer_map"),
        "BMQ-04": ("Q1", "pricing_map"),
        "BMQ-05": ("Q1", "revenue_recognition"),
        "BMQ-06": ("Q1", "gross_net_treatment"),
        "BMQ-07": ("Q4", "segment_alignment"),
        "BMQ-08": ("Q2", "disclosed_operating_metrics"),
        "BMQ-09": ("Q5", "unit_econ_proxies"),
        "BMQ-10": ("Q5", "cost_structure"),
        "BMQ-11": ("Q5", "margin_drivers"),
        "BMQ-12": ("Q4", "growth_drivers"),
        "BMQ-13": ("Q6", "subsidy_dependency"),
        "BMQ-14": ("Q8", "cross_checks"),
        "BMQ-15": ("Q8", "sbc_dilution_check"),
        "BMQ-16": ("Q7", "fragile_points"),
        "BMQ-17": ("Q7", "unknowns_and_contradictions"),
        "BMQ-18": ("Q9", "handoff"),
    }
    answers = []
    for bmq_id, (legacy_qid, required_field) in mappings.items():
        legacy_question = question_by_id.get(legacy_qid) or {}
        status = _bmue_question_status(bmq_id, legacy_question, evidence_pack, financial_pack)
        answers.append(
            {
                "question_id": bmq_id,
                "prompt": BMQ_TEXT[bmq_id],
                "status": status,
                "required_field": required_field,
                "answer_short": _trim(_bmue_bmq_answer_short(bmq_id, legacy_question, evidence_pack), limit=360),
                "answer_detail": _trim(legacy_question.get("finding"), limit=1200),
                "confidence": _bmue_answer_confidence(status, legacy_question.get("confidence")),
                "primary_card_ids": card_ids.get(legacy_qid, [])[:8],
                "open_question_ids": [bmq_id] if status in {"partial", "unknown"} else [],
                "open_issues": legacy_question.get("open_issues") or [],
            }
        )
    return answers


def _bmue_question_status(
    bmq_id: str,
    question: dict[str, Any],
    evidence_pack: dict[str, Any],
    financial_pack: dict[str, Any],
) -> str:
    if bmq_id in {"BMQ-04", "BMQ-05", "BMQ-06"}:
        return "partial"
    if bmq_id == "BMQ-15":
        return "partial" if financial_pack else "unknown"
    if bmq_id == "BMQ-17":
        return "partial" if evidence_pack.get("open_issues") else "answered"
    if not question:
        return "unknown"
    if question.get("open_issues"):
        return "partial"
    return "answered" if question.get("evidence") else "partial"


def _bmue_answer_confidence(status: str, legacy_confidence: Any) -> float:
    if status == "answered":
        return {"high": 0.9, "medium": 0.7, "low": 0.45}.get(str(legacy_confidence or ""), 0.65)
    if status == "partial":
        return 0.55
    if status == "not_applicable":
        return 0.8
    return 0.25


def _bmue_bmq_answer_short(bmq_id: str, question: dict[str, Any], evidence_pack: dict[str, Any]) -> str:
    if bmq_id == "BMQ-04":
        return "Current evidence supports merchant-funded transaction-services and online-marketing mechanics, but exact fee basis, take rate, billing, and seller terms remain under-disclosed."
    if bmq_id == "BMQ-05":
        return "Revenue-recognition evidence anchors the revenue streams, but exact timing, performance-obligation detail, and contract-balance relevance still need explicit structured extraction."
    if bmq_id == "BMQ-06":
        return "Gross/net treatment is not fully resolved in the current workpaper; revenue-recognition evidence is available but principal-agent basis needs explicit extraction."
    if bmq_id == "BMQ-15":
        return "SBC/dilution should be checked through Financial Reality and Management/Governance; current adapter records this as a required cross-check rather than a completed unit-economics conclusion."
    if bmq_id == "BMQ-17":
        issues = evidence_pack.get("open_issues") or []
        return "; ".join(str(issue) for issue in issues[:3]) or "No major unknowns recorded."
    return str(question.get("finding") or "Not evaluated.")


def _bmue_unknowns(
    question_answers: list[dict[str, Any]],
    evidence_pack: dict[str, Any],
    source_coverage: dict[str, Any],
    financial_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    unknowns = []
    counter = 1
    for answer in question_answers:
        if answer.get("status") in {"partial", "unknown"}:
            unknowns.append(
                {
                    "unknown_id": f"BMUE-UNK-{counter:03d}",
                    "question_id": answer.get("question_id"),
                    "reason": "not_disclosed" if answer.get("status") == "unknown" else "ambiguous_or_partial",
                    "needed_source": _bmue_needed_source(str(answer.get("question_id"))),
                    "impact_area": _bmue_impact_area(str(answer.get("question_id"))),
                    "notes": "; ".join(str(item) for item in (answer.get("open_issues") or [])[:3]),
                }
            )
            counter += 1
    for gap in (source_coverage.get("top_connected_gaps") or [])[:4]:
        unknowns.append(
            {
                "unknown_id": f"BMUE-UNK-{counter:03d}",
                "question_id": "BMQ-17",
                "reason": "source_connected_but_not_fully_consumed",
                "needed_source": str(gap.get("group_id") or ""),
                "impact_area": ["business_model", "unit_economics"],
                "notes": f"{gap.get('priority')}: {gap.get('status')}",
            }
        )
        counter += 1
    missing = financial_pack.get("missing_facts") or {}
    for item in ((missing.get("by_metric_family") or {}).get("source_of_growth_attribution_v1") or [])[:3]:
        unknowns.append(
            {
                "unknown_id": f"BMUE-UNK-{counter:03d}",
                "question_id": "BMQ-12",
                "reason": "not_disclosed",
                "needed_source": "segment/product/geography/take-rate disclosure",
                "impact_area": ["growth", "valuation_assumption"],
                "notes": str(item),
            }
        )
        counter += 1
    return unknowns


def _bmue_needed_source(question_id: str) -> str:
    mapping = {
        "BMQ-04": "pricing pages, fee schedules, merchant terms",
        "BMQ-06": "revenue recognition note with principal-agent basis",
        "BMQ-07": "segment and geography disclosure",
        "BMQ-09": "company-disclosed KPI or stronger proxy metric",
        "BMQ-13": "marketing/subsidy policy and financial trend evidence",
        "BMQ-15": "SBC, share-count, and proxy compensation evidence",
    }
    return mapping.get(question_id, "stronger source evidence")


def _bmue_impact_area(question_id: str) -> list[str]:
    mapping = {
        "BMQ-04": ["business_model", "growth", "valuation_assumption"],
        "BMQ-06": ["business_model", "valuation_assumption", "risk"],
        "BMQ-07": ["competitive_position", "growth", "risk"],
        "BMQ-09": ["right_business", "valuation_assumption"],
        "BMQ-13": ["risk", "right_business"],
        "BMQ-15": ["management", "valuation_assumption"],
    }
    return mapping.get(question_id, ["right_business"])


def _bmue_contradictions(evidence_pack: dict[str, Any]) -> list[dict[str, Any]]:
    cross = evidence_pack.get("financial_cross_check") or {}
    contradictions = []
    for index, item in enumerate(cross.get("contradicted_by_financials") or [], start=1):
        if item:
            contradictions.append(
                {
                    "contradiction_id": f"BMUE-CON-{index:03d}",
                    "card_ids": [],
                    "resolution_status": "open",
                    "resolution_note": _trim(item),
                    "affected_questions": ["BMQ-11", "BMQ-14"],
                }
            )
    return contradictions


def _bmue_cross_checks(
    evidence_pack: dict[str, Any],
    financial_pack: dict[str, Any],
    card_ids: dict[str, list[str]],
) -> list[dict[str, Any]]:
    cross = evidence_pack.get("financial_cross_check") or {}
    return [
        {
            "check_id": "BMUE-CHK-001",
            "check_type": "operating_leverage",
            "claim_tested": "The business model should show operating leverage with scale.",
            "result": "tension" if cross.get("contradicted_by_financials") else "insufficient_evidence",
            "explanation": _trim("; ".join(cross.get("contradicted_by_financials") or [])),
            "series_refs": ["financial_report_pack.diagnostic_findings.profitability_with_scale"],
            "card_ids": card_ids.get("Q8", [])[:4],
        },
        {
            "check_id": "BMUE-CHK-002",
            "check_type": "cash_conversion",
            "claim_tested": "The model should convert profit into cash.",
            "result": "supports" if cross.get("confirmed_by_financials") else "insufficient_evidence",
            "explanation": _trim("; ".join(cross.get("confirmed_by_financials") or [])),
            "series_refs": ["financial_report_pack.diagnostic_findings.cash_profit_quality"],
            "card_ids": card_ids.get("Q8", [])[:4],
        },
        {
            "check_id": "BMUE-CHK-003",
            "check_type": "revenue_growth_quality",
            "claim_tested": "Revenue growth should be attributable to durable volume, price, mix, geography, or product drivers.",
            "result": "insufficient_evidence" if cross.get("needs_investigation") else "supports",
            "explanation": _trim("; ".join(cross.get("needs_investigation") or [])),
            "series_refs": ["financial_report_pack.missing_facts.source_of_growth_attribution_v1"],
            "card_ids": card_ids.get("Q4", [])[:4],
        },
        {
            "check_id": "BMUE-CHK-004",
            "check_type": "sbc_dilution",
            "claim_tested": "Unit economics should not be overstated by ignoring SBC and dilution.",
            "result": "insufficient_evidence",
            "explanation": "Current Business Model adapter routes SBC/dilution to Financial Reality and Management/Governance workpapers for deeper review.",
            "series_refs": ["financial_report_pack.financial_metrics.sbc_dilution"],
            "card_ids": [],
        },
    ]


def _bmue_handoff(evidence_pack: dict[str, Any], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    downstream = evidence_pack.get("questions_for_other_agents") or {}
    agent_map = {
        "moat_agent": "Competitive Position Workpaper",
        "growth_runway_agent": "Growth Runway Workpaper",
        "risk_agent": "Risk / Fragility / Red Flag Workpaper",
        "valuation_agent": "Valuation Assumption Workpaper",
        "management_agent": "Management / Governance / Capital Allocation Workpaper",
    }
    packages = []
    for source_agent, target_agent in agent_map.items():
        questions = downstream.get(source_agent) or []
        packages.append(
            {
                "consumer_agent": target_agent,
                "facts_passed": card_ids.get("Q1", [])[:2] + card_ids.get("Q8", [])[:2],
                "questions_to_answer": questions,
                "priority": "high" if source_agent in {"risk_agent", "valuation_agent"} else "medium",
            }
        )
    packages.append(
        {
            "consumer_agent": "Right Business Agent",
            "facts_passed": card_ids.get("Q1", [])[:3] + card_ids.get("Q5", [])[:2] + card_ids.get("Q8", [])[:3],
            "questions_to_answer": [
                "Does the evidence support an understandable and attractive business through a cycle?",
                "Which unknowns must be resolved before a stronger Right Business judgment is allowed?",
            ],
            "priority": "high",
        }
    )
    return packages


def _bmue_revenue_streams(
    question_by_id: dict[str, dict[str, Any]],
    card_ids: dict[str, list[str]],
) -> list[dict[str, Any]]:
    q1 = question_by_id.get("Q1") or {}
    return [
        {
            "stream_id": "BMUE-REV-001",
            "stream_name": "Transaction services",
            "offer": "Platform transaction-related services to merchants.",
            "payer": ["third-party merchants"],
            "user": ["buyers", "merchants"],
            "supplier": ["merchants", "logistics and fulfillment partners where relevant"],
            "pricing": {"mechanism": "transaction-related fees or service fees", "fee_basis": "not fully disclosed", "take_rate_basis": "unknown", "live_price_snapshot": None},
            "recognition": {"timing": "unknown", "performance_obligation": "platform services", "contract_asset_liability_relevance": "unknown"},
            "gross_net": {"treatment": "unknown", "basis": "Principal-agent basis needs explicit revenue-recognition extraction."},
            "mix_estimate": "partial",
            "summary": _trim(q1.get("finding")),
            "card_ids": card_ids.get("Q1", []),
        },
        {
            "stream_id": "BMUE-REV-002",
            "stream_name": "Online marketing services and others",
            "offer": "Marketing and demand-generation services to merchants.",
            "payer": ["third-party merchants"],
            "user": ["merchants", "buyers indirectly through product discovery"],
            "supplier": ["platform traffic and advertising inventory"],
            "pricing": {"mechanism": "online marketing service fees", "fee_basis": "not fully disclosed", "take_rate_basis": "not_applicable_or_unknown", "live_price_snapshot": None},
            "recognition": {"timing": "unknown", "performance_obligation": "online marketing services", "contract_asset_liability_relevance": "unknown"},
            "gross_net": {"treatment": "unknown", "basis": "Needs explicit extraction from revenue-recognition note."},
            "mix_estimate": "partial",
            "summary": _trim(q1.get("finding")),
            "card_ids": card_ids.get("Q1", []),
        },
    ]


def _bmue_party_map(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    q2 = question_by_id.get("Q2") or {}
    return [
        {
            "party_map_id": "BMUE-PARTY-001",
            "payer": "third-party merchants",
            "user": "buyers and merchants",
            "supplier": "third-party merchants, logistics vendors, fulfillment partners",
            "same_payer_and_user": "mixed",
            "summary": _trim(q2.get("finding")),
            "evidence_card_ids": card_ids.get("Q2", []),
        }
    ]


def _bmue_offer_map(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "offer_id": "BMUE-OFFER-001",
            "offer": "Commerce platform services: transaction services, online marketing services, buyer demand aggregation, and merchant access to traffic.",
            "status": "partial",
            "evidence_card_ids": card_ids.get("Q1", [])[:4] + card_ids.get("Q3", [])[:2],
        }
    ]


def _bmue_pricing_map(card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "pricing_id": "BMUE-PRICE-001",
            "mechanism": "merchant-funded transaction and online marketing service economics",
            "status": "partial",
            "fee_basis": "not fully disclosed in current adapter output",
            "take_rate_basis": "unknown",
            "needed_source": "pricing pages, fee schedules, merchant terms, seller policy snapshots",
            "evidence_card_ids": card_ids.get("Q1", [])[:4],
        }
    ]


def _bmue_revenue_recognition(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "recognition_id": "BMUE-REC-001",
            "timing": "unknown",
            "performance_obligation": "online platform services / transaction services / online marketing services",
            "basis": _trim((question_by_id.get("Q1") or {}).get("finding")),
            "status": "partial",
            "evidence_card_ids": card_ids.get("Q1", []),
        }
    ]


def _bmue_gross_net_treatment(card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "treatment_id": "BMUE-GN-001",
            "treatment": "unknown",
            "basis": "Needs explicit principal-agent extraction from revenue recognition policy.",
            "status": "partial",
            "evidence_card_ids": card_ids.get("Q1", []),
        }
    ]


def _bmue_segment_alignment(evidence_pack: dict[str, Any], card_ids: dict[str, list[str]]) -> dict[str, Any]:
    p0 = ((evidence_pack.get("source_coverage") or {}).get("p0_source_status") or {})
    return {
        "status": p0.get("segment_geography_disclosure") or "unknown",
        "summary": "Segment/geography economics are partial or missing if Pinduoduo versus Temu economics are not separately disclosed.",
        "evidence_card_ids": card_ids.get("Q4", []),
    }


def _bmue_disclosed_operating_metrics(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    q2_text = _trim((question_by_id.get("Q2") or {}).get("finding"))
    return [
        {
            "metric_id": "BMUE-KPI-001",
            "metric_name": "active merchants",
            "definition": "Merchant accounts or active merchants as disclosed by official source when available.",
            "quality": "company_disclosed_or_partial",
            "latest_read": q2_text,
            "evidence_card_ids": card_ids.get("Q2", []),
        }
    ]


def _bmue_unit_economics_proxies(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    q5 = question_by_id.get("Q5") or {}
    return [
        {
            "proxy_id": "BMUE-UE-001",
            "metric_name": "company-level margin and cash-conversion proxy",
            "definition": "Uses Financial Evidence cross-checks when direct order, merchant ROI, CAC, LTV, or take-rate unit economics are not disclosed.",
            "formula": None,
            "quality": "indirect_proxy",
            "series": [],
            "interpretation_limit": "Does not replace company-disclosed order-level or merchant-level economics.",
            "summary": _trim(q5.get("finding")),
            "card_ids": card_ids.get("Q5", []) + card_ids.get("Q8", []),
        }
    ]


def _bmue_cost_structure(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "bucket_id": "BMUE-COST-001",
            "bucket_name": "sales and marketing / merchant support / supply-chain and logistics-related investments",
            "classification": "operating expense and cost-structure driver",
            "fixed_or_variable": "mixed_or_unknown",
            "linked_stream_ids": ["BMUE-REV-001", "BMUE-REV-002"],
            "summary": _trim((question_by_id.get("Q5") or {}).get("finding")),
            "evidence_card_ids": card_ids.get("Q5", []),
        }
    ]


def _bmue_margin_drivers(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "driver_id": "BMUE-MARGIN-001",
            "driver_text": _trim((question_by_id.get("Q5") or {}).get("finding")),
            "direction": "mixed",
            "durability": "unknown",
            "tested_by_cross_checks": ["BMUE-CHK-001", "BMUE-CHK-002"],
            "evidence_card_ids": card_ids.get("Q5", []) + card_ids.get("Q8", []),
        }
    ]


def _bmue_growth_drivers(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "driver_id": "BMUE-GROWTH-001",
            "driver_text": _trim((question_by_id.get("Q4") or {}).get("finding")),
            "driver_type": "volume_price_mix_geography_product_unknown",
            "direction": "positive",
            "durability": "partial",
            "evidence_card_ids": card_ids.get("Q4", []),
        }
    ]


def _bmue_subsidy_dependencies(question_by_id: dict[str, dict[str, Any]], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "dependency_id": "BMUE-SUB-001",
            "instrument": "discounts, merchant support, supply-chain investment, marketing, or incentives",
            "who_pays": "company, merchants, or ecosystem participants depending on policy; not fully disclosed",
            "severity": "unknown",
            "status": "partial",
            "summary": _trim((question_by_id.get("Q6") or {}).get("finding")),
            "card_ids": card_ids.get("Q6", []) + card_ids.get("Q7", []),
        }
    ]


def _bmue_fragile_points(evidence_pack: dict[str, Any], card_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    points = []
    for index, point in enumerate(evidence_pack.get("fragility_points") or [], start=1):
        points.append(
            {
                "fragile_id": f"BMUE-FRAG-{index:03d}",
                "point": point.get("risk") or "",
                "mechanism": point.get("evidence") or "",
                "severity": point.get("severity") or "unknown",
                "monitoring_metric": _bmue_monitoring_metric(point.get("risk")),
                "card_ids": card_ids.get("Q7", []),
            }
        )
    return points


def _bmue_monitoring_metric(risk: Any) -> str:
    text = str(risk or "").lower()
    if "merchant" in text:
        return "merchant fee/ROI, seller terms, merchant complaints, ad intensity"
    if "temu" in text or "segment" in text:
        return "segment/geography disclosure and Temu-specific margin commentary"
    if "leverage" in text or "margin" in text:
        return "incremental operating margin and operating margin trend"
    if "regulation" in text or "trade" in text:
        return "regulatory events, customs/tariff changes, product-safety actions"
    return "source refresh and downstream risk review"


def _bmue_coverage_status(question_answers: list[dict[str, Any]]) -> str:
    statuses = [answer.get("status") for answer in question_answers]
    if statuses and all(status == "answered" for status in statuses):
        return "complete"
    if any(status == "answered" for status in statuses):
        return "partial"
    return "thin"


def _bmue_quality_flags(
    question_answers: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    evidence_pack: dict[str, Any],
) -> list[str]:
    flags = []
    if unknowns:
        flags.append(f"{len(unknowns)} unknown or partial items require source follow-up.")
    if contradictions:
        flags.append(f"{len(contradictions)} financial cross-check tensions remain open.")
    if ((evidence_pack.get("source_coverage") or {}).get("p0_source_status") or {}).get("segment_geography_disclosure") == "partial_or_missing":
        flags.append("Segment/geography disclosure is partial or missing; Pinduoduo versus Temu economics remain under-disclosed.")
    partial_count = sum(1 for answer in question_answers if answer.get("status") == "partial")
    if partial_count:
        flags.append(f"{partial_count} BMQ answers are partial; adapter abstained instead of inventing unit economics.")
    return flags


def _bmue_question_overview_table(answers: list[dict[str, Any]]) -> str:
    rows = ["| Question | Status | Short Answer | Confidence | Evidence Cards |", "|---|---|---|---|---|"]
    for answer in answers:
        rows.append(
            "| {qid} | {status} | {short} | {confidence} | {cards} |".format(
                qid=_md_cell(answer.get("question_id")),
                status=_md_cell(answer.get("status")),
                short=_md_cell(answer.get("answer_short")),
                confidence=_md_cell(answer.get("confidence")),
                cards=_md_cell(", ".join(answer.get("primary_card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_revenue_stream_table(streams: list[dict[str, Any]]) -> str:
    if not streams:
        return "- No revenue streams mapped."
    rows = ["| Revenue Stream | Offer | Payer | User | Supplier | Pricing | Gross/Net | Evidence Cards |", "|---|---|---|---|---|---|---|---|"]
    for stream in streams:
        rows.append(
            "| {stream} | {offer} | {payer} | {user} | {supplier} | {pricing} | {gross_net} | {cards} |".format(
                stream=_md_cell(stream.get("stream_name")),
                offer=_md_cell(stream.get("offer")),
                payer=_md_cell(", ".join(stream.get("payer") or [])),
                user=_md_cell(", ".join(stream.get("user") or [])),
                supplier=_md_cell(", ".join(stream.get("supplier") or [])),
                pricing=_md_cell((stream.get("pricing") or {}).get("mechanism")),
                gross_net=_md_cell((stream.get("gross_net") or {}).get("treatment")),
                cards=_md_cell(", ".join(stream.get("card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_party_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- No party map recorded."
    rows = ["| Payer | User | Supplier | Same Payer/User | Evidence Cards |", "|---|---|---|---|---|"]
    for item in items:
        rows.append(
            "| {payer} | {user} | {supplier} | {same} | {cards} |".format(
                payer=_md_cell(item.get("payer")),
                user=_md_cell(item.get("user")),
                supplier=_md_cell(item.get("supplier")),
                same=_md_cell(item.get("same_payer_and_user")),
                cards=_md_cell(", ".join(item.get("evidence_card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_simple_object_table(items: Any, keys: list[str]) -> str:
    if isinstance(items, dict):
        items = [items]
    if not items:
        return "- None recorded."
    rows = [
        "| " + " | ".join(keys) + " |",
        "| " + " | ".join("---" for _ in keys) + " |",
    ]
    for item in items:
        row = []
        for key in keys:
            value = item.get(key)
            if isinstance(value, list):
                value = ", ".join(str(part) for part in value)
            elif isinstance(value, dict):
                value = "; ".join(f"{nested_key}={nested_value}" for nested_key, nested_value in value.items())
            row.append(_md_cell(value))
        rows.append("| " + " | ".join(row) + " |")
    return "\n".join(rows)


def _bmue_handoff_markdown(packages: list[dict[str, Any]]) -> str:
    if not packages:
        return "- No handoff packages recorded."
    sections = []
    for package in packages:
        sections.extend(
            [
                f"### {package.get('consumer_agent')}",
                "",
                f"- Priority: {package.get('priority')}",
                f"- Facts passed: {', '.join(package.get('facts_passed') or []) or 'None'}",
                "- Questions:",
                _bullet_list(package.get("questions_to_answer") or []),
                "",
            ]
        )
    return "\n".join(sections).strip()


def _bmue_evidence_card_index(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return "- No evidence cards recorded."
    rows = ["| Card ID | Claim | Label | Source Scope | Locator |", "|---|---|---|---|---|"]
    for card in cards[:80]:
        evidence = (card.get("evidence") or [{}])[0]
        rows.append(
            "| {card_id} | {claim} | {label} | {scope} | {locator} |".format(
                card_id=_md_cell(card.get("card_id")),
                claim=_md_cell(card.get("claim_text")),
                label=_md_cell(card.get("assertion_class")),
                scope=_md_cell(card.get("source_scope")),
                locator=_md_cell(evidence.get("locator")),
            )
        )
    if len(cards) > 80:
        rows.append(f"| ... | {len(cards) - 80} additional cards omitted from report render |  |  |  |")
    return "\n".join(rows)


def _bmue_zh_preliminary_read(summary: dict[str, Any], company: dict[str, Any]) -> str:
    read = _bmue_zh_value(summary.get("preliminary_read"))
    if read:
        return read
    issuer = company.get("issuer_name") or company.get("primary_ticker") or "该公司"
    return f"{issuer} 的商业模式初步读法仍需要更多证据支持。"


def _bmue_zh_question_overview_table(answers: list[dict[str, Any]]) -> str:
    rows = ["| 问题 | 状态 | 中文问题 | 当前结论 | 证据卡 |", "|---|---|---|---|---|"]
    for answer in answers:
        question_id = str(answer.get("question_id") or "")
        rows.append(
            "| {qid} | {status} | {question} | {short} | {cards} |".format(
                qid=_md_cell(question_id),
                status=_md_cell(_bmue_zh_status(answer.get("status"))),
                question=_md_cell(BMQ_ZH_TEXT.get(question_id) or answer.get("prompt")),
                short=_md_cell(_bmue_zh_answer_short(answer)),
                cards=_md_cell(", ".join(answer.get("primary_card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_zh_revenue_stream_table(streams: list[dict[str, Any]]) -> str:
    if not streams:
        return "- 暂无收入流映射。"
    rows = ["| 收入流 | 提供什么 | 付款方 | 使用者 | 供给方 | 定价机制 | Gross/Net | 证据卡 |", "|---|---|---|---|---|---|---|---|"]
    for stream in streams:
        rows.append(
            "| {stream} | {offer} | {payer} | {user} | {supplier} | {pricing} | {gross_net} | {cards} |".format(
                stream=_md_cell(_bmue_zh_value(stream.get("stream_name"))),
                offer=_md_cell(_bmue_zh_value(stream.get("offer"))),
                payer=_md_cell(_bmue_zh_sequence(stream.get("payer") or [])),
                user=_md_cell(_bmue_zh_sequence(stream.get("user") or [])),
                supplier=_md_cell(_bmue_zh_sequence(stream.get("supplier") or [])),
                pricing=_md_cell(_bmue_zh_value((stream.get("pricing") or {}).get("mechanism"))),
                gross_net=_md_cell(_bmue_zh_value((stream.get("gross_net") or {}).get("treatment"))),
                cards=_md_cell(", ".join(stream.get("card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_zh_party_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- 暂无付款方 / 使用者 / 供给方地图。"
    rows = ["| 付款方 | 使用者 | 供给方 | 付款方与使用者是否相同 | 证据卡 |", "|---|---|---|---|---|"]
    for item in items:
        rows.append(
            "| {payer} | {user} | {supplier} | {same} | {cards} |".format(
                payer=_md_cell(_bmue_zh_value(item.get("payer"))),
                user=_md_cell(_bmue_zh_value(item.get("user"))),
                supplier=_md_cell(_bmue_zh_value(item.get("supplier"))),
                same=_md_cell(_bmue_zh_value(item.get("same_payer_and_user"))),
                cards=_md_cell(", ".join(item.get("evidence_card_ids") or [])),
            )
        )
    return "\n".join(rows)


def _bmue_zh_simple_object_table(items: Any, columns: list[tuple[str, str]]) -> str:
    if isinstance(items, dict):
        items = [items]
    if not items:
        return "- 暂无记录。"
    labels = [label for _, label in columns]
    rows = [
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join("---" for _ in labels) + " |",
    ]
    for item in items:
        row = []
        for key, _label in columns:
            value = item.get(key)
            if isinstance(value, list):
                value = _bmue_zh_sequence(value)
            elif isinstance(value, dict):
                value = "; ".join(f"{nested_key}={_bmue_zh_value(nested_value)}" for nested_key, nested_value in value.items())
            else:
                value = _bmue_zh_value(value)
            row.append(_md_cell(value))
        rows.append("| " + " | ".join(row) + " |")
    return "\n".join(rows)


def _bmue_zh_handoff_markdown(packages: list[dict[str, Any]]) -> str:
    if not packages:
        return "- 暂无下游交接问题。"
    sections = []
    for package in packages:
        sections.extend(
            [
                f"### {_bmue_zh_value(package.get('consumer_agent'))}",
                "",
                f"- 优先级：{_bmue_zh_value(package.get('priority'))}",
                f"- 传递的证据卡：{', '.join(package.get('facts_passed') or []) or '无'}",
                "- 待回答问题：",
                _bmue_zh_bullet_list(package.get("questions_to_answer") or []),
                "",
            ]
        )
    return "\n".join(sections).strip()


def _bmue_zh_evidence_card_index(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return "- 暂无 evidence card。"
    rows = ["| Card ID | 原始主张 | 标签 | 来源范围 | 定位 |", "|---|---|---|---|---|"]
    for card in cards[:80]:
        evidence = (card.get("evidence") or [{}])[0]
        rows.append(
            "| {card_id} | {claim} | {label} | {scope} | {locator} |".format(
                card_id=_md_cell(card.get("card_id")),
                claim=_md_cell(card.get("claim_text")),
                label=_md_cell(_bmue_zh_value(card.get("assertion_class"))),
                scope=_md_cell(_bmue_zh_value(card.get("source_scope"))),
                locator=_md_cell(evidence.get("locator")),
            )
        )
    if len(cards) > 80:
        rows.append(f"| ... | 另有 {len(cards) - 80} 张 evidence card 未在 markdown 中展开 |  |  |  |")
    return "\n".join(rows)


def _bmue_zh_bullet_list(items: list[Any]) -> str:
    clean = [_bmue_zh_value(item) for item in items if item]
    if not clean:
        return "- 无"
    return "\n".join(f"- {item}" for item in clean)


def _bmue_zh_answer_short(answer: dict[str, Any]) -> str:
    question_id = str(answer.get("question_id") or "")
    summaries = {
        "BMQ-01": "当前证据支持：公司主要是商家付费的需求聚合与电商服务平台。收入来自 transaction services 和 online marketing services and others，而不是传统自营库存零售。",
        "BMQ-02": "付款方主要是第三方商家；终端使用者包括买家和商家；供给侧依赖商家、物流和履约伙伴。Pinduoduo 国内业务与 Temu 跨境业务仍未完全拆开。",
        "BMQ-03": "公司卖的不是单一商品，而是平台服务：交易相关服务、在线营销、流量分发、买家需求聚合，以及帮助商家触达消费者的基础设施。",
        "BMQ-04": "当前证据只能支持“商家付费”的机制；具体 fee basis、take-rate、billing、seller terms 和广告/流量收费规则仍披露不足。",
        "BMQ-05": "收入确认证据能锚定收入流，但确认时点、具体履约义务、合同资产/负债相关性仍需要更结构化地从收入确认注释中抽取。",
        "BMQ-06": "Gross / Net 列报尚未完全解决；需要从 revenue recognition policy 中明确 principal-agent 依据。",
        "BMQ-07": "分部和地域披露仍是核心缺口。当前证据显示交易服务占比提升，但 Pinduoduo 与 Temu 的经济性没有被充分拆开。",
        "BMQ-08": "可用运营指标有限，active merchants 等披露可以作为锚点，但不能替代订单级、商家 ROI、CAC 或留存等单位经济指标。",
        "BMQ-09": "直接单位经济缺失时，只能用公司层面的利润率、现金转化、ROIC、capex/revenue 等代理指标；这些代理指标有解释边界。",
        "BMQ-10": "成本结构至少包括销售与营销、商家支持、供应链/物流相关投入、研发和收入成本；固定/可变属性仍需进一步拆分。",
        "BMQ-11": "公司层面仍有较高毛利率和现金生成，但 2025 年经营利润率、FCF、ROIC 等指标走弱，不能简单得出“经营杠杆很好”的结论。",
        "BMQ-12": "增长驱动可能来自商家数、每商家收入、交易服务占比、广告/流量变现、Temu/地域扩张等，但产品、地域、take-rate 拆分仍不足。",
        "BMQ-13": "模型主要是交易型和商家付费型，不是订阅模式。增长是否依赖补贴、商家支持、营销投入或供应链投入，需要继续验证。",
        "BMQ-14": "财务交叉验证支持资本开支轻、现金生成较好；但经营杠杆叙事存在张力，因为收入增长没有同步转化成更好的经营利润和 ROIC。",
        "BMQ-15": "SBC 和摊薄尚未在 BMUE 中完成判断，应交给 Financial Reality 与 Management/Governance workpaper 深挖。",
        "BMQ-16": "主要脆弱点包括商家经济性、Pinduoduo/Temu 披露不足、质量/物流/退货摩擦、监管和贸易风险，以及低价增长是否由隐性成本支撑。",
        "BMQ-17": "未知项集中在客户复购质量、商家盈利性、Temu 与 Pinduoduo 拆分、fee/take-rate、gross/net、分部披露和补贴依赖。",
        "BMQ-18": "下游应把这些证据交给 Moat、Growth Runway、Risk、Valuation、Management 和 Right Business Agent 继续判断。",
    }
    return summaries.get(question_id) or _bmue_zh_value(answer.get("answer_short"))


def _bmue_zh_sequence(values: list[Any]) -> str:
    return ", ".join(_bmue_zh_value(value) for value in values)


def _bmue_zh_status(value: Any) -> str:
    mapping = {
        "answered": "已回答",
        "partial": "部分回答 / 证据不足",
        "unknown": "未知",
        "complete": "完整",
        "thin": "薄弱",
        "high": "高",
        "medium": "中",
        "low": "低",
        "supports": "支持",
        "tension": "存在张力",
        "insufficient_evidence": "证据不足",
        "open": "待解决",
        "mixed": "混合",
    }
    return mapping.get(str(value or ""), str(value or "未知"))


def _bmue_zh_value(value: Any) -> str:
    text = _trim(value, limit=900)
    if not text:
        return ""
    exact = {
        "Transaction services": "交易服务",
        "Online marketing services and others": "在线营销服务及其他",
        "third-party merchants": "第三方商家",
        "buyers": "买家",
        "merchants": "商家",
        "buyers, merchants": "买家、商家",
        "buyers and merchants": "买家和商家",
        "logistics and fulfillment partners where relevant": "相关场景下的物流和履约伙伴",
        "merchants, buyers indirectly through product discovery": "商家，以及通过商品发现间接受益的买家",
        "buyers indirectly through product discovery": "通过商品发现间接受益的买家",
        "merchants, logistics and fulfillment partners where relevant": "商家，以及相关场景下的物流和履约伙伴",
        "third-party merchants, logistics vendors, fulfillment partners": "第三方商家、物流服务商和履约伙伴",
        "platform traffic and advertising inventory": "平台流量和广告库存",
        "mixed": "混合",
        "unknown": "未知",
        "partial": "部分披露 / 证据不足",
        "high": "高",
        "medium": "中",
        "low": "低",
        "open": "待解决",
        "supports": "支持",
        "tension": "存在张力",
        "insufficient_evidence": "证据不足",
        "marketplace": "交易平台 / marketplace",
        "advertising_platform": "广告/流量平台",
        "Competitive Position Workpaper": "竞争位置底稿",
        "Growth Runway Workpaper": "增长空间底稿",
        "Risk / Fragility / Red Flag Workpaper": "风险 / 脆弱性 / 红旗底稿",
        "Valuation Assumption Workpaper": "估值假设底稿",
        "Management / Governance / Capital Allocation Workpaper": "管理层 / 治理 / 资本配置底稿",
        "Right Business Agent": "Right Business 判断 Agent",
        "filing_fact": "申报文件事实",
        "revenue_recognition_fact": "收入确认事实",
        "calculated_metric": "计算指标",
        "management_claim": "管理层说法",
        "system_inference": "系统推断",
        "filed_narrative": "申报文件叙事",
        "filed_financial_note": "申报财务注释",
        "system_generated": "系统生成",
        "furnished_or_transcript_management_claim": "业绩材料或访谈中的管理层说法",
        "Commerce platform services: transaction services, online marketing services, buyer demand aggregation, and merchant access to traffic.": "电商平台服务：交易服务、在线营销、买家需求聚合，以及商家获取流量的入口。",
        "The business model should show operating leverage with scale.": "如果商业模式有规模效应，经营杠杆应该随规模扩大而体现。",
        "The model should convert profit into cash.": "该模型应该能把利润转化为现金。",
        "Revenue growth should be attributable to durable volume, price, mix, geography, or product drivers.": "收入增长应该能被可持续的销量、价格、结构、地域或产品驱动解释。",
        "Unit economics should not be overstated by ignoring SBC and dilution.": "单位经济不能因为忽略 SBC 和摊薄而被高估。",
        "merchant fee/ROI, seller terms, merchant complaints, ad intensity": "商家费用/ROI、卖家条款、商家投诉、广告强度",
        "segment/geography disclosure and Temu-specific margin commentary": "分部/地域披露，以及 Temu 相关利润率说明",
        "incremental operating margin and operating margin trend": "增量经营利润率和经营利润率趋势",
        "regulatory events, customs/tariff changes, product-safety actions": "监管事件、海关/关税变化、产品安全行动",
        "segment/product/geography/take-rate disclosure": "分部、产品、地域、take-rate 披露",
        "Is the buyer-merchant flywheel observable outside management language?": "买家-商家飞轮是否能在管理层叙事之外被外部证据观察到？",
        "Do competitors show grudging respect or copy-resistant disadvantages versus PDD/Temu?": "竞争对手是否体现出对 PDD/Temu 的被迫尊重，或显示出难以复制的劣势？",
        "Can merchant ROI remain attractive after platform fees, advertising, logistics, returns, and price pressure?": "扣除平台费用、广告、物流、退货和价格压力后，商家 ROI 还能否保持吸引力？",
        "How much growth is domestic Pinduoduo versus Temu/global expansion?": "增长中有多少来自国内 Pinduoduo，有多少来自 Temu/全球扩张？",
        "Which driver matters most now: merchant count, revenue per merchant, ad load, take rate, geography, or new products?": "当前最重要的增长驱动是什么：商家数量、每商家收入、广告负载、take-rate、地域扩张，还是新产品？",
        "Customer happiness and repeat-purchase quality outside official reports.": "官方报告之外的客户满意度和复购质量。",
        "Merchant profitability after ads, discounts, logistics, and platform rules.": "扣除广告、折扣、物流和平台规则后的商家盈利性。",
        "What regulatory, trade, tariff, consumer-protection, and platform-governance risks could impair the model?": "哪些监管、贸易、关税、消费者保护和平台治理风险可能削弱该模型？",
        "Does low-price growth depend on subsidies or merchant margin compression?": "低价增长是否依赖补贴或商家利润率压缩？",
        "What valuation sensitivity follows from lower 2025 operating margin and ROIC?": "2025 年经营利润率和 ROIC 下滑会带来怎样的估值敏感性？",
        "What normalized FCF margin should be used if current investment pressure persists?": "如果当前投资压力持续，应该使用什么 normalized FCF margin？",
        "Is management's long-term investment explanation consistent with financial outcomes?": "管理层关于长期投入的解释是否与财务结果一致？",
        "Does management answer merchant economics, Temu disclosure, and margin-pressure questions directly?": "管理层是否直接回答商家经济性、Temu 披露和利润率压力问题？",
        "Do executive interviews clarify business-model philosophy without being over-weighted as evidence?": "高管访谈是否能澄清商业模式哲学，同时不被过度当作事实证据？",
        "Does the evidence support an understandable and attractive business through a cycle?": "现有证据是否支持这是一个穿越周期后仍可理解、仍有吸引力的生意？",
        "Which unknowns must be resolved before a stronger Right Business judgment is allowed?": "在做出更强的 Right Business 判断前，哪些未知项必须先解决？",
    }
    if text in exact:
        return exact[text]
    if text.startswith("PDD is best read as a merchant-funded demand aggregation"):
        return "PDD 更适合被理解为商家付费的需求聚合与电商服务平台：买家因为低价、选择和互动购物被吸引，商家则为需求获取、在线营销和交易相关服务付费。"
    if text.startswith("The filing identifies buyers/consumers and merchants"):
        return "申报文件识别出的核心参与者是买家/消费者和商家。经济付款方主要是购买平台服务的商家，终端使用者是买家；供给侧依赖第三方商家，Temu 还依赖物流和履约伙伴。"
    if text.startswith("Current evidence supports merchant-funded"):
        return "当前证据支持商家付费的交易服务和在线营销机制，但具体费率基础、take-rate、billing 和卖家条款仍披露不足。"
    if text.startswith("Revenue-recognition evidence anchors"):
        return "收入确认证据可以锚定收入流，但收入确认时点、履约义务细节和合同余额相关性仍需要结构化抽取。"
    if text.startswith("Gross/net treatment is not fully resolved"):
        return "Gross / Net 列报尚未完全解决；已有收入确认证据，但 principal-agent 依据需要继续抽取。"
    if text.startswith("Official data show a major mix shift"):
        return "官方数据说明收入结构发生明显变化：交易服务从较小收入来源提升到接近一半收入，在线营销仍占另一半。这意味着模型不再只是广告化平台，也更受交易服务强度、商家 ROI 和 Temu 结构影响。"
    if text.startswith("At company level, yes, but with an important warning"):
        return "从公司层面看，PDD 仍有较高毛利率、自由现金流、现金转化和 ROIC，但 2025 年相对 2024 年走弱：收入增长没有同步转化成经营利润、净利润、FCF、利润率和 ROIC 的改善。"
    if text.startswith("The model is primarily transactional and merchant-funded"):
        return "该模型主要是交易型、商家付费型，不是订阅模式。重复行为由平台规模间接支持，但仍缺少完整的买家/订单/留存 KPI；增长可能受到商家支持、供应链投入、营销和补贴影响。"
    if text.startswith("Financial evidence confirms company-level cash generation"):
        return "财务证据支持公司层面的现金生成和轻资本特征，但与简单的经营杠杆叙事存在冲突：2025 年收入增长的同时，经营利润、净利润、自由现金流、经营利润率和 ROIC 走弱。"
    if text.startswith("SBC/dilution should be checked"):
        return "SBC 和摊薄需要通过 Financial Reality 与 Management/Governance 底稿继续检查；当前 BMUE 只把它记录为必查项。"
    if text.startswith("The strongest anti-moat concern"):
        return "最强的反护城河问题是：低价可能由隐藏成本支撑，包括质量问题、退款摩擦、监管/贸易暴露、物流负担、商家利润压力或高昂增长投入。2025 年利润率和 ROIC 下滑让这不是泛泛风险，而是真正的尽调问题。"
    if text.startswith("Other agents should investigate"):
        return "其他 agent 应继续调查商业模式背后的未证实假设：护城河耐久性、增长空间、风险、估值敏感性和管理层一致性。"
    if text.startswith("Partial. Latest revenue growth is"):
        return "部分支持但存在张力：最新收入增长和经营利润率仍为正，但增量经营利润率为负；官方收入组件能覆盖全部收入，交易服务收入是当前抽取到的最大组件。"
    if text.startswith("Latest gross margin is"):
        return "最新毛利率、经营利润率和净利率仍为正，但增量经营利润率为负，说明新增收入没有自然转化成新增经营利润。"
    match = re.match(r"(\d+) unknown or partial items require source follow-up\.", text)
    if match:
        return f"有 {match.group(1)} 个未知或部分回答项需要继续补充 source。"
    match = re.match(r"(\d+) financial cross-check tensions remain open\.", text)
    if match:
        return f"仍有 {match.group(1)} 个财务交叉验证张力待解决。"
    if text.startswith("Segment/geography disclosure is partial or missing"):
        return "分部/地域披露仍然部分缺失；Pinduoduo 与 Temu 的经济性仍未被充分拆开。"
    match = re.match(r"(\d+) BMQ answers are partial", text)
    if match:
        return f"有 {match.group(1)} 个 BMQ 回答仍是部分回答；adapter 选择 abstain，而不是编造单位经济。"
    replacements = [
        ("Platform transaction-related services to merchants.", "向商家提供的平台交易相关服务。"),
        ("Marketing and demand-generation services to merchants.", "向商家提供营销和需求生成服务。"),
        ("transaction-related fees or service fees", "交易相关费用或服务费"),
        ("online marketing service fees", "在线营销服务费"),
        ("merchant-funded transaction and online marketing service economics", "由商家付费的交易服务和在线营销经济机制"),
        ("online platform services / transaction services / online marketing services", "在线平台服务 / 交易服务 / 在线营销服务"),
        ("Needs explicit principal-agent extraction from revenue recognition policy.", "需要从收入确认政策中明确抽取 principal-agent 依据。"),
        ("company-level margin and cash-conversion proxy", "公司层面的利润率和现金转化代理指标"),
        ("indirect_proxy", "间接代理指标"),
        ("Does not replace company-disclosed order-level or merchant-level economics.", "不能替代公司披露的订单级或商家级单位经济。"),
        ("sales and marketing / merchant support / supply-chain and logistics-related investments", "销售与营销 / 商家支持 / 供应链和物流相关投入"),
        ("mixed_or_unknown", "固定与可变混合，或尚未知"),
        ("volume_price_mix_geography_product_unknown", "销量 / 价格 / mix / 地域 / 产品驱动仍未拆清"),
        ("discounts, merchant support, supply-chain investment, marketing, or incentives", "折扣、商家支持、供应链投入、营销或激励"),
        ("Merchant economics may be fragile after ads, fees, discounts, logistics, returns, and platform rules.", "商家经济性可能受广告、费用、折扣、物流、退货和平台规则影响而变脆弱。"),
        ("Pinduoduo versus Temu economics are not fully separated.", "Pinduoduo 与 Temu 的经济性没有被充分拆开。"),
        ("Operating leverage claim is under pressure in 2025.", "2025 年经营杠杆叙事承压。"),
        ("Quality, counterfeit, logistics, regulation, trade, and consumer-protection risks can damage the low-price model.", "质量、假货、物流、监管、贸易和消费者保护风险可能伤害低价模型。"),
        ("operating_leverage", "经营杠杆"),
        ("cash_conversion", "现金转化"),
        ("revenue_growth_quality", "收入增长质量"),
        ("sbc_dilution", "SBC / 摊薄"),
        ("not_disclosed", "未披露"),
        ("ambiguous_or_partial", "模糊或部分披露"),
        ("source_connected_but_not_fully_consumed", "source 已连接但尚未充分消费"),
        ("stronger source evidence", "更强来源证据"),
        ("pricing pages, fee schedules, merchant terms", "定价页面、费率表、商家条款"),
        ("revenue recognition note with principal-agent basis", "包含 principal-agent 依据的收入确认注释"),
        ("segment and geography disclosure", "分部与地域披露"),
        ("company-disclosed KPI or stronger proxy metric", "公司披露 KPI 或更强代理指标"),
        ("marketing/subsidy policy and financial trend evidence", "营销/补贴政策与财务趋势证据"),
        ("SBC, share-count, and proxy compensation evidence", "SBC、股数和薪酬代理证据"),
    ]
    translated = text
    for source, target in replacements:
        translated = translated.replace(source, target)
    return translated
