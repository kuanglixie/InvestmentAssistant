from __future__ import annotations

from html import escape
from typing import Any


def build_financial_visual_report(
    pack: dict[str, Any],
    *,
    audit_status: str = "Draft pending audit review",
    markdown_report_path: str | None = None,
    official_evidence_pack: dict[str, Any] | None = None,
    management_communication_pack: dict[str, Any] | None = None,
) -> str:
    company = (pack.get("company") or {}).get("legal_name") or pack.get("company") or "Company"
    annual_rows = _annual_rows(pack)
    quarterly_rows = _quarterly_rows(pack)
    metrics = _metrics_by_id(pack)
    latest_annual = annual_rows[-1] if annual_rows else {}
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}

    summary_cards = _summary_cards(pack, latest_annual, latest_quarter, metrics)
    operating_bridge = _operating_bridge_items(metrics)
    below_operating_bridge = _below_operating_bridge_items(metrics)
    working_capital_bridge = _working_capital_items(metrics)
    revenue_structure_rows = _revenue_structure_rows(annual_rows)

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>财务可视化报告：{escape(str(company))}</title>",
            "<style>",
            _CSS,
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            _hero(company, audit_status, pack, markdown_report_path),
            _summary_grid(summary_cards),
            _decision_snapshot(annual_rows, quarterly_rows, metrics),
            '<section class="section">',
            "<h2>一、财务主线</h2>",
            '<p class="section-lead">这里先回答“业务还在增长吗、利润为什么没同步兑现、现金是否能支撑投入期”。Markdown 继续作为底稿；HTML 负责把主线直接交给读者。</p>',
            '<div class="chart-grid">',
            _chart_card(
                "三年/多年趋势",
                "收入、经营利润、净利润和经营现金流是否同向。",
                _line_chart(
                    annual_rows,
                    [
                        ("revenue", "收入", "#2563eb"),
                        ("operating_income", "经营利润", "#16a34a"),
                        ("net_income", "净利润", "#dc2626"),
                        ("operating_cash_flow", "经营现金流", "#7c3aed"),
                    ],
                ),
                insight=_trend_insight(annual_rows),
            ),
            _chart_card(
                "收入结构",
                "区分在线营销服务及其他与交易服务，避免只看总收入。",
                _stacked_bar_chart(
                    revenue_structure_rows,
                    [
                        ("online_marketing_services_revenue", "在线营销服务及其他", "#2563eb"),
                        ("transaction_services_revenue", "交易服务", "#f97316"),
                    ],
                ),
                insight=_revenue_mix_insight(annual_rows, metrics),
            ),
            "</div>",
            "</section>",
            '<section class="section">',
            "<h2>二、桥表：把变化来源摆出来</h2>",
            '<p class="section-lead">桥表把“为什么”从长段落里拿出来：新增收入、成本/费用、经营利润以下项目、营运资本分别贡献了什么。</p>',
            '<div class="chart-grid">',
            _chart_card(
                "经营利润桥",
                "解释最新年度收入增长为什么没有转成经营利润增长。",
                _delta_bar_chart(operating_bridge, unit_label="RMB bn"),
                insight=_operating_bridge_insight(metrics),
            ),
            _chart_card(
                "经营利润以下桥",
                "解释最新季度经营利润改善但净利润下降的主要来源。",
                _delta_bar_chart(below_operating_bridge, unit_label="RMB bn"),
                insight=_below_operating_insight(metrics),
            ),
            _chart_card(
                "营运资本现金桥",
                "区分经营现金流来自利润，还是来自经营负债/平台浮存金顺风。",
                _delta_bar_chart(working_capital_bridge, unit_label="RMB bn"),
                insight=_working_capital_insight(metrics),
            ),
            _chart_card(
                "现金与短投构成",
                "账面现金厚，但受限现金和短投要分开读。",
                _cash_stack(latest_annual),
                insight=_cash_insight(latest_annual),
            ),
            "</div>",
            "</section>",
            '<section class="section">',
            "<h2>三、三层证据合并读法</h2>",
            _layer_evidence_summary(
                pack,
                official_evidence_pack or {},
                management_communication_pack or {},
            ),
            "</section>",
            '<section class="section">',
            "<h2>四、仍需追踪的披露缺口</h2>",
            _gap_cards((pack.get("fact_extraction_summary") or {}).get("disclosure_gap_registry") or []),
            "</section>",
            '<section class="section appendix">',
            "<h2>附录：读取方式</h2>",
            "<p>本 HTML 从 <code>financial_report_pack.json</code> 生成。Markdown 仍保留为审阅稿；HTML 用于图表、首页仪表板和后续 drill-down。当前版本不包含价格、目标价、买卖建议或 reverse DCF。</p>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _hero(
    company: Any,
    audit_status: str,
    pack: dict[str, Any],
    markdown_report_path: str | None,
) -> str:
    generated_at = pack.get("generated_at") or "unknown"
    md_line = (
        f'<span>Markdown review copy: <code>{escape(markdown_report_path)}</code></span>'
        if markdown_report_path
        else "<span>Markdown review copy: not linked</span>"
    )
    return f"""
<section class="hero">
  <div>
    <p class="eyebrow">Financial Visual Report</p>
    <h1>财务可视化报告：{escape(str(company))}</h1>
    <p class="hero-copy">面向图表阅读的财报证据入口；保留事实边界，不输出估值或买卖建议。</p>
  </div>
  <div class="meta">
    <span>Audit status: <code>{escape(audit_status)}</code></span>
    <span>Generated at: <code>{escape(str(generated_at))}</code></span>
    {md_line}
  </div>
</section>
""".strip()


