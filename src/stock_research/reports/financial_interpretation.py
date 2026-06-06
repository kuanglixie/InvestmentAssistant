from __future__ import annotations

import re
from typing import Any

# Presentation principle for the easy-reading report:
# use tables only when they make comparison easier across periods, metrics, or categories.
# For 2-4 related numbers, prefer compact prose or short bullets so the report stays readable.

def build_financial_easy_reading_report(
    pack: dict[str, Any],
    *,
    audit_status: str,
    official_evidence_pack: dict[str, Any] | None = None,
    management_communication_pack: dict[str, Any] | None = None,
) -> str:
    company = pack.get("company") or {}
    company_name = company.get("legal_name") or company.get("company_id") or "Unknown Company"
    fact_quality_gate = pack.get("fact_quality_gate") or {}
    if fact_quality_gate and not fact_quality_gate.get("can_generate_full_report", True):
        return _extraction_failure_report(pack, audit_status=audit_status)
    diagnostics = (pack.get("diagnostic_findings") or {}).get("questions") or []
    review_flags = pack.get("human_review_flags") or []

    return f"""# 财务报告易读版：{company_name}

## 一页结论与动作卡片

{_action_card(pack)}

> 说明：这里的动作只代表基于官方财报的基本面研究动作，不包含市场价格、目标价或买卖建议。分数读法：8 分以上通常为高质量，6.5-7.9 分为质量较高但仍需验证，5-6.4 分为中性观察，5 分以下为承压或回避。

## 第一层：核心指标与红旗诊断（财务证据层）

{_layer_one_intro(pack)}

### 1. 核心判断

{_core_judgment_section(pack)}

### 2. 主要财务指标

#### A. 三年财务趋势：年度主线

{_annual_trend_table(pack)}

{_annual_trend_readout(pack)}

#### B. 季度趋势与拐点：最新季度验证

{_quarterly_trend_table(pack)}

{_quarterly_trend_readout(pack)}

#### C. 收入结构与增长质量

{_revenue_structure_summary(pack)}

#### D. 营运资本桥

{_working_capital_bridge_summary(pack)}

#### E. 资产负债表与现金缓冲

{_liquidity_summary(pack)}

### 3. 关键问题与红旗（主要问题与下一步要证伪）

{_top_open_items(pack)}

### 4. 数据洞察与异常发现

{_numeric_insights_section(pack)}

## 第二层：官方文件解释与叙事发现（官方报告层）

{_layer_two_intro(pack)}

### 1. 第一层问题回查：当前官方证据包

{format_financial_diagnostic_questions_compact_zh(diagnostics, pack, official_evidence_pack=official_evidence_pack)}

### 2. 官方证据主动发现：叙事、结构与治理

{_decision_relevant_narratives_section(official_evidence_pack)}

{_investigation_notes_section(pack)}

## 第三层：管理层沟通与叙事裁判（管理层沟通层）

{_layer_three_intro(management_communication_pack)}

### 1. 前两层留下的问题：管理层怎么解释

{_management_issue_reviews_section(management_communication_pack)}

### 2. 管理层新叙事与战略变化

{_management_narratives_section(management_communication_pack)}

### 3. Q&A 压力与回答质量

{_qa_pressure_section(management_communication_pack)}

## 后续跟踪清单

{_watchlist_summary(pack)}

## 附录：来源、口径与复核点

### 证据覆盖与置信度

{_evidence_coverage_table(pack)}

### 来源与范围

{_source_scope_summary(pack)}

### 披露边界与口径

{_disclosure_boundary_table(pack)}

### 需要人工复核的关键点

{_review_flags_summary(review_flags)}

### 使用限制

- 本报告只做财报阅读和财务质量判断；企业价值、估值收益率、目标价和买卖建议应放在独立估值报告里。
- 自由现金流近似值按经营现金流减资本开支计算，不能区分维护性资本开支和增长性资本开支，只能作为现金质量线索。
- 重大事项扫描不是逐份 6-K / 8-K / proxy 的摘要；它只提升可能影响财务风险、稀释、控制权、审计可靠性或资本结构的事项。
"""


