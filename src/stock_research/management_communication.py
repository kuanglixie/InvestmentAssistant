from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stock_research.state import ResearchState, utc_now_iso


PDD_Q1_2026_RECORD_CANDIDATES = [
    Path("data/raw/official_event_transcripts/pdd/local_transcripts/PDD-2026Q1-local-transcript/record.json"),
    Path("data/raw/official_event_transcripts/pdd/pdd_q1_2026_earnings_call_webcast/record.json"),
]


def build_management_communication_pack(state: ResearchState) -> dict[str, Any]:
    """Build layer-three evidence from management communication sources.

    V1 intentionally starts narrow: it uses the user-provided PDD 2026Q1
    earnings-call transcript when available. The output schema is source-led so
    later deck, shareholder-letter, investor-day, and newsroom sources can be
    added without changing the report renderer.
    """

    company = state.get("canonical_company") or {}
    company_id = str(company.get("company_id") or state.get("company_query") or "").lower()
    if company_id != "pdd":
        return _empty_pack(company_id or "unknown", "not_configured_for_company_v1")

    loaded = _load_pdd_q1_2026_record()
    if not loaded:
        return _empty_pack(company_id, "pdd_q1_2026_transcript_not_found")

    record, record_path, transcript_text, transcript_path = loaded
    blocks = _parse_speaker_blocks(transcript_text)
    source = _source_catalog_item(record, record_path, transcript_path, blocks)
    pack = {
        "agent_run": {
            "agent_id": "management_communication_agent_v1",
            "company_id": company_id,
            "generated_at": utc_now_iso(),
            "source_policy": "management_communication_only",
            "status": "generated_from_single_earnings_call_transcript",
            "scope_note": (
                "第三层只读取管理层沟通材料，用来判断解释质量、Q&A 压力和战略叙事；"
                "不替代第一层数字和第二层 filing 证据。"
            ),
        },
        "source_catalog": [source],
        "layer_issue_reviews": _pdd_issue_reviews(source, blocks),
        "new_narratives": _pdd_new_narratives(source, blocks),
        "qa_pressure_topics": _pdd_qa_pressure_topics(source, blocks),
        "quality_flags": [
            {
                "flag_id": "raw_transcript_not_independently_verified",
                "severity": "medium",
                "message": "该 transcript 来自用户提供文本，尚未独立核对 webcast audio；适合用于管理层沟通分析，不作为财务数字 source of record。",
            }
        ],
    }
    pack["summary"] = {
        "source_count": len(pack["source_catalog"]),
        "issue_review_count": len(pack["layer_issue_reviews"]),
        "narrative_count": len(pack["new_narratives"]),
        "qa_pressure_topic_count": len(pack["qa_pressure_topics"]),
    }
    return pack


def _empty_pack(company_id: str, status: str) -> dict[str, Any]:
    return {
        "agent_run": {
            "agent_id": "management_communication_agent_v1",
            "company_id": company_id,
            "generated_at": utc_now_iso(),
            "source_policy": "management_communication_only",
            "status": status,
        },
        "source_catalog": [],
        "layer_issue_reviews": [],
        "new_narratives": [],
        "qa_pressure_topics": [],
        "quality_flags": [],
    }


def _load_pdd_q1_2026_record() -> tuple[dict[str, Any], Path, str, Path | None] | None:
    for record_path in PDD_Q1_2026_RECORD_CANDIDATES:
        if not record_path.exists():
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        transcript_text = str(record.get("transcript_text") or "")
        transcript_path: Path | None = None
        stored_at = str(record.get("stored_at") or "").strip()
        if stored_at:
            candidate = Path(stored_at)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            if candidate.exists():
                transcript_path = candidate
                transcript_text = candidate.read_text(encoding="utf-8")
        if transcript_text:
            return record, record_path, transcript_text, transcript_path
    return None