def _summary_cards(
    pack: dict[str, Any],
    latest_annual: dict[str, Any],
    latest_quarter: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
) -> list[tuple[str, str, str]]:
    margin = _latest_annual_metric(metrics, "margin_profile_v1")
    incremental = _latest_annual_metric(metrics, "incremental_margin_v1")
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1")
    cash_conversion = _latest_annual_metric(metrics, "cash_conversion_ratio_v1")
    source_growth = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    top_component = source_growth.get("top_component") or {}
    cfo_to_net_income = (
        (cash_conversion or {}).get("value")
        if cash_conversion
        else _safe_div(_num(latest_annual.get("operating_cash_flow")), _num(latest_annual.get("net_income")))
    )
    return [
        (
            "财务状态",
            _status_label(pack.get("financial_health_status") or "unknown"),
            f"Score: {_number(pack.get('financial_health_score'), digits=1)}/10",
        ),
        (
            "最新年度收入",
            _money(latest_annual.get("revenue")),
            f"同比 {_pct(latest_annual.get('revenue_growth_yoy') or (margin or {}).get('revenue_growth_yoy'))}",
        ),
        (
            "经营利润率",
            _pct((margin or {}).get("operating_margin") or latest_annual.get("operating_margin")),
            f"增量经营利润率 {_pct((incremental or {}).get('incremental_operating_margin'))}",
        ),
        (
            "现金转化",
            f"CFO/NI {_ratio_x(cfo_to_net_income)}",
            f"营运资本顺风/收入 {_pct((working_capital or {}).get('working_capital_cash_tailwind_to_revenue'))}",
        ),
        (
            "最新季度",
            _text(latest_quarter.get("quarter") or latest_quarter.get("period_end") or "unknown"),
            f"收入 {_money(latest_quarter.get('revenue'))}；净利润 {_money(latest_quarter.get('net_income'))}",
        ),
        (
            "最大收入组件",
            _metric_label(top_component.get("metric") or "unknown"),
            f"占比 {_pct(top_component.get('share_of_revenue'))}",
        ),
    ]


def _summary_grid(cards: list[tuple[str, str, str]]) -> str:
    items = []
    for title, value, note in cards:
        items.append(
            f"""
<article class="kpi-card">
  <div class="kpi-title">{escape(title)}</div>
  <div class="kpi-value">{escape(value)}</div>
  <div class="kpi-note">{escape(note)}</div>
</article>
""".strip()
        )
    return '<section class="kpi-grid">' + "\n".join(items) + "</section>"


