from __future__ import annotations

import re
from typing import Any


def build_financial_research_draft(
    pack: dict[str, Any],
    *,
    audit_status: str = "Draft pending audit review",
    layer1_question_pack: dict[str, Any] | None = None,
    evidence_communication_pack: dict[str, Any] | None = None,
    feedback_loop_pack: dict[str, Any] | None = None,
    official_evidence_pack: dict[str, Any] | None = None,
    management_communication_pack: dict[str, Any] | None = None,
) -> str:
    layer1_question_pack = layer1_question_pack or pack.get("layer1_question_pack") or {}
    evidence_communication_pack = evidence_communication_pack or pack.get("evidence_communication_pack") or {}
    feedback_loop_pack = feedback_loop_pack or pack.get("feedback_loop_pack") or {}
    transitional_packs = evidence_communication_pack.get("transitional_source_packs") or {}
    official_evidence_pack = official_evidence_pack or {}
    management_communication_pack = management_communication_pack or {}
    if evidence_communication_pack:
        official_evidence_pack = official_evidence_pack or transitional_packs.get("official_report_evidence_pack") or {}
        management_communication_pack = (
            management_communication_pack or transitional_packs.get("management_communication_pack") or {}
        )
    company = (pack.get("company") or {}).get("legal_name") or pack.get("company") or "Company"
    annual_rows = _annual_rows(pack)
    quarterly_rows = _quarterly_rows(pack)
    latest = annual_rows[-1] if annual_rows else {}
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}
    metrics = _metrics_by_id(pack)
    dockets = _build_question_dockets(pack, official_evidence_pack, management_communication_pack)

    lines: list[str] = [
        f"# 财务研究底稿：{company}（V1）",
        "",
        "> 定位：这是财务研究底稿，不是最终展示版。它应当比易读报告更广、更深、更可追溯：把关键问题、硬数字、官方文件解释、管理层沟通、证据裁判、仍未知和下一步查证路径放在同一张研究底稿里。最终 HTML 投资报告应从这里提炼重点。",
        "",
        "## 0. 来源覆盖与证据边界",
        "",
        _source_boundary(pack, official_evidence_pack, management_communication_pack, audit_status, latest, latest_quarter),
        "",
        _pipeline_artifact_note(layer1_question_pack, evidence_communication_pack, feedback_loop_pack),
        "",
        "## 1. 核心投资问题：标准回答表",
        "",
        "底稿先回答一组标准问题，再进入异常、红旗和追问。这样读者不会只看到“哪里有问题”，也能先得到一家公司基本面状态的正面答案：是否增长、增长来自哪里、是否兑现为利润和现金、资产负债表是否能支撑、商业模式是否正在变化。",
        "",
        _core_question_answer_sheet(annual_rows, quarterly_rows, metrics, management_communication_pack),
        "",
        "## 2. 研究问题索引：后文导航",
        "",
        "这一节是后文导航，不是新增结论。它记录标准问题之外进一步冒出来的重点追问：这些问题来自第一层数字异常、第二层官方文件解释、第三层管理层沟通，或者公司特有披露缺口；后续 HTML 报告应优先从这里挑选最有价值的投资片段。",
        "",
        _question_map(dockets),
        "",
        "## 3. 关键问题台账：问题底稿",
        "",
        "每个问题底稿都按同一证据顺序展开：`第一层数字触发点` 先说明为什么要问；`第二层官方文件证据` 再说明官方文件能回答什么；`第三层管理层沟通` 判断管理层有没有正面解释；最后给出 `证据裁判`、`仍未解决` 和 `下一步查证路径`。",
        "",
        _render_question_dockets(dockets),
        "",
        "## 4. 财务事实层：长周期财务历史",
        "",
        "底稿默认使用可抽取的最长年度历史，而不是只看 3-5 年。短期表回答当前状态，长周期表用来识别商业模式阶段变化、利润率阶段切换、现金流模式和资产负债表结构变化。",
        "",
        _long_horizon_history(annual_rows, metrics),
        "",
        "## 5. 详细数字证据",
        "",
        "这一节是问题底稿背后的数字底稿。它保留更完整的年度、季度、利润桥、营运资本和经营利润以下桥，供人工复核或 HTML 图表层引用。",
        "",
        _detailed_numeric_evidence(annual_rows, quarterly_rows, metrics),
        "",
        "## 6. 叙事证据层：洞察登记",
        "",
        "这里记录已经从数据和文字证据里冒出来、但不一定完整回答的问题。它不是最终结论，而是后续 HTML 报告和下一轮调研的素材池。",
        "",
        _insight_register(pack, official_evidence_pack, management_communication_pack),
        "",
        "## 7. 公司特有证据卡",
        "",
        "这一节只放公司特有变量。通用财务比率不足以理解 PDD；必须跟踪交易服务、Temu / 全球业务、自营品牌、商家资金沉淀、受限现金 / VIE 和治理变化。",
        "",
        _business_specific_cards(pack, official_evidence_pack, management_communication_pack),
        "",
        "## 8. 未解问题、限制与下一轮抽取清单",
        "",
        "这一节是所有披露缺口、仍未知和下一轮数据抽取需求的固定停车场。前半部分把问题转成下一轮抽取清单；后半部分保留原始未知登记，方便回溯。",
        "",
        _unknown_register(pack, official_evidence_pack, management_communication_pack, feedback_loop_pack, dockets),
        "",
        "## 9. 证据附录",
        "",
        _evidence_appendix(pack, official_evidence_pack, management_communication_pack, metrics),
    ]
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def _source_boundary(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    audit_status: str,
    latest: dict[str, Any],
    latest_quarter: dict[str, Any],
) -> str:
    extraction = pack.get("fact_extraction_summary") or {}
    quality_gate = pack.get("fact_quality_gate") or {}
    official_sources = _as_list(official_pack.get("source_catalog") or pack.get("source_inventory"))
    management_sources = _as_list(management_pack.get("source_catalog"))
    rows = [
        "| 层级 | 当前覆盖 | 在底稿中的作用 |",
        "| --- | --- | --- |",
        f"| 来源抓取 | {len(pack.get('document_inventory') or pack.get('source_inventory') or [])} 条文件/来源记录 | 原始 SEC / IR / transcript 材料池，作为事实来源入口。 |",
        f"| 财务事实 | 已选择事实 {_fmt_int(extraction.get('selected_fact_count'))} 条；原始事实 {_fmt_int(extraction.get('raw_fact_count'))} 条 | 三张表、收入拆分、利润桥、现金流桥、资产负债表和公式指标。 |",
        f"| 官方证据 | {len(official_sources)} 条来源记录；{len(_as_list(official_pack.get('question_answers')))} 个问题回答；{len(_as_list(official_pack.get('decision_relevant_narratives')))} 条叙事 | 用官方文件回答第一层留下的问题，并登记业务模式/治理/风险叙事。 |",
        f"| 管理层沟通 | {len(management_sources)} 条来源记录；{len(_as_list(management_pack.get('qa_pressure_topics')))} 个问答压力点；{len(_as_list(management_pack.get('new_narratives')))} 条叙事 | 判断管理层如何解释、是否正面回答、是否给数字、是否留下新的可验证承诺。 |",
    ]
    coverage_table = _evidence_coverage_confidence_table(pack, official_pack)
    notes = [
        f"- 审阅状态：`{_status_label(audit_status)}`",
        f"- 生成时间：`{pack.get('generated_at') or '未知'}`；运行编号：`{pack.get('run_id') or '未知'}`",
        f"- 最新年度口径：`{latest.get('year') or '未知'}`；最新季度口径：`{latest_quarter.get('quarter') or latest_quarter.get('period_end') or '未知'}`",
        f"- 事实质量门：`{_status_label(quality_gate.get('status') or pack.get('financial_health_status'))}`",
        "- 本底稿不输出估值、目标价或买卖建议；价格相关判断进入独立估值 / 合理价格层。",
        "- 证据标签：`事实` 是结构化数字或官方披露；`官方解释` 是年报/季报/业绩稿里的解释；`管理层说法` 是电话会或管理层沟通；`我们的推断` 是证据裁判；`未知` 是当前来源集未回答。",
    ]
    return "\n".join(notes + [""] + rows + ["", "### 0.1 证据覆盖与置信度", "", coverage_table])


def _pipeline_artifact_note(
    layer1_question_pack: dict[str, Any],
    evidence_communication_pack: dict[str, Any],
    feedback_loop_pack: dict[str, Any],
) -> str:
    layer1_summary = layer1_question_pack.get("summary") or {}
    evidence_summary = evidence_communication_pack.get("summary") or {}
    feedback_summary = feedback_loop_pack.get("summary") or {}
    layer1_status = "已生成" if layer1_question_pack else "未生成"
    evidence_status = "已生成" if evidence_communication_pack else "未生成"
    feedback_status = "已生成" if feedback_loop_pack else "未生成"
    layer1_path = layer1_question_pack.get("source_financial_report_pack_path") or "见 run 目录"
    evidence_policy = (evidence_communication_pack.get("agent_run") or {}).get("source_policy") or "未生成"
    feedback_status_label = feedback_loop_pack.get("closed_loop_status") or "未生成"
    rows = [
        "### 0.2 Pipeline 中间产物",
        "",
        "| 中间产物 | 状态 | 在底稿中的作用 |",
        "| --- | --- | --- |",
        (
            f"| `layer1_question_pack.json` | {layer1_status}；标准问题 "
            f"{_fmt_int(layer1_summary.get('standard_question_count'))} 个，研究问题 "
            f"{_fmt_int(layer1_summary.get('research_question_count'))} 个 | "
            "把 Financial Extraction + Metrics 生成的硬数字转成问题队列、数字异常、红旗和 extractor backlog。 |"
        ),
        (
            f"| `evidence_communication_pack.json` | {evidence_status}；问题复核 "
            f"{_fmt_int(evidence_summary.get('question_answer_count'))} 个，主动发现 "
            f"{_fmt_int(evidence_summary.get('proactive_discovery_count'))} 个 | "
            "把官方文件解释、管理层沟通、分析师追问、仍未知和下一轮 extractor 需求归一化。 |"
        ),
        (
            f"| `feedback_loop_pack.json` | {feedback_status}；回第一层 "
            f"{_fmt_int(feedback_summary.get('layer1_requery_request_count'))} 个，回 extractor "
            f"{_fmt_int(feedback_summary.get('financial_extractor_request_count'))} 个 | "
            "把第二层新问题、未解项和数字缺口路由回 Financial Extractor、Metrics、Layer 1 或 Evidence，而不是只停留在底稿文字里。 |"
        ),
        "",
        (
            f"**怎么读：** 底稿优先消费这三个中间 pack；"
            f"`official_report_evidence_pack` 和 `management_communication_pack` 暂时保留为迁移兼容输入。"
            f"Layer1 来源路径：`{layer1_path}`；Evidence policy：`{evidence_policy}`；"
            f"闭环状态：`{feedback_status_label}`。"
        ),
    ]
    return "\n".join(rows)


def _evidence_coverage_confidence_table(pack: dict[str, Any], official_pack: dict[str, Any]) -> str:
    quality_gate = pack.get("fact_quality_gate") or {}
    material_scan = pack.get("material_event_scan") or {}
    annual_status = "已覆盖" if quality_gate.get("can_generate_full_report") else "部分覆盖"
    annual_impact = (
        "核心年度三表事实已抽齐，是长期主线和跨年指标的主锚点。"
        if quality_gate.get("can_generate_full_report")
        else "核心年度事实仍有缺口，完整报告结论需要降级。"
    )
    quarterly_rows = [row for row in _quarterly_rows(pack) if _has_quarter_signal(row)]
    quarterly_status = "已覆盖" if quarterly_rows else "未稳定覆盖"
    note_status = "部分覆盖"
    event_status = _status_label(material_scan.get("status") or "unknown")
    if material_scan.get("status") == "no_material_events_found":
        event_status = "未发现结构化重大事项"
    non_gaap_status = "已作为辅助抽取"
    if not (pack.get("financial_metrics") or []):
        non_gaap_status = "未稳定抽取"
    rows = [
        "| 证据层 | 当前状态 | 对结论的影响 |",
        "| --- | --- | --- |",
        f"| 年报 / 20-F / 10-K | {annual_status} | {annual_impact} |",
        f"| 季度 6-K / 10-Q | {quarterly_status} | 用于验证年度主线是否改变；季度信号不直接替代长期 thesis。 |",
        f"| 附注与结构化拆分 | {note_status} | 营运资本、受限现金、收入组件、经营利润桥、经营利润以下桥已进入底稿；债务期限、现金税、维护性/增长性资本开支仍影响置信度。 |",
        f"| 重大事项扫描 | {event_status} | 本次扫描只说明当前结构化规则未发现需晋级事项，不能等同于完整排除所有事件风险。 |",
        f"| non-GAAP | {non_gaap_status} | 只用于解释管理层口径和净利润桥，不替代 GAAP 经营利润、净利润和经营现金流。 |",
    ]
    official_flags = _as_list(official_pack.get("quality_flags"))
    if official_flags:
        rows.append(f"| 官方证据质量标记 | {len(official_flags)} 个 | 相关结论需要人工复核来源片段和标签。 |")
    rows.extend(
        [
            "",
            "**怎么读：** 年度三表和核心公式的置信度最高；季度、附注和 non-GAAP 负责解释变化；重大事项扫描是风险筛查入口，不是“没有风险”的证明。",
        ]
    )
    return "\n".join(rows)