def _parse_speaker_blocks(transcript_text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    speaker: str | None = None
    lines: list[str] = []

    def flush() -> None:
        nonlocal lines, speaker
        if speaker is None:
            lines = []
            return
        text = "\n".join(lines).strip()
        if text:
            blocks.append(
                {
                    "block_id": f"block_{len(blocks) + 1:03d}",
                    "speaker": speaker,
                    "speaker_role": _speaker_role(speaker),
                    "text": _clean_text(text),
                }
            )
        lines = []

    for raw_line in transcript_text.splitlines():
        match = re.match(r"^###\s+(.+?)\s*$", raw_line)
        if match:
            flush()
            speaker = match.group(1).strip()
            continue
        if speaker is not None:
            lines.append(raw_line)
    flush()
    return blocks


def _speaker_role(speaker: str) -> str:
    normalized = speaker.lower()
    if any(name in normalized for name in ("alicia", "ronald", "joyce")):
        return "analyst"
    if any(name in normalized for name in ("zhao", "chen", "liu")):
        return "management"
    if "operator" in normalized:
        return "operator"
    return "host"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _source_catalog_item(
    record: dict[str, Any],
    record_path: Path,
    transcript_path: Path | None,
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    analyst_question_count = sum(1 for block in blocks if block.get("speaker_role") == "analyst")
    management_block_count = sum(1 for block in blocks if block.get("speaker_role") == "management")
    return {
        "source_id": "pdd_2026q1_earnings_call_user_transcript",
        "source_type": "earnings_call_transcript",
        "company": record.get("company") or record.get("company_name") or "PDD Holdings Inc.",
        "ticker": record.get("ticker") or "PDD",
        "period": record.get("period") or record.get("quarter") or "2026Q1",
        "event": record.get("event") or "1Q 2026 Earnings Conference Call",
        "provider": record.get("provider") or "local_user_provided_transcript",
        "status": record.get("status") or "raw_transcript_not_independently_verified",
        "source_url": record.get("source_url") or "https://edge.media-server.com/mmc/p/t6vpaffq/",
        "local_file_path": str(transcript_path or record_path),
        "record_path": str(record_path),
        "speaker_block_count": len(blocks),
        "management_block_count": management_block_count,
        "analyst_question_count": analyst_question_count,
        "source_quality_note": "用于管理层沟通、Q&A 与战略叙事分析；不作为财务数字 source of record。",
    }


def _pdd_issue_reviews(source: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "issue_id": "margin_pressure_investment_or_structural",
            "issue_text": "利润率压力到底是主动投入，还是结构性竞争压力？",
            "management_explanation": (
                "管理层把利润率波动主要放在“长期供应链投入”和“平台生态投入”的框架里解释。CFO 明确说季度财务结果会受季节性和投资周期影响，"
                "公司优先考虑平台长期内在价值，而不是短期财务表现；同时管理层把 first-party brand、送货进村、新质量供应链都归为长期项目。"
                "这能解释为什么公司愿意牺牲部分短期利润率，但没有给出利润率底部、投资期长度或费用桶拆分。"
            ),
            "answer_quality": "directional_only",
            "consistency_with_layer1": "clarifies",
            "consistency_with_layer2": "supports",
            "still_unknown": [
                "供应链 / 商家支持 / 履约投入分别是多少",
                "利润率是否有内部目标或底部",
                "利润压力中有多少来自竞争、有多少来自主动投入",
            ],
            "watch_items": ["费用率", "履约和支付成本", "non-GAAP 调整", "后续季度经营利润率"],
            "evidence": [
                _evidence(source, blocks, "Jun Liu", ["seasonality", "investment cycle"], "CFO 将短期财务波动解释为季节性和投资周期。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["long-term value creation", "supply chain"], "管理层称优先长期价值和供应链/生态投入。"),
            ],
        },
        {
            "issue_id": "first_party_brand_business_model_shift",
            "issue_text": "first-party brand 是普通营销项目，还是会改变商业模式和资本强度？",
            "management_explanation": (
                "管理层把 first-party brand 描述成三年战略下的核心动作：上海设立专门公司，初始现金注入 RMB 15B，计划三年投入 RMB 100B。"
                "Q&A 中进一步说明平台会更深介入产品开发、标准制定、质量控制、仓储履约、法务合规和客服，并承担更大责任和风险，向供应链提供销量确定性。"
                "这说明它不只是广告或补贴项目，而可能把 PDD 从更轻的平台撮合，推向更深的供应链组织者。"
            ),
            "answer_quality": "specific_with_numbers",
            "consistency_with_layer1": "clarifies",
            "consistency_with_layer2": "supports",
            "still_unknown": [
                "是否承担库存风险",
                "first-party brand 是否单独披露收入、利润和现金投入",
                "RMB 100B 投入的费用化 / 资本化 / 营运资本路径",
            ],
            "watch_items": ["收入结构", "存货或合同义务", "经营费用", "现金和短投变化"],
            "evidence": [
                _evidence(source, blocks, "Jiazhen Zhao", ["15 billion", "100 billion"], "管理层披露 first-party brand 初始现金注入和三年投入计划。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["product design", "quality control"], "Q&A 中说明品牌建设涉及产品、质量、履约、合规等能力。"),
            ],
        },
        {
            "issue_id": "online_marketing_growth_slowdown",
            "issue_text": "在线营销服务增速放缓后，未来 GMV 和广告变现靠什么增长？",
            "management_explanation": (
                "分析师直接追问 online marketing service 增速放缓和未来 GMV / 广告增长。管理层没有给出广告 take-rate、GMV、商家广告预算或用户增长的具体数字，"
                "而是把回答转向供应链赋能、农业产区、产业带、村级物流和远程地区物流补贴，强调通过降低供需连接成本创造有效需求。"
                "所以第三层能确认管理层把增长叙事从前端流量和广告，转向供应链效率，但不能证明广告业务已经找到新的量化增长引擎。"
            ),
            "answer_quality": "avoided",
            "consistency_with_layer1": "clarifies",
            "consistency_with_layer2": "no_change",
            "still_unknown": [
                "GMV 增速",
                "广告 take-rate",
                "商家广告 ROI",
                "online marketing 与 transaction services 的长期结构",
            ],
            "watch_items": ["交易服务收入占比", "在线营销收入同比", "管理层是否恢复披露 GMV / 用户指标"],
            "evidence": [
                _evidence(source, blocks, "Ronald Keung", ["online marketing service growth"], "分析师追问在线营销服务增速和 GMV 增长。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["logistics support", "effective demand"], "管理层回答转向供应链和远程物流创造需求。"),
            ],
        },
        {
            "issue_id": "global_business_retention_and_unit_economics",
            "issue_text": "global business 的增长和留存是否能由管理层解释清楚？",
            "management_explanation": (
                "管理层承认全球业务经过近三年增长后获得消费者支持，但回答的重点不是用户数量，而是供应链能力。"
                "陈磊把后续重点拆成两条：整合和优化供应链、深化 first-party brand；他也指出电商切换成本低，长期优势来自看不见的供应链能力。"
                "这能解释为什么公司把全球业务与供应链投资绑定，但没有披露 Temu / global business 的单独收入、利润、GMV、留存或获客成本。"
            ),
            "answer_quality": "directional_only",
            "consistency_with_layer1": "clarifies",
            "consistency_with_layer2": "supports",
            "still_unknown": [
                "global business 单独收入和利润",
                "用户留存和复购",
                "履约成本、退货和监管成本",
            ],
            "watch_items": ["跨境履约成本", "地区监管", "first-party brand 在全球业务中的占比"],
            "evidence": [
                _evidence(source, blocks, "Alicia Yap", ["global business", "user growth"], "分析师追问全球业务用户增长和留存。"),
                _evidence(source, blocks, "Lei Chen", ["supply chain capabilities"], "管理层把全球业务后续重点定位为供应链能力。"),
            ],
        },
        {
            "issue_id": "cash_allocation_and_investment_capacity",
            "issue_text": "现金安全垫会怎么被使用？会不会主要投向新业务而不是股东回报？",
            "management_explanation": (
                "电话会提供了两类现金线索：财务负责人披露 2026Q1 末现金等价物和短期投资为 RMB 436.1B；管理层同时强调 first-party brand "
                "初始投入 RMB 15B、三年投入 RMB 100B。管理层没有讨论回购、分红或明确的资本回报框架。"
                "所以第三层支持“公司有能力承受投入期”，但也提示现金更可能优先服务供应链和新业务投资。"
            ),
            "answer_quality": "specific_with_numbers",
            "consistency_with_layer1": "clarifies",
            "consistency_with_layer2": "supports",
            "still_unknown": [
                "RMB 436.1B 中有多少可自由调配",
                "未来三年 RMB 100B 的实际支付节奏",
                "是否存在明确股东回报政策",
            ],
            "watch_items": ["现金和短投", "受限现金", "投资现金流", "资本配置披露"],
            "evidence": [
                _evidence(source, blocks, "Jun Liu", ["436.1 billion"], "CFO 披露 2026Q1 末现金等价物和短期投资。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["100 billion RMB"], "管理层披露三年 RMB 100B 投入计划。"),
            ],
        },
    ]


def _pdd_new_narratives(source: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "narrative_id": "platform_to_deeper_supply_chain_operator",
            "narrative_type": "business_model_change",
            "title": "从轻平台叙事转向更深供应链组织者",
            "summary": (
                "管理层反复把 PDD 的下一阶段竞争优势定义为供应链能力，而不是单纯流量、营销或用户增长。"
                "first-party brand 被描述为平台更主动参与产品开发、标准、质量、履约、合规和客服的机制。"
            ),
            "why_it_matters": "如果这个叙事兑现，PDD 的护城河可能更深；如果执行不好，也可能带来更高费用、更重营运资本和更低短期利润率。",
            "still_unknown": ["库存风险", "履约成本", "品牌业务的收入和利润披露"],
            "evidence": [
                _evidence(source, blocks, "Lei Chen", ["supply chain capabilities"], "管理层称长期竞争优势来自供应链能力。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["greater responsibility", "risks"], "管理层称平台会承担更大责任和风险。"),
            ],
        },
        {
            "narrative_id": "three_year_build_another_pinduoduo",
            "narrative_type": "strategy",
            "title": "三年“再造一个拼多多”进入执行期",
            "summary": (
                "管理层把 2026Q1 定义为三年战略的第一个完整季度，核心抓手是 first-party brand、供应链投入和 RMB 100B 支持计划。"
                "这说明 2025 年以来的利润率压力不是单季偶发，而是管理层主动选择的投入周期。"
            ),
            "why_it_matters": "估值和跟踪重点应从单季利润最大化，转向投入是否能形成更高收入质量、商家质量和长期供应链效率。",
            "still_unknown": ["投入回收期", "投入项目的 KPI", "三年后利润率框架"],
            "evidence": [
                _evidence(source, blocks, "Jiazhen Zhao", ["3-year strategy"], "管理层称进入三年战略新阶段。"),
                _evidence(source, blocks, "Lei Chen", ["first full quarter"], "管理层称 Q1 是三年战略下 first-party brand 的首个完整季度。"),
            ],
        },
        {
            "narrative_id": "compliance_and_platform_governance",
            "narrative_type": "governance_and_compliance",
            "title": "安全、合规和平台治理被前置",
            "summary": (
                "管理层把安全、合规和社会责任称为一切工作的前提，并具体提到第一季度推出 20 多项食品安全治理措施，"
                "包括资质审核、食品广告和直播监测、食品数据库、举报渠道和自动/人工巡检。"
            ),
            "why_it_matters": "这可能是应对监管和平台责任压力的信号；短期可能增加治理成本，长期可能降低平台信任和监管风险。",
            "still_unknown": ["治理投入金额", "违规率是否下降", "监管事件是否减少"],
            "evidence": [
                _evidence(source, blocks, "Jiazhen Zhao", ["20 food safety"], "管理层披露一季度推出 20 多项食品安全措施。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["safety, compliance"], "管理层把安全、合规、社会责任置于优先位置。"),
            ],
        },
        {
            "narrative_id": "rural_logistics_and_effective_demand",
            "narrative_type": "growth_mechanism",
            "title": "下沉物流被包装成创造有效需求的增长机制",
            "summary": (
                "管理层用中山灯具到甘肃的运费案例、河南县域进村配送案例和远程地区物流补贴解释增长机制：平台通过承担转运成本，"
                "把部分偏远地区纳入包邮区，从而扩大需求和商家订单。"
            ),
            "why_it_matters": "这提供了比“消费复苏”更具体的增长解释，但需要验证补贴停止后需求是否仍可持续，以及物流支持是否压低利润率。",
            "still_unknown": ["补贴金额", "订单增长是否 profitable", "地区扩张后的留存"],
            "evidence": [
                _evidence(source, blocks, "Jiazhen Zhao", ["40 to 50 RMB", "10 RMB"], "管理层举例说明远程物流成本下降。"),
                _evidence(source, blocks, "Jiazhen Zhao", ["70% of local villages"], "管理层披露部分县域进村覆盖超过 70%。"),
            ],
        },
        {
            "narrative_id": "no_margin_target_commitment",
            "narrative_type": "communication_signal",
            "title": "管理层没有给稳定利润率目标",
            "summary": (
                "在被直接问到长期稳定利润率时，CFO 没有给出利润率区间或时间表，而是强调季节性、投资周期、长期内在价值和供应链能力积累。"
            ),
            "why_it_matters": "这意味着短期利润率预测置信度低，后续报告更应该看经营利润率是否企稳，而不是假设很快回到 2024 年高点。",
            "still_unknown": ["利润率底部", "投资强度峰值", "恢复时间表"],
            "evidence": [
                _evidence(source, blocks, "Joyce Ju", ["stable profit margin"], "分析师追问稳定利润率水平。"),
                _evidence(source, blocks, "Jun Liu", ["short-term financial performance"], "CFO 回答强调不以短期财务表现为优先。"),
            ],
        },
    ]


def _pdd_qa_pressure_topics(source: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "topic": "first-party brand 是否是重大战略转向",
            "analyst_concern": "Citigroup 追问公司从电商平台定位转向 first-party brand 的原因，以及是否应理解为重大战略 pivot。",
            "answer_quality": "specific_with_numbers",
            "management_response_read": "管理层承认平台会更深介入供应链，并给出 RMB 15B 初始注资、三年 RMB 100B 投入和承担更大责任/风险的表述。",
            "follow_up_needed": ["库存风险", "单独 P&L", "品牌业务 GMV / 收入 / 利润"],
            "evidence": [_evidence(source, blocks, "Alicia Yap", ["major pivot"], "分析师追问 first-party brand 是否构成战略转向。")],
        },
        {
            "topic": "global business 用户增长和留存",
            "analyst_concern": "Citigroup 追问第三方数据看到的 global business 用户增长是否符合预期，以及公司如何留住消费者。",
            "answer_quality": "directional_only",
            "management_response_read": "管理层回答集中在供应链优化和 first-party brand，没有披露用户增长、留存、获客成本或区域经济性。",
            "follow_up_needed": ["用户留存", "获客成本", "地区利润率", "履约/退货成本"],
            "evidence": [_evidence(source, blocks, "Alicia Yap", ["retain", "consumer"], "分析师追问 global business 用户留存。")],
        },
        {
            "topic": "RMB 100B 投入的用途、反映时间和增量增长",
            "analyst_concern": "Goldman Sachs 追问三年 RMB 100B 投入会投向哪里、何时反映到财务报表、如何评估增量增长。",
            "answer_quality": "specific_without_numbers",
            "management_response_read": "管理层详细讲了产品设计、标准、制造、QC、仓储履约、合规、客服等方向，但没有给出财务确认节奏、ROI 或利润率路径。",
            "follow_up_needed": ["费用化节奏", "ROI", "收入贡献", "现金支付节奏"],
            "evidence": [_evidence(source, blocks, "Ronald Keung", ["100 billion investment"], "分析师追问 RMB 100B 投入的财务影响。")],
        },
        {
            "topic": "online marketing service 增速放缓",
            "analyst_concern": "Goldman Sachs 追问消费背景较好、线上渗透仍提升时，PDD online marketing services 增速为什么放缓，以及未来 GMV 和广告增长在哪里。",
            "answer_quality": "avoided",
            "management_response_read": "管理层没有直接解释广告增速、take-rate 或 GMV，而是回到供应链支持、村级物流和远程地区需求创造。",
            "follow_up_needed": ["广告 take-rate", "商家广告 ROI", "GMV", "在线营销收入拆分"],
            "evidence": [_evidence(source, blocks, "Ronald Keung", ["online marketing service"], "分析师追问在线营销服务放缓。")],
        },
        {
            "topic": "直播电商、即时零售等新模式",
            "analyst_concern": "Bank of America 追问直播电商、即时零售等新商业模式对行业的影响，以及公司是否会布局。",
            "answer_quality": "directional_only",
            "management_response_read": "管理层没有给出具体产品布局，而是说前端模式变化不改变用户核心需求，竞争最终回到供应链能力。",
            "follow_up_needed": ["即时零售策略", "直播电商策略", "前端流量入口变化"],
            "evidence": [_evidence(source, blocks, "Joyce Ju", ["live e-commerce", "instant retail"], "分析师追问新电商模式。")],
        },
        {
            "topic": "利润率波动与稳定利润率水平",
            "analyst_concern": "Bank of America 直接追问一季度 cost-to-profit ratio 和利润率波动，以及长期稳定利润率如何预测。",
            "answer_quality": "directional_only",
            "management_response_read": "CFO 没有给出稳定利润率水平，只强调季节性、投资周期和长期内在价值。",
            "follow_up_needed": ["利润率目标", "投资周期长度", "费用率拆分", "margin floor"],
            "evidence": [_evidence(source, blocks, "Joyce Ju", ["stable profit margin"], "分析师追问长期稳定利润率。")],
        },
    ]


def _evidence(
    source: dict[str, Any],
    blocks: list[dict[str, Any]],
    speaker: str,
    terms: list[str],
    summary: str,
) -> dict[str, Any]:
    block = _find_block(blocks, speaker=speaker, terms=terms)
    return {
        "source_id": source.get("source_id"),
        "source_document": source.get("event"),
        "source_document_type": source.get("source_type"),
        "period": source.get("period"),
        "source_url": source.get("source_url"),
        "local_file_path": source.get("local_file_path"),
        "speaker": block.get("speaker") if block else speaker,
        "speaker_role": block.get("speaker_role") if block else "unknown",
        "block_id": block.get("block_id") if block else None,
        "exact_fact_or_summary": summary,
        "evidence_type": "management_communication_summary",
        "confidence": 0.75 if block else 0.35,
    }


def _find_block(blocks: list[dict[str, Any]], *, speaker: str, terms: list[str]) -> dict[str, Any] | None:
    speaker_key = speaker.lower()
    lowered_terms = [term.lower() for term in terms]
    speaker_matches = [block for block in blocks if speaker_key in str(block.get("speaker") or "").lower()]
    for block in speaker_matches:
        text = str(block.get("text") or "").lower()
        if any(term in text for term in lowered_terms):
            return block
    return speaker_matches[0] if speaker_matches else None