def _decision_snapshot(
    annual_rows: list[dict[str, Any]],
    quarterly_rows: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
) -> str:
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    quarter = quarterly_rows[-1] if quarterly_rows else {}
    margin = _latest_annual_metric(metrics, "margin_profile_v1") or {}
    incremental = _latest_annual_metric(metrics, "incremental_margin_v1") or {}
    working_capital = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    source_growth = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    revenue_growth = margin.get("revenue_growth_yoy") or _growth(latest.get("revenue"), prior.get("revenue"))
    operating_growth = _growth(latest.get("operating_income"), prior.get("operating_income"))
    net_growth = _growth(latest.get("net_income"), prior.get("net_income"))
    q_revenue_growth = source_growth.get("revenue_growth_yoy")
    q_net_growth = _growth(quarter.get("net_income"), None)
    top_component = (source_growth.get("top_component") or {}).get("metric")
    items = [
        (
            "当前结论",
            (
                f"公司仍在增长，最新年度收入同比 {_pct(revenue_growth)}，但经营利润同比 {_pct(operating_growth)}、"
                f"净利润同比 {_pct(net_growth)}。这不是“没有增长”，而是增长没有稳定兑现为利润。"
            ),
        ),
        (
            "核心争议",
            (
                f"增量经营利润率为 {_pct(incremental.get('incremental_operating_margin'))}，"
                "需要区分这是主动供应链/商家支持投入，还是交易服务扩张带来的结构性成本压力。"
            ),
        ),
        (
            "现金读法",
            (
                f"CFO/NI 为 {_ratio_x((_latest_annual_metric(metrics, 'cash_conversion_ratio_v1') or {}).get('value'))}，"
                f"但营运资本现金顺风/收入为 {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}，"
                "所以现金流强，但不能全部理解为纯利润质量。"
            ),
        ),
        (
            "下一步要证伪",
            (
                f"最新季度收入同比 {_pct(q_revenue_growth)}，最大季度收入组件是 {_metric_label(top_component)}。"
                "后续最先看增量经营利润率、履约/支付/商家支持成本、经营利润以下项目是否修复。"
            ),
        ),
    ]
    cards = []
    for title, body in items:
        cards.append(
            f"""
<article class="thesis-card">
  <h3>{escape(title)}</h3>
  <p>{escape(body)}</p>
</article>
""".strip()
        )
    return '<section class="section thesis-section"><h2>主报告摘要</h2><div class="thesis-grid">' + "\n".join(cards) + "</div></section>"


def _trend_insight(annual_rows: list[dict[str, Any]]) -> str:
    if len(annual_rows) < 2:
        return "年度数据不足，趋势判断只能保留。"
    latest, prior = annual_rows[-1], annual_rows[-2]
    return (
        f"最新年度收入同比 {_pct(_growth(latest.get('revenue'), prior.get('revenue')))}，"
        f"经营利润同比 {_pct(_growth(latest.get('operating_income'), prior.get('operating_income')))}，"
        f"净利润同比 {_pct(_growth(latest.get('net_income'), prior.get('net_income')))}；"
        "主线是收入继续增长，但利润兑现回落。"
    )


def _revenue_mix_insight(
    annual_rows: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
) -> str:
    latest = annual_rows[-1] if annual_rows else {}
    revenue = _num(latest.get("revenue"))
    online = _num(latest.get("online_marketing_services_revenue"))
    transaction = _num(latest.get("transaction_services_revenue"))
    latest_interim = (metrics.get("source_of_growth_attribution_v1") or {}).get("latest_interim_result") or {}
    top = latest_interim.get("top_component") or {}
    if revenue and online is not None and transaction is not None:
        return (
            f"年度口径下在线营销服务及其他占 {_pct(online / revenue)}，交易服务占 {_pct(transaction / revenue)}；"
            f"最新季度最大组件为 {_metric_label(top.get('metric'))}，占 {_pct(top.get('share_of_revenue'))}。"
        )
    return "收入组件披露不足，不能把收入增长进一步拆成业务驱动。"