def _core_question_answer_sheet(
    annual_rows: list[dict[str, Any]],
    quarterly_rows: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
    management_pack: dict[str, Any],
) -> str:
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    first_revenue_year = next((row for row in annual_rows if _num(row.get("revenue"))), {})
    usable_quarters = [row for row in quarterly_rows if _has_quarter_signal(row)]
    latest_quarter = usable_quarters[-1] if usable_quarters else {}
    profit_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    incremental_margin = _latest_annual_metric(metrics, "incremental_margin_v1") or {}
    source_growth = _latest_annual_metric(metrics, "source_of_growth_attribution_v1") or {}
    latest_interim_source = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    cash_conversion = _latest_annual_metric(metrics, "cash_conversion_ratio_v1") or {}
    balance_metric = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    cap_intensity = _latest_annual_metric(metrics, "capital_intensity_v1") or {}
    owner_earnings = _latest_annual_metric(metrics, "owner_earnings_v1") or {}
    incremental_roic = _latest_annual_metric(metrics, "incremental_roic_proxy_v1") or {}
    tax_metric = _latest_annual_metric(metrics, "tax_non_gaap_accounting_quality_v1") or {}
    non_gaap = (metrics.get("tax_non_gaap_accounting_quality_v1") or {}).get("latest_interim_non_gaap") or {}
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    sbc_metric = _latest_annual_metric(metrics, "share_based_compensation_burden_v1") or {}
    first_party_topic = _find_topic(_as_list(management_pack.get("qa_pressure_topics")), ["first-party", "自营品牌", "品牌"])

    horizon_years = None
    if first_revenue_year and latest and first_revenue_year.get("year") != latest.get("year"):
        horizon_years = int(latest.get("year")) - int(first_revenue_year.get("year"))
    long_cagr = _cagr(first_revenue_year.get("revenue"), latest.get("revenue"), horizon_years or 0)
    latest_quarter_yoy = latest_quarter.get("revenue_yoy")
    if latest_quarter_yoy is None and latest_quarter:
        latest_quarter_yoy = _computed_quarter_yoy(latest_quarter, _quarter_lookup(usable_quarters))

    rows = [
        {
            "question": "有没有增长？",
            "answer": "有增长，但增速已经从高速扩张切换到明显放缓后的增长。",
            "evidence": (
                f"收入从 {first_revenue_year.get('year') or '未知'} 年 {_money(first_revenue_year.get('revenue'))}"
                f" 增至 {latest.get('year') or '未知'} 年 {_money(latest.get('revenue'))}，长周期复合增速 {_pct(long_cagr)}；"
                f"最新年度收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}，"
                f"最新季度收入同比 {_pct(latest_quarter_yoy)}。"
            ),
            "confidence": "历史增长证据强；未来增长可持续性仍需验证",
            "follow": "Q1 / Q6",
        },
        {
            "question": "增长来自哪里？",
            "answer": "增长来源已经具备公司特征：收入结构从在线营销主导，转向在线营销与交易服务接近五五开；最新季度交易服务占比更高。",
            "evidence": (
                f"{_revenue_component_sentence(latest, prefix=str(latest.get('year') or '最新年度') + ' 年')} "
                f"{_quarter_revenue_component_sentence(latest_quarter, latest_interim_source)} "
                f"年度收入组件覆盖率 {_pct(source_growth.get('value'))}。"
            ),
            "confidence": "披露收入结构的证据强；GMV / 抽佣率 / 用户驱动拆分不足",
            "follow": "Q6 / Q7",
        },
        {
            "question": "经济引擎是什么？",
            "answer": "当前披露下，PDD 的经济引擎主要是商家侧平台货币化：在线营销服务及其他 + 交易服务，而不是传统自营零售收入。",
            "evidence": (
                f"2025 年在线营销服务及其他占收入 {_pct(_safe_div(latest.get('online_marketing_services_revenue'), latest.get('revenue')))}，"
                f"交易服务占收入 {_pct(_safe_div(latest.get('transaction_services_revenue'), latest.get('revenue')))}；"
                f"毛利率 {_pct(_safe_div(latest.get('gross_profit'), latest.get('revenue')))}，经营利润率 {_pct(_safe_div(latest.get('operating_income'), latest.get('revenue')))}。"
            ),
            "confidence": "披露收入模式的证据强；抽佣率 / GMV / 商家 cohort 经济性不足",
            "follow": "Q6",
        },
        {
            "question": "增长有没有兑现为利润？",
            "answer": "最新年度没有充分兑现。收入仍增长，但经营利润和净利润回落，新增收入的边际经营利润为负。",
            "evidence": (
                f"收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}；"
                f"经营利润同比 {_pct(_growth(latest.get('operating_income'), prior.get('operating_income')))}；"
                f"净利润同比 {_pct(_growth(latest.get('net_income'), prior.get('net_income')))}；"
                f"增量经营利润率 {_pct(profit_bridge.get('incremental_operating_margin'))}。"
            ),
            "confidence": "数字诊断置信度高；原因解释仍是部分回答",
            "follow": "Q1 / Q2",
        },
        {
            "question": "边际经济性是否优于存量业务？",
            "answer": "最新年度边际经济性弱于存量业务。存量经营利润率仍高，但新增收入对应的经营利润和自由现金流增量为负。",
            "evidence": (
                f"2025 年经营利润率 {_pct(_safe_div(latest.get('operating_income'), latest.get('revenue')))}，"
                f"增量经营利润率 {_pct(incremental_margin.get('incremental_operating_margin') or profit_bridge.get('incremental_operating_margin'))}；"
                f"增量自由现金流率 {_pct(incremental_margin.get('incremental_free_cash_flow_margin'))}。"
            ),
            "confidence": "最新年度边际数学证据强；主动投入还是结构压力仍需验证",
            "follow": "Q1 / Q2",
        },
        {
            "question": "利润有没有变成现金？",
            "answer": "会计利润有经营现金流支撑，但现金质量必须拆营运资本桥，不能只看经营现金流 / 净利润。",
            "evidence": (
                f"经营现金流 {_money(latest.get('operating_cash_flow'))}，净利润 {_money(latest.get('net_income'))}，"
                f"经营现金流 / 净利润 {_ratio_x(cash_conversion.get('value'))}；自由现金流近似 {_money(latest.get('free_cash_flow'))}；"
                f"营运资本现金顺风/收入 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}。"
            ),
            "confidence": "中高；营运资本依赖仍需持续监控",
            "follow": "Q3",
        },
        {
            "question": "现金流质量是否可持续？",
            "answer": "现金流质量偏强，但可持续性要看商家资金沉淀、应付和保证金是否继续稳定，而不是只看单年经营现金流。",
            "evidence": (
                f"自由现金流 / 经营现金流 {_pct(cap_intensity.get('free_cash_flow_to_operating_cash_flow'))}，"
                f"所有者收益近似值 {_money(owner_earnings.get('value'))}；"
                f"经营负债净增加 {_money(working_capital.get('cash_source_liability_delta'))}，"
                f"营运资本现金顺风/收入 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}。"
            ),
            "confidence": "中等；持续造血能力存在，但平台浮存和反转风险要跟踪",
            "follow": "Q3",
        },
        {
            "question": "资产负债表能不能支撑投入期？",
            "answer": "能支撑投入期，但账面现金不能全部当作自由现金或股东可用现金。",
            "evidence": (
                f"广义现金与短投 {_money(_broad_cash(latest))}，流动比率 {_ratio_x(balance_metric.get('current_ratio'))}，"
                f"负债/资产 {_pct(balance_metric.get('liabilities_to_assets'))}；"
                f"受限现金/现金 {_pct(balance_metric.get('restricted_cash_to_cash'))}。"
            ),
            "confidence": "资产负债表强度证据高；股东可用现金仍需保守处理",
            "follow": "Q4",
        },
        {
            "question": "再投资是否有效？",
            "answer": "目前还不能证明。公司有充足现金和明确投入方向，但 2025 年新增资产和新增收入没有同步带来新增经营利润。",
            "evidence": (
                f"2025 年收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}，总资产同比 {_pct(_growth(latest.get('total_assets'), prior.get('total_assets')))}；"
                f"资本开支 / 收入 {_pct(cap_intensity.get('capex_to_revenue'))}；"
                f"增量 ROIC 近似值 {_pct(incremental_roic.get('value'))}；"
                "管理层披露自营品牌业务初始注资 RMB 15B、三年 RMB 100B 投入。"
            ),
            "confidence": "中低；投入方向可见，已实现回报尚不可见",
            "follow": "Q2 / Q5",
        },
        {
            "question": "商业模式是否在变化？",
            "answer": "有变化信号，但还没有完整财务闭环。交易服务占比接近一半，管理层又推出自营品牌和供应链投入叙事。",
            "evidence": (
                f"交易服务收入占最新年度收入 {_pct(_safe_div(latest.get('transaction_services_revenue'), latest.get('revenue')))}；"
                f"资本开支 / 收入 {_pct(cap_intensity.get('capex_to_revenue'))}，说明变化目前未主要体现为传统固定资产扩张。"
                f"{' 管理层回答：' + first_party_topic.get('management_response_read') if first_party_topic.get('management_response_read') else ''}"
            ),
            "confidence": "中等；战略信号清楚，财务足迹仍不完整",
            "follow": "Q5 / Q7",
        },
        {
            "question": "风险是否已经进入财务结果？",
            "answer": "部分压力已经进入利润率和经营利润以下项目，但监管、法律、Temu 地区风险和竞争压力尚不能被精确量化到财务结果。",
            "evidence": (
                f"成本率从 {_pct(_cost_ratio(prior))} 升至 {_pct(_cost_ratio(latest))}，"
                f"经营利润率从 {_pct(_safe_div(prior.get('operating_income'), prior.get('revenue')))} 降至 {_pct(_safe_div(latest.get('operating_income'), latest.get('revenue')))}；"
                f"最新季度经营利润以下净影响变化 {_money(below_bridge.get('below_operating_delta'))}。"
            ),
            "confidence": "财务压力证据中等；归因到具体外部风险的证据较弱",
            "follow": "Q2 / Q7 / Q8",
        },
        {
            "question": "净利润、税项和 non-GAAP 有没有遮蔽经营质量？",
            "answer": "non-GAAP 目前像辅助项，不像主矛盾；但净利润需要拆经营利润以下项目。",
            "evidence": (
                f"2025 年投资收益/税前利润 {_pct(tax_metric.get('investment_income_to_pretax'))}，"
                f"有效税率 {_pct(tax_metric.get('effective_tax_rate'))}；"
                f"最新季度经营利润变化 {_money(below_bridge.get('operating_income_delta'))}，"
                f"净利润变化 {_money(below_bridge.get('net_income_delta'))}，"
                f"non-GAAP 净利润 uplift {_pct(non_gaap.get('non_gaap_net_income_uplift'))}。"
            ),
            "confidence": "中等；经营利润以下桥应成为季度固定检查项",
            "follow": "Q8",
        },
        {
            "question": "股东每股价值有没有明显被稀释？",
            "answer": "SBC 和稀释暂时不像主线风险，但还不能证明现金最终会转化为每股股东回报。",
            "evidence": (
                f"SBC / 收入 {_pct(sbc_metric.get('sbc_to_revenue'))}，SBC / 经营现金流 {_pct(sbc_metric.get('sbc_to_operating_cash_flow'))}；"
                f"稀释股数同比 {_pct(sbc_metric.get('diluted_shares_yoy'))}。"
            ),
            "confidence": "中等；资本回报和股数桥仍需更完整的股东经济性分析",
            "follow": "Q9",
        },
        {
            "question": "资本配置是否对股东友好？",
            "answer": "现金储备很强，但当前底稿只能证明公司有能力投入，不能证明资本配置已经直接回馈股东或提升每股价值。",
            "evidence": (
                f"广义现金与短投 {_money(_broad_cash(latest))}；"
                f"自由现金流近似 {_money(latest.get('free_cash_flow'))}；"
                "管理层沟通重点是供应链、商家支持和自营品牌，而不是回购、分红或明确股东回报框架。"
            ),
            "confidence": "财务能力证据中等；股东回报政策证据不足",
            "follow": "Q4 / Q9",
        },
    ]

    table = [
        "| 标准问题 | 当前回答 | 证据锚点 | 置信度 / 边界 | 关联研究问题 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        table.append(
            "| {question} | {answer} | {evidence} | {confidence} | {follow} |".format(
                question=_md_cell(_zh_text(row["question"])),
                answer=_md_cell(_zh_text(row["answer"])),
                evidence=_md_cell(_zh_text(row["evidence"])),
                confidence=_md_cell(_zh_text(row["confidence"])),
                follow=_md_cell(_linked_research_questions(row["follow"])),
            )
        )

    readout = [
        "### 1.1 标准问题回答",
        "",
        *table,
        "",
        "### 1.2 读法",
        "",
        "- 已经可以回答的主线：PDD 仍在增长，收入结构正在从在线营销主导转向交易服务占比更高，资产负债表仍然很强，经营现金流仍覆盖净利润。",
        "- 还不能直接回答的主线：新增收入为什么没有带来新增经营利润、自营品牌是否让平台模式变重、Temu / 全球业务的单独经济性、现金中有多少真正可由股东使用、再投资回报和资本配置是否足够股东友好。",
        "- 因此，后面的研究问题索引不是替代标准问题，而是在标准问题回答之后，把最需要追问的矛盾和证据缺口单独展开。",
    ]
    return "\n".join(readout)


def _linked_research_questions(value: Any) -> str:
    labels = {
        "Q1": "Q1 增量利润",
        "Q2": "Q2 利润率压力",
        "Q3": "Q3 现金流质量",
        "Q4": "Q4 现金可用性",
        "Q5": "Q5 自营品牌",
        "Q6": "Q6 收入结构",
        "Q7": "Q7 Temu / 全球业务",
        "Q8": "Q8 净利润质量",
        "Q9": "Q9 股东回报",
    }
    parts = [part.strip() for part in str(value or "").split("/") if part.strip()]
    return "；".join(labels.get(part, part) for part in parts) or "未关联"