def _extraction_failure_report(pack: dict[str, Any], *, audit_status: str) -> str:
    company = pack.get("company") or {}
    company_name = company.get("legal_name") or company.get("company_id") or "Unknown Company"
    gate = pack.get("fact_quality_gate") or {}
    extraction = pack.get("fact_extraction_summary") or {}
    baseline = (pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {}
    missing = gate.get("missing_core_metrics") or []
    present = gate.get("present_core_metrics") or []
    latest_year = gate.get("latest_annual_year") or "未识别"
    methods = extraction.get("methods_used") or []
    source_doc = baseline.get("document_id") or baseline.get("local_path") or "未识别"
    return f"""# 财务报告易读版：{company_name}

## 事实抽取失败：缺少核心财务事实

本次没有生成完整财务报告。原因不是分析层判断为负面，而是第一层事实抽取没有通过质量门：最新年度必须至少抽到收入、经营利润、净利润、经营现金流和现金，才能继续生成完整分析。

- 抽取状态：{gate.get("status") or "failed"}
- 年度锚点：{latest_year}
- 已抽核心事实：{", ".join(present) if present else "无"}
- 缺失核心事实：{", ".join(missing) if missing else "未列明"}
- 最新年度文件：{source_doc}
- 抽取方法：{", ".join(methods) if methods else extraction.get("method") or "未识别"}
- Raw facts：{extraction.get("raw_fact_count", 0)}
- Selected facts：{extraction.get("selected_fact_count", 0)}
- Audit status：{audit_status}

## 处理原则

在核心事实缺失时，pipeline 不应继续写完整投资报告，也不应把缺失数字用推测、手工记忆或第三方数据补上。下一步应先修复 Financial Fact Extractor 或补齐官方文件缓存，再重新运行报告。
"""


def _layer_one_intro(pack: dict[str, Any]) -> str:
    latest_annual = (pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {}
    trend = pack.get("latest_interim_trend") or {}
    document_type = latest_annual.get("document_type") or "annual report"
    filing_date = latest_annual.get("filing_date") or "未识别日期"
    report_date = latest_annual.get("report_date") or "未识别报告期"
    annual_source = f"{filing_date} {document_type}（报告期 {report_date}）" if latest_annual else "未识别最新年度文件"
    latest_quarter = trend.get("latest_period_end") or "未识别"
    return (
        "这一层只处理可结构化复算的官方财务数字，用固定公式检查增长、利润率、现金转化、营运资本、"
        f"资产负债表、稀释和会计质量。年度锚点是 {annual_source}；最新季度口径是 {latest_quarter}。"
        "它能发现模式和红旗，但不能单独证明管理层动机、未披露 KPI 或估值高低。"
    )


def _layer_two_intro(pack: dict[str, Any]) -> str:
    latest_annual = (pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {}
    trend = pack.get("latest_interim_trend") or {}
    document_type = latest_annual.get("document_type") or "annual report"
    filing_date = latest_annual.get("filing_date") or "未识别日期"
    report_date = latest_annual.get("report_date") or "未识别报告期"
    latest_quarter = trend.get("latest_period_end") or "未识别"
    return (
        "这一层读取官方文件里的解释、附注和治理材料，包括 20-F / 10-K、MD&A / OFR、收入和成本附注、"
        "现金流与流动性披露、资金可用性 / 受限现金 / 税项 / 非 GAAP 调节、季度 6-K / 10-Q、业绩稿，以及 proxy / AGM。"
        f"当前主文件是 {filing_date} {document_type}（报告期 {report_date}），最新季度口径是 {latest_quarter}。"
        "它不重算第一层指标，而是判断官方记录能证明什么、只能解释什么、仍然不知道什么。"
    )


def _layer_three_intro(management_communication_pack: dict[str, Any] | None) -> str:
    source_count = len((management_communication_pack or {}).get("source_catalog") or [])
    if not management_communication_pack:
        return (
            "这一层读取管理层沟通材料，例如业绩电话会文字稿、Q&A、股东信、投资者演示、投资者日材料、"
            "行业会议 / fireside chat、管理层访谈和官方新闻 / 产品公告。"
            "它不是新的财务事实来源，也不覆盖第一层数字或第二层官方 filing 证据；它只判断管理层如何解释问题、回答是否具体、"
            "是否回避市场追问，以及有没有新的战略叙事。当前报告尚未接入 `management_communication_pack.json`，"
            "所以本层先显示应追问的框架，不把管理层沟通写成已完成分析。"
        )
    source_catalog = (management_communication_pack or {}).get("source_catalog") or []
    status_note = ""
    if source_catalog:
        first_source = source_catalog[0]
        status = _source_status_label_zh(first_source.get("status") or first_source.get("source_quality_note"))
        period = first_source.get("period") or ""
        status_note = f"当前 V1 主要来源是 {period} 业绩电话会文字稿；来源状态：{status}。"
    return (
        f"这一层已接入 {source_count} 个管理层沟通来源，主要检查管理层如何解释问题、回答是否具体、"
        "是否回避追问，以及是否出现新的战略叙事。本层证据权重低于第一层数字和第二层 filing；"
        "文字稿里的数字不能覆盖正式财务数据来源。"
        f"{status_note}"
    )


def _source_status_label_zh(status: Any) -> str:
    mapping = {
        "raw_transcript_not_independently_verified": "原始文字稿，尚未独立校验",
    }
    return mapping.get(str(status or ""), str(status or "未标注"))


def _alpha_index(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if 1 <= index <= len(alphabet):
        return alphabet[index - 1]
    return str(index)


def _company_id(pack: dict[str, Any] | None) -> str:
    return str(((pack or {}).get("company") or {}).get("company_id") or "").lower()


def _numeric_insights_section(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return "- 年度数据不足，暂时无法做数据洞察。"
    latest = rows[-1]
    prior = rows[-2]
    insights: list[str] = []

    revenue_growth = _growth(latest, prior, "revenue")
    quarterly = _quarterly_rows(pack)
    latest_q = quarterly[-1] if quarterly else None
    prior_q = _prior_year_quarter(quarterly, latest_q) if latest_q else None
    q_operating_growth = _growth(latest_q, prior_q, "operating_income")
    q_net_growth = _growth(latest_q, prior_q, "net_income")
    if q_operating_growth is not None and q_operating_growth > 0 and q_net_growth is not None and q_net_growth < 0:
        insights.append(
            "**季度利润分叉发生在经营利润以下：** 最新季度经营利润同比 "
            f"{_pct(q_operating_growth)}，但净利润同比 {_pct(q_net_growth)}。"
            "这说明单季净利润压力不只来自经营层面，还要拆投资收益、利息、税项和非 GAAP 调整；"
            "否则容易把经营利润改善和归母净利润下降混在一起。"
        )

    tax_metric = _metric_by_id(pack.get("financial_metrics") or [], "tax_non_gaap_accounting_quality_v1")
    tax_result = _latest_calculated_result(tax_metric or {})
    investment_income_to_pretax = (tax_result or {}).get("investment_income_to_pretax")
    effective_tax_rate = (tax_result or {}).get("effective_tax_rate")
    if investment_income_to_pretax is not None and abs(investment_income_to_pretax) >= 0.20:
        insights.append(
            "**净利润受非经营收益影响较大：** 最新年度投资收益 / 税前利润为 "
            f"{_pct(investment_income_to_pretax)}，有效税率为 {_pct(effective_tax_rate)}。"
            "这不是坏事，但说明读盈利质量时要优先看经营利润和经营现金流，不能只看最终净利润。"
        )

    capital_metric = _metric_by_id(pack.get("financial_metrics") or [], "capital_intensity_v1")
    capital_result = _latest_calculated_result(capital_metric or {})
    capex_to_revenue = (capital_result or {}).get("capex_to_revenue")
    fcf_to_cfo = (capital_result or {}).get("free_cash_flow_to_operating_cash_flow")
    if capex_to_revenue is not None and capex_to_revenue < 0.01:
        insights.append(
            "**投入压力没有主要体现在固定资产上：** 最新年度资本开支 / 收入只有 "
            f"{_pct(capex_to_revenue)}，自由现金流 / 经营现金流为 {_pct(fcf_to_cfo)}。"
            "如果公司同时强调供应链、商家支持或自营品牌业务，第一层应默认这些投入更可能体现在费用、履约、补贴或营运资本中，而不是传统资本开支。"
        )

    asset_growth = _growth(latest, prior, "total_assets")
    if asset_growth is not None and revenue_growth is not None and asset_growth > revenue_growth * 1.5:
        latest_asset_turnover = _safe_divide(latest.get("revenue"), latest.get("total_assets"))
        prior_asset_turnover = _safe_divide(prior.get("revenue"), prior.get("total_assets"))
        insights.append(
            "**资产规模扩张快于收入：** 最新年度总资产同比 "
            f"{_pct(asset_growth)}，明显高于收入同比 {_pct(revenue_growth)}；收入 / 总资产从 "
            f"{_pct(prior_asset_turnover)} 降到 {_pct(latest_asset_turnover)}。"
            "这提示报表正在变得更“资金沉淀”，下一层要看增长放缓时现金、短投、受限资金和投资资产如何影响资本效率。"
        )

    if not insights:
        return "- 除前面三节已经覆盖的核心问题外，没有发现额外的硬数据异常。"
    intro = (
        "这一节只列前面三节没有充分展开的额外硬数据信号；已经说清楚的收入结构、非 GAAP 和现金缓冲不再重复。"
    )
    return intro + "\n\n" + "\n".join(f"- {item}" for item in insights[:6])


def _management_issue_reviews_section(management_communication_pack: dict[str, Any] | None) -> str:
    if not management_communication_pack:
        return (
            "- 当前未运行第三层。应优先把第二层仍未知的问题交给业绩电话会 Q&A：利润率压力、自营品牌、"
            "供应链投入、Temu / 全球业务、现金资本配置和组织变化。"
        )
    reviews = management_communication_pack.get("layer_issue_reviews") or []
    if not reviews:
        return "- 第三层已接入，但没有生成针对前两层问题的回答。"
    lines = []
    for index, item in enumerate(reviews[:7], start=1):
        issue = _cell(item.get("issue_text") or item.get("issue_id") or "未命名问题")
        explanation = _cell(item.get("management_explanation") or "管理层没有给出明确解释。")
        quality = _answer_quality_label_zh(item.get("answer_quality"))
        unknown = _list_text_zh(item.get("still_unknown") or [])
        consistency = _consistency_label_zh(item.get("consistency_with_layer1"))
        lines.extend(
            [
                f"#### {_alpha_index(index)}. {issue}",
                "",
                f"**管理层回答：** {explanation}",
                "",
                f"**读法：** {quality}；与第一层数字的关系是{consistency}。"
                "这条只能解释管理层口径，不能替代第一层数字和第二层 filing 证据。",
                "",
                f"**仍未解决：** {unknown or '暂未标出新的未知项。'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _management_narratives_section(management_communication_pack: dict[str, Any] | None) -> str:
    if not management_communication_pack:
        return (
            "- 当前未运行第三层。这里未来应登记 management communication 中的新战略、新 KPI、业务模式变化、"
            "管理层承诺和官方产品 / 市场公告；但不能把它们写成已产生财务效果。"
        )
    narratives = management_communication_pack.get("new_narratives") or management_communication_pack.get("management_claims") or []
    if not narratives:
        return "- 第三层没有识别出新的管理层叙事或战略变化。"
    lines = []
    for index, item in enumerate(narratives[:8], start=1):
        title = _cell(item.get("title") or item.get("claim_text") or item.get("narrative_id") or "未命名叙事")
        summary = _cell(item.get("summary") or item.get("claim_text") or "暂无摘要。")
        why = _cell(item.get("why_it_matters") or item.get("why_it_matters_to_layer1") or "需要后续判断其财务影响。")
        unknown = _list_text_zh(item.get("still_unknown") or item.get("watch_items") or [])
        lines.extend(
            [
                f"#### {_alpha_index(index)}. {title}",
                "",
                f"{summary}",
                "",
                f"**投资读法：** {why}",
                "",
                f"**仍需验证：** {unknown or '后续用第一层数字和第二层 filing 验证。'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _qa_pressure_section(management_communication_pack: dict[str, Any] | None) -> str:
    if not management_communication_pack:
        return (
            "- 当前未运行第三层。未来本节应记录分析师反复追问的话题、管理层是否正面回答、是否给出数字或机制，"
            "以及是否回避利润率、单位经济性、监管、资本配置或新业务风险。"
        )
    topics = management_communication_pack.get("qa_pressure_topics") or []
    if not topics:
        return "- 第三层没有识别到集中的 Q&A 压力主题。"
    lines = []
    for index, item in enumerate(topics[:8], start=1):
        topic = _cell(item.get("topic") or item.get("title") or "未命名主题")
        concern = _cell(item.get("analyst_concern") or item.get("summary") or "分析师关注点未结构化。")
        response = _cell(
            item.get("management_response_read")
            or item.get("management_answer")
            or item.get("management_explanation")
            or ""
        )
        quality = _answer_quality_label_zh(item.get("answer_quality"))
        follow_up = _list_text_zh(item.get("follow_up_needed") or item.get("watch_items") or [])
        lines.extend(
            [
                f"#### {_alpha_index(index)}. {topic}",
                "",
                f"**分析师问什么：** {concern}",
                "",
            ]
        )
        if response:
            lines.extend([f"**管理层怎么回答：** {response}", ""])
        lines.extend(
            [
                f"**读法：** {quality}。",
                "",
                f"**后续追问：** {follow_up or '继续观察下一次电话会是否给出更具体数字或机制。'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _decision_relevant_narratives_section(official_evidence_pack: dict[str, Any] | None) -> str:
    narratives = (official_evidence_pack or {}).get("decision_relevant_narratives") or []
    if not narratives:
        return "- 第二层没有生成可进入报告的官方叙事。"
    lines = [
        "本节主动找官方文件中可能改变判断的事项，不重复第一层指标。重点是经济引擎、业务模式变化、现金可用性、治理、监管和会计可靠性。"
    ]
    governance_items = [item for item in narratives if item.get("narrative_type") == "governance"]
    emitted_governance = False
    for narrative in narratives[:9]:
        if narrative.get("narrative_type") == "governance":
            if emitted_governance:
                continue
            lines.extend(["", _governance_narrative_group_zh(governance_items)])
            emitted_governance = True
            continue
        title = _cell(narrative.get("title") or narrative.get("narrative_id") or "未命名叙事")
        narrative_type = _narrative_type_label_zh(narrative.get("narrative_type"))
        why = _cell(narrative.get("why_it_matters") or "")
        content = _narrative_official_content_zh(narrative)
        reading = _narrative_investment_reading_zh(narrative)
        still_unknown = _narrative_still_unknown_zh(narrative)
        lines.extend(
            [
                "",
                f"- **{title}**（{narrative_type}）：{content}",
                f"  - 读法：{reading}",
            ]
        )
        if still_unknown:
            lines.append(f"  - 缺口：{still_unknown}")
    return "\n".join(lines)


def _governance_narrative_group_zh(narratives: list[dict[str, Any]]) -> str:
    if not narratives:
        return "- **治理与股权计划**（治理）：当前证据包没有识别到可进入正文的治理事项。"
    known_ids = {str(item.get("narrative_id") or "") for item in narratives}
    facts = []
    if "management_governance_change" in known_ids:
        facts.append("Lei Chen 与 Zhao Jiazhen 为联席董事长兼联席 CEO，且 2025 年后续 6-K 披露了工程和财务负责人任命")
    if "agm_ads_voting_board" in known_ids:
        facts.append("AGM / proxy 材料显示 ADS 投票需经存托人，2025 年董事重选均获通过")
    if "share_plan_extension" in known_ids:
        facts.append("2015 Global Share Plan 期限由 10 年延长至 20 年")
    fact_text = "；".join(facts) if facts else "官方材料披露了治理、投票或股权计划事项"
    return "\n".join(
        [
            f"- **治理与股权计划**（治理）：{fact_text}。",
            "  - 读法：这些事项不直接解释收入和利润，但会影响执行稳定性、少数股东权利和长期稀释。",
            "  - 缺口：后续继续看董事反对票、股权激励强度、回购是否抵消稀释，以及关键管理层变化后的执行结果。",
        ]
    )


def _narrative_official_content_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return (
            "20-F 将收入分为交易服务和在线营销服务及其他；最新季度披露收入 RMB 106.2B，"
            "其中交易服务收入 RMB 56.3B、占 53.0%，在线营销服务及其他收入 RMB 49.9B、占 47.0%。"
            "公司也说明本季度收入增长主要来自交易服务收入增加。"
        )
    if narrative_id == "first_party_brand":
        return (
            "最新业绩稿将自营品牌业务列为新的重点业务，并表示公司会投入重要资源建设这一业务。"
            "这个叙事和供应链投入一起出现，说明管理层正在把平台能力更深地推进到产品、品牌和供应链环节。"
        )
    if narrative_id == "supply_chain_investment":
        return (
            "20-F 披露公司向商家提供工具、培训和支持；收入成本中也包含履约、支付处理、平台运营、带宽和服务器、商家支持等项目。"
            "最新业绩稿进一步把供应链投入列为核心战略优先事项，并强调平台生态和商家支持。"
        )
    if narrative_id == "global_business_temu":
        return (
            "20-F 披露 Temu 于 2022 年推出，并已扩展到多个海外市场；同时，官方文件没有单独披露 Temu 的收入、利润、GMV 或履约成本。"
            "因此，全球业务是重要叙事，但目前仍不是一个可独立建模的财务分部。"
        )
    if narrative_id == "restricted_cash_vie":
        return (
            "2025 年末公司披露现金 RMB 108.9B、受限现金 RMB 73.8B、短期投资 RMB 313.4B；"
            "20-F 同时披露 VIE 结构、中国境内资金转移限制、汇兑和跨境交易限制。"
        )
    if narrative_id == "management_governance_change":
        return (
            "20-F 和后续 6-K 确认 Lei Chen 与 Zhao Jiazhen 为联席董事长兼联席 CEO；"
            "2025 年 12 月 6-K 还披露 Jiazhen Zhao 被任命为联席董事长，并任命 Mi Wang 为工程高级副总裁、Jiong Li 为财务负责人。"
            "这条叙事说明组织和管理层职责仍在调整。"
        )
    if narrative_id == "agm_ads_voting_board":
        return (
            "Proxy / AGM 材料披露 ADS 持有人需要通过存托人提交投票指示；2025 年 AGM 结果显示 5.647B votes、"
            "占记录日总投票权 99.2% 出席或由代理出席，Lei Chen、Jiazhen Zhao、Anthony Kam Ping Leung、Haifeng Lin、"
            "Ivonne M.C.M. Rietjens 和 George Yong-Boon Yeo 六项董事重选普通决议均通过。"
        )
    if narrative_id == "share_plan_extension":
        return (
            "2025 年 6-K 附件披露董事会和薪酬委员会批准修订 2015 Global Share Plan，将该计划期限由初始生效日起 10 年延长至 20 年。"
            "这属于治理 / 激励事件，不是经营业绩解释。"
        )
    if narrative_id == "audit_accounting_reliability":
        return (
            "20-F 披露独立注册会计师对 2025 年财报和内控有效性出具审计意见；"
            "当前第二层没有识别到重述或重大内控缺陷。"
        )
    facts = _evidence_summary(narrative.get("filing_facts") or [])
    management = _evidence_summary(narrative.get("management_explanations") or [])
    if management and management != "官方文件未提供足够直接证据。":
        return f"{facts} 管理层解释：{management}"
    return facts


def _narrative_investment_reading_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return (
            "这条信息会改变收入增长的读法：PDD 最新季度已经不能只按广告/流量变现平台来理解，"
            "交易服务成为最大收入组件。它支持“增长来源在交易服务”的判断，但不能单独证明增长质量；"
            "如果交易服务占比提高的同时利润率下降，就要继续追问交易服务是否伴随更高履约、商家支持或平台治理成本。"
        )
    if narrative_id == "first_party_brand":
        return (
            "自营品牌可能是业务模式变化，而不只是营销口号。积极一面是公司可能通过更深供应链控制提升质量、标准化和品牌能力；"
            "保守一面是平台可能承担更多库存、质量控制、履约、合规和资本占用风险。"
            "所以这条叙事应进入核心跟踪，但现在还不能直接写成已经产生回报。"
        )
    if narrative_id == "supply_chain_investment":
        return (
            "这能解释一部分利润率压力：如果公司把资源投向商家支持、履约、供应链能力和平台治理，短期经营利润率下降并不一定等于竞争力恶化。"
            "但它也不能自动证明投入是高回报的；后续必须看到收入质量、费用率、现金流或商家经济性改善，才能把它升级为正面护城河证据。"
        )
    if narrative_id == "global_business_temu":
        return (
            "Temu / 全球业务可能是长期增长空间，也可能是成本和监管不确定性的来源。"
            "由于公司没有单独披露 Temu 财务闭环，报告只能把它作为战略叙事和风险变量，不能把海外增长、单位经济性或利润贡献当成已验证事实。"
        )
    if narrative_id == "restricted_cash_vie":
        return (
            "这条叙事直接影响资产负债表的读法：账面现金和短投很厚，但并不等于全部现金都能自由分配、回购或跨境调配。"
            "因此第一层的“安全垫强”仍成立，但置信度需要被受限现金、VIE 和资金转移限制打折。"
        )
    if narrative_id == "management_governance_change":
        return (
            "管理层与关键财务/工程岗位变化不直接推翻财务主线，但会影响执行风险和组织转型判断。"
            "尤其在公司强调供应链、自营品牌和平台治理投入的阶段，工程负责人和财务负责人的更替应进入后续治理监控。"
        )
    if narrative_id == "agm_ads_voting_board":
        return (
            "这不是收入、利润或现金流证据，但它会影响少数股东治理读法。董事重选均获通过，说明没有直接治理否决信号；"
            "但部分董事存在约 8%-14% 的反对票，值得作为治理温度计继续跟踪。"
        )
    if narrative_id == "share_plan_extension":
        return (
            "这会把“稀释暂未成为主线风险”的判断变成持续监控项：当前 SBC / 收入和稀释股数并不高，"
            "但股权计划期限延长说明长期激励工具仍然重要，后续要和 SBC、稀释股数、回购抵消情况一起看。"
        )
    if narrative_id == "audit_accounting_reliability":
        return (
            "审计和内控披露支持这份财报可以作为分析基础，但这不是“没有会计风险”的证明。"
            "对 PDD 这类平台，后续仍要特别看补贴/激励分类、收入确认、非 GAAP 调整、投资收益和关键审计事项。"
        )
    return _cell(narrative.get("our_inference") or "官方叙事已登记，但 V1 尚未生成更细的投资读法。")


def _narrative_still_unknown_zh(narrative: dict[str, Any]) -> str:
    narrative_id = str(narrative.get("narrative_id") or "")
    if narrative_id == "transaction_services_revenue_mix":
        return "全年收入结构是否稳定、交易服务增长来自价格/量/服务范围还是 take rate、以及交易服务扩张是否会带来更高成本。"
    if narrative_id == "first_party_brand":
        return "是否承担库存风险、是否形成单独收入和利润、投入回收期多长、以及这项业务会不会让平台模式变重。"
    if narrative_id == "supply_chain_investment":
        return "商家支持和供应链投入的金额、持续性、费用归类，以及这些投入能否在后续季度转化为收入质量或利润率修复。"
    if narrative_id == "global_business_temu":
        return "Temu 单独收入、利润、GMV、履约成本、监管成本和地区结构；目前官方财报没有给出完整拆分。"
    if narrative_id == "restricted_cash_vie":
        return "现金在母公司、境内子公司和 VIE 之间的可转移性，以及受限现金能否真正用于股东回报或海外业务投入。"
    if narrative_id == "management_governance_change":
        return "新治理/管理层安排对执行质量、资本配置纪律、关联交易和少数股东保护的实际影响。"
    if narrative_id == "agm_ads_voting_board":
        return "下一次 AGM 是否继续出现较高反对票、ADS 持有人投票机制是否影响少数股东表达，以及是否出现治理争议。"
    if narrative_id == "share_plan_extension":
        return "剩余可授予股份、未来 SBC 强度、稀释股数变化，以及回购是否能抵消股权激励稀释。"
    if narrative_id == "audit_accounting_reliability":
        return "关键审计事项的敏感性、会计估计变化、补贴分类和未来是否出现重述或内控变化。"
    unknown = "；".join(_cell(item) for item in narrative.get("still_unknown") or [] if item)
    return _ensure_sentence_zh(unknown) if unknown else ""


def _narrative_type_label_zh(narrative_type: Any) -> str:
    labels = {
        "KPI": "公司特有 KPI",
        "strategic_initiative": "战略举措",
        "business_model_change": "业务模式变化",
        "regulation": "监管 / 结构风险",
        "governance": "治理变化",
        "dilution": "稀释 / 激励",
        "accounting": "会计 / 审计信号",
    }
    return labels.get(str(narrative_type or ""), str(narrative_type or "未分类"))


def _narrative_source_trace(narrative: dict[str, Any]) -> str:
    evidence = (narrative.get("filing_facts") or narrative.get("evidence_bundle") or [])
    if not evidence:
        return "官方来源未结构化定位。"
    item = evidence[0]
    filing_date = item.get("filing_date") or item.get("period") or "未识别日期"
    document_type = item.get("source_document_type") or "official filing"
    section = item.get("source_section") or "未识别章节"
    document = item.get("source_document") or "未识别文件"
    return f"{filing_date}，{document_type}，{section}，{document}。"


def _summary_judgment(pack: dict[str, Any]) -> str:
    diagnostics = pack.get("diagnostic_findings") or {}
    summary = diagnostics.get("summary") or {}
    trend = pack.get("latest_interim_trend") or {}
    material_scan = pack.get("material_event_scan") or {}
    review_flags = pack.get("human_review_flags") or []
    pieces = [
        f"- 财务质量问题：已回答 {summary.get('answered', 0)} 个，部分回答 {summary.get('partial', 0)} 个，缺失 {summary.get('missing', 0)} 个。",
        f"- 最新季度状态：{_trend_status_zh(trend.get('overall_status'))}，方向：{_trend_direction_zh(trend.get('direction'))}。",
        f"- 重大事项：{material_scan.get('material_event_count', 0)} 个，其中高优先级 {material_scan.get('high_priority_event_count', 0)} 个。",
        f"- 人工确认：{len(review_flags)} 个标记，主要来自近似公式、缺失事实、重大事项或来源冲突。",
    ]
    return "\n".join(pieces)


def _source_scope_summary(pack: dict[str, Any]) -> str:
    latest_annual = (pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {}
    trend = pack.get("latest_interim_trend") or {}
    material_scan = pack.get("material_event_scan") or {}
    annual_line = _annual_source_line(latest_annual)
    latest_quarter = trend.get("latest_period_end") or "未识别"
    material_text = _material_scope_text_zh(material_scan)
    lines = [
        f"- 年报主锚：{annual_line}。",
        f"- 季度更新：最新季度为 {latest_quarter}，只用于验证年报主线是否改变。",
        f"- 重大事项：{material_text}",
        "- 来源追踪：结构化数字追踪到 XBRL / financial_report_pack；官方解释追踪到 filing date、form、document id 和 section。当前 HTML 文件尚未生成稳定页码，因此先使用文档和章节定位。",
        "- 不包含：估值结论、目标价、买卖建议或第三方数据。已接入的业绩电话会文字稿只用于第三层管理层沟通分析，不作为正式财务数据来源。",
    ]
    return "\n".join(lines)


def _action_card(pack: dict[str, Any]) -> str:
    status = _fundamental_status(pack)
    action = _research_action(status)
    strength = _evidence_strength(pack)
    score = _fundamental_score(pack)
    lines = [
        "| 项目 | 当前判断 |",
        "| --- | --- |",
        f"| 基本面状态 | {status} |",
        f"| 基本面分数 | {_score(score)} |",
        f"| 研究动作 | {action} |",
        f"| 证据强度 | {strength} |",
        f"| 最大正面证据 | {_primary_positive_evidence(pack)} |",
        f"| 最大反证风险 | {_primary_disconfirming_risk(pack)} |",
        f"| 下一次最先验证 | {_next_validation_point(pack)} |",
    ]
    return "\n".join(lines)


def _core_judgment_section(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return "- 年度数据不足，暂时不能形成三大核心判断。"
    latest = rows[-1]
    prior = rows[-2]
    growth_question = _diagnostic_question(pack, "growth_quality")
    cash_question = _diagnostic_question(pack, "cash_profit_quality")
    balance_question = _diagnostic_question(pack, "balance_sheet_resilience")
    top_component = ((growth_question or {}).get("latest_values") or {}).get("top_revenue_component")
    cash_values = (cash_question or {}).get("latest_values") or {}
    balance_values = (balance_question or {}).get("latest_values") or {}
    latest_quarter = _quarterly_rows(pack)[-1] if _quarterly_rows(pack) else None
    prior_year_quarter = _prior_year_quarter(_quarterly_rows(pack), latest_quarter) if latest_quarter else None
    lines = [
        "#### A. 有没有增长？",
        "",
        (
            f"- 结论：{_growth_readout(latest, prior)}。最新年度收入同比 {_pct(_growth(latest, prior, 'revenue'))}，"
            f"最新季度收入同比 {_pct(_latest_quarter_growth(pack))}。"
        ),
        (
            f"- 关键证据：年度经营利润同比 {_pct(_growth(latest, prior, 'operating_income'))}，"
            f"年度净利润同比 {_pct(_growth(latest, prior, 'net_income'))}；"
            f"最新季度经营利润同比 {_pct(_growth(latest_quarter, prior_year_quarter, 'operating_income'))}，"
            f"最新季度净利润同比 {_pct(_growth(latest_quarter, prior_year_quarter, 'net_income'))}。"
        ),
        *_core_revenue_source_lines(pack, latest, prior, top_component),
        "",
        "#### B. 增长有没有兑现为利润和现金？",
        "",
        (
            f"- 结论：{_margin_readout(latest, prior)}；{_cash_readout(latest)}。"
            f"数字上，经营利润率 {_pct(_margin(prior, 'operating_income'))} -> {_pct(_margin(latest, 'operating_income'))}，"
            f"经营现金流 / 净利润 {_ratio(_safe_divide(latest.get('operating_cash_flow'), latest.get('net_income')))}。"
        ),
        (
            f"- 利润证据：经营利润率从 {_pct(_margin(prior, 'operating_income'))} 变为 {_pct(_margin(latest, 'operating_income'))}，"
            f"净利率从 {_pct(_margin(prior, 'net_income'))} 变为 {_pct(_margin(latest, 'net_income'))}。"
        ),
        f"- 现金证据：{_core_cash_evidence_zh(latest, cash_values)}。",
        "",
        "#### C. 资产负债表能不能支撑投入期？",
        "",
        (
            f"- 结论：{_balance_readout(latest)}。广义现金与短投 {_money(_broad_liquidity(latest))}，"
            f"{_core_balance_snapshot_zh(latest)}。"
        ),
        f"- 抗压证据：{_core_balance_evidence_zh(latest, balance_values)}。",
        f"- 需要保守看的地方：{_core_balance_caveat_zh(balance_values)}",
    ]
    return "\n".join(lines)


def _core_cash_evidence_zh(latest: dict[str, Any], cash_values: dict[str, Any]) -> str:
    return _join_metric_pieces_zh(
        _metric_piece_zh("经营现金流 / 净利润", _ratio(_safe_divide(latest.get("operating_cash_flow"), latest.get("net_income")))),
        _metric_piece_zh("自由现金流率", _pct(_margin(latest, "free_cash_flow"))),
        _metric_piece_zh("营运资本现金顺风 / 收入", _pct(cash_values.get("working_capital_cash_tailwind_to_revenue"))),
    )


def _core_balance_snapshot_zh(latest: dict[str, Any]) -> str:
    return _join_metric_pieces_zh(
        _metric_piece_zh("流动比率", _ratio(_safe_divide(latest.get("current_assets"), latest.get("current_liabilities")))),
        _metric_piece_zh("总负债 / 总资产", _pct(_safe_divide(latest.get("total_liabilities"), latest.get("total_assets")))),
    )


def _core_balance_evidence_zh(latest: dict[str, Any], balance_values: dict[str, Any]) -> str:
    return _join_metric_pieces_zh(
        _metric_piece_zh("现金 / 总负债", _ratio(_safe_divide(latest.get("cash"), latest.get("total_liabilities")))),
        _metric_piece_zh("受限现金 / 现金", _pct(balance_values.get("restricted_cash_to_cash"))),
    )


def _core_balance_caveat_zh(balance_values: dict[str, Any]) -> str:
    restricted = _pct(balance_values.get("restricted_cash_to_cash"))
    if restricted:
        return (
            f"受限现金 / 现金 {restricted}，所以现金很厚不等于全部现金都能自由用于股东回报或跨境调配；"
            "第二层已把受限现金、资金转移限制和债务披露单独拆开。"
        )
    return (
        "当前缺少受限现金、流动资产/负债或债务到期等细项，"
        "所以“现金缓冲”不能直接等同于可自由分配现金；第二层应继续核对资金可用性和债务期限。"
    )


def _core_revenue_source_lines(
    pack: dict[str, Any],
    latest: dict[str, Any],
    prior: dict[str, Any],
    fallback_top_component: Any,
) -> list[str]:
    source_metric = _metric_by_id(pack.get("financial_metrics") or [], "source_of_growth_attribution_v1")
    result = _latest_component_result(source_metric)
    if not result:
        return [
            (
                "- 收入来源：没有可结构化抽取的收入组件；当前只能用总收入同比 "
                f"{_pct(_growth(latest, prior, 'revenue'))} 判断增长方向，不能证明增长来自哪类业务。"
            )
        ]

    period = result.get("year") or result.get("period_end") or "最新期间"
    components = result.get("component_details") or []
    ranked = sorted(components, key=lambda item: item.get("share_of_revenue") or 0, reverse=True)
    top = ranked[0] if ranked else {}
    top_label = _metric_label_zh(str(top.get("metric") or fallback_top_component or "未识别"))
    top_value = _money(top.get("value"))
    top_share = _pct(top.get("share_of_revenue"))
    comparison = ""
    if len(ranked) > 1:
        second = ranked[1]
        comparison = (
            f"，高于{_metric_label_zh(str(second.get('metric')))}"
            f"（{_money(second.get('value'))}，占 {_pct(second.get('share_of_revenue'))}）"
        )
    return [
        (
            f"- 收入来源：{period} 口径下，已抽取收入组件覆盖总收入 {_pct(result.get('value'))}；"
            f"{top_label}为 {_money(top.get('value'))}，占收入 {top_share}{comparison}；"
            f"同一口径收入同比 {_pct(result.get('revenue_growth_yoy'))}。"
        ),
        (
            f"- 解释边界：这组数字证明的是“最新可用口径的收入结构”，不是增长质量本身；"
            f"因为最新年度收入同比 {_pct(_growth(latest, prior, 'revenue'))}，但经营利润同比 "
            f"{_pct(_growth(latest, prior, 'operating_income'))}、净利润同比 {_pct(_growth(latest, prior, 'net_income'))}，"
            "所以还必须用利润率和现金流继续验证。"
        ),
    ]


def _evidence_coverage_table(pack: dict[str, Any]) -> str:
    latest_annual = (pack.get("annual_report_baseline") or {}).get("latest_annual_report") or {}
    quarterly_rows = _quarterly_rows(pack)
    material_scan = pack.get("material_event_scan") or {}
    working_capital = _metric_by_id(pack.get("financial_metrics") or [], "working_capital_quality_v1")
    balance_sheet = _metric_by_id(pack.get("financial_metrics") or [], "balance_sheet_risk_v1")
    tax_metric = _metric_by_id(pack.get("financial_metrics") or [], "tax_non_gaap_accounting_quality_v1")
    has_non_gaap = ((tax_metric or {}).get("latest_interim_non_gaap") or {}).get("status") == "calculated"
    footnote_status = "部分覆盖" if working_capital or balance_sheet or tax_metric else "未稳定覆盖"
    material_status = _material_coverage_status_zh(material_scan)
    material_impact = _material_coverage_impact_zh(material_scan)
    lines = [
        "| 证据层 | 当前状态 | 对结论的影响 |",
        "| --- | --- | --- |",
        (
            f"| 年报 / 20-F / 10-K | {'已覆盖' if latest_annual else '缺失'} | "
            "作为主线锚点；年度结论优先级最高。 |"
        ),
        (
            f"| 季度 6-K / 10-Q | {'已覆盖' if quarterly_rows else '缺失'} | "
            "只用于验证主线是否改变，不直接重写长期投资主线。 |"
        ),
        (
            f"| 附注与结构化拆分 | {footnote_status} | "
            "已覆盖部分营运资本、资金可用性、税项和非 GAAP 证据；债务到期、现金纳税、维护/增长资本开支等细拆仍影响置信度。 |"
        ),
        (
            f"| 重大事项扫描 | {material_status} | "
            f"{material_impact} |"
        ),
        (
            f"| 非 GAAP | {'已作为辅助抽取' if has_non_gaap else '未稳定抽取'} | "
            "只用于解释管理层口径，不进入主结论。 |"
        ),
    ]
    return "\n".join(lines)


def _material_scope_text_zh(scan: dict[str, Any]) -> str:
    if not scan:
        return "重大事项扫描尚未运行；不能据此断言不存在事件风险。"
    note = scan.get("scan_scope_note")
    scanned = int(scan.get("scanned_document_count") or 0)
    events = int(scan.get("material_event_count") or 0)
    high_priority = int(scan.get("high_priority_event_count") or 0)
    if scanned > 0:
        return f"已扫描 {scanned} 份事件披露，发现 {events} 个重大事项，其中高优先级 {high_priority} 个。{note or ''}".strip()
    if scan.get("coverage_status") == "routine_financial_documents_only":
        routine = int(scan.get("routine_financial_document_count") or 0)
        return (
            f"年报当日及之后有 {routine} 份常规官方财务披露进入财务更新，但没有治理、审计/会计、融资、资本配置或管理层变动类文件被晋级为重大事项扫描对象。"
        )
    if note:
        return f"{note} 不能据此断言不存在事件风险。"
    return "本次没有完整事件披露索引；不能据此断言不存在 6-K / 8-K / proxy 风险。"


def _material_coverage_status_zh(scan: dict[str, Any]) -> str:
    status = (scan or {}).get("coverage_status")
    if status == "event_documents_scanned":
        return "已扫描事件文件"
    if status == "routine_financial_documents_only":
        return "仅有常规财务披露"
    if status == "no_post_annual_trusted_documents":
        return "缺少年报后可信文件"
    if status == "post_annual_documents_not_scannable":
        return "有年报后文件但未匹配事件类别"
    return "本次未完整覆盖"


def _material_coverage_impact_zh(scan: dict[str, Any]) -> str:
    if not scan:
        return "重大事项扫描尚未运行，不能用于排除事件风险。"
    events = int(scan.get("material_event_count") or 0)
    if events:
        return "发现的事件应进入人工复核，并优先影响财务可靠性、治理和资本配置判断。"
    status = scan.get("coverage_status")
    if status == "routine_financial_documents_only":
        return "说明常规季度财务更新已纳入，但没有发现需要单独晋级的事件披露；仍不能证明未来没有事件风险。"
    if status == "event_documents_scanned":
        return "已按事件类别扫描但未发现命中项；结论仍受规则词表和文件覆盖范围限制。"
    return "覆盖不足，不能声称不存在事件风险。"


def _thesis_summary(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return "- 年度数据不足，暂时不能形成跨年主线。"
    latest = rows[-1]
    prior = rows[-2]
    revenue_growth = _growth(latest, prior, "revenue")
    net_income_growth = _growth(latest, prior, "net_income")
    operating_income_growth = _growth(latest, prior, "operating_income")
    operating_margin = _margin(latest, "operating_income")
    prior_operating_margin = _margin(prior, "operating_income")
    broad_liquidity = _broad_liquidity(latest)
    current_ratio = _safe_divide(latest.get("current_assets"), latest.get("current_liabilities"))
    liabilities_to_assets = _safe_divide(latest.get("total_liabilities"), latest.get("total_assets"))

    if revenue_growth is not None and revenue_growth > 0 and net_income_growth is not None and net_income_growth < 0:
        headline = (
            "公司仍在增长，但 2025 年已经从“高增长、高利润释放”切到“增速放缓、利润再投入”。"
        )
        implication = "不能简单外推上一轮高增长高利润，核心要验证投入是否能重新带来利润率和现金流修复。"
    elif revenue_growth is not None and revenue_growth > 0 and operating_margin is not None and operating_margin > 0:
        headline = "公司仍在增长，且经营利润率仍为正，主线仍有盈利支撑。"
        implication = "下一步重点不是确认公司是否赚钱，而是确认增长来源和利润率是否可持续。"
    elif revenue_growth is not None and revenue_growth < 0:
        headline = "最新年度收入下滑，主线应先从需求、价格、客户流失或业务收缩开始验证。"
        implication = "在收入端重新稳定前，不应只用利润率改善外推价值。"
    else:
        headline = "最新年度主线信号不完整，需要先补齐收入、利润和现金流的跨年事实。"
        implication = "当前报告只能作为初步阅读框架，不能形成完整投资判断。"

    return "\n".join(
        [
            f"- 核心判断：{headline}",
            (
                f"- 为什么：最新年度收入同比 {_pct(revenue_growth)}，但经营利润同比 {_pct(operating_income_growth)}、"
                f"净利润同比 {_pct(net_income_growth)}；经营利润率从 {_pct(prior_operating_margin)} 降到 {_pct(operating_margin)}。"
            ),
            (
                f"- 安全垫：广义现金与短投 {_money(broad_liquidity)}，流动比率 {_ratio(current_ratio)}，"
                f"总负债 / 总资产 {_pct(liabilities_to_assets)}，说明公司有能力承受一段投入期。"
            ),
            f"- 财报读法：{implication}",
        ]
    )


def _decision_snapshot_table(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return "- 数据不足，暂时不能生成关键证据快照。"
    latest = rows[-1]
    prior = rows[-2]
    latest_quarter = _quarterly_rows(pack)[-1] if _quarterly_rows(pack) else None
    prior_year_quarter = _prior_year_quarter(_quarterly_rows(pack), latest_quarter) if latest_quarter else None
    lines = [
        "| 判断 | 证据 | 读法 |",
        "| --- | --- | --- |",
        "| 年度主线 | 收入同比 {revenue_growth}；经营利润同比 {operating_growth}；净利润同比 {net_growth} | 增长仍在，但利润回吐 |".format(
            revenue_growth=_pct(_growth(latest, prior, "revenue")),
            operating_growth=_pct(_growth(latest, prior, "operating_income")),
            net_growth=_pct(_growth(latest, prior, "net_income")),
        ),
        "| 利润率 | 经营利润率 {prior_op_margin} -> {latest_op_margin}；净利率 {prior_net_margin} -> {latest_net_margin} | {margin_read} |".format(
            prior_op_margin=_pct(_margin(prior, "operating_income")),
            latest_op_margin=_pct(_margin(latest, "operating_income")),
            prior_net_margin=_pct(_margin(prior, "net_income")),
            latest_net_margin=_pct(_margin(latest, "net_income")),
            margin_read=_margin_readout(latest, prior),
        ),
        "| 现金 | 经营现金流 / 净利润 {cash_conversion}；自由现金流率 {fcf_margin} | {cash_read} |".format(
            cash_conversion=_ratio(_safe_divide(latest.get("operating_cash_flow"), latest.get("net_income"))),
            fcf_margin=_pct(_margin(latest, "free_cash_flow")),
            cash_read=_cash_readout(latest),
        ),
        "| 抗压能力 | 广义现金与短投 {liquidity}；流动比率 {current_ratio}；总负债 / 总资产 {liabilities_to_assets} | {balance_read} |".format(
            liquidity=_money(_broad_liquidity(latest)),
            current_ratio=_ratio(_safe_divide(latest.get("current_assets"), latest.get("current_liabilities"))),
            liabilities_to_assets=_pct(_safe_divide(latest.get("total_liabilities"), latest.get("total_assets"))),
            balance_read=_balance_readout(latest),
        ),
        "| 最新季度 | 收入同比 {quarter_growth}；经营利润同比 {quarter_op_growth}；净利润同比 {quarter_net_growth} | {quarter_read} |".format(
            quarter_growth=_pct(_growth(latest_quarter, prior_year_quarter, "revenue")),
            quarter_op_growth=_pct(_growth(latest_quarter, prior_year_quarter, "operating_income")),
            quarter_net_growth=_pct(_growth(latest_quarter, prior_year_quarter, "net_income")),
            quarter_read=_quarter_readout(latest_quarter, prior_year_quarter),
        ),
    ]
    return "\n".join(lines)


def _top_open_items(pack: dict[str, Any]) -> str:
    diagnostics = (pack.get("diagnostic_findings") or {}).get("questions") or []
    warnings: list[str] = []
    missing: list[str] = []
    for question in diagnostics:
        for warning in question.get("warning_flags") or []:
            translated = _sentence_fragment(_warning_zh(str(warning)))
            if translated not in warnings:
                warnings.append(translated)
        for item in question.get("missing") or []:
            translated = _missing_zh(str(item))
            if translated not in missing:
                missing.append(translated)
    lines = []
    if warnings:
        primary = warnings[0]
        lines.append(f"- {_open_item_question_zh(primary)}当前触发点：{primary}。")
    if missing:
        lines.append("- 哪些数据还不足以证明投入回报？缺口包括：" + "、".join(missing[:5]) + "。")
    material_scan = pack.get("material_event_scan") or {}
    if material_scan.get("material_event_count", 0):
        lines.append(
            f"- 是否存在会改变主线的重大事项？已发现 {material_scan.get('material_event_count')} 个事项，需要先读事件披露再做结论。"
        )
    return "\n".join(lines) if lines else "- 暂无高优先级待验证事项。"


def _open_item_question_zh(primary_warning: str) -> str:
    if "现金 / 总负债" in primary_warning or "现金覆盖" in primary_warning:
        return "现金缓冲相对负债是否足够？"
    if "受限现金" in primary_warning:
        return "账面现金能否自由使用？"
    if "营运资本" in primary_warning or "现金流" in primary_warning:
        return "经营现金流质量是否依赖营运资本顺风？"
    if "投资收益" in primary_warning:
        return "净利润是否过度依赖经营利润以下项目？"
    return "利润率压力到底是主动投入，还是结构性竞争压力？"


def _fundamental_status(pack: dict[str, Any]) -> str:
    health = pack.get("financial_health") or {}
    if health.get("label"):
        return str(health.get("label"))
    score = _fundamental_score(pack)
    if score is None:
        return "无法判断"
    if _has_major_red_flag(pack):
        return "非高质量资产 / 需回避"
    if score >= 8.0 and not _has_core_warning(pack):
        return "高质量资产"
    if score >= 6.5:
        return "质量较高，但处于验证期"
    if score >= 5.0:
        return "中性观察 / 证据不足"
    if score >= 3.0:
        return "承压资产"
    return "非高质量资产 / 需回避"


def _fundamental_score(pack: dict[str, Any]) -> float | None:
    health = pack.get("financial_health") or {}
    if health.get("score") is not None:
        return _float_value(health.get("score"))
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return None
    latest = rows[-1]
    prior = rows[-2]
    if _has_major_red_flag(pack):
        return 2.0
    revenue_growth = _growth(latest, prior, "revenue")
    operating_margin = _margin(latest, "operating_income")
    cash_conversion = _safe_divide(latest.get("operating_cash_flow"), latest.get("net_income"))
    current_ratio = _safe_divide(latest.get("current_assets"), latest.get("current_liabilities"))
    liabilities_to_assets = _safe_divide(latest.get("total_liabilities"), latest.get("total_assets"))
    score = 0.0
    if revenue_growth is not None:
        if revenue_growth > 0:
            score += 2.0
        elif revenue_growth > -0.05:
            score += 0.8
    if operating_margin is not None:
        if operating_margin > 0.10:
            score += 2.0
        elif operating_margin > 0:
            score += 1.0
    if cash_conversion is not None:
        if cash_conversion >= 1.0:
            score += 2.0
        elif cash_conversion >= 0.8:
            score += 1.0
    if current_ratio is not None:
        if current_ratio >= 1.5:
            score += 1.5
        elif current_ratio >= 1.0:
            score += 0.7
    if liabilities_to_assets is not None:
        if liabilities_to_assets <= 0.55:
            score += 1.0
        elif liabilities_to_assets <= 0.70:
            score += 0.4
    if _has_core_warning(pack):
        score -= 1.5
    if _evidence_strength(pack) == "低":
        score -= 0.5
    return max(0.0, min(10.0, score))


def _research_action(status: str) -> str:
    if status == "高质量资产":
        return "加深研究；下一步进入估值或同行比较。"
    if status.startswith("质量较高"):
        return "继续跟踪；先验证利润率和现金质量是否修复。"
    if status.startswith("中性观察"):
        return "先补齐关键证据；暂不升级为高优先级研究。"
    if status.startswith("承压") or status.startswith("非高质量"):
        return "降低优先级或回避；先解决红旗和资产负债表问题。"
    return "补齐关键证据后再判断。"


def _evidence_strength(pack: dict[str, Any]) -> str:
    health = pack.get("financial_health") or {}
    if health.get("evidence_strength"):
        return {
            "high": "高",
            "medium": "中",
            "low": "低",
        }.get(str(health.get("evidence_strength")), str(health.get("evidence_strength")))
    annual_ok = bool((pack.get("annual_report_baseline") or {}).get("latest_annual_report"))
    quarterly_ok = bool(_quarterly_rows(pack))
    review_flags = [
        flag
        for flag in pack.get("human_review_flags") or []
        if str(flag.get("formula_id") or "") not in {"enterprise_value_v1", "true_yield_v1", "free_cash_flow_yield_v1"}
    ]
    material_scan = pack.get("material_event_scan") or {}
    if annual_ok and quarterly_ok and not review_flags and material_scan.get("scanned_document_count", 0) > 0:
        return "高"
    if annual_ok and quarterly_ok:
        return "中"
    return "低"


def _primary_positive_evidence(pack: dict[str, Any]) -> str:
    health = pack.get("financial_health") or {}
    if health.get("main_positive_evidence"):
        return _clean_missing_metric_sentence_zh(str(health.get("main_positive_evidence")))
    rows = _annual_rows(pack)
    if not rows:
        return "年度事实不足。"
    latest = rows[-1]
    return _join_metric_pieces_zh(
        _metric_piece_zh("经营现金流 / 净利润", _ratio(_safe_divide(latest.get("operating_cash_flow"), latest.get("net_income")))),
        _metric_piece_zh("广义现金与短投", _money(_broad_liquidity(latest))),
        _metric_piece_zh("流动比率", _ratio(_safe_divide(latest.get("current_assets"), latest.get("current_liabilities")))),
    )


def _primary_disconfirming_risk(pack: dict[str, Any]) -> str:
    health = pack.get("financial_health") or {}
    if health.get("main_negative_evidence"):
        return _sentence_fragment(_warning_zh(str(health.get("main_negative_evidence"))))
    warnings = _diagnostic_warnings(pack)
    if warnings:
        return _sentence_fragment(_warning_zh(warnings[0]))
    material_scan = pack.get("material_event_scan") or {}
    if material_scan.get("high_priority_event_count", 0):
        return "存在高优先级重大事项，需要先读事件披露。"
    return "暂未发现结构化重大红旗，但附注和重大事项扫描仍需保持保守。"


def _clean_missing_metric_sentence_zh(text: str) -> str:
    parts = [part.strip(" ，。;；") for part in re.split(r"[，；;]", text) if part.strip(" ，。;；")]
    kept = [part for part in parts if "缺失" not in part]
    return "，".join(kept) if kept else "结构化正面证据不足。"


def _next_validation_point(pack: dict[str, Any]) -> str:
    health = pack.get("financial_health") or {}
    if health.get("next_verification_point"):
        return str(health.get("next_verification_point"))
    growth_question = _diagnostic_question(pack, "growth_quality") or {}
    values = growth_question.get("latest_values") or {}
    if values.get("incremental_operating_margin") is not None:
        return "下个季度先看增量经营利润率是否从负转正，并拆费用率、商家支持和供应链投入。"
    return "下个季度先看收入增速、经营利润率、经营现金流和非 GAAP 调整是否同向改善。"


def _diagnostic_question(pack: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    for question in (pack.get("diagnostic_findings") or {}).get("questions") or []:
        if question.get("question_id") == question_id:
            return question
    return None


def _diagnostic_warnings(pack: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for question in (pack.get("diagnostic_findings") or {}).get("questions") or []:
        for warning in question.get("warning_flags") or []:
            text = str(warning)
            if text not in warnings:
                warnings.append(text)
    return warnings


def _has_major_red_flag(pack: dict[str, Any]) -> bool:
    material_scan = pack.get("material_event_scan") or {}
    return bool(material_scan.get("high_priority_event_count", 0))


def _has_core_warning(pack: dict[str, Any]) -> bool:
    warning_text = " ".join(_diagnostic_warnings(pack)).lower()
    core_terms = ["incremental operating margin", "material weakness", "non-reliance", "restricted cash", "working-capital"]
    return any(term in warning_text for term in core_terms)


def _latest_quarter_growth(pack: dict[str, Any]) -> float | None:
    rows = _quarterly_rows(pack)
    if not rows:
        return None
    latest = rows[-1]
    prior = _prior_year_quarter(rows, latest)
    return _growth(latest, prior, "revenue")


def _growth_readout(latest: dict[str, Any], prior: dict[str, Any]) -> str:
    revenue_growth = _growth(latest, prior, "revenue")
    net_income_growth = _growth(latest, prior, "net_income")
    if revenue_growth is not None and revenue_growth > 0 and net_income_growth is not None and net_income_growth < 0:
        return "收入仍增长，但利润没有同步确认"
    if revenue_growth is not None and revenue_growth > 0:
        return "规模仍在扩张"
    if revenue_growth is not None and revenue_growth < 0:
        return "收入端承压"
    return "增长证据不足"


def _margin_readout(latest: dict[str, Any], prior: dict[str, Any]) -> str:
    latest_margin = _margin(latest, "operating_income")
    prior_margin = _margin(prior, "operating_income")
    if latest_margin is not None and prior_margin is not None and latest_margin < prior_margin:
        return "经营杠杆回吐，需判断是短期投入还是结构性压力"
    if latest_margin is not None and prior_margin is not None and latest_margin >= prior_margin:
        return "利润率稳定或改善"
    return "利润率证据不足"


def _cash_readout(latest: dict[str, Any]) -> str:
    cash_conversion = _safe_divide(latest.get("operating_cash_flow"), latest.get("net_income"))
    if cash_conversion is not None and cash_conversion >= 1:
        return "会计利润有经营现金流支撑"
    if cash_conversion is not None:
        return "现金转化弱于净利润，需要拆营运资本"
    return "现金流证据不足"


def _balance_readout(latest: dict[str, Any]) -> str:
    current_ratio = _safe_divide(latest.get("current_assets"), latest.get("current_liabilities"))
    liabilities_to_assets = _safe_divide(latest.get("total_liabilities"), latest.get("total_assets"))
    if current_ratio is not None and current_ratio >= 2 and liabilities_to_assets is not None and liabilities_to_assets < 0.5:
        return "安全垫强，能承受投入期"
    if liabilities_to_assets is not None and liabilities_to_assets >= 0.6:
        return "杠杆偏高，坏年份抗压性要保守"
    return "资产负债表需要结合现金可用性看"


def _quarter_readout(row: dict[str, Any] | None, prior: dict[str, Any] | None) -> str:
    revenue_growth = _growth(row, prior, "revenue")
    net_income_growth = _growth(row, prior, "net_income")
    if revenue_growth is not None and revenue_growth > 0 and net_income_growth is not None and net_income_growth < 0:
        return "季度仍增长，但盈利兑现偏弱"
    if revenue_growth is not None and revenue_growth > 0:
        return "季度增长仍在延续"
    if revenue_growth is not None and revenue_growth < 0:
        return "季度增长信号转弱"
    return "季度同比证据不足"


def _annual_source_line(document: dict[str, Any]) -> str:
    if not document:
        return "未找到年报基准文件"
    parts = [
        str(document.get("filing_date") or "no filing date"),
        str(document.get("document_type") or "unknown type"),
        str(document.get("document_id") or "unknown document"),
    ]
    if document.get("local_path"):
        parts.append(f"`{document.get('local_path')}`")
    return " | ".join(parts)


def _disclosure_boundary_table(pack: dict[str, Any]) -> str:
    latest = _latest_row(pack.get("annual_facts") or [], "year")
    source_metric = _metric_by_id(pack.get("financial_metrics") or [], "source_of_growth_attribution_v1")
    tax_metric = _metric_by_id(pack.get("financial_metrics") or [], "tax_non_gaap_accounting_quality_v1")
    has_core = bool(latest and latest.get("revenue") is not None and latest.get("net_income") is not None)
    has_fcf = bool(latest and latest.get("free_cash_flow") is not None)
    has_revenue_components = _has_revenue_components(source_metric)
    has_non_gaap = ((tax_metric or {}).get("latest_interim_non_gaap") or {}).get("status") == "calculated"
    rows = [
        ("收入、利润、现金流", "已抽取" if has_core else "缺失", "直接使用官方年报 / 20-F / 10-K 的结构化事实。"),
        ("自由现金流近似值", "已计算" if has_fcf else "缺失", "按经营现金流减资本开支；只作为现金质量线索。"),
        (
            "收入组件 / 业务线",
            "部分已抽取" if has_revenue_components else "未稳定抽取",
            "只使用官方文件中能结构化抽取的组件；缺失时不做估算。",
        ),
        (
            "非 GAAP 经营利润 / 净利润",
            "已抽取最新季度" if has_non_gaap else "未稳定抽取",
            "只作为管理层口径补充，不能替代 GAAP 利润。",
        ),
        ("调整后 EBITDA", "未稳定抽取", "如果公司没有稳定披露，本报告不自行构造替代口径。"),
        ("GMV / ARPU / MAU / 活跃买家", "未稳定抽取", "不把未披露 KPI 反推成事实。"),
        ("地区收入 / 单一品牌收入", "未稳定抽取", "未单独披露时只做定性风险提示，不做数值拆分。"),
    ]
    lines = ["| 项目 | 披露状态 | 本报告处理方式 |", "| --- | --- | --- |"]
    lines.extend(f"| {item} | {status} | {treatment} |" for item, status, treatment in rows)
    return "\n".join(lines)


def _annual_trend_table(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if not rows:
        return "- 没有可用年度事实。"
    rows = rows[-3:]
    by_year = {row.get("year"): row for row in _annual_rows(pack)}
    years = [str(row.get("year")) for row in rows]
    separator = "| --- |" + " ---: |" * len(rows)
    lines = [
        "单位：金额为 RMB bn；比率为 %。",
        "",
        "| 指标 | " + " | ".join(years) + " |",
        separator,
    ]
    metrics = [
        ("收入", lambda row, previous: _money_bn(row.get("revenue"))),
        ("毛利", lambda row, previous: _money_bn(row.get("gross_profit"))),
        ("经营利润", lambda row, previous: _money_bn(row.get("operating_income"))),
        ("净利润", lambda row, previous: _money_bn(row.get("net_income"))),
        ("经营现金流", lambda row, previous: _money_bn(row.get("operating_cash_flow"))),
        ("自由现金流近似值", lambda row, previous: _money_bn(row.get("free_cash_flow"))),
        ("收入同比", lambda row, previous: _pct(_growth(row, previous, "revenue"))),
        ("毛利率", lambda row, previous: _pct(_margin(row, "gross_profit"))),
        ("经营利润率", lambda row, previous: _pct(_margin(row, "operating_income"))),
        ("净利率", lambda row, previous: _pct(_margin(row, "net_income"))),
        ("经营现金流率", lambda row, previous: _pct(_margin(row, "operating_cash_flow"))),
    ]
    for label, formatter in metrics:
        values = []
        for row in rows:
            previous = by_year.get((row.get("year") or 0) - 1)
            values.append(formatter(row, previous))
        lines.append("| {label} | {values} |".format(label=label, values=" | ".join(values)))
    return "\n".join(lines)


def _annual_trend_readout(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return "**怎么读：** 年度趋势数据不足。"
    latest = rows[-1]
    prior = rows[-2]
    revenue_growth = _growth(latest, prior, "revenue")
    operating_income_growth = _growth(latest, prior, "operating_income")
    net_income_growth = _growth(latest, prior, "net_income")
    ocf_growth = _growth(latest, prior, "operating_cash_flow")
    pieces = [
        f"**怎么读：** 最新年度收入同比 {_pct(revenue_growth)}，经营利润同比 {_pct(operating_income_growth)}，净利润同比 {_pct(net_income_growth)}，经营现金流同比 {_pct(ocf_growth)}。"
    ]
    if revenue_growth is not None and revenue_growth > 0 and operating_income_growth is not None and operating_income_growth < 0:
        pieces.append(
            "**核心问题：** 不是“有没有增长”，而是“新增收入为什么没有带来新增经营利润”。"
        )
    if ocf_growth is not None and net_income_growth is not None and ocf_growth < net_income_growth:
        pieces.append("**后续重点：** 经营现金流变化弱于净利润变化，需要拆营运资本和一次性现金项目。")
    return "\n".join(pieces)


def _quarterly_trend_table(pack: dict[str, Any]) -> str:
    rows = _quarterly_rows(pack)
    if not rows:
        return "- 没有可用季度事实。"
    lines = [
        "只展示最近 6 个季度，避免季度表过长；同比仍按去年同期计算。",
        "",
        "| 季度 | 收入 (RMB bn) | 收入同比 | 经营利润 (RMB bn) | 经营利润率 | 净利润 (RMB bn) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows[-6:]:
        prior = _prior_year_quarter(rows, row)
        lines.append(
            "| {quarter} | {revenue} | {revenue_growth} | {operating_income} | {operating_margin} | {net_income} |".format(
                quarter=row.get("quarter") or row.get("period_end"),
                revenue=_money_bn(row.get("revenue")),
                revenue_growth=_pct(_growth(row, prior, "revenue")),
                operating_income=_money_bn(row.get("operating_income")),
                operating_margin=_pct(_margin(row, "operating_income")),
                net_income=_money_bn(row.get("net_income")),
            )
        )
    return "\n".join(lines)


def _quarterly_trend_readout(pack: dict[str, Any]) -> str:
    rows = _quarterly_rows(pack)
    if not rows:
        return "**怎么读：** 季度数据不足。"
    latest = rows[-1]
    prior = _prior_year_quarter(rows, latest)
    if not prior:
        return "**怎么读：** 缺少可比去年同期季度，暂时不能判断同比拐点。"
    revenue_growth = _growth(latest, prior, "revenue")
    operating_income_growth = _growth(latest, prior, "operating_income")
    net_income_growth = _growth(latest, prior, "net_income")
    line = (
        f"**怎么读：** 最新季度收入同比 {_pct(revenue_growth)}，"
        f"经营利润同比 {_pct(operating_income_growth)}，净利润同比 {_pct(net_income_growth)}。"
    )
    if revenue_growth is not None and revenue_growth > 0 and net_income_growth is not None and net_income_growth < 0:
        return line + "规模仍在扩张，但净利润没有同步兑现。**后续重点：** 看投入、补贴、费用率和非 GAAP 调整。"
    if revenue_growth is not None and revenue_growth > 0:
        return line + "收入仍在增长。**后续重点：** 看利润率和现金流是否同步确认。"
    return line + "收入端尚未确认改善，先不要用单季利润改善外推主线。"


def _revenue_structure_summary(pack: dict[str, Any]) -> str:
    source_metric = _metric_by_id(pack.get("financial_metrics") or [], "source_of_growth_attribution_v1")
    if not source_metric:
        return "- 没有收入组件指标，无法形成收入结构判断。"
    result = _latest_component_result(source_metric)
    if not result:
        return (
            "- 年报或季度口径中没有可结构化抽取的收入组件。报告只能判断总收入增长，"
            "不能判断增长来自业务线、产品、地区、客户/用户指标或变现率变化。"
        )
    period = result.get("year") or result.get("period_end") or "latest period"
    components = result.get("component_details") or []
    top = max(components, key=lambda item: item.get("share_of_revenue") or 0) if components else {}
    if top:
        other_components = [component for component in components if component is not top]
        other_text = "；".join(
            "{metric}为 {value}，占收入 {share}".format(
                metric=_metric_label_zh(str(component.get("metric"))),
                value=_money(component.get("value")),
                share=_pct(component.get("share_of_revenue")),
            )
            for component in other_components
        )
        other_clause = f"；其他已抽取组件中，{other_text}" if other_text else ""
        facts = (
            f"收入结构只回答“收入来自哪类业务”，不单独证明增长质量。以 {period} 为口径，"
            f"官方收入组件覆盖总收入 {_pct(result.get('value'))}，同一口径收入同比 {_pct(result.get('revenue_growth_yoy'))}。"
            f"其中，{_metric_label_zh(str(top.get('metric')))}为 {_money(top.get('value'))}，"
            f"占收入 {_pct(top.get('share_of_revenue'))}，是当前可抽取组件中占比最高的一项{other_clause}。"
        )
        if _company_id(pack) == "pdd":
            readout = (
                "这说明读增长时不能只看总收入，还要区分交易服务与广告/流量变现的贡献；"
                "但季度结构不能直接外推全年，也不能单独证明增长质量。"
            )
        else:
            readout = (
                "这说明读增长时不能只看总收入，还要继续区分业务线、产品、地区和客户/用户指标；"
                "但单期结构不能直接外推全年，也不能单独证明增长质量。"
            )
        return f"{facts}\n\n**怎么读：** {readout}"
    return (
        f"收入结构只回答“收入来自哪类业务”，不单独证明增长质量。以 {period} 为口径，"
        f"官方收入组件覆盖总收入 {_pct(result.get('value'))}，同一口径收入同比 {_pct(result.get('revenue_growth_yoy'))}。"
        "当前没有足够组件细节判断哪一类业务贡献最大。"
    )


def _working_capital_bridge_summary(pack: dict[str, Any]) -> str:
    metric = _metric_by_id(pack.get("financial_metrics") or [], "working_capital_quality_v1")
    result = _latest_calculated_result(metric or {})
    if not result:
        return "- 营运资本桥没有可用结构化输出；现金质量只能先看经营现金流 / 净利润。"
    components = result.get("component_details") or []
    if not components:
        return "- 营运资本组件不足，暂时不能拆出现金流来源。"
    sorted_components = sorted(components, key=lambda item: abs(_float_value(item.get("delta")) or 0), reverse=True)
    top_two = sorted_components[:2]
    top_two_text = "、".join(
        f"{_metric_label_zh(str(component.get('metric')))}增加 {_money(_float_value(component.get('delta')))}"
        for component in top_two
        if _float_value(component.get("delta")) is not None
    )
    smaller_total = sum(
        _float_value(component.get("delta")) or 0.0
        for component in sorted_components[2:4]
    )
    smaller_clause = f"，其他经营性小项合计增加约 {_money(smaller_total)}" if smaller_total else ""
    source_clause = f"主要来自{top_two_text}{smaller_clause}" if top_two_text else "来源需要回到营运资本明细继续拆分"
    facts = (
        f"最新年度营运资本对现金流有明显顺风：营运资本现金顺风相当于收入的 "
        f"{_pct(result.get('working_capital_cash_tailwind_to_revenue'))}，经营负债净增加 "
        f"{_money(result.get('cash_source_liability_delta'))}。{source_clause}。"
    )
    readout = (
        "这不是坏事，但说明经营现金流有平台浮存金 / 经营负债扩张的帮助，"
        "因此不能只用 CFO / 净利润来判断现金质量。"
    )
    return f"{facts}\n\n**怎么读：** {readout}"


def _liquidity_summary(pack: dict[str, Any]) -> str:
    rows = _annual_rows(pack)
    if not rows:
        return "- 没有可用资产负债表事实。"
    lines = [
        "这张表回答公司有没有财务缓冲，但不回答投入回报是否足够好。",
        "",
        "| 年度 | 广义现金与短投 (RMB bn) | 流动比率 | 总负债 / 总资产 | 债务 (RMB bn) | 现金 / 总负债 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows[-3:]:
        lines.append(
            "| {year} | {liquidity} | {current_ratio} | {liabilities_to_assets} | {debt} | {cash_to_liabilities} |".format(
                year=row.get("year"),
                liquidity=_money_bn(_broad_liquidity(row)),
                current_ratio=_ratio(_safe_divide(row.get("current_assets"), row.get("current_liabilities"))),
                liabilities_to_assets=_pct(_safe_divide(row.get("total_liabilities"), row.get("total_assets"))),
                debt=_money_bn(row.get("debt")),
                cash_to_liabilities=_ratio(_safe_divide(row.get("cash"), row.get("total_liabilities"))),
            )
        )
    latest = rows[-1]
    return "\n".join(lines + [
        "",
        (
            f"**怎么读：** 最新年度广义现金与短投为 {_money(_broad_liquidity(latest))}，"
            f"{_liquidity_readout_sentence_zh(latest)}"
        )
    ])


def _liquidity_readout_sentence_zh(latest: dict[str, Any]) -> str:
    current_ratio = _ratio(_safe_divide(latest.get("current_assets"), latest.get("current_liabilities")))
    if current_ratio:
        return (
            f"流动比率为 {current_ratio}。这支持“能扛投入期”的判断；第二层会把受限现金、"
            "资金转移限制和债务披露单独拆开，避免把全部账面资金直接当成自由现金。"
        )
    return (
        "但流动比率、受限现金和债务到期结构仍未稳定抽取。"
        "因此这里只能说明现金和短投规模，不能直接断言全部资金都可自由使用。"
    )


def _diagnostic_questions(questions: list[dict[str, Any]]) -> str:
    return format_financial_diagnostic_questions_zh(questions)


def format_financial_diagnostic_questions_compact_zh(
    questions: list[dict[str, Any]],
    pack: dict[str, Any] | None = None,
    official_evidence_pack: dict[str, Any] | None = None,
) -> str:
    if not questions:
        return "- 诊断规则没有输出问题，通常是因为核心财务事实不足。"
    major_flags = _major_red_flags(pack or {})
    secondary_flags = _secondary_red_flags(pack or {})
    lines = [_diagnostic_section_intro_zh(major_flags, secondary_flags)]
    if official_evidence_pack:
        lines.append(_official_qa_scope_note_zh(official_evidence_pack))
    for question in sorted(questions, key=lambda item: item.get("rank", 999))[:7]:
        question_id = str(question.get("question_id") or "")
        label = _question_short_label_zh(question_id, str(question.get("question") or question_id))
        lines.extend(
            [
                "",
                f"#### {label}",
                "",
                _official_question_adjudication_block(question, official_evidence_pack),
            ]
        )
    supplement = _data_insight_official_review_zh(pack or {}, official_evidence_pack)
    if supplement:
        lines.extend(["", "#### 数据洞察补充复核", "", supplement])
    return "\n".join(lines)


def _official_qa_scope_note_zh(official_evidence_pack: dict[str, Any]) -> str:
    source_catalog = official_evidence_pack.get("source_catalog") or []
    role_counts: dict[str, int] = {}
    for source in source_catalog:
        role = str(source.get("source_role") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
    covered = []
    if role_counts.get("annual_report"):
        covered.append("最新年报 / 20-F")
    if role_counts.get("latest_quarterly_or_6k"):
        covered.append("最新季度 6-K / 业绩稿")
    if role_counts.get("governance_proxy_agm"):
        covered.append("治理、AGM、股权计划相关 6-K / proxy 材料")
    if role_counts.get("material_event"):
        covered.append("已识别重大事项文件")
    covered_text = "、".join(covered) if covered else "当前官方证据包"
    return (
        f"覆盖范围：当前证据包已接入{covered_text}。本节按问题检索官方段落、附注和结构化事实；"
        "它是当前证据包的回答，不等于所有第二层材料已逐页审计；每题的检索路径保留在证据包 JSON，正文只保留判断相关信息。"
    )


def _data_insight_official_review_zh(
    pack: dict[str, Any],
    official_evidence_pack: dict[str, Any] | None,
) -> str:
    if not official_evidence_pack:
        return ""
    rows = _annual_rows(pack)
    if len(rows) < 2:
        return ""
    latest = rows[-1]
    prior = rows[-2]
    quarterly = _quarterly_rows(pack)
    latest_q = quarterly[-1] if quarterly else None
    prior_q = _prior_year_quarter(quarterly, latest_q) if latest_q else None
    tax_metric = _metric_by_id(pack.get("financial_metrics") or [], "tax_non_gaap_accounting_quality_v1")
    tax_result = _latest_calculated_result(tax_metric or {})
    lines = [
        "这一段只保留第 4 节里能被官方文件进一步解释的硬数据信号；如果只是重复第一层或上一小节已经回答的内容，就不再单独列出。",
    ]

    q_operating_growth = _growth(latest_q, prior_q, "operating_income")
    q_net_growth = _growth(latest_q, prior_q, "net_income")
    if q_operating_growth is not None and q_net_growth is not None:
        below_op = _latest_quarter_below_operating_items_from_official_pack(official_evidence_pack)
        if below_op:
            below_op_swing = _delta(below_op.get("net_below_operating_latest"), below_op.get("net_below_operating_prior"))
            other_swing = _delta(below_op.get("other_income_latest"), below_op.get("other_income_prior"))
            interest_swing = _delta(below_op.get("interest_investment_latest"), below_op.get("interest_investment_prior"))
            lines.append(
                "- **季度利润分叉：** 2026Q1 6-K 已经把经营利润以下项目列出来。经营利润同比 "
                f"{_pct(q_operating_growth)}，但净利润同比 {_pct(q_net_growth)}，核心原因不是经营利润表上方继续恶化，"
                f"而是经营利润以下项目合计从 {_money(below_op.get('net_below_operating_prior'))} 变成 "
                f"{_money(below_op.get('net_below_operating_latest'))}，净拖累扩大约 {_money(abs(below_op_swing or 0))}。"
                f"其中其他收益/损失从 {_money(below_op.get('other_income_prior'))} 变成 {_money(below_op.get('other_income_latest'))}"
                f"（恶化约 {_money(abs(other_swing or 0))}），利息和投资收益/损失从 "
                f"{_money(below_op.get('interest_investment_prior'))} 变成 {_money(below_op.get('interest_investment_latest'))}"
                f"（恶化约 {_money(abs(interest_swing or 0))}）。"
                "所以这一条已经可以由季度 6-K 解释到方向和主要科目；剩下的问题是这些项目是否会反复发生。"
            )
        else:
            lines.append(
                "- **季度利润分叉：** 最新 6-K / 季度财务表确认经营利润同比 "
                f"{_pct(q_operating_growth)}、净利润同比 {_pct(q_net_growth)}。"
                "这说明分叉发生在经营利润以下；当前证据包尚未成功抽出全部经营利润以下细项，所以这里不做更细归因。"
            )

    investment_income_to_pretax = (tax_result or {}).get("investment_income_to_pretax")
    effective_tax_rate = (tax_result or {}).get("effective_tax_rate")
    if investment_income_to_pretax is not None and not any("季度利润分叉" in line for line in lines):
        lines.append(
            "- **净利润受非经营收益影响：** 20-F 已经能回答一部分：最新年度投资收益 / 税前利润为 "
            f"{_pct(investment_income_to_pretax)}，有效税率为 {_pct(effective_tax_rate)}。"
            "这支持第二层的裁判：读盈利质量时应优先看经营利润和经营现金流，净利润要拆开看。"
        )

    asset_growth = _growth(latest, prior, "total_assets")
    revenue_growth = _growth(latest, prior, "revenue")
    broad_delta = _broad_liquidity(latest) - _broad_liquidity(prior)
    asset_delta = _delta(latest.get("total_assets"), prior.get("total_assets"))
    broad_delta_share = _safe_divide(broad_delta, asset_delta)
    if asset_growth is not None and revenue_growth is not None and asset_growth > revenue_growth:
        cash_parts = _cash_investment_breakdown_zh(latest)
        if broad_delta_share is not None and broad_delta_share >= 0.50:
            source_read = "广义现金与短投是资产扩张的重要来源；需要保守处理的是这些资金的可动用性和收益波动。"
        elif broad_delta_share is not None:
            source_read = "广义现金与短投不是资产扩张的主要解释；还需要继续拆投资资产、权益法投资、固定资产和其他资产。"
        else:
            source_read = "当前无法把资产增量完整归因到现金、投资资产或其他资产科目。"
        lines.append(
            "- **资产规模扩张快于收入：** 年报资产负债表确认最新年度总资产同比 "
            f"{_pct(asset_growth)}，高于收入同比 {_pct(revenue_growth)}；广义现金与短投增加 {_money(broad_delta)}"
            f"（约占总资产增量的 {_pct(broad_delta_share)}）。"
            f"{cash_parts}{source_read}"
        )

    return "\n".join(lines) if len(lines) > 1 else ""


def _latest_quarter_below_operating_items_from_official_pack(
    official_evidence_pack: dict[str, Any] | None,
) -> dict[str, float] | None:
    if not official_evidence_pack:
        return None
    for answer in official_evidence_pack.get("question_answers") or []:
        if str(answer.get("question_id") or "") != "tax_non_gaap_accounting_quality":
            continue
        for evidence in answer.get("evidence_bundle") or []:
            text = str(evidence.get("quote_or_summary") or "")
            if "Operating profit" not in text or "Net income" not in text:
                continue
            operating = _extract_rmb_millions_row_values(text, "Operating profit")
            net_income = _extract_rmb_millions_row_values(text, "Net income")
            interest = _extract_rmb_millions_row_values(text, "Interest and investment income/(loss), net")
            foreign_exchange = _extract_rmb_millions_row_values(text, "Foreign exchange loss")
            other = _extract_rmb_millions_row_values(text, "Other income/(loss), net")
            equity = _extract_rmb_millions_row_values(text, "Share of results of equity investees")
            tax = _extract_rmb_millions_row_values(text, "Income tax expenses")
            if not operating or not net_income:
                continue
            prior_operating, latest_operating = operating[0], operating[1]
            prior_net, latest_net = net_income[0], net_income[1]
            return {
                "operating_profit_prior": prior_operating,
                "operating_profit_latest": latest_operating,
                "net_income_prior": prior_net,
                "net_income_latest": latest_net,
                "net_below_operating_prior": prior_net - prior_operating,
                "net_below_operating_latest": latest_net - latest_operating,
                "interest_investment_prior": interest[0] if interest else None,
                "interest_investment_latest": interest[1] if interest else None,
                "foreign_exchange_prior": foreign_exchange[0] if foreign_exchange else None,
                "foreign_exchange_latest": foreign_exchange[1] if foreign_exchange else None,
                "other_income_prior": other[0] if other else None,
                "other_income_latest": other[1] if other else None,
                "equity_income_prior": equity[0] if equity else None,
                "equity_income_latest": equity[1] if equity else None,
                "tax_prior": tax[0] if tax else None,
                "tax_latest": tax[1] if tax else None,
            }
    return None


def _extract_rmb_millions_row_values(text: str, label: str) -> list[float]:
    index = text.find(label)
    if index < 0:
        return []
    chunk = text[index + len(label): index + len(label) + 140]
    tokens = re.findall(r"\(?\s*-?\d[\d,]*\s*\)?", chunk)
    return [_parse_rmb_millions_token(token) for token in tokens[:3]]


def _cash_investment_breakdown_zh(row: dict[str, Any]) -> str:
    pieces = [
        _metric_piece_zh("期末现金", _money(row.get("cash"))),
        _metric_piece_zh("受限现金", _money(row.get("restricted_cash"))),
        _metric_piece_zh("短期投资", _money(row.get("short_term_investments"))),
    ]
    text = _join_metric_pieces_zh(*pieces)
    return f"已抽取资金科目包括：{text}。" if text else ""


def _parse_rmb_millions_token(token: str) -> float:
    cleaned = token.strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("() ").replace(",", "")
    value = float(cleaned) * 1_000_000
    return -value if negative else value


def _diagnostic_section_intro_zh(major_flags: list[str], secondary_flags: list[str]) -> str:
    if major_flags:
        return (
            "本节把第一层异常逐项回到官方文件核对。当前发现会否决主结论的重大红旗："
            + "；".join(major_flags[:3])
            + "。"
        )
    if secondary_flags:
        highlighted = "；".join(secondary_flags[:3])
        return (
            "本节把第一层异常逐项回到官方文件核对。当前未发现直接否决主结论的结构化重大红旗；"
            f"主要次级红旗是：{highlighted}。"
        )
    return (
        "本节把第一层关键问题逐项回到官方文件核对，重点看官方记录能解释什么、还缺什么。"
    )


def format_financial_diagnostic_questions_zh(questions: list[dict[str, Any]]) -> str:
    if not questions:
        return "- 诊断规则没有输出问题，通常是因为核心财务事实不足。"
    lines = []
    for question in sorted(questions, key=lambda item: item.get("rank", 999))[:7]:
        warnings = question.get("warning_flags") or []
        missing = question.get("missing") or []
        question_id = str(question.get("question_id") or "")
        lines.extend(
            [
                "### {rank}. {question}".format(
                    rank=question.get("rank", ""),
                    question=question.get("question") or question_id,
                ),
                "",
                f"- 判断：{_diagnostic_interpretation_zh(question)}",
                f"- 关键读数：{_diagnostic_answer_zh(question)}",
                f"- 为什么看这些数：{_why_metrics_answer_question_zh(question_id)}",
            ]
        )
        if warnings:
            lines.append(f"- 需要留意：{'；'.join(_sentence_fragment(_warning_zh(str(item))) for item in warnings[:2])}。")
        if missing:
            lines.append(f"- 证据缺口：{'、'.join(_missing_zh(str(item)) for item in missing[:4])}。")
        follow_up = _follow_up_zh(question_id)
        if follow_up:
            lines.append(f"- 回查位置：{follow_up}")
        interpretation_limit = _interpretation_limit_zh(str(question.get("interpretation_limit") or ""))
        if interpretation_limit:
            lines.append(f"- 限制：{interpretation_limit}")
        lines.append("")
    return "\n".join(lines)


def _official_question_adjudication_block(
    question: dict[str, Any],
    official_evidence_pack: dict[str, Any] | None,
) -> str:
    question_id = str(question.get("question_id") or "")
    company_id = str(((official_evidence_pack or {}).get("agent_run") or {}).get("company_id") or "")
    problem = _diagnostic_problem_sentence_zh(question)
    if not official_evidence_pack:
        return "\n".join(
            [
                f"- **问题：** {problem}",
                "- **官方证据：** 暂无。",
                "- **裁判：** 需要先生成官方证据包后再判断。",
            ]
        )
    answer = next(
        (
            item
            for item in official_evidence_pack.get("question_answers") or []
            if str(item.get("question_id") or "") == question_id
        ),
        None,
    )
    if not answer:
        return "\n".join(
            [
                f"- **问题：** {problem}",
                "- **官方证据：** 暂无。",
                "- **裁判：** 官方文件解释缺失，需要回到原始 filing 人工核对。",
            ]
        )
    rendered = answer.get("rendered_answer") or {}
    unknowns = answer.get("still_unknown") or []
    official_explanation = (
        _official_answer_summary_zh(question_id, answer, company_id=company_id)
        or rendered.get("official_explanation")
        or "官方文件未提供足够解释。"
    )
    judgment = (
        _official_judgment_summary_zh(question_id, answer, company_id=company_id)
        or rendered.get("our_judgment")
        or (answer.get("our_inference") or {}).get("text")
        or "暂无判断。"
    )
    explanation, caveat = _split_official_explanation_for_risk_zh(str(official_explanation))
    unresolved_parts = []
    if judgment and judgment != "暂无判断。":
        unresolved_parts.append(str(judgment))
    if caveat:
        unresolved_parts.append(_remove_leading_contrast_zh(caveat))
    if unknowns and not any("仍未解决" in part for part in unresolved_parts):
        unresolved_parts.append("仍未解决：" + "；".join(_missing_zh(str(item)) for item in unknowns if item))
    if not unresolved_parts:
        unresolved_parts.append("官方文件没有标出新的未解决事项，但仍需在后续披露中验证")
    return "\n".join(
        [
            f"- **问题：** {problem}",
            f"- **官方证据：** {_ensure_sentence_zh(explanation)}",
            f"- **裁判：** {_join_sentence_parts_zh(unresolved_parts)}",
        ]
    )


def _diagnostic_problem_sentence_zh(question: dict[str, Any]) -> str:
    judgment = _ensure_sentence_zh(_diagnostic_short_judgment_zh(question))
    evidence = _diagnostic_key_evidence_zh(question)
    if evidence == "关键结构化读数不足":
        return judgment + "关键结构化读数不足。"
    return judgment + f"关键证据：{evidence}。"


def _official_answer_summary_zh(question_id: str, answer: dict[str, Any], *, company_id: str = "") -> str:
    evidence_types = _answer_source_types_zh(answer)
    unknowns = "、".join(_missing_zh(str(item)) for item in answer.get("still_unknown") or [] if item)
    status = _answer_status_label_zh(answer.get("answer_status"))
    latest_values = answer.get("latest_values") or {}
    if company_id != "pdd":
        if question_id == "growth_quality":
            return (
                f"{evidence_types} 支持收入增长和经营利润同向改善：收入同比 "
                f"{_pct(latest_values.get('revenue_growth_yoy'))}，增量经营利润率 "
                f"{_pct(latest_values.get('incremental_operating_margin'))}。"
                f"当前仍缺少 {unknowns or '业务线、地区、产品和客户维度拆分'}，所以只能证明增长方向，不能解释增长来源。"
            )
        if question_id == "profitability_with_scale":
            return (
                f"{evidence_types} 支持利润率稳定或改善：毛利率 "
                f"{_pct(latest_values.get('gross_margin'))}，经营利润率 {_pct(latest_values.get('operating_margin'))}。"
                "当前官方证据包尚未抽出足够的业务线成本/费用解释，所以不能把利润率变化完整归因到具体业务。"
            )
        if question_id == "cash_profit_quality":
            return (
                f"{evidence_types} 提供经营现金流和净利润口径，可验证利润是否转成现金。"
                f"当前仍需补充 {unknowns or '应收、存货、应付、递延收入等营运资本桥'}，才能判断现金流是否依赖临时营运资本顺风。"
            )
        if question_id == "capital_needed_for_growth":
            return (
                f"{evidence_types} 提供资本开支和自由现金流近似口径。"
                f"当前仍需补充 {unknowns or '维护性资本开支、增长性资本开支和资本化投入拆分'}。"
            )
        if question_id == "balance_sheet_resilience":
            return (
                f"{evidence_types} 提供现金、债务、总资产和总负债口径；"
                "但流动资产/负债、受限现金、短长期债务到期结构仍未稳定抽取。"
            )
        if question_id == "sbc_and_per_share_quality":
            return (
                f"{evidence_types} 提供股权激励成本口径；当前仍需补充 "
                f"{unknowns or '完整股数桥、回购抵消和长期稀释趋势'}。"
            )
        if question_id == "tax_non_gaap_accounting_quality":
            return (
                f"{evidence_types} 提供税率和部分经营利润以下项目；当前仍需补充 "
                f"{unknowns or '现金税、投资收益、权益法收益、减值和 non-GAAP 调节'}，才能完整判断净利润质量。"
            )
    if question_id == "growth_quality":
        return (
            f"{evidence_types} 确认收入主要来自交易服务和在线营销服务及其他；最新季度业绩稿说明收入增长主要来自交易服务收入增加。"
            f"当前回答状态为{status}，仍需补充 {unknowns or '商家分群、价格/量、take-rate 和单商家经济性'}。"
        )
    if question_id == "profitability_with_scale":
        return (
            f"{evidence_types} 提供收入成本、履约、支付处理、平台运营、商家支持和运营费用披露，并能对利润率下降给出部分成本/费用背景。"
            "但这些文件尚未把利润率压力完整拆成主动投入、竞争压力和结构变化。"
        )
    if question_id == "cash_profit_quality":
        return (
            f"{evidence_types} 提供年度和季度现金流表，可验证经营现金流与净利润的关系。"
            f"当前仍需补充 {unknowns or '应收、存货、商家相关负债和结算周期'}，才能判断现金流顺风是否可持续。"
        )
    if question_id == "capital_needed_for_growth":
        return (
            f"{evidence_types} 提供资本开支、折旧摊销和部分投入科目；当前可确认传统资本开支占收入很低。"
            f"仍需补充 {unknowns or '维护性资本开支与增长性资本开支拆分，以及被费用化的供应链/商家支持投入'}。"
        )
    if question_id == "balance_sheet_resilience":
        return (
            f"{evidence_types} 提供现金、受限现金、短期投资、流动资产/负债和 VIE / 资金转移限制披露。"
            "这支持“安全垫强但现金可用性要打折”的读法。"
        )
    if question_id == "sbc_and_per_share_quality":
        return (
            f"{evidence_types} 披露股权激励计划、SBC 风险和 ADS / EPS 口径；当前数字显示 SBC 与稀释不构成主线风险。"
            f"仍需补充 {unknowns or '完整 ADS / 普通股稀释桥和回购抵消分析'}。"
        )
    if question_id == "tax_non_gaap_accounting_quality":
        return (
            f"{evidence_types} 提供 non-GAAP 调节、税项和经营利润以下项目。"
            "官方文件支持把经营利润、投资收益/损失、税项和 non-GAAP 调整拆开读，避免只看净利润。"
        )
    return ""


def _official_judgment_summary_zh(question_id: str, answer: dict[str, Any], *, company_id: str = "") -> str:
    if company_id == "pdd":
        return ""
    if question_id == "growth_quality":
        return "官方数字支持增长和利润同向改善，但增长来源仍缺少业务线、地区、产品或客户维度拆分。"
    if question_id == "profitability_with_scale":
        return "当前数字显示利润率没有恶化；第二层还不能解释利润率改善来自产品结构、成本控制、投资收益还是业务组合。"
    if question_id == "cash_profit_quality":
        return "经营现金流覆盖净利润是正面信号，但营运资本桥不足，现金质量仍需拆分。"
    if question_id == "capital_needed_for_growth":
        return "自由现金流仍为正，但资本开支口径需要进一步拆成维护性和增长性。"
    if question_id == "balance_sheet_resilience":
        return "负债率不高，但现金/总负债偏低，且债务期限和资金可用性细节缺失，资产负债表判断需要保守。"
    if question_id == "sbc_and_per_share_quality":
        return "股权激励成本需要跟踪，但当前还不能判断是否侵蚀每股价值。"
    if question_id == "tax_non_gaap_accounting_quality":
        return "净利润质量需要拆经营利润以下项目；当前税率可见，但现金税、投资收益和减值仍缺。"
    return ""


def _official_question_answer_block(question_id: str, official_evidence_pack: dict[str, Any] | None) -> str:
    """Backward-compatible wrapper for older callers."""
    return _official_question_adjudication_block({"question_id": question_id}, official_evidence_pack)


def _coverage_gate_for_answer_zh(answer: dict[str, Any]) -> str:
    docs = _answer_source_types_zh(answer)
    status = _answer_status_label_zh(answer.get("answer_status"))
    target_sections = [str(item) for item in answer.get("target_sections") or [] if item]
    route = "、".join(target_sections[:3])
    if route and len(target_sections) > 3:
        route += "等"
    if route:
        return f"已用 {docs}；检索路径：{route}；状态：{status}。"
    return f"已用 {docs}；状态：{status}。"


def _answer_source_types_zh(answer: dict[str, Any]) -> str:
    labels = []
    for evidence in answer.get("evidence_bundle") or []:
        source_type = str(evidence.get("source_document_type") or "")
        if source_type == "financial_report_pack":
            label = "结构化财务包"
        elif source_type.startswith("20-F"):
            label = "20-F"
        elif source_type.startswith("10-K"):
            label = "10-K"
        elif source_type.startswith("6-K"):
            label = "6-K"
        elif source_type.startswith("10-Q"):
            label = "10-Q"
        elif "DEF 14A" in source_type or "proxy" in source_type.lower():
            label = "proxy / AGM"
        else:
            label = source_type or "官方文件"
        if label and label not in labels:
            labels.append(label)
    return "、".join(labels[:4]) if labels else "当前证据包"


def _answer_status_label_zh(status: Any) -> str:
    mapping = {
        "answered": "已回答",
        "partial": "部分回答",
        "unknown": "未知",
        "contradicted": "存在冲突",
        "conflicted": "存在冲突",
    }
    return mapping.get(str(status or ""), "未知")


def _split_official_explanation_for_risk_zh(text: str) -> tuple[str, str]:
    cleaned = _normalize_sentence_text_zh(text)
    if not cleaned:
        return "官方文件未提供足够解释。", ""
    caveat_markers = [
        "；但",
        "，但",
        "。但",
        "但不能",
        "但官方",
        "但仍",
        "但报告",
        "但缺少",
        "但无法",
        "；因此",
        "，因此",
        "。因此",
        "因此",
        "；这说明",
        "，这说明",
        "。这说明",
        "这说明",
        "；尚未",
        "，尚未",
        "。尚未",
        "尚未",
    ]
    matches = [(cleaned.find(marker), marker) for marker in caveat_markers if cleaned.find(marker) >= 0]
    if matches:
        index, marker = min(matches, key=lambda item: item[0])
        before = cleaned[:index]
        after = cleaned[index + len(marker) :]
        caveat = _caveat_from_marker_zh(marker, after)
        return _normalize_sentence_text_zh(before), _normalize_sentence_text_zh(caveat)
    return cleaned, ""


def _caveat_from_marker_zh(marker: str, after: str) -> str:
    if "但" in marker:
        return "但" + after
    if "因此" in marker:
        return "因此" + after
    if "这说明" in marker:
        return "这说明" + after
    if "尚未" in marker:
        return "尚未" + after
    return after


def _remove_leading_contrast_zh(text: str) -> str:
    cleaned = _normalize_sentence_text_zh(text)
    replacements = [
        ("但不能", "官方文件不能"),
        ("但官方", "官方"),
        ("但仍", "仍"),
        ("但报告", "报告"),
        ("但缺少", "缺少"),
        ("但无法", "无法"),
        ("但也要求", "需要"),
        ("但", ""),
        ("因此，", ""),
        ("因此", ""),
        ("这说明", ""),
        ("也要求", "需要"),
    ]
    for prefix, replacement in replacements:
        if cleaned.startswith(prefix):
            return replacement + cleaned[len(prefix) :]
    return cleaned


def _join_sentence_parts_zh(parts: list[str]) -> str:
    sentences = []
    for part in parts:
        cleaned = _normalize_sentence_text_zh(part)
        if cleaned and cleaned not in sentences:
            sentences.append(_ensure_sentence_zh(cleaned))
    return "".join(sentences) if sentences else "暂无。"


def _ensure_sentence_zh(text: str) -> str:
    cleaned = _normalize_sentence_text_zh(text)
    if not cleaned:
        return ""
    return cleaned if cleaned[-1] in "。！？.!?" else cleaned + "。"


def _normalize_sentence_text_zh(text: str) -> str:
    return str(text or "").strip().strip("；;，,。 ")


def _fallback_source_trace(answer: dict[str, Any]) -> str:
    sources = []
    for item in answer.get("evidence_bundle") or []:
        source_type = item.get("source_document_type")
        if source_type == "financial_report_pack":
            label = f"第一层财务数据包，{item.get('period') or '当前期间'}"
        else:
            label = "，".join(
                part
                for part in [
                    str(item.get("filing_date") or ""),
                    str(source_type or item.get("source_document") or ""),
                    str(item.get("source_section") or ""),
                ]
                if part
            )
        if label and label not in sources:
            sources.append(label)
    return "；".join(sources[:3]) if sources else "来源未标注"


def _watchlist_summary(pack: dict[str, Any]) -> str:
    diagnostics = (pack.get("diagnostic_findings") or {}).get("questions") or []
    warnings = []
    missing = []
    for question in diagnostics:
        warnings.extend(question.get("warning_flags") or [])
        missing.extend(question.get("missing") or [])
    annual_only = [
        "业务线 / 产品 / 地区收入拆分",
        "客户、用户或商户经济性",
        "应收账款、存货、递延收入和应付账款营运资本桥",
        "维护性资本开支与增长性资本开支拆分",
        "资金可用性、债务到期和其他长期承诺",
    ]
    if missing:
        annual_only = []
        for item in missing:
            translated = _missing_zh(str(item))
            if translated not in annual_only:
                annual_only.append(translated)
    lines = [
        "### 下个季度 / 6-K 可直接验证",
        "",
        _revenue_watch_item_zh(pack),
        "- 经营利润率、销售与营销费用率、研发 / 管理费用率是否企稳。",
        "- 经营现金流、自由现金流近似值和非 GAAP 调整是否支持利润质量。",
        "- 如果只选一个核心信号：看增量经营利润率能否从负转正，或至少明显接近存量经营利润率。",
        "",
        "### 需要后续官方披露或更细结构化抽取",
        "",
        "- " + "、".join(annual_only[:6]) + "。",
        "- 季度业绩稿适合验证趋势有没有变；年报 / 20-F 更适合验证结构性解释是否站得住。",
    ]
    return "\n".join(lines)


def _revenue_watch_item_zh(pack: dict[str, Any]) -> str:
    if _company_id(pack) == "pdd":
        return "- 收入增速是否稳定，交易服务收入和在线营销收入是否延续当前结构。"
    return "- 收入增速是否稳定；如果公司披露业务线、分部、产品或地区收入，优先验证增长到底来自哪里。"


def _investigation_notes_section(pack: dict[str, Any]) -> str:
    investigation = pack.get("financial_investigation_notes") or {}
    notes = investigation.get("notes") or []
    if not notes:
        return ""
    lines = ["## 异常解释追踪", ""]
    for note in notes[:5]:
        title = note.get("question_id") or note.get("trigger") or "未命名问题"
        lines.extend(
            [
                f"### {title}",
                "",
                f"- 回答状态：{_status_zh(note.get('answer_status') or investigation.get('status'))}。",
            ]
        )
        report_sentence = note.get("report_sentence")
        if report_sentence:
            lines.append(f"- 报告读法：{report_sentence}")
        evidence = note.get("evidence") or []
        for label in ["文件事实", "管理层解释", "基于现有数据的推测", "仍未知"]:
            items = [item for item in evidence if item.get("label") == label]
            if items:
                joined = "；".join(_cell(item.get("text")) for item in items[:3] if item.get("text"))
                if joined:
                    lines.append(f"- {label}：{joined}。")
        lines.append("")
    return "\n".join(lines).rstrip()


def _major_red_flags(pack: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    material_scan = pack.get("material_event_scan") or {}
    if material_scan.get("high_priority_event_count", 0):
        flags.append(f"发现 {material_scan.get('high_priority_event_count')} 个高优先级重大事项")
    for flag in pack.get("human_review_flags") or []:
        detail = str(flag.get("formula_id") or flag.get("event_type") or flag.get("metric") or flag.get("flag_id"))
        if str(flag.get("severity")) == "critical":
            flags.append(detail)
    return _unique_text(flags)


def _secondary_red_flags(pack: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    for warning in _diagnostic_warnings(pack):
        flags.append(_sentence_fragment(_warning_zh(warning)))
    for flag in pack.get("human_review_flags") or []:
        detail = str(flag.get("formula_id") or flag.get("event_type") or flag.get("metric") or flag.get("flag_id"))
        if detail in {"enterprise_value_v1", "true_yield_v1", "free_cash_flow_yield_v1", "owner_earnings_v1"}:
            continue
        if str(flag.get("severity")) == "high":
            flags.append(f"需要人工确认：{detail}")
    return _unique_text(flags)


def _working_capital_role_zh(role: str) -> str:
    translations = {
        "cash_source_liability": "现金来源型经营负债",
        "cash_use_asset": "现金占用型经营资产",
    }
    return translations.get(role, role or "未知")


def _working_capital_component_readout(role: str, delta: float | None) -> str:
    if delta is None:
        return "只有余额，缺少同比变化。"
    if role == "cash_source_liability":
        if delta > 0:
            return "余额增加，对经营现金流形成顺风。"
        if delta < 0:
            return "余额下降，对经营现金流形成逆风。"
    if role == "cash_use_asset":
        if delta > 0:
            return "资产增加，占用经营现金。"
        if delta < 0:
            return "资产下降，释放经营现金。"
    return "用于解释营运资本对现金流的影响。"


def _unique_text(items: list[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in unique:
            unique.append(text)
    return unique


def _latest_trend_summary(trend: dict[str, Any]) -> str:
    if not trend:
        return "- 没有最新季度趋势判断。"
    lines = [
        f"- 总体判断：{_trend_status_zh(trend.get('overall_status'))}；方向：{_trend_direction_zh(trend.get('direction'))}。",
        f"- 年度基准：{trend.get('annual_anchor_year')}；最新季度：{trend.get('latest_period_end')}。",
    ]
    topics = trend.get("topic_results") or []
    if topics:
        lines.extend(["", "| 主题 | 判断 | 方向 | 原因 |", "| --- | --- | --- | --- |"])
        for topic in topics:
            lines.append(
                "| {topic} | {status} | {direction} | {reason} |".format(
                    topic=_cell(_trend_topic_zh(topic.get("topic"))),
                    status=_cell(_trend_status_zh(topic.get("status"))),
                    direction=_cell(_trend_direction_zh(topic.get("direction"))),
                    reason=_cell(_trend_reason_zh(topic.get("reason"))),
                )
            )
    return "\n".join(lines)


def _material_event_summary(scan: dict[str, Any]) -> str:
    if not scan:
        return "- 重大事项扫描没有运行。"
    events = scan.get("events") or []
    if not events:
        if scan.get("scanned_document_count", 0) == 0:
            return "- 本次没有可扫描的事件披露文件；这里不能替代完整的 6-K / 8-K / proxy 索引检查。"
        return (
            f"- 扫描 {scan.get('scanned_document_count', 0)} 份事件披露文件，"
            "没有发现需要提升到正文的重大事项。"
        )
    lines = [
        f"- 发现 {scan.get('material_event_count', 0)} 个重大事项，其中高优先级 {scan.get('high_priority_event_count', 0)} 个。",
        "",
        "| 披露日期 | 事项 | 严重程度 | 文件 |",
        "| --- | --- | --- | --- |",
    ]
    for event in events[:8]:
        lines.append(
            "| {date} | {event_type} | {severity} | `{document}` |".format(
                date=_cell(event.get("filing_date")),
                event_type=_cell(event.get("event_type")),
                severity=_cell(event.get("severity")),
                document=_cell(event.get("document_id")),
            )
        )
    return "\n".join(lines)


def _valuation_summary(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return "- Valuation Agent 没有可用输出。"
    lines = []
    for formula_id in [
        "enterprise_value_v1",
        "true_yield_v1",
        "free_cash_flow_yield_v1",
        "investment_adjusted_operating_yield_v1",
    ]:
        metric = _metric_by_id(metrics, formula_id)
        if not metric:
            continue
        latest = _latest_calculated_result(metric)
        if latest:
            value = latest.get("value")
            text = _money(value) if latest.get("unit") == "CNY" else _pct(value)
            suffix = "；需要人工复核" if latest.get("review_required") else ""
            lines.append(f"- {_valuation_label_zh(formula_id)}：{text}{suffix}")
        else:
            lines.append(f"- {_valuation_label_zh(formula_id)}：{_metric_status_zh(metric.get('status'))}")
    return "\n".join(lines) if lines else "- Valuation Agent 没有可用输出。"


def _review_flags_summary(flags: list[dict[str, Any]]) -> str:
    if not flags:
        return "- 没有需要放入本财报阅读报告的人工复核点。"
    excluded_details = {
        "enterprise_value_v1",
        "true_yield_v1",
        "free_cash_flow_yield_v1",
        "investment_adjusted_operating_yield_v1",
        "owner_earnings_v1",
        "incremental_roic_proxy_v1",
        "unlevered_roic_v1",
        "advertising_expense",
    }
    grouped: dict[str, int] = {}
    for flag in flags:
        detail = flag.get("formula_id") or flag.get("event_type") or flag.get("metric") or flag.get("flag_id")
        if str(detail) in excluded_details:
            continue
        item = _review_flag_readout_zh(flag)
        if not item:
            continue
        grouped[item] = grouped.get(item, 0) + 1
    lines = []
    for item, count in sorted(grouped.items())[:6]:
        suffix = f"（{count} 处来源需要核对）" if count > 1 else ""
        lines.append(f"- {item}{suffix}")
    return "\n".join(lines) if lines else "- 没有需要放入本财报阅读报告的人工复核点。"


def _review_flag_readout_zh(flag: dict[str, Any]) -> str:
    detail = str(flag.get("formula_id") or flag.get("event_type") or flag.get("metric") or flag.get("flag_id") or "")
    severity = str(flag.get("severity") or "")
    if detail == "short_term_investments":
        return "短期投资抽取需要人工复核；它会影响“广义现金与短投”和现金缓冲判断。"
    if flag.get("source") == "material_event_scan" and severity in {"high", "critical"}:
        document = flag.get("document_id")
        filing_date = flag.get("filing_date")
        suffix = " | ".join(str(item) for item in [filing_date, document] if item)
        return f"重大事项扫描发现需要复核的事件：{detail}{'（' + suffix + '）' if suffix else ''}。"
    return ""


def _diagnostic_answer_zh(question: dict[str, Any]) -> str:
    values = question.get("latest_values") or {}
    question_id = question.get("question_id")
    if question_id == "growth_quality":
        component = values.get("top_revenue_component") or "未识别"
        return (
            f"收入增长 {_pct(values.get('revenue_growth_yoy'))}；经营利润率 {_pct(values.get('operating_margin'))}；"
            f"增量经营利润率 {_pct(values.get('incremental_operating_margin'))}；"
            f"最大已抽取收入组件是 {_metric_label_zh(str(component))}。"
        )
    if question_id == "profitability_with_scale":
        return (
            f"毛利率 {_pct(values.get('gross_margin'))}，经营利润率 {_pct(values.get('operating_margin'))}，"
            f"净利率 {_pct(values.get('net_margin'))}；增量经营利润率 {_pct(values.get('incremental_operating_margin'))}。"
        )
    if question_id == "cash_profit_quality":
        return (
            f"经营现金流 / 净利润为 {_ratio(values.get('cash_conversion'))}；"
            f"营运资本现金顺风 / 收入为 {_pct(values.get('working_capital_cash_tailwind_to_revenue'))}；"
            f"股权激励费用 / 经营现金流为 {_pct(values.get('sbc_to_operating_cash_flow'))}。"
        )
    if question_id == "capital_needed_for_growth":
        return (
            f"资本开支 / 收入为 {_pct(values.get('capex_to_revenue'))}；"
            f"自由现金流率为 {_pct(values.get('free_cash_flow_margin'))}；"
            f"ROIC proxy 为 {_pct(values.get('roic'))}；"
            f"新增资本回报 proxy 为 {_pct(values.get('incremental_roic_proxy'))}。"
        )
    if question_id == "balance_sheet_resilience":
        return (
            f"负债 / 资产为 {_pct(values.get('liabilities_to_assets'))}；"
            f"现金 / 总负债为 {_ratio(values.get('cash_to_total_liabilities'))}；"
            f"流动比率为 {_ratio(values.get('current_ratio'))}；"
            f"债务 / 现金为 {_ratio(values.get('debt_to_cash')) or '缺失'}。"
        )
    if question_id == "sbc_and_per_share_quality":
        return (
            f"股权激励费用 / 收入为 {_pct(values.get('sbc_to_revenue'))}；"
            f"股权激励费用 / 经营现金流为 {_pct(values.get('sbc_to_operating_cash_flow'))}；"
            f"稀释股数同比为 {_pct(values.get('diluted_shares_yoy'))}。"
        )
    if question_id == "tax_non_gaap_accounting_quality":
        return (
            f"有效税率为 {_pct(values.get('effective_tax_rate'))}；"
            f"最新官方非 GAAP 净利润调整幅度为 {_pct(values.get('latest_non_gaap_net_income_uplift'))}。"
        )
    return str(question.get("current_answer") or "")


def _metric_meaning_zh(question_id: str) -> str:
    meanings = {
        "growth_quality": (
            "收入增长率看规模是否还在扩大；经营利润率看现有收入的盈利能力；"
            "增量经营利润率看新增收入有没有转成新增经营利润；收入组件用于判断增长来自哪类业务，"
            "而不是只看总收入同比。"
        ),
        "profitability_with_scale": (
            "毛利率反映业务的基础经济性；经营利润率把销售、研发、管理等费用纳入后看经营杠杆；"
            "增量利润率用于判断规模变大后利润是否同步流入股东。"
        ),
        "cash_profit_quality": (
            "CFO / 净利润检验会计利润能否变成经营现金流；FCF 检验扣除资本开支后的现金质量；"
            "营运资本变化用于判断现金流是否靠应付、商家保证金或递延收入暂时撑起来。"
        ),
        "capital_needed_for_growth": (
            "资本开支 / 收入看增长是否吃资本；自由现金流率看收入变成自由现金流的能力；"
            "ROIC 近似值看已有资本回报；增量 ROIC 近似值看新增资本的边际回报。"
        ),
        "balance_sheet_resilience": (
            "负债 / 资产看总体杠杆；现金 / 总负债和流动比率看短期抗压能力；"
            "受限现金和债务到期结构用来判断现金是否真的可用、债务是否临近压力。"
        ),
        "sbc_and_per_share_quality": (
            "SBC / 收入和 SBC / CFO 衡量股权激励对真实现金收益的消耗；"
            "稀释股数增长看经营增长是否被每股摊薄抵消。"
        ),
        "tax_non_gaap_accounting_quality": (
            "有效税率看税负是否可持续；非 GAAP 调整幅度看管理层调整后利润比 GAAP 好多少；"
            "投资收益、减值和税项用于识别利润中非经营或估计成分。"
        ),
    }
    return meanings.get(question_id, "该指标组用于把抽取出的财务数字转成可检查的财务质量问题。")


def _why_metrics_answer_question_zh(question_id: str) -> str:
    explanations = {
        "growth_quality": (
            "收入增速回答“有没有增长”，收入组件回答“靠什么增长”，增量经营利润率回答“新增收入有没有赚钱”。"
        ),
        "profitability_with_scale": (
            "毛利率看单位经济性，经营利润率看费用后的经营杠杆，增量利润率看规模变大后是否更赚钱。"
        ),
        "cash_profit_quality": (
            "净利润是会计口径，经营现金流和自由现金流用来验证利润是否真正变成现金。"
        ),
        "capital_needed_for_growth": (
            "资本开支 / 收入看增长吃不吃资本，自由现金流率和 ROIC 近似值看投入之后还能留下多少回报。"
        ),
        "balance_sheet_resilience": (
            "坏年份里最重要的是现金是否可用、负债是否集中到期，以及公司会不会被迫融资或削减投入。"
        ),
        "sbc_and_per_share_quality": (
            "股东买的是每股价值，所以总利润增长必须和 SBC、稀释股数、回购一起看。"
        ),
        "tax_non_gaap_accounting_quality": (
            "税率、非 GAAP 调整和投资收益会改变净利润读法，需要把经营利润和非经营项目分开。"
        ),
    }
    return explanations.get(question_id, "这些数字把问题拆成规模、利润、现金、资本和风险几个可验证维度。")


def _diagnostic_interpretation_zh(question: dict[str, Any]) -> str:
    values = question.get("latest_values") or {}
    question_id = question.get("question_id")
    if question_id == "growth_quality":
        revenue_growth = _float_value(values.get("revenue_growth_yoy"))
        operating_margin = _float_value(values.get("operating_margin"))
        incremental_margin = _float_value(values.get("incremental_operating_margin"))
        if incremental_margin is not None and incremental_margin < 0:
            return (
                f"收入仍增长（{_pct(revenue_growth)}），存量业务也仍有 {_pct(operating_margin)} 的经营利润率；"
                f"但增量经营利润率为 {_pct(incremental_margin)}，说明新增收入没有转成新增经营利润。"
                "这更像“增长变贵了”，需要验证原因是主动投入、竞争加剧，还是收入结构变差。"
            )
        if revenue_growth is not None and revenue_growth > 0 and operating_margin is not None and operating_margin > 0.15:
            return "收入增长和经营利润率同时为正，说明增长目前仍有利润支撑；下一步要看增长来源是否可持续。"
        return "增长信号不够完整，需要结合收入组件、费用率和管理层对增长来源的解释。"
    if question_id == "profitability_with_scale":
        incremental_margin = _float_value(values.get("incremental_operating_margin"))
        if incremental_margin is not None and incremental_margin < 0:
            return (
                "整体利润率仍高，但新增收入对应的经营利润为负，说明规模扩大没有带来经营杠杆。"
                "关键不是利润率下降本身，而是下降来自可收回的主动投入，还是来自竞争和结构压力。"
            )
        return "如果毛利率和经营利润率稳定，说明规模没有明显侵蚀盈利；如果两者分化，需要回到费用结构。"
    if question_id == "cash_profit_quality":
        cash_conversion = _float_value(values.get("cash_conversion"))
        working_capital_tailwind = _float_value(values.get("working_capital_cash_tailwind_to_revenue"))
        if cash_conversion is not None and cash_conversion >= 1 and working_capital_tailwind is not None and working_capital_tailwind > 0.05:
            return (
                "经营现金流覆盖净利润，利润有现金支撑；但部分现金流来自营运资本顺风，"
                "不能把全部现金流表现都视为经营质量改善。"
            )
        if cash_conversion is not None and cash_conversion >= 1:
            return "经营现金流高于净利润，说明利润现金化较好；下一步确认是否有一次性营运资本或税项影响。"
        return "现金转化低于理想水平，需要回查应收、存货、预付/递延、税项和一次性现金流。"
    if question_id == "capital_needed_for_growth":
        capex_to_revenue = _float_value(values.get("capex_to_revenue"))
        incremental_roic = _float_value(values.get("incremental_roic_proxy"))
        if capex_to_revenue is not None and capex_to_revenue < 0.02 and incremental_roic is not None and incremental_roic < 0:
            return (
                "公司表面仍是轻资本模式，资本开支占收入很低、自由现金流率很高；"
                "但新增资本回报近似值为负，说明边际投入的回报还没有体现出来。"
            )
        return "资本消耗和回报率需要结合维护性资本开支、增长性投入、投资组合和现金结构一起看。"
    if question_id == "balance_sheet_resilience":
        restricted_cash = _float_value(values.get("restricted_cash_to_cash"))
        current_ratio = _float_value(values.get("current_ratio"))
        if restricted_cash is not None and restricted_cash > 0.25:
            return (
                f"流动比率为 {_ratio(current_ratio)}，短期流动性较强；但受限现金占比较高，"
                "账面现金不能全部视为自由可支配现金。"
            )
        return "资产负债表抗压能力看起来取决于现金可用性和债务披露完整性；缺失债务细节时应保持保守。"
    if question_id == "sbc_and_per_share_quality":
        dilution = _float_value(values.get("diluted_shares_yoy"))
        if dilution is not None and dilution < 0.02:
            return "SBC 相对收入和 CFO 不算失控，稀释股数增长也较低；但仍需确认回购是否只是抵消 SBC，而不是创造每股价值。"
        return "股权激励要和回购、稀释股数、每股 FCF 一起看，不能只看总利润。"
    if question_id == "tax_non_gaap_accounting_quality":
        non_gaap_uplift = _float_value(values.get("latest_non_gaap_net_income_uplift"))
        if non_gaap_uplift is not None and non_gaap_uplift > 0.1:
            return (
                "非 GAAP 净利润比 GAAP 高一截，说明管理层调整项对利润叙事有影响；"
                "同时投资收益/损失占税前利润比例较高，读净利润时要区分经营利润和非经营项目。"
            )
        return "税率和非 GAAP 调整目前没有单独证明利润质量有问题，但仍需看调整项是否反复出现。"
    return str(question.get("current_answer") or "")


def _follow_up_zh(question_id: str) -> str:
    follow_ups = {
        "growth_quality": "MD&A 里关于收入增长、商家支持、生态投入、供应链投入的解释；收入附注和分部/产品收入拆分。",
        "profitability_with_scale": "销售与营销、研发、履约/支付/服务器等费用率；管理层是否解释利润率下降是短期投入还是结构性变化。",
        "cash_profit_quality": "现金流量表的营运资本项目；应付商家款项、商家保证金、递延收入、应收和存货披露。",
        "capital_needed_for_growth": "资本开支明细、折旧摊销、资本化软件/云/物流投入；确认维护性资本开支估算是否过粗。",
        "balance_sheet_resilience": "受限现金注释、可转债/债务到期表、VIE 和资金可转移限制。",
        "sbc_and_per_share_quality": "股权激励附注、ADS / 普通股桥表、回购是否抵消稀释。",
        "tax_non_gaap_accounting_quality": "税率调节表、现金税、非 GAAP 调节表、投资收益/公允价值变动。"
    }
    return follow_ups.get(question_id, "")


def _question_short_label_zh(question_id: str, fallback: str) -> str:
    labels = {
        "growth_quality": "增长质量",
        "profitability_with_scale": "利润率",
        "cash_profit_quality": "现金质量",
        "capital_needed_for_growth": "资本效率",
        "balance_sheet_resilience": "资产负债表",
        "sbc_and_per_share_quality": "稀释",
        "tax_non_gaap_accounting_quality": "会计与非 GAAP",
    }
    return labels.get(question_id, fallback)


def _diagnostic_short_judgment_zh(question: dict[str, Any]) -> str:
    values = question.get("latest_values") or {}
    question_id = question.get("question_id")
    if question_id == "growth_quality":
        incremental_margin = _float_value(values.get("incremental_operating_margin"))
        if incremental_margin is not None and incremental_margin < 0:
            return "增长还在，但新增收入没有转成新增经营利润。"
        return "增长有利润支撑，但来源仍要验证。"
    if question_id == "profitability_with_scale":
        incremental_margin = _float_value(values.get("incremental_operating_margin"))
        if incremental_margin is not None and incremental_margin < 0:
            return "存量利润率高，边际利润率弱。"
        return "利润率没有明显失控。"
    if question_id == "cash_profit_quality":
        cash_conversion = _float_value(values.get("cash_conversion"))
        if cash_conversion is not None and cash_conversion >= 1:
            return "利润有现金流支撑。"
        return "现金转化需要谨慎。"
    if question_id == "capital_needed_for_growth":
        incremental_roic = _float_value(values.get("incremental_roic_proxy"))
        if incremental_roic is not None and incremental_roic < 0:
            return "轻资本表象仍在，但新增回报未体现。"
        return "资本消耗暂未成为主要压力。"
    if question_id == "balance_sheet_resilience":
        return "现金缓冲强，但自由动用性要打折。"
    if question_id == "sbc_and_per_share_quality":
        return "股权激励和稀释暂未成为主线风险。"
    if question_id == "tax_non_gaap_accounting_quality":
        return "净利润受非 GAAP 调整和投资收益影响，需要拆开看。"
    return _sentence_fragment(_diagnostic_interpretation_zh(question))


def _diagnostic_key_evidence_zh(question: dict[str, Any]) -> str:
    values = question.get("latest_values") or {}
    question_id = question.get("question_id")
    if question_id == "growth_quality":
        component = values.get("top_revenue_component") or "未识别"
        return _join_metric_pieces_zh(
            _metric_piece_zh("收入同比", _pct(values.get("revenue_growth_yoy"))),
            _metric_piece_zh("增量经营利润率", _pct(values.get("incremental_operating_margin"))),
            f"最大组件：{_metric_label_zh(str(component))}" if component != "未识别" else "",
        )
    if question_id == "profitability_with_scale":
        return _join_metric_pieces_zh(
            _metric_piece_zh("毛利率", _pct(values.get("gross_margin"))),
            _metric_piece_zh("经营利润率", _pct(values.get("operating_margin"))),
            _metric_piece_zh("增量经营利润率", _pct(values.get("incremental_operating_margin"))),
        )
    if question_id == "cash_profit_quality":
        return _join_metric_pieces_zh(
            _metric_piece_zh("经营现金流 / 净利润", _ratio(values.get("cash_conversion"))),
            _metric_piece_zh("营运资本现金顺风 / 收入", _pct(values.get("working_capital_cash_tailwind_to_revenue"))),
            _metric_piece_zh("SBC / 经营现金流", _pct(values.get("sbc_to_operating_cash_flow"))),
        )
    if question_id == "capital_needed_for_growth":
        return _join_metric_pieces_zh(
            _metric_piece_zh("资本开支 / 收入", _pct(values.get("capex_to_revenue"))),
            _metric_piece_zh("自由现金流率", _pct(values.get("free_cash_flow_margin"))),
        )
    if question_id == "balance_sheet_resilience":
        return _join_metric_pieces_zh(
            _metric_piece_zh("负债 / 资产", _pct(values.get("liabilities_to_assets"))),
            _metric_piece_zh("流动比率", _ratio(values.get("current_ratio"))),
            _metric_piece_zh("现金 / 总负债", _ratio(values.get("cash_to_total_liabilities"))),
        )
    if question_id == "sbc_and_per_share_quality":
        return _join_metric_pieces_zh(
            _metric_piece_zh("SBC / 收入", _pct(values.get("sbc_to_revenue"))),
            _metric_piece_zh("SBC / 经营现金流", _pct(values.get("sbc_to_operating_cash_flow"))),
            _metric_piece_zh("稀释股数同比", _pct(values.get("diluted_shares_yoy"))),
        )
    if question_id == "tax_non_gaap_accounting_quality":
        return _join_metric_pieces_zh(
            _metric_piece_zh("有效税率", _pct(values.get("effective_tax_rate"))),
            _metric_piece_zh("非 GAAP 净利润调整幅度", _pct(values.get("latest_non_gaap_net_income_uplift"))),
        )
    return _diagnostic_answer_zh(question)


def _metric_piece_zh(label: str, value: str) -> str:
    if value in {"", "缺失"}:
        return ""
    return f"{label} {value}" if value else ""


def _join_metric_pieces_zh(*pieces: str) -> str:
    filtered = [piece for piece in pieces if piece]
    return "；".join(filtered) if filtered else "关键结构化读数不足"


def _diagnostic_risk_zh(question: dict[str, Any]) -> str:
    warnings = [_sentence_fragment(_warning_zh(str(item))) for item in (question.get("warning_flags") or [])]
    missing = [_missing_zh(str(item)) for item in (question.get("missing") or [])]
    parts = []
    if warnings:
        parts.append(warnings[0])
    if missing:
        missing_text = missing[0]
        if missing_text.startswith("缺口："):
            missing_text = missing_text.removeprefix("缺口：")
        parts.append(("证据缺口：" if warnings else "") + missing_text)
    return "；".join(parts) if parts else "暂无明显红旗"


def _diagnostic_next_step_zh(question: dict[str, Any]) -> str:
    question_id = str(question.get("question_id") or "")
    missing = [_missing_zh(str(item)) for item in (question.get("missing") or [])]
    if question_id in {"growth_quality", "profitability_with_scale"}:
        return "回查投入、补贴、商家支持和费用率是否解释利润率下滑。"
    if question_id == "cash_profit_quality":
        return "拆营运资本，确认现金流是否依赖商家相关负债。"
    if question_id == "capital_needed_for_growth":
        return "区分维护性资本开支、增长性投入和投资资产。"
    if question_id == "balance_sheet_resilience":
        return "确认受限现金、债务到期和 VIE 资金可转移性。"
    if question_id == "sbc_and_per_share_quality":
        return "看回购是否只是抵消 SBC 稀释。"
    if question_id == "tax_non_gaap_accounting_quality":
        return "拆非 GAAP 调整、税率调节和投资收益。"
    return "补齐：" + "、".join(missing[:3]) if missing else "继续跟踪。"


def _delta(latest: Any, prior: Any) -> float | None:
    latest_value = _float_value(latest)
    prior_value = _float_value(prior)
    if latest_value is None or prior_value is None:
        return None
    return latest_value - prior_value


def _list_text_zh(items: list[Any]) -> str:
    cleaned = [_cell(item) for item in items if item not in (None, "")]
    return "；".join(cleaned)


def _evidence_refs_zh(item: dict[str, Any]) -> str:
    evidence_items = item.get("evidence") or item.get("evidence_bundle") or []
    refs: list[str] = []
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue
        period = _cell(evidence.get("period"))
        source = _cell(evidence.get("source_document"))
        speaker = _cell(evidence.get("speaker"))
        block_id = _cell(evidence.get("block_id"))
        parts = [part for part in (period, source, speaker, block_id) if part]
        if parts:
            ref = " / ".join(parts)
            if ref not in refs:
                refs.append(ref)
    return "；".join(refs[:3])


def _answer_quality_label_zh(value: Any) -> str:
    labels = {
        "specific_with_numbers": "回答具体，并且给出数字",
        "specific_without_numbers": "回答具体，但缺少量化",
        "directional_only": "回答只有方向性，没有量化",
        "avoided": "没有正面回答核心问题",
        "contradicted_by_filings_or_metrics": "回答与财务数字或 filing 证据冲突",
    }
    text = "" if value is None else str(value)
    return labels.get(text, text or "未评分")


def _consistency_label_zh(value: Any) -> str:
    labels = {
        "supports": "支持",
        "weakens": "削弱",
        "clarifies": "提供解释但不完全证明",
        "no_change": "不改变判断",
        "conflicts": "冲突",
    }
    text = "" if value is None else str(value)
    return labels.get(text, text or "未判断")


def _status_zh(status: Any) -> str:
    translations = {
        "answered": "已回答",
        "partial": "部分回答",
        "missing": "缺失",
    }
    text = "" if status is None else str(status)
    return f"{translations.get(text, text)} ({text})" if text else "未知"


def _priority_zh(priority: Any) -> str:
    translations = {
        "highest": "最高",
        "high": "高",
        "medium": "中",
        "low": "低",
    }
    text = "" if priority is None else str(priority)
    return f"{translations.get(text, text)} ({text})" if text else "未知"


def _metric_label_zh(metric: str) -> str:
    labels = {
        "online_marketing_services_revenue": "在线营销服务及其他收入",
        "transaction_services_revenue": "交易服务收入",
        "revenue": "收入",
        "gross_profit": "毛利润",
        "operating_income": "经营利润",
        "net_income": "净利润",
        "accounts_payable_and_accrued_expenses": "应付账款及应计费用",
        "payable_to_merchants": "应付商家款项",
        "merchant_deposits": "商家保证金",
        "deferred_revenue": "递延收入",
        "accounts_receivable": "应收账款",
        "inventory": "存货",
        "accrued_expenses": "应计费用",
        "未识别": "未识别",
    }
    return labels.get(metric, metric)


def _valuation_label_zh(formula_id: str) -> str:
    labels = {
        "enterprise_value_v1": "企业价值 EV",
        "true_yield_v1": "所有者收益率近似值",
        "free_cash_flow_yield_v1": "自由现金流收益率",
        "investment_adjusted_operating_yield_v1": "投资资产调整后的经营收益率",
    }
    return labels.get(formula_id, formula_id)


def _metric_status_zh(status: Any) -> str:
    translations = {
        "missing_investment_portfolio": "缺少投资组合数据，暂不计算",
        "missing_market_inputs": "缺少市场价格或股本输入",
        "missing_required_facts": "缺少必要财务事实",
        "calculated": "已计算",
    }
    text = "" if status is None else str(status)
    return translations.get(text, text or "未知")


def _trend_status_zh(status: Any) -> str:
    translations = {
        "trend_confirmed": "主线基本确认",
        "trend_changed": "主线发生变化",
        "trend_unclear": "趋势不明确",
        "not available": "不可用",
        "None": "不可用",
    }
    text = "" if status is None else str(status)
    return translations.get(text, text or "未知")


def _trend_direction_zh(direction: Any) -> str:
    translations = {
        "positive": "改善",
        "negative": "走弱",
        "neutral_or_unclear": "中性或不明确",
        "not available": "不可用",
        "None": "不可用",
    }
    text = "" if direction is None else str(direction)
    return translations.get(text, text or "未知")


def _trend_topic_zh(topic: Any) -> str:
    translations = {
        "revenue_growth": "收入增长",
        "margin_quality": "利润率质量",
        "cash_conversion": "现金转化",
        "balance_sheet": "资产负债表",
        "dilution": "稀释",
    }
    text = "" if topic is None else str(topic)
    return translations.get(text, text or "未知")


def _trend_reason_zh(reason: Any) -> str:
    translations = {
        "latest quarter revenue growth is close to the annual baseline": "最新季度收入增速接近年度基准",
        "latest quarter margin moved, but the signal is not decisive": "最新季度利润率有变化，但信号还不够决定性",
        "latest quarter cash conversion is close to the annual baseline": "最新季度现金转化接近年度基准",
        "latest quarter balance sheet is broadly consistent with the annual baseline": "最新季度资产负债表与年度基准大体一致",
        "dilution is within the 2% confirmation band": "稀释幅度在 2% 确认区间内",
    }
    text = "" if reason is None else str(reason)
    return translations.get(text, text or "未知")


def _interpretation_limit_zh(limit: str) -> str:
    translations = {
        "Source-of-growth attribution uses only official extracted revenue component facts. Missing segment/product/geography/take-rate fields remain evidence gaps.": (
            "增长来源只使用已从官方文件抽取出的收入组件；如果缺少业务线、产品、地区或变现率数据，不能把增长来源判断当成完整解释。"
        ),
        "Margin trend does not prove moat; it only shows whether scale is currently flowing through to profits.": (
            "利润率趋势不能单独证明护城河，只能说明当前规模增长是否流入利润。"
        ),
        "Working-capital quality is calculated only from extracted official line items. If a company embeds merchant balances inside broader line items, the report must flag that limitation.": (
            "营运资本质量只基于已抽取的官方科目；如果客户、商户或供应商相关余额被放在更宽泛的科目里，现金流判断需要保守。"
        ),
        "V1 cannot yet separate maintenance and growth capex, so owner-earnings quality remains approximate.": (
            "V1 还不能区分维护性资本开支和增长性资本开支，因此自由现金流只能作为现金质量近似线索。"
        ),
        "Balance-sheet ratios do not address trapped cash, VIE structure, or capital-control risk.": (
            "资产负债表比率本身不能解决受限现金、结构性资金限制或跨境资金限制问题。"
        ),
        "SBC is not automatically bad, but it must be measured against cash generation and per-share value.": (
            "SBC 不一定是坏事，但必须和现金创造能力、回购以及每股价值一起看。"
        ),
        "The rule flags unusual accounting/tax/non-GAAP patterns. It does not prove manipulation without reading the footnotes.": (
            "该规则只提示会计、税项或非 GAAP 异常模式；是否有问题仍要回到附注和调节表验证。"
        ),
    }
    return translations.get(limit, limit)


def _warning_zh(warning: str) -> str:
    translations = {
        "Incremental operating margin is negative.": "增量经营利润率为负，新增收入没有带来新增经营利润",
        "Incremental FCF margin is negative.": "增量自由现金流率为负，新增收入没有带来新增自由现金流",
        "Incremental operating margin is below latest operating margin.": "增量经营利润率低于当前经营利润率，说明边际盈利能力弱于存量业务",
        "Working-capital source liabilities added more than 5% of revenue to cash-flow tailwind.": "营运资本中的现金来源负债贡献超过收入的 5%，现金流有营运资本顺风",
        "Restricted cash exceeds 25% of cash.": "受限现金占现金比例超过 25%，账面现金不能全部视为自由现金",
        "Investment income/loss is more than 20% of pretax income.": "投资收益/损失占税前利润比例超过 20%，净利润受非经营项目影响较大",
        "Cash covers less than half of total liabilities.": "现金 / 总负债低于 0.5x，现金覆盖总负债的比例偏低",
    }
    if warning.startswith("Optional balance-sheet details are missing:"):
        raw_items = [item.strip().rstrip(".") for item in warning.split(":", 1)[1].split(",")]
        translated = "、".join(_missing_zh(item) for item in raw_items if item)
        return f"关键资产负债表细节缺失：{translated}"
    return translations.get(warning, warning)


def _missing_zh(item: str) -> str:
    translations = {
        "segment/product/geography/take-rate revenue facts": "业务线 / 产品 / 地区 / 变现率收入拆分",
        "merchant cohort economics": "客户、用户或商户分群 / 单客户经济性",
        "商家分群 / 单商家经济性": "客户、用户或商户分群 / 单客户经济性",
        "accounts_receivable": "应收账款",
        "payables": "应付账款",
        "inventory": "存货",
        "deferred_revenue": "递延收入",
        "receivables/payables/inventory/deferred-revenue working-capital bridge": "应收、应付、存货和递延收入营运资本桥",
        "restricted_cash": "受限现金",
        "short_term_investments": "短期投资",
        "current_assets": "流动资产",
        "current_liabilities": "流动负债",
        "maintenance capex versus growth capex": "维护性资本开支与增长性资本开支拆分",
        "debt": "债务",
        "debt_current": "一年内到期债务",
        "debt_noncurrent": "长期债务",
        "buyback offset analysis": "回购是否抵消股权激励稀释",
        "full per-ADS dilution bridge": "完整 ADS / 普通股稀释桥",
        "investment_income": "投资收益",
        "equity_method_income": "权益法投资收益",
        "cash_paid_for_taxes": "现金纳税",
        "impairment": "减值项目",
    }
    return translations.get(item, item)


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


def _annual_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in pack.get("annual_facts", []) if row.get("year") is not None]
    return sorted(rows, key=lambda row: row.get("year", 0))


def _quarterly_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in pack.get("quarterly_facts", []) if row.get("period_end") or row.get("quarter")]
    return sorted(rows, key=lambda row: str(row.get("period_end") or row.get("quarter") or ""))


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
    components = [
        _float_value(row.get("cash")),
        _float_value(row.get("restricted_cash")),
        _float_value(row.get("short_term_investments")),
    ]
    values = [value for value in components if value is not None]
    if not values:
        return None
    return sum(values)


def _has_revenue_components(metric: dict[str, Any] | None) -> bool:
    return _latest_component_result(metric) is not None


def _latest_component_result(metric: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metric:
        return None
    annual_results = [
        row
        for row in metric.get("annual_results", [])
        if row.get("status") == "calculated" and row.get("component_details")
    ]
    if annual_results:
        return sorted(annual_results, key=lambda row: row.get("year", 0))[-1]
    latest_interim = metric.get("latest_interim_result") or {}
    if latest_interim.get("status") == "calculated" and latest_interim.get("component_details"):
        return latest_interim
    return None


def _prior_year_quarter(rows: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any] | None:
    identity = _quarter_identity(row)
    if not identity:
        return None
    year, quarter = identity
    for candidate in rows:
        if _quarter_identity(candidate) == (year - 1, quarter):
            return candidate
    return None


def _quarter_identity(row: dict[str, Any]) -> tuple[int, int] | None:
    quarter_label = str(row.get("quarter") or "")
    parts = quarter_label.replace("Q", " Q").split()
    if len(parts) >= 2:
        try:
            year = int(parts[0])
            quarter = int(str(parts[1]).replace("Q", ""))
            return year, quarter
        except (TypeError, ValueError):
            pass
    period_end = str(row.get("period_end") or "")
    if len(period_end) >= 7:
        try:
            year = int(period_end[:4])
            month = int(period_end[5:7])
            return year, ((month - 1) // 3) + 1
        except (TypeError, ValueError):
            return None
    return None


def _latest_calculated_result(metric: dict[str, Any]) -> dict[str, Any] | None:
    rows = [row for row in metric.get("annual_results", []) if row.get("status") == "calculated"]
    if not rows:
        return None
    return sorted(rows, key=lambda row: row.get("year", 0))[-1]


def _latest_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(rows, key=lambda row: row.get(key, 0))[-1]


def _money(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"RMB {float(value) / 1_000_000_000:.1f}B"
    except (TypeError, ValueError):
        return str(value)


def _money_bn(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) / 1_000_000_000:.1f}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _ratio(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return str(value)


def _score(value: Any) -> str:
    if value is None:
        return "无法评分"
    try:
        return f"{float(value):.1f} / 10"
    except (TypeError, ValueError):
        return str(value)


def _float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sentence_fragment(text: str) -> str:
    return text.rstrip("。.;； ")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return _polish_report_terms_zh(str(value).replace("\n", " ").replace("|", "/"))


def _polish_report_terms_zh(text: str) -> str:
    replacements = [
        ("raw_transcript_not_independently_verified", "原始文字稿，尚未独立校验"),
        ("source of record", "正式财务数据来源"),
        ("first-party brand business", "自营品牌业务"),
        ("first-party brand", "自营品牌"),
        ("online marketing services", "在线营销服务"),
        ("online marketing service", "在线营销服务"),
        ("online marketing", "在线营销"),
        ("transaction services", "交易服务"),
        ("global business", "全球业务"),
        ("non-GAAP", "非 GAAP"),
        ("CapEx", "资本开支"),
        ("transcript", "文字稿"),
        ("profitable", "有利润"),
        ("margin floor", "利润率底部"),
        ("take-rate", "变现率"),
        ("cost-to-profit ratio", "成本利润比"),
        ("strategic pivot", "战略转向"),
        ("pivot", "转向"),
    ]
    polished = text
    for source, target in replacements:
        polished = polished.replace(source, target)
    polished = re.sub(r"\s+(自营品牌业务|自营品牌|在线营销服务|在线营销|交易服务|全球业务)\s+", r"\1", polished)
    polished = re.sub(r"\s+(自营品牌业务|自营品牌|在线营销服务|在线营销|交易服务|全球业务)", r"\1", polished)
    polished = re.sub(r"(自营品牌业务|自营品牌|在线营销服务|在线营销|交易服务|全球业务)\s+", r"\1", polished)
    polished = polished.replace(" /全球业务", " / 全球业务")
    polished = polished.replace("是否 有利润", "是否有利润")
    polished = polished.replace("广告 变现率", "广告变现率")
    polished = polished.replace("战略 转向", "战略转向")
    polished = polished.replace("PDD在线营销", "PDD 在线营销")
    return polished