def _operating_bridge_insight(metrics: dict[str, dict[str, Any]]) -> str:
    result = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    return (
        f"最新年度收入增加 {_money(result.get('revenue_delta'))}，但经营利润变化为 {_money(result.get('operating_income_delta'))}；"
        f"增量经营利润率 {_pct(result.get('incremental_operating_margin'))}，说明新增收入的边际盈利弱于存量业务。"
    )


def _below_operating_insight(metrics: dict[str, dict[str, Any]]) -> str:
    result = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    return (
        f"最新季度经营利润变化 {_money(result.get('operating_income_delta'))}，净利润变化 {_money(result.get('net_income_delta'))}；"
        f"经营利润以下净拖累变化 {_money(result.get('below_operating_delta'))}，所以需要单独拆投资收益、其他收益/损失和税项。"
    )


def _working_capital_insight(metrics: dict[str, dict[str, Any]]) -> str:
    result = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    return (
        f"经营负债现金来源增加 {_money(result.get('cash_source_liability_delta'))}，"
        f"经营资产现金占用增加 {_money(result.get('cash_use_asset_delta'))}；"
        f"净营运资本顺风/收入 {_pct(result.get('working_capital_cash_tailwind_to_revenue'))}。"
    )


def _cash_insight(latest_annual: dict[str, Any]) -> str:
    cash = _num(latest_annual.get("cash"))
    restricted = _num(latest_annual.get("restricted_cash"))
    short_term = _num(latest_annual.get("short_term_investments"))
    total = (cash or 0) + (restricted or 0) + (short_term or 0)
    restricted_share = restricted / total if restricted is not None and total else None
    return (
        f"现金、受限现金与短投合计 {_money(total)}，其中受限现金占广义资金 {_pct(restricted_share)}；"
        "资产负债表强，但可自由使用现金需要继续看附注和 VIE/跨境转移限制。"
    )


def _layer_evidence_summary(
    pack: dict[str, Any],
    official_evidence_pack: dict[str, Any],
    management_communication_pack: dict[str, Any],
) -> str:
    layer1_cards = _layer1_cards(pack)
    official_cards = _official_answer_cards(official_evidence_pack)
    management_cards = _management_cards(management_communication_pack)
    return (
        '<div class="layer-grid">'
        + _evidence_column("第一层：硬数字", "固定公式与结构化事实；负责发现模式和红旗。", layer1_cards)
        + _evidence_column("第二层：官方文件", "20-F / 6-K / 附注 / 业绩稿；负责解释哪些问题能被官方记录支持。", official_cards)
        + _evidence_column("第三层：管理层沟通", "电话会与 Q&A；负责判断管理层是否正面回应核心争议。", management_cards)
        + "</div>"
    )


def _layer1_cards(pack: dict[str, Any]) -> list[str]:
    findings = pack.get("diagnostic_findings") or {}
    questions = findings.get("questions") or []
    cards = []
    for question in questions[:3]:
        title = question.get("question") or question.get("question_id") or "diagnostic"
        key_read = question.get("current_judgment") or question.get("key_read") or question.get("short_answer")
        evidence = question.get("key_evidence") or question.get("evidence") or ""
        text = "；".join(str(item) for item in [key_read, evidence] if item)
        if text:
            cards.append(f"<strong>{escape(str(title))}</strong><br>{escape(text)}")
    if not cards:
        status = pack.get("financial_health_status") or "unknown"
        cards.append(f"财务质量状态：{escape(_status_label(status))}。")
    return cards


def _official_answer_cards(pack: dict[str, Any]) -> list[str]:
    cards = []
    for answer in (pack.get("question_answers") or [])[:3]:
        title = answer.get("question_title") or answer.get("question_text") or answer.get("question_id")
        rendered = answer.get("rendered_answer") or {}
        judgment = rendered.get("our_judgment") or answer.get("short_answer")
        if title and judgment:
            cards.append(f"<strong>{escape(str(title))}</strong><br>{escape(str(judgment))}")
    if not cards:
        cards.append("当前没有可展示的官方文件解释摘要；详见 Markdown 底稿和 official evidence pack。")
    return cards