def _build_question_dockets(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    annual_rows = _annual_rows(pack)
    quarterly_rows = _quarterly_rows(pack)
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}
    metrics = _metrics_by_id(pack)
    official_answers = {answer.get("question_id"): answer for answer in _as_list(official_pack.get("question_answers"))}
    topics = _as_list(management_pack.get("qa_pressure_topics"))
    reviews = _as_list(management_pack.get("layer_issue_reviews"))
    gaps = {gap.get("gap_id"): gap for gap in _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry"))}

    growth = official_answers.get("growth_quality") or {}
    profit = official_answers.get("profitability_with_scale") or {}
    cash = official_answers.get("cash_profit_quality") or {}
    capital = official_answers.get("capital_needed_for_growth") or {}
    balance = official_answers.get("balance_sheet_resilience") or {}
    sbc = official_answers.get("sbc_and_per_share_quality") or {}
    accounting = official_answers.get("tax_non_gaap_accounting_quality") or {}
    profit_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    source_growth = _latest_annual_metric(metrics, "source_of_growth_attribution_v1") or {}
    latest_interim_source = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    cash_conversion = _latest_annual_metric(metrics, "cash_conversion_ratio_v1") or {}
    balance_metric = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    cap_intensity = _latest_annual_metric(metrics, "capital_intensity_v1") or {}
    tax_metric = _latest_annual_metric(metrics, "tax_non_gaap_accounting_quality_v1") or {}
    non_gaap = (metrics.get("tax_non_gaap_accounting_quality_v1") or {}).get("latest_interim_non_gaap") or {}

    first_party_topic = _find_topic(topics, ["first-party", "自营品牌", "品牌"])
    global_topic = _find_topic(topics, ["global", "用户增长", "留存"])
    investment_topic = _find_topic(topics, ["RMB 100B", "100B", "投入"])
    online_marketing_topic = _find_topic(topics, ["online marketing", "营销", "广告"])
    margin_topic = _find_topic(topics, ["利润率", "margin", "cost-to-profit"])
    cash_review = _find_review(reviews, ["现金", "cash", "RMB 436.1B", "100B"])
    margin_review = _find_review(reviews, ["利润率", "投资周期", "供应链"])
    first_party_review = _find_review(reviews, ["自营", "first-party", "品牌"])

    dockets = [
        {
            "id": "Q1",
            "question": "新增收入为什么没有带来新增经营利润？",
            "why": "这是当前最重要的基本面矛盾：公司仍增长，但边际利润兑现为负，会直接影响对增长质量、竞争压力和投入回报的判断。",
            "status": "partial",
            "current_answer": "收入仍增长，但新增收入没有转化为新增经营利润；官方文件能解释收入结构，不能完整解释利润背离。",
            "layer1": [
                f"2025 年收入 {_money(latest.get('revenue'))}，同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}。",
                f"2025 年经营利润 {_money(latest.get('operating_income'))}，同比 {_pct(_growth(latest.get('operating_income'), prior.get('operating_income')))}；净利润同比 {_pct(_growth(latest.get('net_income'), prior.get('net_income')))}。",
                f"收入增加 {_money(profit_bridge.get('revenue_delta'))}，经营利润减少 {_money(profit_bridge.get('operating_income_delta'))}，增量经营利润率 {_pct(profit_bridge.get('incremental_operating_margin'))}。",
            ],
            "official": _answer_summary(growth),
            "management": _topic_summary(online_marketing_topic, fallback="管理层对在线营销服务放缓没有直接给出 GMV / take-rate / 广告 ROI，而是把增长叙事转向供应链和远程物流创造需求。"),
            "judge": _rendered(growth, "our_judgment") or "官方文件和管理层沟通都能说明增长来源和战略方向，但还不能证明新增收入为何没有转成新增经营利润。",
            "unknown": _unique_list((growth.get("still_unknown") or []) + (online_marketing_topic.get("follow_up_needed") or [])),
            "next_route": [
                "继续拆收入组件 YoY / QoQ，特别是 transaction services 与 online marketing 的贡献。",
                "把经营利润桥分解到 cost of revenue、S&M、R&D、G&A 和商家支持/履约/支付处理等细项。",
                "寻找商家 cohort、单商家收入、GMV、take-rate 或广告 ROI。官方文件没有披露时，明确登记为 disclosure gap。",
            ],
            "source_trace": _source_trace(growth, online_marketing_topic),
        },
        {
            "id": "Q2",
            "question": "利润率压力是主动投入，还是结构性竞争压力？",
            "why": "如果是主动投入，未来应看到收入质量或利润率修复；如果是结构性竞争压力，估值框架和长期利润率假设都要下调。",
            "status": "partial",
            "current_answer": "成本率和费用率同时上升，与供应链、履约、支付处理、商家支持等投入方向一致，但官方文件未量化每个驱动。",
            "layer1": [
                f"2025 年毛利率 {_pct(latest.get('gross_profit') and _safe_div(latest.get('gross_profit'), latest.get('revenue')))}，经营利润率 {_pct(_safe_div(latest.get('operating_income'), latest.get('revenue')))}，净利率 {_pct(_safe_div(latest.get('net_income'), latest.get('revenue')))}。",
                f"成本率从 {_pct(_cost_ratio(prior))} 升至 {_pct(_cost_ratio(latest))}。",
                f"经营费用率从 {_pct(_opex_ratio(prior))} 升至 {_pct(_opex_ratio(latest))}。",
            ],
            "official": _answer_summary(profit),
            "management": _topic_summary(margin_topic, review=margin_review, fallback="财务负责人将短期波动解释为季节性和投资周期，并强调长期内在价值，但没有给出稳定利润率水平或费用率拆分。"),
            "judge": _rendered(profit, "our_judgment") or "投入叙事和数字方向一致，但不是完整证明；需要后续费用率、履约成本和利润率修复来验证。",
            "unknown": _unique_list((profit.get("still_unknown") or []) + (margin_topic.get("follow_up_needed") or []) + (margin_review.get("still_unknown") or [])),
            "next_route": [
                "逐期追踪 cost of revenue / revenue、S&M / revenue、R&D / revenue、G&A / revenue。",
                "如果官方只披露履约、支付处理、平台运营、商家支持的叙事而不披露金额，应保留为“部分回答”，而不是强行归因。",
                "电话会继续追问投资周期长度、利润率底线和供应链投入何时开始贡献利润。",
            ],
            "source_trace": _source_trace(profit, margin_topic, margin_review),
        },
        {
            "id": "Q3",
            "question": "经营现金流质量是否依赖商家资金沉淀 / 经营负债扩张？",
            "why": "平台型公司经营现金流很强可能是商业模式优势，也可能有部分来自应付商家款项、保证金和应计费用的时间差；这决定现金流质量和可持续性。",
            "status": "partial",
            "current_answer": "经营现金流覆盖净利润，但营运资本现金顺风较明显；现金流不是空泛的好，需要拆桥。",
            "layer1": [
                f"2025 年经营现金流 {_money(latest.get('operating_cash_flow'))}，净利润 {_money(latest.get('net_income'))}，经营现金流 / 净利润 {_ratio_x(cash_conversion.get('value'))}。",
                f"营运资本现金顺风/收入 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}。",
                _working_capital_component_sentence(working_capital),
            ],
            "official": _answer_summary(cash),
            "management": _review_summary(cash_review, fallback="电话会披露季度现金和短投余额，但没有系统解释经营现金流的营运资本桥。"),
            "judge": _rendered(cash, "our_judgment") or "现金流强，但有经营负债贡献；需要把 float 视为平台特征，同时监控反转风险。",
            "unknown": _unique_list((cash.get("still_unknown") or []) + (cash_review.get("still_unknown") or [])),
            "next_route": [
                "补全 receivables、prepayments、inventory、payables、merchant deposits、deferred revenue 的期初期末和现金流影响。",
                "区分现金流来自利润、非现金费用，还是来自商家/供应商/客户相关负债扩张。",
                "观察 merchant payable 和 deposits 是否随收入增速放缓而反转。",
            ],
            "source_trace": _source_trace(cash, cash_review),
        },
        {
            "id": "Q4",
            "question": "账面现金很多，但多少是真正股东可用？",
            "why": "PDD 的账面现金和短投很厚，但受限现金、VIE、跨境资金转移和未来三年投入会影响股东可用现金的读法。",
            "status": "partial",
            "current_answer": "资产负债表能支撑投入期，但受限现金比例和结构限制要求保守处理。",
            "layer1": [
                f"2025 年现金 {_money(latest.get('cash'))}，受限现金 {_money(latest.get('restricted_cash'))}，短期投资 {_money(latest.get('short_term_investments'))}，广义现金与短投 {_money(_broad_cash(latest))}。",
                f"流动比率 {_ratio_x(balance_metric.get('current_ratio'))}，负债/资产 {_pct(balance_metric.get('liabilities_to_assets'))}，受限现金/现金 {_pct(balance_metric.get('restricted_cash_to_cash'))}。",
                f"电话会披露 2026Q1 末现金、现金等价物和短期投资约 RMB 436.1B；同时管理层提到三年 RMB 100B 投入计划。",
            ],
            "official": _answer_summary(balance),
            "management": _review_summary(cash_review, fallback="管理层披露现金和短投余额以及三年投入计划，但没有给出股东可用现金或股东回报框架。"),
            "judge": _rendered(balance, "our_judgment") or "安全垫强，但不能把账面现金直接等同于自由现金或可回购资金。",
            "unknown": _unique_list((balance.get("still_unknown") or []) + (cash_review.get("still_unknown") or [])),
            "next_route": [
                "拆现金、受限现金、短投、长期投资的币种、地区、期限和限制。",
                "回到 VIE / 资金转移 / 受限现金附注，确认母公司可动用现金。",
                "把三年 RMB 100B 投入计划加入现金用途监控。",
            ],
            "source_trace": _source_trace(balance, cash_review),
        },
        {
            "id": "Q5",
            "question": "自营品牌是否会让平台模式变重？",
            "why": "这是 PDD 当前最重要的业务模式变化信号：如果承担库存、质量控制、履约和品牌风险，平台的资本强度、利润率和现金流模式都可能改变。",
            "status": "partial",
            "current_answer": "管理层给出了 RMB 15B 初始注资和三年 RMB 100B 投入，但官方文件还没有形成单独财务闭环。",
            "layer1": [
                f"2025 年资本开支 / 收入 {_pct(cap_intensity.get('capex_to_revenue'))}，说明当前投入尚未主要体现为传统固定资产扩张。",
                f"自营品牌披露缺口：{_join((gaps.get('first_party_brand_unit_economics') or {}).get('missing_metrics'))}。",
                "如果投入主要走费用、履约、补贴或营运资本，第一层只看 capex 会低估模式变重的风险。",
            ],
            "official": _narrative_summary(official_pack, ["自营", "first-party", "品牌"]),
            "management": _topic_summary(first_party_topic, review=first_party_review, fallback="管理层把自营品牌放在三年战略核心位置，并表示平台将承担更大责任和风险。"),
            "judge": "这是一个已出现但尚未被财务报表量化的业务模式变化。底稿应把它列为核心跟踪项，而不是把它当成已经兑现的增长质量证据。",
            "unknown": _unique_list((first_party_topic.get("follow_up_needed") or []) + (first_party_review.get("still_unknown") or []) + ((gaps.get("first_party_brand_unit_economics") or {}).get("missing_metrics") or [])),
            "next_route": [
                "检查下一期 6-K / 20-F 是否出现自营品牌收入、存货、采购承诺、仓库租赁或单独损益。",
                "电话会追问库存风险、毛利率、履约成本、现金支付节奏、投资回报和投入回收期。",
                "如果仍未披露，HTML 报告应明确写作“重大叙事，财务闭环未披露”。",
            ],
            "source_trace": _source_trace(first_party_topic, first_party_review),
        },
        {
            "id": "Q6",
            "question": "交易服务占比提高，到底是更强货币化，还是更高履约/治理成本？",
            "why": "PDD 已不只是广告变现故事。交易服务收入占比变化影响增长来源、成本结构、平台控制深度和监管/履约压力。",
            "status": "partial",
            "current_answer": "年度收入结构接近五五开，最新季度交易服务成为最大组件；但缺少 take-rate、GMV、订单和服务范围拆分。",
            "layer1": [
                _revenue_component_sentence(latest, prefix="2025 年"),
                _quarter_revenue_component_sentence(latest_quarter, latest_interim_source),
                f"年度收入归因覆盖率 {_pct(source_growth.get('value'))}；最新季度覆盖率 {_pct(latest_interim_source.get('value'))}。",
            ],
            "official": _narrative_summary(official_pack, ["交易服务", "收入结构", "KPI"]),
            "management": _topic_summary(online_marketing_topic, fallback="管理层没有直接量化 GMV、广告 take-rate 或商家广告 ROI，回答转向供应链和物流创造需求。"),
            "judge": "收入结构变化是明确事实，但它既可能代表更深交易服务和货币化，也可能代表更高履约/治理/商家支持成本。必须和利润桥联读。",
            "unknown": _unique_list((online_marketing_topic.get("follow_up_needed") or []) + ((gaps.get("user_and_transaction_kpis") or {}).get("missing_metrics") or [])),
            "next_route": [
                "持续抽取 online marketing services 与 transaction services 的 YoY / QoQ。",
                "寻找 GMV、订单、活跃用户/买家、商家数、抽佣率、广告变现率；缺失时标记为披露缺口。",
                "把交易服务占比变化和 cost of revenue / fulfillment / payment processing 变化放在同一张图里。",
            ],
            "source_trace": _source_trace(growth, online_marketing_topic),
        },
        {
            "id": "Q7",
            "question": "Temu / 全球业务是可验证增长引擎，还是仍只是战略叙事？",
            "why": "Temu 可能解释交易服务、履约、监管和利润率变化，但没有独立财务数据时，不能把它写成已验证的价值来源。",
            "status": "unknown_to_partial",
            "current_answer": "官方文件和电话会都提到全球业务和供应链机会，但没有单独收入、利润、GMV、履约成本或地区经济性。",
            "layer1": [
                f"Temu / 全球业务披露缺口：{_join((gaps.get('temu_standalone_economics') or {}).get('missing_metrics'))}。",
                "第一层无法把全球业务单独拆入增长、利润率或现金流模型。",
                "最新季度管理层把全球业务后续重点绑定到供应链和自营品牌，而不是单独用户 KPI。",
            ],
            "official": _narrative_summary(official_pack, ["Temu", "全球", "global"]),
            "management": _topic_summary(global_topic, fallback="管理层把全球业务的长期竞争力归因于供应链能力，但没有披露用户留存、获客成本或地区利润率。"),
            "judge": "这仍是重要战略叙事和风险变量，不是可独立建模的财务分部。",
            "unknown": _unique_list((global_topic.get("follow_up_needed") or []) + ((gaps.get("temu_standalone_economics") or {}).get("missing_metrics") or [])),
            "next_route": [
                "继续搜索 20-F / 6-K / earnings release 是否出现 Temu 单独收入、成本、GMV、订单、履约或监管成本。",
                "如果官方仍不披露，第三层只评价管理层说法的具体性和可验证性，不把它转成事实。",
                "后续可用外部替代数据验证，但那应进入单独的替代数据层。",
            ],
            "source_trace": _source_trace(global_topic),
        },
        {
            "id": "Q8",
            "question": "净利润和 non-GAAP 是否掩盖了经营质量？",
            "why": "PDD 现金和投资资产多，投资收益、其他收益/损失、税项和 non-GAAP 调整都可能让净利润偏离经营表现。",
            "status": "partial",
            "current_answer": "当前 non-GAAP 调整幅度不算主矛盾，但净利润需要拆经营利润以下项目。",
            "layer1": [
                f"2025 年投资收益/税前利润 {_pct(tax_metric.get('investment_income_to_pretax'))}，有效税率 {_pct(tax_metric.get('effective_tax_rate'))}。",
                f"2026Q1 non-GAAP 净利润 uplift {_pct(non_gaap.get('non_gaap_net_income_uplift'))}，调整项/收入 {_pct(non_gaap.get('non_gaap_adjustment_burden_to_revenue'))}。",
                f"2026Q1 经营利润变化 {_money(below_bridge.get('operating_income_delta'))}，净利润变化 {_money(below_bridge.get('net_income_delta'))}，经营利润以下净影响变化 {_money(below_bridge.get('below_operating_delta'))}。",
                _below_operating_bridge_readout(below_bridge),
            ],
            "official": _answer_summary(accounting),
            "management": _topic_summary(margin_topic, fallback="管理层强调长期投入和投资周期，但没有详细拆净利润下滑中的其他收益/损失或投资收益变化。"),
            "judge": _rendered(accounting, "our_judgment") or "读盈利质量时应优先看经营利润、经营现金流和经营利润以下桥，而不是只看最终净利润或 non-GAAP。",
            "unknown": _unique_list((accounting.get("still_unknown") or []) + (margin_topic.get("follow_up_needed") or [])),
            "next_route": [
                "每季度固定拆 operating income -> pretax -> net income bridge。",
                "保留 non-GAAP 调节项历史，尤其是 SBC、fair value、amortization、tax effect。",
                "确认投资收益/损失和其他收益/损失是否重复出现，避免把非经营收益当成经营质量。",
            ],
            "source_trace": _source_trace(accounting, margin_topic),
        },
        {
            "id": "Q9",
            "question": "股权激励、治理和每股价值有没有隐藏风险？",
            "why": "现金牛型平台最终要落到每股价值；SBC、稀释、回购、控制权和股权计划期限都会影响少数股东。",
            "status": "partial",
            "current_answer": "SBC 和稀释暂未成为主线风险，但仍缺少完整 share-count / repurchase / ADS bridge。",
            "layer1": [
                _rendered(sbc, "filing_facts") or "SBC / 收入、SBC / 经营现金流和摊薄股数同比已被第一层抽取。",
                "治理材料已被第二层纳入：AGM / proxy / 股权计划相关 6-K 可作为治理和稀释的来源路径。",
            ],
            "official": _answer_summary(sbc) + "\n" + _narrative_summary(official_pack, ["治理", "股权", "AGM", "Share Plan"]),
            "management": "电话会没有把股东回报、回购或稀释作为重点沟通事项；这本身是一个资本配置层面的沉默信号。",
            "judge": _rendered(sbc, "our_judgment") or "当前不是主要反证，但还不能证明每股价值创造。",
            "unknown": _unique_list(sbc.get("still_unknown") or []),
            "next_route": [
                "在 proxy / AGM / equity plan 中继续追踪董事投票、控制权、SBC 计划、RSU/options 和 ADS/common share ratio。",
                "补股数桥：基本 / 摊薄股数、SBC 发行、回购抵消、ADS 比例。",
                "如果现金很多但资本回报缺位，HTML 报告应把它作为资本配置问题。",
            ],
            "source_trace": _source_trace(sbc),
        },
    ]
    return dockets


def _question_map(dockets: list[dict[str, Any]]) -> str:
    lines = [
        "| 编号 | 研究问题 | 当前回答 | 状态 | 主要未解证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for docket in dockets:
        lines.append(
            "| {id} | {question} | {answer} | {status} | {unknown} |".format(
                id=_md_cell(docket.get("id")),
                question=_md_cell(_zh_text(docket.get("question"))),
                answer=_md_cell(_zh_text(docket.get("current_answer"))),
                status=_md_cell(_status_label(docket.get("status"))),
                unknown=_md_cell(_join((docket.get("unknown") or [])[:4])),
            )
        )
    return "\n".join(lines)


def _render_question_dockets(dockets: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for docket in dockets:
        lines.extend(
            [
                f"### {docket.get('id')}. {_zh_text(docket.get('question'))}",
                "",
                f"**为什么重要：** {_zh_text(docket.get('why'))}",
                "",
                f"**状态：** `{_status_label(docket.get('status'))}`",
                "",
                f"**当前回答：** {_zh_text(docket.get('current_answer'))}",
                "",
                "**第一层数字触发点：**",
                *_bullet_lines(docket.get("layer1")),
                "",
                "**第二层官方文件证据：**",
                *_paragraph_or_bullets(docket.get("official")),
                "",
                "**第三层管理层沟通：**",
                *_paragraph_or_bullets(docket.get("management")),
                "",
                f"**证据裁判：** {_zh_text(docket.get('judge') or '未形成裁判')}",
                "",
                "**仍未解决：**",
                *_bullet_lines(docket.get("unknown") or ["未披露"]),
                "",
                "**下一步查证路径：**",
                *_bullet_lines(docket.get("next_route")),
                "",
                f"**来源追踪：** {docket.get('source_trace') or '见结构化证据包'}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _long_horizon_history(rows: list[dict[str, Any]], metrics: dict[str, dict[str, Any]]) -> str:
    if not rows:
        return "_没有可用的年度财务历史。_"
    first = rows[0]
    latest = rows[-1]
    revenue_cagr = _cagr(first.get("revenue"), latest.get("revenue"), int(latest.get("year")) - int(first.get("year"))) if first.get("year") and latest.get("year") else None
    lines = [
        "### 4.1 可抽取最长年度历史",
        "",
        f"- 可抽取年度：{rows[0].get('year')} - {rows[-1].get('year')}，共 {len(rows)} 年。",
        f"- 期间收入从 {_money(first.get('revenue'))} 增至 {_money(latest.get('revenue'))}，长周期复合增速约 {_pct(revenue_cagr)}。",
        f"- 经营利润率从 {_pct(_safe_div(first.get('operating_income'), first.get('revenue')))} 变为 {_pct(_safe_div(latest.get('operating_income'), latest.get('revenue')))}；中间经历亏损增长、利润释放、再投入三个阶段。",
        "",
        "| 年度 | 收入 | 收入同比 | 毛利率 | 经营利润率 | 净利率 | 经营现金流率 | 自由现金流率 | 广义现金与短投 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    prior: dict[str, Any] = {}
    for row in rows:
        lines.append(
            "| {year} | {revenue} | {growth} | {gm} | {opm} | {nm} | {cfom} | {fcfm} | {cash} |".format(
                year=row.get("year"),
                revenue=_money(row.get("revenue")),
                growth=_pct(_growth(row.get("revenue"), prior.get("revenue"))),
                gm=_pct(_safe_div(row.get("gross_profit"), row.get("revenue"))),
                opm=_pct(_safe_div(row.get("operating_income"), row.get("revenue"))),
                nm=_pct(_safe_div(row.get("net_income"), row.get("revenue"))),
                cfom=_pct(_safe_div(row.get("operating_cash_flow"), row.get("revenue"))),
                fcfm=_pct(_safe_div(row.get("free_cash_flow"), row.get("revenue"))),
                cash=_money(_broad_cash(row)),
            )
        )
        prior = row
    lines.extend(
        [
            "",
            "### 4.2 阶段变化读法",
            "",
            "- **2017-2020：亏损增长期。** 收入高速扩张，但经营利润率为负；经营现金流和自由现金流受平台营运资本结构影响，不能简单按传统亏损企业读取。",
            "- **2021-2024：利润释放期。** 经营利润率从正数低位抬升至 2024 年约 27.5%，净利润和经营现金流同步放大，是上一轮高增长高利润叙事的基础。",
            "- **2025-2026Q1：再投入 / 再平衡期。** 收入继续增长，但年度经营利润和净利润回落；管理层把叙事切到供应链、商家支持、平台治理和自营品牌。",
            "",
            "### 4.3 长周期收入结构",
            "",
            _revenue_mix_history(rows, metrics),
        ]
    )
    return "\n".join(lines)


def _revenue_mix_history(rows: list[dict[str, Any]], metrics: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| 年度 | 在线营销服务及其他 | 占收入 | 交易服务 | 占收入 | 组件覆盖率 | 最大组件 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    attribution_by_year = {
        int(result.get("year")): result
        for result in (metrics.get("source_of_growth_attribution_v1") or {}).get("annual_results") or []
        if result.get("year") is not None
    }
    for row in rows:
        year = int(row.get("year") or 0)
        revenue = row.get("revenue")
        result = attribution_by_year.get(year) or {}
        top = result.get("top_component") or {}
        lines.append(
            "| {year} | {online} | {online_share} | {txn} | {txn_share} | {coverage} | {top} |".format(
                year=row.get("year"),
                online=_money(row.get("online_marketing_services_revenue")),
                online_share=_pct(_safe_div(row.get("online_marketing_services_revenue"), revenue)),
                txn=_money(row.get("transaction_services_revenue")),
                txn_share=_pct(_safe_div(row.get("transaction_services_revenue"), revenue)),
                coverage=_pct(result.get("value")),
                top=_metric_label(top.get("metric")) if top else "未披露",
            )
        )
    return "\n".join(lines)


def _detailed_numeric_evidence(
    annual_rows: list[dict[str, Any]],
    quarterly_rows: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
) -> str:
    annual_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    below_bridge = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    lines = [
        "### 5.1 年度三表主干",
        "",
        "| 年度 | 收入 | 毛利 | 经营利润 | 净利润 | 经营现金流 | 自由现金流近似 | 资本开支 | 总资产 | 总负债 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in annual_rows:
        lines.append(
            "| {year} | {revenue} | {gross} | {op} | {net} | {cfo} | {fcf} | {capex} | {assets} | {liabilities} |".format(
                year=row.get("year"),
                revenue=_money(row.get("revenue")),
                gross=_money(row.get("gross_profit")),
                op=_money(row.get("operating_income")),
                net=_money(row.get("net_income")),
                cfo=_money(row.get("operating_cash_flow")),
                fcf=_money(row.get("free_cash_flow")),
                capex=_money(row.get("capex")),
                assets=_money(row.get("total_assets")),
                liabilities=_money(row.get("total_liabilities")),
            )
        )
    lines.extend(["", f"**怎么读：** {_annual_spine_readout(annual_rows)}"])
    lines.extend(
        [
            "",
            "### 5.2 完整季度趋势",
            "",
            "只展示已抽取到收入、经营利润、净利润或收入组件的季度；全空季度不进入主表，避免把披露缺口伪装成数据覆盖。",
            "",
            "| 季度 | 收入 | 收入同比 | 经营利润 | 经营利润率 | 净利润 | 净利率 | 交易服务占比 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    usable_quarters = [row for row in quarterly_rows if _has_quarter_signal(row)]
    quarter_lookup = _quarter_lookup(usable_quarters)
    for row in usable_quarters:
        lines.append(
            "| {q} | {revenue} | {growth} | {op} | {opm} | {net} | {nm} | {txn} |".format(
                q=row.get("quarter") or row.get("period_end"),
                revenue=_money(row.get("revenue")),
                growth=_pct(row.get("revenue_yoy") if row.get("revenue_yoy") is not None else _computed_quarter_yoy(row, quarter_lookup)),
                op=_money(row.get("operating_income")),
                opm=_pct(_safe_div(row.get("operating_income"), row.get("revenue"))),
                net=_money(row.get("net_income")),
                nm=_pct(_safe_div(row.get("net_income"), row.get("revenue"))),
                txn=_pct(_safe_div(row.get("transaction_services_revenue"), row.get("revenue"))),
            )
        )
    if not usable_quarters:
        lines.append("| 未披露 | 未披露 | 未披露 | 未披露 | 未披露 | 未披露 | 未披露 | 未披露 |")
    lines.extend(["", f"**怎么读：** {_quarter_trend_readout(usable_quarters)}"])
    lines.extend(
        [
            "",
            "### 5.3 最新年度经营利润桥",
            "",
            _bridge_table(annual_bridge),
            "",
            f"**怎么读：** {_operating_profit_bridge_readout(annual_bridge)}",
            "",
            "### 5.4 最新季度经营利润以下桥",
            "",
            _bridge_table(below_bridge),
            "",
            f"**怎么读：** {_below_operating_bridge_readout(below_bridge)}",
            "",
            "### 5.5 最新年度营运资本桥",
            "",
            _working_capital_table(working_capital),
            "",
            f"**怎么读：** {_working_capital_readout(working_capital)}",
        ]
    )
    return "\n".join(lines)


def _annual_spine_readout(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "没有可用年度主表，不能建立年度主线。"
    latest = rows[-1]
    prior = rows[-2] if len(rows) >= 2 else {}
    return (
        f"最新年度收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}，"
        f"经营利润同比 {_pct(_growth(latest.get('operating_income'), prior.get('operating_income')))}，"
        f"净利润同比 {_pct(_growth(latest.get('net_income'), prior.get('net_income')))}，"
        f"经营现金流同比 {_pct(_growth(latest.get('operating_cash_flow'), prior.get('operating_cash_flow')))}。"
        "这张表先回答增长、利润和现金是否同向。"
    )


def _quarter_trend_readout(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "没有可用季度主表，不能用最新季度验证年度主线。"
    latest = rows[-1]
    lookup = _quarter_lookup(rows)
    revenue_yoy = latest.get("revenue_yoy") if latest.get("revenue_yoy") is not None else _computed_quarter_yoy(latest, lookup)
    op_yoy = _computed_quarter_yoy(latest, lookup, metric="operating_income")
    net_yoy = _computed_quarter_yoy(latest, lookup, metric="net_income")
    return (
        f"最新季度收入同比 {_pct(revenue_yoy)}，经营利润同比 {_pct(op_yoy)}，净利润同比 {_pct(net_yoy)}。"
        "季度没有推翻“收入仍增长、利润兑现偏弱”的年度主线，反而把追问集中到利润率和经营利润以下项目。"
    )


def _operating_profit_bridge_readout(result: dict[str, Any]) -> str:
    if not result:
        return "没有可用经营利润桥，无法拆出收入增长如何传导到经营利润。"
    revenue_delta = _bridge_row_delta(result, "revenue")
    cost_delta = _bridge_row_delta(result, "cost_of_revenue")
    gross_delta = _bridge_row_delta(result, "gross_profit")
    sm_delta = _bridge_row_delta(result, "sales_and_marketing_expense")
    rd_delta = _bridge_row_delta(result, "research_and_development_expense")
    op_delta = result.get("operating_income_delta") if result.get("operating_income_delta") is not None else _bridge_row_delta(result, "operating_income")
    return (
        f"收入增加 {_money(revenue_delta)}，但收入成本增加 {_money(cost_delta)}、销售与营销增加 {_money(sm_delta)}、研发增加 {_money(rd_delta)}，"
        f"毛利只增加 {_money(gross_delta)}，最终经营利润变化 {_money(op_delta)}；"
        f"增量经营利润率为 {_pct(result.get('incremental_operating_margin'))}。"
        "这就是“收入增长但经营利润回吐”的核心桥。"
    )


def _below_operating_bridge_readout(result: dict[str, Any]) -> str:
    if not result:
        return "没有可用经营利润以下桥，无法解释经营利润和净利润的分叉。"
    operating_delta = result.get("operating_income_delta")
    net_delta = result.get("net_income_delta")
    below_delta = result.get("below_operating_delta")
    other_delta = _bridge_row_delta(result, "other_income_net")
    investment_delta = _bridge_row_delta(result, "investment_income")
    tax_delta = _bridge_row_delta(result, "tax_expense")
    tax_sentence = (
        f"税项减少约 {_money_abs(tax_delta)}，形成部分对冲"
        if (_num(tax_delta) or 0) < 0
        else f"税项增加约 {_money_abs(tax_delta)}，进一步拖累净利润"
    )
    return (
        f"最新季度经营利润同比改善 {_money(operating_delta)}，但净利润同比减少 {_money_abs(net_delta)}，差异主要落在经营利润以下："
        f"经营利润以下项目净拖累扩大约 {_money_abs(below_delta)}，其中其他收益/损失恶化约 {_money_abs(other_delta)}，"
        f"利息和投资收益/损失恶化约 {_money_abs(investment_delta)}；{tax_sentence}。"
        "所以 Q1 净利润压力不能只按经营层面解释。"
    )


def _working_capital_readout(result: dict[str, Any]) -> str:
    if not result:
        return "没有可用营运资本桥，无法判断经营现金流的来源质量。"
    return (
        f"最新年度营运资本现金顺风/收入为 {_pct(result.get('working_capital_cash_tailwind_to_revenue'))}，"
        f"现金来源型经营负债增加 {_money(result.get('cash_source_liability_delta'))}。"
        f"{_working_capital_component_sentence(result)} 这说明经营现金流有平台 float 支持，应和净利润质量分开看。"
    )


def _bridge_row_delta(result: dict[str, Any], metric: str) -> float | None:
    for row in result.get("bridge_rows") or []:
        if row.get("metric") == metric:
            return _num(row.get("delta"))
    return None


def _bridge_table(result: dict[str, Any]) -> str:
    rows = result.get("bridge_rows") or []
    if not rows:
        return "_没有可用的桥表行。_"
    lines = [
        "| 项目 | 本期 | 上期 | 变化 | 本期 / 收入 | 角色 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {metric} | {current} | {prior} | {delta} | {to_rev} | {role} |".format(
                metric=_metric_label(row.get("metric")),
                current=_money(row.get("current")),
                prior=_money(row.get("prior")),
                delta=_money(row.get("delta")),
                to_rev=_pct(row.get("current_to_revenue")),
                role=_md_cell(_role_label(row.get("role") or "")),
            )
        )
    if result.get("incremental_operating_margin") is not None:
        lines.append(
            f"| **增量经营利润率** |  |  |  | **{_pct(result.get('incremental_operating_margin'))}** | 派生指标 |"
        )
    if result.get("below_operating_delta") is not None:
        lines.append(f"| **经营利润以下净变化** |  |  | **{_money(result.get('below_operating_delta'))}** |  | 派生指标 |")
    return "\n".join(lines)


def _working_capital_table(result: dict[str, Any]) -> str:
    rows = result.get("component_details") or []
    if not rows:
        return "_没有可用的营运资本细项。_"
    lines = [
        f"- 营运资本现金顺风/收入：{_pct(result.get('working_capital_cash_tailwind_to_revenue'))}",
        f"- 现金来源型经营负债增加：{_money(result.get('cash_source_liability_delta'))}",
        f"- 现金使用型经营资产增加：{_money(result.get('cash_use_asset_delta'))}",
        "",
        "| 项目 | 角色 | 本期余额 | 变化 | 占收入 |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {metric} | {role} | {value} | {delta} | {to_rev} |".format(
                metric=_metric_label(row.get("metric")),
                role=_md_cell(_role_label(row.get("role") or "")),
                value=_money(row.get("value")),
                delta=_money(row.get("delta")),
                to_rev=_pct(row.get("to_revenue")),
            )
        )
    return "\n".join(lines)


def _insight_register(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
) -> str:
    annual_rows = _annual_rows(pack)
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    metrics = _metrics_by_id(pack)
    profit_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    below = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    cap_intensity = _latest_annual_metric(metrics, "capital_intensity_v1") or {}
    tax_metric = _latest_annual_metric(metrics, "tax_non_gaap_accounting_quality_v1") or {}
    narratives = _as_list(management_pack.get("new_narratives"))
    asset_growth = _growth(latest.get("total_assets"), prior.get("total_assets"))
    broad_cash_delta = _broad_cash(latest) - _broad_cash(prior) if latest and prior else None
    asset_delta = (_num(latest.get("total_assets")) or 0) - (_num(prior.get("total_assets")) or 0) if latest and prior else None
    rows = [
        {
            "title": "增长和利润背离",
            "evidence": f"2025 年收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}，但经营利润同比 {_pct(_growth(latest.get('operating_income'), prior.get('operating_income')))}，增量经营利润率 {_pct(profit_bridge.get('incremental_operating_margin'))}。",
            "implication": "核心矛盾不是有没有增长，而是新增收入质量和利润兑现。",
            "limitation": "第一层不能证明原因，必须回到成本、费用、供应链投入、竞争和管理层解释。",
            "linked": "Q1 / Q2",
        },
        {
            "title": "季度利润分叉发生在经营利润以下",
            "evidence": _below_operating_bridge_readout(below),
            "implication": "季度净利润下降不能简单归因于经营层面恶化，需要拆投资收益、其他收益/损失和税项。",
            "limitation": "还需要观察这些 below-operating 项是否反复出现。",
            "linked": "Q8",
        },
        {
            "title": "现金流有平台 float 贡献",
            "evidence": f"经营现金流 / 净利润 {_ratio_x((_latest_annual_metric(metrics, 'cash_conversion_ratio_v1') or {}).get('value'))}，营运资本现金顺风/收入 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}。",
            "implication": "强现金流是真实优势，但不能全部解释为纯利润质量；应付商家款项、保证金和应计费用要持续拆。",
            "limitation": "应收账款、存货和更多经营资产/负债细项仍需补齐。",
            "linked": "Q3",
        },
        {
            "title": "投入压力没有主要体现为固定资产",
            "evidence": f"2025 年资本开支 / 收入 {_pct(cap_intensity.get('capex_to_revenue'))}，自由现金流 / 经营现金流 {_pct(cap_intensity.get('free_cash_flow_to_operating_cash_flow'))}。",
            "implication": "供应链、商家支持、自营品牌的投入更可能通过费用、履约、补贴、营运资本体现。",
            "limitation": "维护性和增长性资本开支未披露，自营品牌的库存和采购承诺未形成结构化事实。",
            "linked": "Q2 / Q5",
        },
        {
            "title": "资产规模扩张快于收入",
            "evidence": f"2025 年总资产同比 {_pct(asset_growth)}，收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}；广义现金与短投增加 {_money(broad_cash_delta)}，约占总资产增量 {_pct(_safe_div(broad_cash_delta, asset_delta))}。",
            "implication": "资产负债表正在沉淀更多资金和投资资产，资本效率不能只看收入表。",
            "limitation": "资金可用性、投资资产性质、币种/地区限制仍要回附注。",
            "linked": "Q4",
        },
        {
            "title": "收入结构已具备公司特征",
            "evidence": _revenue_component_sentence(latest, prefix="2025 年"),
            "implication": "PDD 不应再只按广告平台理解；交易服务和广告变现需要分开跟踪。",
            "limitation": "GMV、take-rate、订单、用户和商户 cohort 未稳定披露。",
            "linked": "Q6 / Q7",
        },
        {
            "title": "净利润受非经营项目影响",
            "evidence": f"2025 年投资收益/税前利润 {_pct(tax_metric.get('investment_income_to_pretax'))}，有效税率 {_pct(tax_metric.get('effective_tax_rate'))}。",
            "implication": "盈利质量读法应优先看经营利润和经营现金流，再拆投资收益、其他收益和税项。",
            "limitation": "现金纳税、减值和投资收益来源还未完整进入主表。",
            "linked": "Q8",
        },
    ]
    for narrative in narratives:
        rows.append(
            {
                "title": _narrative_title(narrative),
                "evidence": _zh_text(narrative.get("summary") or _first_evidence_summary(narrative.get("evidence"))),
                "implication": _zh_text(narrative.get("why_it_matters") or "管理层沟通中的新叙事，可能改变下一轮问题设置。"),
                "limitation": _join(narrative.get("unknowns") or narrative.get("follow_up_needed")) if narrative.get("unknowns") or narrative.get("follow_up_needed") else "需要未来官方文件或后续季度验证。",
                "linked": "第三层",
            }
        )
    lines = [
        "| 洞察 | 证据 | 为什么重要 | 局限 | 关联问题 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {title} | {evidence} | {implication} | {limitation} | {linked} |".format(
                title=_md_cell(_zh_text(row["title"])),
                evidence=_md_cell(_zh_text(row["evidence"])),
                implication=_md_cell(_zh_text(row["implication"])),
                limitation=_md_cell(_zh_text(row["limitation"])),
                linked=_md_cell(_zh_text(row["linked"])),
            )
        )
    return "\n".join(lines)


def _business_specific_cards(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
) -> str:
    gaps = _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry"))
    official_narratives = _as_list(official_pack.get("decision_relevant_narratives"))
    management_narratives = _as_list(management_pack.get("new_narratives"))
    topics = _as_list(management_pack.get("qa_pressure_topics"))
    lines: list[str] = [
        "### 业务模型事实地图",
        "",
        _business_model_fact_map(pack, official_pack, management_pack),
        "",
    ]
    for gap in gaps:
        lines.extend(
            [
                f"### {_gap_card_heading(gap)}",
                "",
                f"- **状态：** `{_status_label(gap.get('status') or 'unknown')}`",
                f"- **为什么重要：** {_gap_why_cn(gap)}",
                f"- **缺失指标：** {_metric_list_cn(gap.get('missing_metrics'))}",
                f"- **可用指标：** {_metric_list_cn(gap.get('available_metrics'), fallback='暂无结构化数值')}",
                "",
            ]
        )
    if official_narratives:
        lines.extend(["### 官方叙事登记", ""])
        for item in official_narratives:
            lines.extend(
                [
                    f"#### {_narrative_title(item)}",
                    "",
                    f"- **类型：** `{_narrative_type_label(item.get('narrative_type'))}`",
                    f"- **摘要：** {_zh_text(item.get('summary') or item.get('why_it_matters') or '未披露')}",
                    f"- **为什么重要：** {_zh_text(item.get('why_it_matters') or '未披露')}",
                    f"- **证据：** {_evidence_refs(item.get('evidence_bundle') or item.get('evidence'))}",
                    "",
                ]
            )
        governance_detail = _governance_audit_detail_section(pack, official_narratives)
        if governance_detail:
            lines.extend(["### 治理与审计细节卡", "", governance_detail, ""])
    if management_narratives:
        lines.extend(["### 管理层沟通叙事登记", ""])
        for item in management_narratives:
            lines.extend(
                [
                    f"#### {_narrative_title(item)}",
                    "",
                    f"- **摘要：** {_zh_text(item.get('summary') or _first_evidence_summary(item.get('evidence')))}",
                    f"- **证据：** {_evidence_refs(item.get('evidence'))}",
                    "",
                ]
            )
    if topics:
        lines.extend(["### 问答压力点", ""])
        for topic in topics:
            lines.extend(
                [
                    f"#### {_zh_text(topic.get('topic'))}",
                    "",
                    f"- **分析师关注：** {_zh_text(topic.get('analyst_concern') or '未披露')}",
                    f"- **管理层回答：** {_zh_text(topic.get('management_response_read') or '未披露')}",
                    f"- **回答质量：** `{_answer_quality_label(topic.get('answer_quality') or 'unknown')}`",
                    f"- **后续追问：** {_join(topic.get('follow_up_needed'))}",
                    f"- **证据：** {_evidence_refs(topic.get('evidence'))}",
                    "",
                ]
            )
    return "\n".join(lines).strip() or "_没有可用的公司特有证据卡。_"


def _gap_card_heading(gap: dict[str, Any]) -> str:
    gap_id = str(gap.get("gap_id") or "").strip()
    if not gap_id:
        return "披露缺口"
    title = _backlog_need_title(gap_id)
    return f"{_zh_text(title)}（{gap_id}）"


def _business_model_fact_map(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
) -> str:
    annual_rows = _annual_rows(pack)
    latest = annual_rows[-1] if annual_rows else {}
    quarterly_rows = [row for row in _quarterly_rows(pack) if _has_quarter_signal(row)]
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}
    metrics = _metrics_by_id(pack)
    source_growth = _latest_annual_metric(metrics, "source_of_growth_attribution_v1") or {}
    latest_interim_source = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    operating_bridge = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    balance = _latest_annual_metric(metrics, "balance_sheet_risk_v1") or {}
    cap_intensity = _latest_annual_metric(metrics, "capital_intensity_v1") or {}
    gaps = {str(gap.get("gap_id") or ""): gap for gap in _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry"))}
    rows = [
        {
            "module": "收入 / 货币化",
            "fact": "收入主要来自商家侧平台服务：在线营销服务及其他、交易服务。",
            "disclosed": (
                f"{_revenue_component_sentence(latest, prefix=str(latest.get('year') or '最新年度') + ' 年')} "
                f"{_quarter_revenue_component_sentence(latest_quarter, latest_interim_source)} "
                f"年度收入组件覆盖率 {_pct(source_growth.get('value'))}。"
            ),
            "missing": _metric_list_cn((gaps.get("user_and_transaction_kpis") or {}).get("missing_metrics"), fallback="GMV、抽佣率、用户和订单驱动仍未稳定披露"),
            "status": "硬数字强；增长驱动拆分仍不足",
        },
        {
            "module": "成本 / 利润压力",
            "fact": "利润压力主要要从收入成本、销售与营销、研发和具体履约/支付/商家支持成本里拆。",
            "disclosed": (
                f"2025 年收入成本/收入 {_pct(_cost_ratio(latest))}，销售与营销/收入 {_pct(_safe_div(latest.get('sales_and_marketing_expense'), latest.get('revenue')))}，"
                f"研发/收入 {_pct(_safe_div(latest.get('research_and_development_expense'), latest.get('revenue')))}；"
                f"经营利润桥显示收入增加 {_money(operating_bridge.get('revenue_delta'))}，经营利润变化 {_money(operating_bridge.get('operating_income_delta'))}。"
            ),
            "missing": _metric_list_cn((gaps.get("cost_of_revenue_subcomponents") or {}).get("missing_metrics"), fallback="履约、支付、服务器、商家支持等细项金额未稳定披露"),
            "status": "硬数字强；成本归因仍部分",
        },
        {
            "module": "现金沉淀 / 平台 float",
            "fact": "现金优势不只在账面现金，也体现在应付商家款项、商家保证金和应计费用等经营负债。",
            "disclosed": (
                f"广义现金与短投 {_money(_broad_cash(latest))}，受限现金/现金 {_pct(balance.get('restricted_cash_to_cash'))}；"
                f"营运资本现金顺风/收入 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}，"
                f"现金来源型经营负债增加 {_money(working_capital.get('cash_source_liability_delta'))}。"
            ),
            "missing": "股东可动用现金、资金跨境/VIE 可转移性、商家/客户资金属性、债务期限墙仍要继续拆。",
            "status": "硬数字强；可用性解释仍部分",
        },
        {
            "module": "模式变化 / 自营品牌",
            "fact": "自营品牌可能让平台更深介入产品、质量、履约和供应链，但目前还没有单独财务闭环。",
            "disclosed": (
                f"管理层沟通披露初始注资 RMB 15B、三年 RMB 100B 投入。"
                f"2025 年资本开支/收入 {_pct(cap_intensity.get('capex_to_revenue'))}，说明目前尚未主要体现为传统固定资产扩张。"
            ),
            "missing": _metric_list_cn((gaps.get("first_party_brand_unit_economics") or {}).get("missing_metrics"), fallback="库存风险、单独损益和投资回收期未披露"),
            "status": "管理层说法强；财务足迹仍弱",
        },
        {
            "module": "全球业务 / Temu",
            "fact": "全球业务可能是增长空间，也可能带来履约、监管、税务和利润率不确定性。",
            "disclosed": _plain_narrative_summary(official_pack, ["Temu", "全球业务"], fallback="官方证据包登记了全球业务 / Temu 叙事，但没有形成单独财务分部。"),
            "missing": _metric_list_cn((gaps.get("temu_standalone_economics") or {}).get("missing_metrics"), fallback="Temu 单独收入、利润、GMV 和履约成本未披露"),
            "status": "官方叙事存在；硬数字缺口大",
        },
    ]
    table = [
        "| 模块 | 当前事实地图 | 已披露 KPI / 数字 | 未披露 / 待验证 | 证据状态 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        table.append(
            "| {module} | {fact} | {disclosed} | {missing} | {status} |".format(
                module=_md_cell(_zh_text(row["module"])),
                fact=_md_cell(_zh_text(row["fact"])),
                disclosed=_md_cell(_zh_text(row["disclosed"])),
                missing=_md_cell(_zh_text(row["missing"])),
                status=_md_cell(_zh_text(row["status"])),
            )
        )
    table.extend(
        [
            "",
            "**怎么读：** 这张地图不是新结论，而是把公司业务模型拆成五个可验证模块。后续 HTML 报告可以从这里提炼主线；如果某个模块只有管理层说法、没有硬数字，就不能把它写成已经兑现的商业模式变化。",
        ]
    )
    return "\n".join(table)


def _plain_narrative_summary(pack: dict[str, Any], keywords: list[str], *, fallback: str) -> str:
    narratives = _as_list(pack.get("decision_relevant_narratives"))
    lowered = [keyword.lower() for keyword in keywords]
    matches: list[str] = []
    for item in narratives:
        haystack = " ".join(str(item.get(key) or "") for key in ["title", "summary", "why_it_matters", "narrative_type"]).lower()
        if any(keyword in haystack for keyword in lowered):
            matches.append(f"{_narrative_title(item)}：{_zh_text(item.get('why_it_matters') or item.get('summary') or '已登记')}")
    return "；".join(matches[:3]) or fallback


def _governance_audit_detail_section(pack: dict[str, Any], narratives: list[dict[str, Any]]) -> str:
    titles = " ".join(_narrative_title(item) for item in narratives)
    if not any(keyword in titles for keyword in ["治理", "AGM", "Share Plan", "审计", "内控"]):
        return ""
    company_name = ((pack.get("company") or {}).get("legal_name") or "").lower()
    pdd_specific = "pdd" in company_name
    lines = [
        "这张卡只记录会影响股东权利、执行稳定性、稀释和会计可信度的官方治理/审计事实；它不直接解释收入和利润，但会影响底稿对长期 owner economics 的置信度。",
        "",
    ]
    if pdd_specific:
        lines.extend(
            [
                "- **管理层与董事会：** 2025 年 20-F 披露 Lei Chen 与 Jiazhen Zhao 为联席董事长兼联席 CEO；同一治理证据包把管理层/董事会变化列为执行风险和资本配置纪律的跟踪项。若后续 6-K 继续披露工程、财务或其他关键岗位变化，应和战略执行质量一起跟踪。",
                "- **ADS 投票机制与 AGM：** 20-F 披露 ADS 持有人需要通过存托人向底层 Class A 普通股发出投票指令，AGM / proxy 材料因此会影响少数股东权利的实际可行性；董事重选和投票参与度仍需后续 AGM 材料继续跟踪。",
                "- **股权激励计划：** 2015 Global Share Plan 在 2025 年 8 月进一步修订并延长期限；这本身不是会计红旗，但必须和 SBC / 收入、SBC / 经营现金流、摊薄股数和回购抵消情况一起读。",
                "- **审计与内控：** 20-F 披露 Ernst & Young 审计了 2025 年 12 月 31 日的财务报告内部控制有效性；当前结构化证据包没有识别出重述或重大内控缺陷，但关键审计事项和会计估计敏感性仍要持续跟踪。",
                "",
                "**怎么读：** 治理和审计项目前不是主矛盾，但它们决定少数股东能否有效表达权利、股权激励是否侵蚀每股价值、以及财报数字能否被足够信任。",
                "",
                "**仍需验证：** 董事重选反对率、ADS 持有人实际投票参与、剩余可授予股份、未来 SBC 强度、回购是否抵消稀释、关键审计事项和管理层职责变化后的执行结果。",
            ]
        )
        return "\n".join(lines)

    matched = [item for item in narratives if item.get("narrative_type") in {"governance", "accounting"}]
    for item in matched:
        lines.append(f"- **{_narrative_title(item)}：** {_zh_text(item.get('why_it_matters') or item.get('our_inference') or '需要跟踪。')}")
    lines.extend(
        [
            "",
            "**怎么读：** 对非 PDD 公司，这里仍按治理、股权激励、审计和内控四类事实组织；具体姓名、投票结果和计划条款以官方证据包为准。",
        ]
    )
    return "\n".join(lines)


def _unknown_register(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    feedback_loop_pack: dict[str, Any],
    dockets: list[dict[str, Any]],
) -> str:
    backlog = _extraction_backlog_table(pack, official_pack, management_pack, dockets)
    feedback_section = _feedback_loop_section(feedback_loop_pack)
    rows = [
        "| 未知 / 限制 | 为什么重要 | 已检查来源 | 当前状态 | 关联问题 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for docket in dockets:
        for item in docket.get("unknown") or []:
            rows.append(
                "| {unknown} | {why} | 问题底稿 | 未解决 | {qid} |".format(
                    unknown=_md_cell(_zh_text(item)),
                    why=_md_cell(docket.get("question")),
                    qid=_md_cell(docket.get("id")),
                )
            )
    for gap in _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry")):
        rows.append(
            "| {unknown} | {why} | 财报 / 结构化抽取器 | {status} | 公司特有变量 |".format(
                unknown=_md_cell(_join(gap.get("missing_metrics") or [gap.get("gap_id") or "gap"])),
                why=_md_cell(_gap_why_cn(gap)),
                status=_md_cell(_status_label(gap.get("status") or "unknown")),
            )
        )
    for flag in official_pack.get("quality_flags") or []:
        rows.append(
            "| {flag} | 官方证据质量标记 | 官方证据包 | 待复核 | 证据质量 |".format(
                flag=_md_cell(flag.get("message") or flag.get("flag") or flag)
            )
        )
    for flag in management_pack.get("quality_flags") or []:
        rows.append(
            "| {flag} | 管理层沟通质量标记 | 管理层沟通包 | 待复核 | 沟通质量 |".format(
                flag=_md_cell(flag.get("message") or flag.get("flag") or flag)
            )
        )
    return "\n".join(
        [
            "### 8.1 下一轮 Extractor 需求清单",
            "",
            backlog,
            "",
            "### 8.2 反馈闭环路由",
            "",
            feedback_section,
            "",
            "### 8.3 未解问题与限制登记",
            "",
            "\n".join(rows),
        ]
    )


def _feedback_loop_section(feedback_loop_pack: dict[str, Any]) -> str:
    if not feedback_loop_pack:
        return "反馈闭环尚未生成；当前底稿只能展示 extractor backlog，不能确认第二层问题是否已回流。"
    summary = feedback_loop_pack.get("summary") or {}
    route_rows = [
        "| 回流方向 | 数量 | 读法 |",
        "| --- | ---: | --- |",
        f"| 回 Financial Extractor | {_fmt_int(summary.get('financial_extractor_request_count'))} | 需要补抽官方数字、表格或附注字段。 |",
        f"| 回 Metrics | {_fmt_int(summary.get('metric_recalculation_request_count'))} | 已有或待补事实需要重新计算桥表、比率或增速。 |",
        f"| 回 Layer 1 | {_fmt_int(summary.get('layer1_requery_request_count'))} | 补充事实或重算指标后，第一层要重新回答标准问题。 |",
        f"| 回 Evidence / Communication | {_fmt_int(summary.get('evidence_communication_followup_count'))} | 还需要继续读官方文字、电话会、Q&A 或管理层叙事。 |",
        f"| 外部数据 / 人工复核 | {_fmt_int(summary.get('external_data_request_count'))} / {_fmt_int(summary.get('human_review_request_count'))} | 当前允许来源不能充分回答，或需要人工判断分类。 |",
    ]
    lines = [
        f"闭环状态：`{feedback_loop_pack.get('closed_loop_status') or 'unknown'}`。这一节回答：第二层冒出的新问题有没有被送回第一层和 extractor，而不是只留在文字报告里。",
        "",
        "\n".join(route_rows),
    ]
    layer1_items = _as_list(feedback_loop_pack.get("layer1_requery_requests"))
    extractor_items = _as_list(feedback_loop_pack.get("financial_extractor_requests"))
    if layer1_items:
        lines.extend(["", "**回第一层优先问题：**"])
        for item in layer1_items[:6]:
            lines.append(
                f"- {_zh_text(item.get('question') or item.get('request'))} "
                f"（状态：`{item.get('current_financial_pack_status') or 'unknown'}`；来源：{_zh_text(item.get('source') or 'feedback_router')}）"
            )
    if extractor_items:
        lines.extend(["", "**需要补抽的关键数字：**"])
        for item in extractor_items[:6]:
            lines.append(
                f"- {item.get('priority') or 'P2'}：{_zh_text(item.get('request'))}；"
                f"缺口：{_join(item.get('missing_metrics'))}"
            )
    lines.extend(
        [
            "",
            "**怎么读：** V1 闭环只负责路由和记录，不在同一轮自动发明缺失事实；真正的数字补抽仍要由 Financial Extractor 下一轮执行。",
        ]
    )
    return "\n".join(lines)


def _extraction_backlog_table(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    dockets: list[dict[str, Any]],
) -> str:
    rows = [
        "| 优先级 | 需求 | 当前缺口 | 为什么重要 | 建议 extractor / 来源路线 | 目标字段 | 关联研究问题 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    gaps = _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry"))
    for gap in gaps:
        items.append(_backlog_item_from_gap(gap, dockets))
    items.extend(_synthetic_extraction_backlog_items(official_pack, management_pack, dockets))
    for item in sorted(items, key=_backlog_sort_key):
        _append_backlog_row(rows, item, seen)
    if len(rows) == 2:
        rows.append("| P2 | 暂无自动识别需求 | 当前事实包未登记明确披露缺口 | 保留占位，后续问题底稿可继续回流 | 年报 / 季报 / 附注 / 管理层沟通 | 待定义 | 未关联 |")
    return "\n".join(rows)


def _append_backlog_row(rows: list[str], item: dict[str, Any], seen: set[str]) -> None:
    item_id = str(item.get("id") or item.get("need") or "").strip()
    if not item_id or item_id in seen:
        return
    seen.add(item_id)
    rows.append(
        "| {priority} | {need} | {gap} | {why} | {route} | {fields} | {questions} |".format(
            priority=_md_cell(item.get("priority")),
            need=_md_cell(item.get("need")),
            gap=_md_cell(item.get("current_gap")),
            why=_md_cell(item.get("why")),
            route=_md_cell(item.get("route")),
            fields=_md_cell(item.get("target_fields")),
            questions=_md_cell(item.get("linked_questions")),
        )
    )


def _backlog_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return (priority_rank.get(str(item.get("priority")), 9), str(item.get("need") or ""))


def _backlog_item_from_gap(gap: dict[str, Any], dockets: list[dict[str, Any]]) -> dict[str, Any]:
    gap_id = str(gap.get("gap_id") or "unclassified_gap")
    missing = gap.get("missing_metrics") or []
    status = _status_label(gap.get("status") or "unknown")
    current_gap = f"{status}；缺少：{_metric_list_cn(missing)}"
    available = _metric_list_cn(gap.get("available_metrics"), fallback="")
    if available:
        current_gap = f"{current_gap}；已有：{available}"
    return {
        "id": gap_id,
        "priority": _backlog_priority(gap_id),
        "need": _backlog_need_title(gap_id),
        "current_gap": current_gap,
        "why": _gap_why_cn(gap),
        "route": _backlog_source_route(gap_id),
        "target_fields": _backlog_output_fields(gap),
        "linked_questions": _backlog_linked_questions(gap_id, dockets),
    }


def _synthetic_extraction_backlog_items(
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    dockets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    has_cash_question = any(str(docket.get("id")) == "Q4" for docket in dockets)
    has_owner_question = any(str(docket.get("id")) == "Q9" for docket in dockets)
    items: list[dict[str, Any]] = []
    if has_cash_question:
        items.append(
            {
                "id": "usable_cash_and_vie_transferability",
                "priority": "P0",
                "need": "可动用现金与 VIE 资金转移性",
                "current_gap": "账面现金、受限现金和短投已进入底稿，但可自由动用、跨境调配、VIE 访问和刚性义务覆盖仍未完全结构化。",
                "why": "PDD 的现金安全垫是核心判断之一；如果现金受限、被监管账户占用或受 VIE / 跨境限制影响，资产负债表读法要打折。",
                "route": _backlog_source_route("usable_cash_and_vie_transferability"),
                "target_fields": "现金、受限现金、短期投资、长期投资、VIE 资产/负债、资金转移限制、12 个月债务/租赁/承诺",
                "linked_questions": _backlog_linked_questions("usable_cash_and_vie_transferability", dockets),
            }
        )
    if has_owner_question:
        items.append(
            {
                "id": "share_count_and_capital_return_bridge",
                "priority": "P2",
                "need": "股数、SBC 与资本回报桥",
                "current_gap": "SBC 负担和稀释率已有初步指标，但股数桥、剩余股权激励、回购/分红和 AGM 股权计划条款还没有形成完整 owner-economics 桥。",
                "why": "现金很厚但是否转化为每股价值，取决于稀释、回购、分红、股权计划和 ADS/普通股权利。",
                "route": _backlog_source_route("share_count_and_capital_return_bridge"),
                "target_fields": "基本/稀释股数、ADS/普通股比例、SBC by function、未确认 SBC、回购、分红、股权计划可授予余额",
                "linked_questions": _backlog_linked_questions("share_count_and_capital_return_bridge", dockets),
            }
        )
    if official_pack.get("quality_flags") or management_pack.get("quality_flags"):
        items.append(
            {
                "id": "evidence_quality_backfill",
                "priority": "P2",
                "need": "证据质量与来源锚点补齐",
                "current_gap": "部分官方/管理层证据仍需要更稳定的页码、段落锚点或 source_id。",
                "why": "底稿可以先读，但后续 HTML 和审阅工作需要更强的回溯链条。",
                "route": "官方文件 section parser、transcript block parser、evidence ledger",
                "target_fields": "document_id、accession、section、page/paragraph anchor、speaker、block_id、evidence label",
                "linked_questions": "全部证据卡",
            }
        )
    return items


def _backlog_priority(gap_id: str) -> str:
    mapping = {
        "cost_of_revenue_subcomponents": "P0",
        "user_and_transaction_kpis": "P0",
        "usable_cash_and_vie_transferability": "P0",
        "temu_standalone_economics": "P1",
        "first_party_brand_unit_economics": "P1",
        "maintenance_vs_growth_capex": "P2",
        "share_count_and_capital_return_bridge": "P2",
    }
    return mapping.get(gap_id, "P2")


def _backlog_need_title(gap_id: str) -> str:
    mapping = {
        "cost_of_revenue_subcomponents": "成本细项抽取",
        "user_and_transaction_kpis": "用户、交易与抽佣 KPI",
        "temu_standalone_economics": "Temu / 全球业务单独经济性",
        "first_party_brand_unit_economics": "自营品牌单位经济性",
        "maintenance_vs_growth_capex": "维护性 / 增长性资本开支拆分",
        "usable_cash_and_vie_transferability": "可动用现金与 VIE 资金转移性",
        "share_count_and_capital_return_bridge": "股数、SBC 与资本回报桥",
    }
    return mapping.get(gap_id, gap_id.replace("_", " "))


def _backlog_source_route(gap_id: str) -> str:
    mapping = {
        "cost_of_revenue_subcomponents": "20-F / 6-K 成本表、附注、业绩稿成本说明；若只有叙事，标记为仅叙事",
        "user_and_transaction_kpis": "20-F / 6-K / 业绩稿 KPI 表；公司未披露时保留披露缺口",
        "temu_standalone_economics": "20-F / 6-K / 业绩稿 / 官方活动；搜索 Temu、全球业务、履约、监管成本",
        "first_party_brand_unit_economics": "6-K / 业绩电话会 / 后续 20-F 附注；搜索自营品牌、库存、采购承诺、仓储租赁",
        "maintenance_vs_growth_capex": "20-F 现金流表、PP&E / 软件 / 无形资产附注；仅在公司明确拆分时填",
        "usable_cash_and_vie_transferability": "现金、受限现金、短投、VIE、资金转移、债务期限、承诺附注",
        "share_count_and_capital_return_bridge": "20-F / 6-K / AGM / equity plan / EPS 表 / 回购分红披露",
    }
    return mapping.get(gap_id, "年报、季度文件、附注、管理层沟通和已有 facts 交叉抽取")


def _backlog_output_fields(gap: dict[str, Any]) -> str:
    missing = gap.get("missing_metrics") or []
    if missing:
        return _metric_list_cn(missing)
    return _metric_list_cn(gap.get("available_metrics"), fallback="待定义")


def _backlog_linked_questions(gap_id: str, dockets: list[dict[str, Any]]) -> str:
    mapping = {
        "cost_of_revenue_subcomponents": ["Q1", "Q2"],
        "user_and_transaction_kpis": ["Q1", "Q6"],
        "temu_standalone_economics": ["Q7"],
        "first_party_brand_unit_economics": ["Q5"],
        "maintenance_vs_growth_capex": ["Q5", "Q8"],
        "usable_cash_and_vie_transferability": ["Q4"],
        "share_count_and_capital_return_bridge": ["Q9"],
    }
    existing = {str(docket.get("id")) for docket in dockets}
    linked = [qid for qid in mapping.get(gap_id, []) if qid in existing]
    return " / ".join(linked) or "公司特有变量"


def _evidence_appendix(
    pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "### 9.1 披露边界与口径",
        "",
        _disclosure_boundary_table(pack),
        "",
        "### 9.2 公式 / 指标族",
        "",
        "| 公式 | 年度行数 | 最新状态 | 最新数值 | 警示标记 |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for formula_id, metric in metrics.items():
        annual = metric.get("annual_results") or []
        latest = _latest_annual_metric(metrics, formula_id) or {}
        lines.append(
            "| {formula} | {count} | {status} | {value} | {flags} |".format(
                formula=f"`{_md_cell(formula_id)}`",
                count=len(annual),
                status=_md_cell(_status_label(latest.get("status") or metric.get("status") or "")),
                value=_metric_value(metric, latest),
                flags=_md_cell(_zh_text(_join(latest.get("warning_flags") or metric.get("warning_flags")))),
            )
        )
    lines.extend(
        [
            "",
            "### 9.3 官方来源目录",
            "",
            _source_catalog_table(_as_list(official_pack.get("source_catalog") or pack.get("source_inventory"))),
            "",
            "### 9.4 管理层沟通来源目录",
            "",
            _source_catalog_table(_as_list(management_pack.get("source_catalog"))),
            "",
            "### 9.5 关键来源事实 ID",
            "",
            _load_bearing_fact_ids(metrics),
        ]
    )
    return "\n".join(lines)


def _disclosure_boundary_table(pack: dict[str, Any]) -> str:
    gaps = _as_list((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry"))
    gap_ids = {str(gap.get("gap_id") or "") for gap in gaps}
    rows = [
        "| 项目 | 披露 / 抽取状态 | 本底稿处理方式 |",
        "| --- | --- | --- |",
        "| 收入、利润、现金流 | 已抽取 | 直接使用官方年报 / 20-F / 10-K 和季度 6-K / 10-Q 的结构化事实；核心三表缺失时不应生成完整报告。 |",
        "| 自由现金流近似值 | 已计算 | 按经营现金流减资本开支估算，只作为现金质量线索；不等同于可自由分配现金。 |",
        "| 收入组件 / 业务线 | 部分已抽取 | 只使用官方文件中能结构化抽取的组件；缺失时不做 GMV、抽佣率或用户口径反推。 |",
        "| non-GAAP 经营利润 / 净利润 | 已抽取最新季度 | 仅作为管理层口径补充，用来解释调整项和净利润桥；不替代 GAAP 主信号。 |",
        "| Adjusted EBITDA | 未稳定抽取 | 如果公司没有稳定披露，本底稿不自行构造替代口径。 |",
        "| GMV / ARPU / MAU / 活跃买家 | 未稳定抽取 | 登记为披露缺口；不把未披露 KPI 反推成事实。 |",
        "| 地区收入 / 单一品牌收入 | 未稳定抽取 | 未单独披露时只做定性风险提示，不做数值拆分。 |",
        "| 维护性资本开支 / 增长性资本开支 | 未稳定拆分 | 资本开支只按披露总额进入公式；维护性和增长性拆分需要官方披露或人工复核。 |",
    ]
    if gap_ids:
        rows.append(f"| 公司特有披露缺口 | {len(gap_ids)} 类已登记 | 进入第 7 节公司特有证据卡和第 8 节未知登记；不会被写成已验证事实。 |")
    rows.extend(
        [
            "",
            "**怎么读：** 这张表是“不能越界”的清单。底稿可以提出问题和推断，但凡未被官方数字或可追溯叙事支持的项目，都必须保留为披露缺口或后续查证项。",
        ]
    )
    return "\n".join(rows)


def _source_catalog_table(sources: list[Any]) -> str:
    if not sources:
        return "_没有可用的来源目录记录。_"
    lines = [
        "| 类型 | 日期 / 期间 | 文件 | 本地路径 / URL |",
        "| --- | --- | --- | --- |",
    ]
    for source in sources:
        if not isinstance(source, dict):
            continue
        lines.append(
            "| {typ} | {date} | {doc} | {path} |".format(
                typ=_md_cell(_source_type_label(source.get("source_document_type") or source.get("document_type") or source.get("status") or source.get("type") or "")),
                date=_md_cell(source.get("filing_date") or source.get("period") or ""),
                doc=_md_cell(source.get("source_document") or source.get("document_id") or source.get("source_id") or source.get("name") or ""),
                path=_md_cell(source.get("local_file_path") or source.get("local_path") or source.get("source_url") or ""),
            )
        )
    return "\n".join(lines)


def _load_bearing_fact_ids(metrics: dict[str, dict[str, Any]]) -> str:
    key_formulas = [
        "margin_profile_v1",
        "operating_profit_bridge_v1",
        "working_capital_quality_v1",
        "below_operating_bridge_v1",
        "balance_sheet_risk_v1",
        "source_of_growth_attribution_v1",
        "tax_non_gaap_accounting_quality_v1",
    ]
    lines: list[str] = []
    for formula in key_formulas:
        latest = _latest_annual_metric(metrics, formula) or (metrics.get(formula) or {}).get("latest_interim_result") or {}
        ids = latest.get("source_fact_ids") or []
        if not ids:
            continue
        lines.extend([f"#### `{formula}`", ""])
        for item in ids[:12]:
            lines.append(f"- `{item}`")
        if len(ids) > 12:
            lines.append(f"- ... 另有 {len(ids) - 12} 个来源事实 ID")
        lines.append("")
    return "\n".join(lines).strip() or "_选定指标族中没有找到关键来源事实 ID。_"


def _annual_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in pack.get("annual_facts") or [] if row.get("year") is not None],
        key=lambda row: int(row.get("year") or 0),
    )


def _quarterly_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in pack.get("quarterly_facts") or [] if row.get("period_end")],
        key=lambda row: str(row.get("period_end")),
    )


def _has_quarter_signal(row: dict[str, Any]) -> bool:
    return any(
        _num(row.get(metric)) is not None
        for metric in [
            "revenue",
            "operating_income",
            "net_income",
            "online_marketing_services_revenue",
            "transaction_services_revenue",
        ]
    )


def _quarter_lookup(rows: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        parsed = _parse_quarter_label(row.get("quarter"))
        if parsed:
            lookup[parsed] = row
    return lookup


def _computed_quarter_yoy(
    row: dict[str, Any],
    lookup: dict[tuple[int, int], dict[str, Any]],
    *,
    metric: str = "revenue",
) -> float | None:
    parsed = _parse_quarter_label(row.get("quarter"))
    if not parsed:
        return None
    year, quarter = parsed
    prior = lookup.get((year - 1, quarter))
    if not prior:
        return None
    return _growth(row.get(metric), prior.get(metric))


def _parse_quarter_label(label: Any) -> tuple[int, int] | None:
    if not isinstance(label, str):
        return None
    match = re.search(r"(\d{4})\s*Q([1-4])", label)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _metrics_by_id(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(metric.get("formula_id")): metric
        for metric in pack.get("financial_metrics") or []
        if metric.get("formula_id")
    }


def _latest_annual_metric(metrics: dict[str, dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    annual_results = (metrics.get(formula_id) or {}).get("annual_results") or []
    calculated = [row for row in annual_results if row.get("status") == "calculated"]
    return calculated[-1] if calculated else (annual_results[-1] if annual_results else None)


def _answer_summary(answer: dict[str, Any]) -> str:
    if not answer:
        return "当前已审阅官方文件未回答。"
    rendered = answer.get("rendered_answer") or {}
    parts = []
    if rendered.get("filing_facts"):
        parts.append(f"事实：{_zh_text(rendered['filing_facts'])}")
    elif answer.get("short_answer"):
        parts.append(f"事实：{_zh_text(answer['short_answer'])}")
    if rendered.get("official_explanation"):
        parts.append(f"官方解释：{_zh_text(rendered['official_explanation'])}")
    elif answer.get("management_explanations"):
        parts.append(f"官方解释：{_zh_text(_first_summary(answer.get('management_explanations')))}")
    if rendered.get("our_judgment"):
        parts.append(f"官方证据裁判：{_zh_text(rendered['our_judgment'])}")
    if answer.get("warning_flags"):
        parts.append(f"警示信号：{_zh_text(_join(answer.get('warning_flags')))}")
    return "\n".join(parts) if parts else "未披露"


def _topic_summary(topic: dict[str, Any], *, review: dict[str, Any] | None = None, fallback: str = "未披露") -> str:
    review = review or {}
    parts = []
    if topic:
        parts.append(f"分析师关注：{_zh_text(topic.get('analyst_concern') or '未披露')}")
        parts.append(f"管理层回答：{_zh_text(topic.get('management_response_read') or '未披露')}")
        parts.append(f"回答质量：`{_answer_quality_label(topic.get('answer_quality') or 'unknown')}`")
        if topic.get("follow_up_needed"):
            parts.append(f"后续追问：{_join(topic.get('follow_up_needed'))}")
        if topic.get("evidence"):
            parts.append(f"证据索引：{_evidence_refs(topic.get('evidence'))}")
    if review:
        parts.append(_review_summary(review))
    return "\n".join(parts) if parts else fallback


def _review_summary(review: dict[str, Any], *, fallback: str = "未披露") -> str:
    if not review:
        return fallback
    parts = []
    if review.get("issue_text"):
        parts.append(f"已复核问题：{_zh_text(review.get('issue_text'))}")
    if review.get("management_explanation"):
        parts.append(f"管理层解释：{_zh_text(review.get('management_explanation'))}")
    if review.get("answer_quality"):
        parts.append(f"回答质量：`{_answer_quality_label(review.get('answer_quality'))}`")
    if review.get("consistency_with_layer1") or review.get("consistency_with_layer2"):
        parts.append(
            f"一致性：相对第一层 `{_status_label(review.get('consistency_with_layer1') or '未知')}`，相对第二层 `{_status_label(review.get('consistency_with_layer2') or '未知')}`"
        )
    if review.get("still_unknown"):
        parts.append(f"仍未知：{_join(review.get('still_unknown'))}")
    if review.get("evidence"):
        parts.append(f"证据索引：{_evidence_refs(review.get('evidence'))}")
    return "\n".join(parts) if parts else fallback


def _narrative_summary(pack: dict[str, Any], keywords: list[str]) -> str:
    narratives = _as_list(pack.get("decision_relevant_narratives"))
    matches = []
    lowered = [keyword.lower() for keyword in keywords]
    for item in narratives:
        haystack = " ".join(str(item.get(key) or "") for key in ["title", "summary", "why_it_matters", "narrative_type"]).lower()
        if any(keyword.lower() in haystack for keyword in lowered):
            matches.append(item)
    if not matches:
        return "当前官方证据包未找到匹配叙事。"
    lines: list[str] = []
    for item in matches:
        lines.append(f"- {_narrative_title(item)}：{_zh_text(item.get('summary') or item.get('why_it_matters') or '未披露')}")
        if item.get("why_it_matters"):
            lines.append(f"  - 为什么重要：{_zh_text(item.get('why_it_matters'))}")
        if item.get("evidence_bundle") or item.get("evidence"):
            lines.append(f"  - 证据索引：{_evidence_refs(item.get('evidence_bundle') or item.get('evidence'))}")
    return "\n".join(lines)


def _rendered(answer: dict[str, Any], key: str) -> str:
    return str((answer.get("rendered_answer") or {}).get(key) or "")


def _source_trace(*items: dict[str, Any]) -> str:
    traces: list[str] = []
    for item in items:
        if not item:
            continue
        rendered = item.get("rendered_answer") or {}
        if rendered.get("source_trace"):
            traces.append(_zh_text(rendered["source_trace"]))
        for evidence in _as_list(item.get("evidence"))[:4]:
            if isinstance(evidence, dict):
                traces.append(
                    "{period} / {doc} / {speaker} / {block}".format(
                        period=evidence.get("period") or "",
                        doc=_source_doc_label(evidence.get("source_document") or evidence.get("source_id") or ""),
                        speaker=evidence.get("speaker") or "",
                        block=evidence.get("block_id") or "",
                    ).strip(" /")
                )
    return "; ".join(_unique_list([trace for trace in traces if trace])) or "见证据包"


def _find_topic(topics: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    lowered = [keyword.lower() for keyword in keywords]
    for topic in topics:
        haystack = " ".join(str(topic.get(key) or "") for key in ["topic", "analyst_concern", "management_response_read"]).lower()
        if any(keyword.lower() in haystack for keyword in lowered):
            return topic
    return {}


def _find_review(reviews: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    lowered = [keyword.lower() for keyword in keywords]
    for review in reviews:
        haystack = " ".join(str(review.get(key) or "") for key in ["issue_id", "issue_text", "management_explanation"]).lower()
        if any(keyword.lower() in haystack for keyword in lowered):
            return review
    return {}


def _bullet_lines(items: Any) -> list[str]:
    lines = []
    for item in _as_list(items) or ["未披露"]:
        if item in {None, ""}:
            continue
        lines.append(f"- {_zh_text(item)}")
    return lines or ["- 未披露"]


def _paragraph_or_bullets(value: Any) -> list[str]:
    if isinstance(value, list):
        return _bullet_lines(value)
    text = str(value or "未披露")
    if "\n" not in text:
        return [text]
    return [line for line in text.splitlines() if line.strip()]


def _unique_list(items: list[Any]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen or text == "n/a":
            continue
        seen.add(text)
        result.append(text)
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("items", "sources", "records", "rows"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
        if all(isinstance(item, dict) for item in value.values()):
            return list(value.values())
        return [value]
    return [value]


def _first_summary(items: Any) -> str:
    items = _as_list(items)
    if not items:
        return "未披露"
    first = items[0] or {}
    if isinstance(first, dict):
        return str(first.get("quote_or_summary") or first.get("exact_fact_or_summary") or first.get("summary") or "未披露")
    return str(first)


def _first_evidence_summary(items: Any) -> str:
    items = _as_list(items)
    if not items:
        return "未披露"
    first = items[0]
    if isinstance(first, dict):
        return str(first.get("exact_fact_or_summary") or first.get("quote_or_summary") or first.get("source_document") or "未披露")
    return str(first)


def _evidence_refs(items: Any) -> str:
    refs = []
    for item in _as_list(items):
        if not isinstance(item, dict):
            refs.append(str(item))
            continue
        bits = [
            item.get("period"),
            _source_doc_label(item.get("source_document") or item.get("source_id")),
            item.get("speaker"),
            item.get("block_id"),
        ]
        refs.append(" / ".join(str(bit) for bit in bits if bit))
    return "; ".join(refs) or "未披露"


def _status_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "Draft pending audit review": "草稿，待审阅",
        "passed": "通过",
        "calculated": "已计算",
        "partial": "部分回答",
        "answered": "已回答",
        "unknown": "未知",
        "unknown_to_partial": "从未知推进到部分回答",
        "not_disclosed": "未披露",
        "not_disclosed_as_structured_numeric_fact": "未作为结构化数字披露",
        "narrative_only_unless_future_tables_disclose_amounts": "仅有叙事，未来表格披露前不能量化",
        "partially_disclosed": "部分披露",
        "supports": "支持",
        "clarifies": "澄清",
        "weakens": "削弱",
        "mixed": "混合",
        "consistent": "一致",
        "partially_consistent": "部分一致",
        "new_unproven": "新增但未证实",
        "not_tested": "未测试",
        "review": "待复核",
        "raw_transcript_not_independently_verified": "原始电话会文本未独立复核",
    }
    return labels.get(text, text or "未知")


def _answer_quality_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "avoided": "回避核心问题",
        "specific_without_numbers": "具体但缺少数字",
        "directional_only": "只有方向性回答",
        "specific_with_numbers": "具体且有数字",
        "partial": "部分回答",
        "unknown": "未知",
    }
    return labels.get(text, _status_label(text))


def _role_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "starting_point": "起点",
        "positive_driver": "正向驱动",
        "negative_driver": "负向驱动",
        "profit_headwind_when_increases": "增加会拖累利润",
        "cash_source_liability": "现金来源型经营负债",
        "cash_use_asset": "现金使用型经营资产",
        "below_operating_driver": "经营利润以下驱动",
        "below_operating_headwind_when_increases": "增加会拖累净利润",
        "result": "结果",
        "subtotal": "小计",
        "derived": "派生指标",
    }
    return labels.get(text, text)


def _source_type_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "filing": "官方文件",
        "official_filing": "官方文件",
        "official_event": "官方事件",
        "earnings_call_transcript": "业绩电话会纪要",
        "transcript": "电话会纪要",
        "raw_transcript_not_independently_verified": "原始电话会文本未独立复核",
    }
    return labels.get(text, text)


def _source_doc_label(value: Any) -> str:
    text = str(value or "").strip()
    replacements = {
        "1Q 2026 Earnings Conference Call": "2026Q1 业绩电话会",
        "Q1 2026 Earnings Conference Call": "2026Q1 业绩电话会",
        "Earnings Conference Call": "业绩电话会",
        "PDD Holdings Announces First Quarter 2026 Unaudited Financial Results": "PDD Holdings 2026Q1 未经审计业绩公告",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _narrative_type_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "business_model": "业务模式",
        "revenue_mix": "收入结构",
        "strategy": "战略",
        "cost_structure": "成本结构",
        "regulation": "监管",
        "governance": "治理",
        "accounting_estimate": "会计估计",
        "capital_allocation": "资本配置",
        "risk": "风险",
        "KPI": "KPI",
    }
    return labels.get(text, text or "未分类")


def _narrative_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("narrative_id") or "叙事").strip()
    replacements = {
        "Management narrative": "管理层叙事",
        "First-party brand": "自营品牌",
        "first-party brand": "自营品牌",
        "global business": "全球业务",
        "Global business": "全球业务",
        "Supply-chain investment": "供应链投入",
        "Revenue mix": "收入结构",
    }
    for source, target in replacements.items():
        title = title.replace(source, target)
    return title


def _gap_why_cn(gap: dict[str, Any]) -> str:
    gap_id = str(gap.get("gap_id") or "")
    by_id = {
        "temu_standalone_economics": "Temu / 全球业务可能改变增长、履约成本、监管风险和利润率；没有单独经济性时，不能把它直接建模为已验证增长引擎。",
        "first_party_brand_unit_economics": "自营品牌可能让平台模式变重，但官方文件尚未量化其收入、利润、库存风险和投入回收期。",
        "cost_of_revenue_subcomponents": "成本细项用于判断利润率压力来自履约、支付、技术、平台治理还是商家支持。",
        "user_and_transaction_kpis": "收入组件已经披露，但用户、交易量、商家数和抽佣率驱动还不是稳定结构化事实。",
        "maintenance_vs_growth_capex": "维护性资本开支和增长性资本开支拆分会影响所有者收益质量。",
    }
    return by_id.get(gap_id, _zh_text(gap.get("why_it_matters") or "当前来源集未回答。"))


def _metric_list_cn(items: Any, *, fallback: str = "未披露") -> str:
    return _join([_metric_label(item) for item in _as_list(items)], fallback=fallback)


def _zh_text(value: Any) -> str:
    text = str(value or "未披露")
    replacements = {
        "n/a": "未披露",
        "N/A": "未披露",
        "Unknown from reviewed official filings.": "当前已审阅官方文件未回答。",
        "No matching official narrative found in current evidence pack.": "当前官方证据包未找到匹配叙事。",
        "Standalone economics are not disclosed.": "单独经济性未披露。",
        "Incremental operating margin is negative.": "增量经营利润率为负。",
        "Incremental FCF margin is negative.": "增量自由现金流率为负。",
        "Incremental operating margin is below latest operating margin.": "增量经营利润率低于最新经营利润率。",
        "Restricted cash exceeds 25% of cash.": "受限现金超过现金的 25%。",
        "Optional balance-sheet details are missing:": "可选资产负债表细项缺失：",
        "Investment income/loss is more than 20% of pretax income.": "投资收益 / 损失超过税前利润的 20%。",
        "receivables_from_online_payment_platforms grew more than 10 percentage points faster than revenue.": "应收在线支付平台款项增速高于收入增速 10 个百分点以上。",
        "prepayments_and_other_current_assets grew more than 10 percentage points faster than revenue.": "预付款及其他流动资产增速高于收入增速 10 个百分点以上。",
        "营运资本 source liabilities added more than 5% of revenue to cash-flow tailwind.": "营运资本中现金来源型负债贡献超过收入的 5%。",
        "Management narrative": "管理层叙事",
        "business / revenue / KPI disclosure": "业务 / 收入 / KPI 披露",
        "operating results / cost discussion": "经营结果 / 成本讨论",
        "official filing text": "官方文件文本",
        "notes / liquidity / risk factors": "附注 / 流动性 / 风险因素",
        "diagnostic_findings": "诊断发现",
        "Layer 1": "第一层",
        "Layer 2": "第二层",
        "Layer 3": "第三层",
        "first-party brand": "自营品牌",
        "First-party brand": "自营品牌",
        "global business": "全球业务",
        "Global business": "全球业务",
        "online marketing services": "在线营销服务",
        "Online marketing services": "在线营销服务",
        "online marketing": "在线营销",
        "Online marketing": "在线营销",
        "transaction services": "交易服务",
        "Transaction services": "交易服务",
        "take-rate": "抽佣率",
        "ad ROI": "广告投资回报",
        "ROI": "投资回报",
        "P&L": "损益",
        "pivot": "战略转向",
        "cohort": "分群",
        "orders": "订单",
        "active buyers": "活跃买家",
        "monthly active users": "月活用户",
        "share-count": "股数",
        "repurchase": "回购",
        "basic/diluted shares": "基本 / 摊薄股数",
        "diluted shares YoY": "摊薄股数同比",
        "equity plan": "股权计划",
        "RSU/options": "RSU / 期权",
        "ADS/common share ratio": "ADS / 普通股比例",
        "ADS bridge": "ADS 桥",
        "below-operating": "经营利润以下",
        "YoY": "同比",
        "QoQ": "环比",
        "S&M": "销售与营销",
        "R&D": "研发",
        "G&A": "管理费用",
        "proxy": "股东代理文件",
        "bandwidth and server": "带宽和服务器",
        "merchant support": "商家支持",
        "platform operation": "平台运营",
        "investment payback": "投入回收期",
        "fair value": "公允价值",
        "amortization": "摊销",
        "tax effect": "税务影响",
        "CFO": "财务负责人",
        "财务负责人 ": "财务负责人",
        "Conference Call": "电话会",
        "conference call": "电话会",
        "Earnings Release": "业绩公告",
        "earnings release": "业绩公告",
        "owner-usable cash": "股东可用现金",
        "owner usable cash": "股东可用现金",
        "owner earnings proxy": "所有者收益近似值",
        "owner-return framework": "股东回报框架",
        "working-capital": "营运资本",
        "Working-capital": "营运资本",
        "merchant float": "商家资金沉淀",
        "disclosure gap": "披露缺口",
        "future filing": "未来官方文件",
        "future 官方文件": "未来官方文件",
        "filing": "官方文件",
        "capex": "资本开支",
        "CapEx": "资本开支",
        "cost of revenue": "收入成本",
        "fulfillment": "履约",
        "payment processing": "支付处理",
        "merchant payable": "应付商家款项",
        "deposits": "保证金",
        "receivables": "应收款项",
        "prepayments": "预付款",
        "inventory": "存货",
        "payables": "应付款项",
        "deferred revenue": "递延收入",
        "purchase commitments": "采购承诺",
        "warehouse lease": "仓库租赁",
        "margin floor": "利润率底线",
        "first_party_revenue": "自营品牌收入",
        "first_party_inventory_risk": "自营品牌库存风险",
        "first_party_operating_income": "自营品牌经营利润",
        "first_party_investment_payback": "自营品牌投入回收期",
        "temu_revenue": "Temu 收入",
        "temu_operating_income": "Temu 经营利润",
        "temu_gmv": "Temu GMV",
        "temu_fulfillment_cost": "Temu 履约成本",
        "gmv": "GMV",
        "active_buyers": "活跃买家",
        "monthly_active_users": "月活用户",
        "take_rate": "抽佣率",
        "广告 抽佣率": "广告抽佣率",
        "商家广告 投资回报": "商家广告投资回报",
        "抽佣率 或": "抽佣率或",
        "单独 损益": "单独损益",
        "战略 战略转向": "战略转向",
        "自营品牌 是否": "自营品牌是否",
        "缺少 抽佣率": "缺少抽佣率",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _metric_value(metric: dict[str, Any], latest: dict[str, Any]) -> str:
    unit = latest.get("unit") or metric.get("unit")
    value = latest.get("value")
    if value is None:
        return ""
    if unit == "ratio":
        return _pct(value)
    if unit == "CNY":
        return _money(value)
    return _md_cell(value)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    num = _num(numerator)
    den = _num(denominator)
    if num is None or den in {None, 0}:
        return None
    return num / den


def _growth(current: Any, prior: Any) -> float | None:
    divided = _safe_div(current, prior)
    return (divided - 1) if divided is not None else None


def _cagr(start: Any, end: Any, years: int) -> float | None:
    start_num = _num(start)
    end_num = _num(end)
    if start_num is None or end_num is None or start_num <= 0 or years <= 0:
        return None
    return (end_num / start_num) ** (1 / years) - 1


def _money(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未披露"
    return f"RMB {number / 1_000_000_000:.1f}B"


def _money_abs(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未披露"
    return _money(abs(number))


def _pct(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未披露"
    return f"{number * 100:.1f}%"


def _ratio_x(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未披露"
    return f"{number:.2f}x"


def _fmt_int(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未知"
    return f"{int(number):,}"


def _broad_cash(row: dict[str, Any]) -> float:
    return sum(_num(row.get(metric)) or 0 for metric in ["cash", "restricted_cash", "short_term_investments"])


def _cost_ratio(row: dict[str, Any]) -> float | None:
    revenue = _num(row.get("revenue"))
    if not revenue:
        return None
    direct_cost_ratio = _safe_div(row.get("cost_of_revenue"), revenue)
    if direct_cost_ratio is not None:
        return direct_cost_ratio
    gross_margin = _safe_div(row.get("gross_profit"), revenue)
    if gross_margin is None:
        return None
    return 1 - gross_margin


def _opex_ratio(row: dict[str, Any]) -> float | None:
    revenue = _num(row.get("revenue"))
    if not revenue:
        return None
    opex = sum(
        _num(row.get(metric)) or 0
        for metric in [
            "sales_and_marketing_expense",
            "research_and_development_expense",
            "general_and_administrative_expense",
        ]
    )
    return opex / revenue


def _revenue_component_sentence(row: dict[str, Any], *, prefix: str) -> str:
    revenue = row.get("revenue")
    return (
        f"{prefix}收入 {_money(revenue)}；在线营销服务及其他 {_money(row.get('online_marketing_services_revenue'))}"
        f"（占 {_pct(_safe_div(row.get('online_marketing_services_revenue'), revenue))}）；"
        f"交易服务 {_money(row.get('transaction_services_revenue'))}"
        f"（占 {_pct(_safe_div(row.get('transaction_services_revenue'), revenue))}）。"
    )


def _quarter_revenue_component_sentence(row: dict[str, Any], source_growth: dict[str, Any]) -> str:
    revenue = row.get("revenue")
    top = source_growth.get("top_component") or {}
    return (
        f"最新季度收入 {_money(revenue)}；交易服务 {_money(row.get('transaction_services_revenue'))}"
        f"（占 {_pct(_safe_div(row.get('transaction_services_revenue'), revenue))}）；"
        f"在线营销服务及其他 {_money(row.get('online_marketing_services_revenue'))}"
        f"（占 {_pct(_safe_div(row.get('online_marketing_services_revenue'), revenue))}）；"
        f"最大组件为 {_metric_label(top.get('metric'))}。"
    )


def _working_capital_component_sentence(result: dict[str, Any]) -> str:
    details = result.get("component_details") or []
    sources = [row for row in details if row.get("role") == "cash_source_liability"]
    if not sources:
        return "营运资本细项未形成可展示桥。"
    top = sorted(sources, key=lambda row: abs(_num(row.get("delta")) or 0), reverse=True)[:4]
    parts = [f"{_metric_label(row.get('metric'))} {_money(row.get('delta'))}" for row in top if row.get("delta") is not None]
    return "主要现金来源型经营负债变化：" + "；".join(parts) + "。"


def _join(items: Any, *, fallback: str = "未披露") -> str:
    if not items:
        return fallback
    if isinstance(items, str):
        return _zh_text(items or fallback)
    return "，".join(_zh_text(item) for item in items if item not in {None, ""}) or fallback


def _metric_label(metric: Any) -> str:
    labels = {
        "revenue": "收入",
        "cost_of_revenue": "收入成本",
        "gross_profit": "毛利",
        "operating_income": "经营利润",
        "net_income": "净利润",
        "online_marketing_services_revenue": "在线营销服务及其他",
        "transaction_services_revenue": "交易服务",
        "sales_and_marketing_expense": "销售与营销",
        "research_and_development_expense": "研发",
        "general_and_administrative_expense": "管理费用",
        "investment_income": "利息和投资收益",
        "foreign_exchange_gain_loss": "汇兑损益",
        "other_income_net": "其他收益/损失",
        "tax_expense": "税项",
        "equity_method_income": "权益法投资",
        "operating_cash_flow": "经营现金流",
        "free_cash_flow": "自由现金流近似",
        "capex": "资本开支",
        "cash": "现金",
        "restricted_cash": "受限现金",
        "short_term_investments": "短期投资",
        "payable_to_merchants": "应付商家款项",
        "accounts_payable_and_accrued_expenses": "应付账款及应计费用",
        "merchant_deposits": "商家保证金",
        "deferred_revenue": "递延收入",
        "receivables_from_online_payment_platforms": "应收在线支付平台款项",
        "prepayments_and_other_current_assets": "预付款及其他流动资产",
        "gmv": "GMV",
        "active_buyers": "活跃买家",
        "monthly_active_users": "月活用户",
        "orders": "订单",
        "take_rate": "抽佣率",
        "fulfillment_fees": "履约费用",
        "payment_processing_fees": "支付处理费用",
        "bandwidth_and_server_costs": "带宽和服务器成本",
        "merchant_support_costs": "商家支持成本",
        "platform_operation_costs": "平台运营成本",
        "first_party_revenue": "自营品牌收入",
        "first_party_inventory_risk": "自营品牌库存风险",
        "first_party_operating_income": "自营品牌经营利润",
        "first_party_investment_payback": "自营品牌投入回收期",
        "temu_revenue": "Temu 收入",
        "temu_operating_income": "Temu 经营利润",
        "temu_gmv": "Temu GMV",
        "temu_fulfillment_cost": "Temu 履约成本",
        "maintenance_capex": "维护性资本开支",
        "growth_capex": "增长性资本开支",
    }
    return labels.get(str(metric), str(metric or "未披露").replace("_", " "))


def _md_cell(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|")
    return " ".join(text.split())