def _management_cards(pack: dict[str, Any]) -> list[str]:
    cards = []
    for topic in (pack.get("qa_pressure_topics") or [])[:3]:
        title = topic.get("topic") or "Q&A"
        response = topic.get("management_response_read") or topic.get("analyst_concern")
        quality = topic.get("answer_quality")
        if response:
            suffix = f"（回答质量：{quality}）" if quality else ""
            cards.append(f"<strong>{escape(str(title))}</strong><br>{escape(str(response) + suffix)}")
    if not cards:
        cards.append("当前没有可展示的管理层沟通摘要；管理层文字稿仍作为低权重证据。")
    return cards


def _evidence_column(title: str, lead: str, cards: list[str]) -> str:
    items = "\n".join(f'<li>{card}</li>' for card in cards)
    return f"""
<article class="layer-card">
  <h3>{escape(title)}</h3>
  <p>{escape(lead)}</p>
  <ul>{items}</ul>
</article>
""".strip()


def _chart_card(title: str, subtitle: str, chart_html: str, *, insight: str | None = None) -> str:
    insight_html = f'<p class="chart-insight"><strong>结论：</strong>{escape(insight)}</p>' if insight else ""
    return f"""
<article class="chart-card">
  <header>
    <h3>{escape(title)}</h3>
    <p>{escape(subtitle)}</p>
  </header>
  {chart_html}
  {insight_html}
</article>
""".strip()


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


def _metrics_by_id(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(metric.get("formula_id")): metric
        for metric in pack.get("financial_metrics") or []
        if metric.get("formula_id")
    }


def _latest_annual_metric(
    metrics: dict[str, dict[str, Any]],
    formula_id: str,
) -> dict[str, Any] | None:
    annual_results = (metrics.get(formula_id) or {}).get("annual_results") or []
    calculated = [row for row in annual_results if row.get("status") == "calculated"]
    return calculated[-1] if calculated else (annual_results[-1] if annual_results else None)


def _revenue_structure_rows(annual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in annual_rows
        if _num(row.get("online_marketing_services_revenue")) is not None
        or _num(row.get("transaction_services_revenue")) is not None
    ]
    return rows[-5:]


def _operating_bridge_items(metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = _latest_annual_metric(metrics, "operating_profit_bridge_v1") or {}
    items = []
    for row in result.get("bridge_rows") or []:
        metric = str(row.get("metric") or "")
        delta = _num(row.get("delta"))
        role = str(row.get("role") or "")
        if delta is None or metric == "gross_profit":
            continue
        if metric == "operating_income":
            items.append({"label": "经营利润变化", "value": delta, "kind": "result"})
        elif role == "profit_headwind_when_increases":
            items.append({"label": _metric_label(metric), "value": -delta, "kind": "driver"})
        else:
            items.append({"label": _metric_label(metric), "value": delta, "kind": "driver"})
    return items


def _below_operating_bridge_items(metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = (metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {}
    items = []
    for row in result.get("bridge_rows") or []:
        metric = str(row.get("metric") or "")
        delta = _num(row.get("delta"))
        if delta is None:
            continue
        if metric == "net_income":
            items.append({"label": "净利润变化", "value": delta, "kind": "result"})
        elif metric == "tax_expense":
            items.append({"label": "税项影响", "value": -delta, "kind": "driver"})
        else:
            items.append({"label": _metric_label(metric), "value": delta, "kind": "driver"})
    return items


def _working_capital_items(metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = _latest_annual_metric(metrics, "working_capital_quality_v1") or {}
    items = []
    for row in result.get("component_details") or []:
        delta = _num(row.get("delta"))
        if delta is None:
            continue
        impact = delta if row.get("role") == "cash_source_liability" else -delta
        items.append({"label": _metric_label(row.get("metric")), "value": impact, "kind": "driver"})
    total = _num(result.get("cash_source_liability_delta"))
    use = _num(result.get("cash_use_asset_delta"))
    if total is not None and use is not None:
        items.append({"label": "净现金顺风", "value": total - use, "kind": "result"})
    return items


def _line_chart(rows: list[dict[str, Any]], series: list[tuple[str, str, str]]) -> str:
    rows = rows[-8:]
    if not rows:
        return _empty_chart("没有可用年度事实")
    values = [
        _num(row.get(metric))
        for row in rows
        for metric, _label, _color in series
        if _num(row.get(metric)) is not None
    ]
    if not values:
        return _empty_chart("没有可用趋势数据")
    width, height = 760, 280
    left, right, top, bottom = 58, 24, 24, 46
    y_min = min(0.0, min(values))
    y_max = max(values)
    if y_max == y_min:
        y_max += 1.0
    step_x = (width - left - right) / max(len(rows) - 1, 1)

    def x_at(index: int) -> float:
        return left + index * step_x

    def y_at(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * (height - top - bottom)

    parts = [_svg_open(width, height)]
    parts.append(_axis_lines(width, height, left, right, top, bottom))
    for i, row in enumerate(rows):
        x = x_at(i)
        parts.append(f'<text x="{x:.1f}" y="{height - 18}" text-anchor="middle" class="axis-label">{escape(str(row.get("year")))}</text>')
    for metric, label, color in series:
        points = []
        for index, row in enumerate(rows):
            value = _num(row.get(metric))
            if value is not None:
                points.append(f"{x_at(index):.1f},{y_at(value):.1f}")
        if len(points) >= 2:
            parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(points)}"/>')
        elif len(points) == 1:
            x, y = points[0].split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{left}" y="{18 + 18 * series.index((metric, label, color))}" class="legend" fill="{color}">{escape(label)}</text>')
    parts.append(f'<text x="{left}" y="{top + 12}" class="axis-label">{escape(_money(y_max))}</text>')
    parts.append(f'<text x="{left}" y="{height - bottom}" class="axis-label">{escape(_money(y_min))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _stacked_bar_chart(
    rows: list[dict[str, Any]],
    components: list[tuple[str, str, str]],
) -> str:
    rows = rows[-5:]
    if not rows:
        return _empty_chart("没有可用收入组件")
    width, height = 760, 280
    left, right, top, bottom = 58, 26, 24, 48
    totals = [
        sum(_num(row.get(metric)) or 0.0 for metric, _label, _color in components)
        for row in rows
    ]
    max_total = max(totals) if totals else 0
    if max_total <= 0:
        return _empty_chart("收入组件没有可绘制数值")
    bar_w = (width - left - right) / max(len(rows), 1) * 0.58
    gap = (width - left - right) / max(len(rows), 1)
    parts = [_svg_open(width, height), _axis_lines(width, height, left, right, top, bottom)]
    for i, row in enumerate(rows):
        x = left + i * gap + (gap - bar_w) / 2
        y_cursor = height - bottom
        for metric, _label, color in components:
            value = _num(row.get(metric)) or 0.0
            bar_h = value / max_total * (height - top - bottom)
            y_cursor -= bar_h
            parts.append(f'<rect x="{x:.1f}" y="{y_cursor:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}" rx="4"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{height - 18}" text-anchor="middle" class="axis-label">{escape(str(row.get("year")))}</text>')
    for index, (_metric, label, color) in enumerate(components):
        parts.append(f'<text x="{left + index * 220}" y="18" class="legend" fill="{color}">{escape(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _delta_bar_chart(items: list[dict[str, Any]], *, unit_label: str) -> str:
    if not items:
        return _empty_chart("没有可用桥表数据")
    items = items[-9:]
    values = [_num(item.get("value")) or 0.0 for item in items]
    max_abs = max(abs(value) for value in values) or 1.0
    width, height = 760, 300
    left, right, top, bottom = 62, 24, 24, 78
    plot_h = height - top - bottom
    zero_y = top + plot_h / 2
    bar_w = (width - left - right) / max(len(items), 1) * 0.54
    gap = (width - left - right) / max(len(items), 1)
    parts = [_svg_open(width, height)]
    parts.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width - right}" y2="{zero_y:.1f}" class="zero-line"/>')
    for index, item in enumerate(items):
        value = _num(item.get("value")) or 0.0
        x = left + index * gap + (gap - bar_w) / 2
        bar_h = abs(value) / max_abs * (plot_h / 2 - 12)
        y = zero_y - bar_h if value >= 0 else zero_y
        color = "#16a34a" if value >= 0 else "#dc2626"
        if item.get("kind") == "result":
            color = "#334155"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}" rx="4"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 6 if value >= 0 else y + bar_h + 14:.1f}" text-anchor="middle" class="bar-value">{escape(_bn(value))}</text>')
        parts.append(
            f'<text transform="translate({x + bar_w / 2:.1f},{height - 28}) rotate(-28)" text-anchor="end" class="axis-label">{escape(str(item.get("label") or ""))}</text>'
        )
    parts.append(f'<text x="{left}" y="{top}" class="axis-label">{escape(unit_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _cash_stack(latest_annual: dict[str, Any]) -> str:
    items = [
        ("cash", "现金", "#2563eb"),
        ("restricted_cash", "受限现金", "#f97316"),
        ("short_term_investments", "短期投资", "#16a34a"),
    ]
    values = [(metric, label, color, _num(latest_annual.get(metric)) or 0.0) for metric, label, color in items]
    total = sum(value for _metric, _label, _color, value in values)
    if total <= 0:
        return _empty_chart("没有可用现金构成")
    width, height = 760, 180
    x, y, bar_w, bar_h = 58, 72, 620, 34
    parts = [_svg_open(width, height)]
    cursor = x
    for _metric, label, color, value in values:
        part_w = value / total * bar_w
        parts.append(f'<rect x="{cursor:.1f}" y="{y}" width="{part_w:.1f}" height="{bar_h}" fill="{color}" rx="5"/>')
        if part_w > 70:
            parts.append(f'<text x="{cursor + part_w / 2:.1f}" y="{y + 22}" text-anchor="middle" class="stack-label">{escape(_bn(value))}</text>')
        cursor += part_w
    for index, (_metric, label, color, value) in enumerate(values):
        parts.append(f'<text x="{x + index * 190}" y="34" class="legend" fill="{color}">{escape(label)} {_bn(value)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _gap_cards(gaps: list[dict[str, Any]]) -> str:
    if not gaps:
        return '<p class="muted">当前没有登记 disclosure gaps。</p>'
    cards = []
    for gap in gaps:
        missing = ", ".join(str(item) for item in gap.get("missing_metrics") or [])
        available = ", ".join(str(item) for item in gap.get("available_metrics") or [])
        cards.append(
            f"""
<article class="gap-card">
  <h3>{escape(str(gap.get("gap_id") or "gap"))}</h3>
  <p>{escape(str(gap.get("why_it_matters") or ""))}</p>
  <p><strong>Status:</strong> {escape(str(gap.get("status") or "unknown"))}</p>
  <p><strong>Missing:</strong> {escape(missing or "n/a")}</p>
  {f"<p><strong>Available:</strong> {escape(available)}</p>" if available else ""}
</article>
""".strip()
        )
    return '<div class="gap-grid">' + "\n".join(cards) + "</div>"


def _empty_chart(message: str) -> str:
    return f'<div class="empty-chart">{escape(message)}</div>'


def _svg_open(width: int, height: int) -> str:
    return f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" aria-hidden="true">'


def _axis_lines(width: int, height: int, left: int, right: int, top: int, bottom: int) -> str:
    return (
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" class="axis"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" class="axis"/>'
    )


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"RMB {number / 1_000_000_000:.1f}B"


def _bn(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"{number / 1_000_000_000:.1f}"


def _pct(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"{number * 100:.1f}%"


def _number(value: Any, *, digits: int = 1) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"{number:.{digits}f}"


def _ratio_x(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"{number:.2f}x"


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return numerator / denominator


def _growth(current: Any, prior: Any) -> float | None:
    current_value = _num(current)
    prior_value = _num(prior)
    if current_value is None or prior_value in {None, 0}:
        return None
    return current_value / prior_value - 1


def _text(value: Any) -> str:
    return str(value) if value not in {None, ""} else "n/a"


def _status_label(value: Any) -> str:
    labels = {
        "mixed": "混合信号",
        "calculated": "已计算",
        "deteriorating": "走弱",
        "stable": "稳定",
        "improving": "改善",
        "unknown": "未知",
    }
    return labels.get(str(value), _text(value))


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
        "receivables_from_online_payment_platforms": "支付平台应收",
        "prepayments_and_other_current_assets": "预付款及其他流动资产",
        "accounts_payable_and_accrued_expenses": "应付账款及应计费用",
        "payable_to_merchants": "应付商家款项",
        "merchant_deposits": "商家保证金",
        "deferred_revenue": "递延收入",
    }
    return labels.get(str(metric), str(metric).replace("_", " "))


_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f8fb;
  --panel: #ffffff;
  --ink: #111827;
  --muted: #64748b;
  --line: #dbe3ef;
  --accent: #2563eb;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.page { max-width: 1180px; margin: 0 auto; padding: 28px 24px 56px; }
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 360px);
  gap: 24px;
  align-items: end;
  padding: 30px 0 22px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
}
h1 { margin: 0; font-size: 34px; line-height: 1.18; letter-spacing: 0; }
.hero-copy { max-width: 720px; margin: 14px 0 0; color: var(--muted); font-size: 16px; line-height: 1.65; }
.meta {
  display: grid;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}
code {
  background: #eef2ff;
  color: #1e3a8a;
  padding: 2px 5px;
  border-radius: 5px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 22px 0 30px;
}
.kpi-card, .chart-card, .gap-card, .thesis-card, .layer-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .05);
}
.kpi-card { padding: 18px; min-height: 128px; }
.kpi-title { color: var(--muted); font-size: 13px; font-weight: 700; }
.kpi-value { margin-top: 10px; font-size: 26px; font-weight: 750; line-height: 1.2; }
.kpi-note { margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.45; }
.section { margin-top: 34px; }
.section h2 { margin: 0 0 8px; font-size: 22px; letter-spacing: 0; }
.section-lead { margin: 0 0 18px; color: var(--muted); line-height: 1.65; }
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.chart-card { padding: 18px; overflow: hidden; }
.chart-card header { margin-bottom: 8px; }
.chart-card h3 { margin: 0; font-size: 17px; }
.chart-card p { margin: 6px 0 0; color: var(--muted); font-size: 13px; line-height: 1.55; }
.chart-card .chart-insight {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  color: var(--ink);
}
.chart { width: 100%; height: auto; display: block; margin-top: 8px; }
.axis { stroke: #cbd5e1; stroke-width: 1; }
.zero-line { stroke: #94a3b8; stroke-width: 1.2; stroke-dasharray: 4 4; }
.axis-label { fill: #64748b; font-size: 12px; }
.legend { font-size: 13px; font-weight: 700; }
.bar-value { fill: #334155; font-size: 11px; font-weight: 700; }
.stack-label { fill: #ffffff; font-size: 12px; font-weight: 700; }
.empty-chart {
  display: grid;
  min-height: 190px;
  place-items: center;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: var(--muted);
  background: #f8fafc;
}
.gap-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.gap-card { padding: 16px; }
.gap-card h3 { margin: 0 0 8px; font-size: 16px; }
.gap-card p { margin: 8px 0 0; color: var(--muted); font-size: 13px; line-height: 1.55; }
.thesis-section { margin-top: 26px; }
.thesis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.thesis-card { padding: 18px; }
.thesis-card h3, .layer-card h3 { margin: 0 0 8px; font-size: 16px; }
.thesis-card p, .layer-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.62;
}
.layer-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.layer-card { padding: 16px; }
.layer-card ul {
  margin: 12px 0 0;
  padding-left: 18px;
}
.layer-card li {
  margin: 10px 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.55;
}
.appendix {
  color: var(--muted);
  border-top: 1px solid var(--line);
  padding-top: 20px;
}
.muted { color: var(--muted); }
@media (max-width: 840px) {
  .page { padding: 20px 14px 40px; }
  .hero, .kpi-grid, .chart-grid, .gap-grid, .thesis-grid, .layer-grid { grid-template-columns: 1fr; }
  h1 { font-size: 27px; }
}
"""
