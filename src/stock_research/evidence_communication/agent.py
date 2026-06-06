from __future__ import annotations

import hashlib
from typing import Any

from stock_research.management_communication import build_management_communication_pack
from stock_research.official_evidence import build_official_report_evidence_pack
from stock_research.state import ResearchState, utc_now_iso


EVIDENCE_COMMUNICATION_PACK_SCHEMA_VERSION = "evidence_communication_pack_v1"


def build_evidence_communication_pack(state: ResearchState) -> dict[str, Any]:
    financial_pack = state.get("financial_report_pack") or {}
    layer1_pack = state.get("layer1_question_pack") or {}
    official_pack = state.get("official_report_evidence_pack") or build_official_report_evidence_pack(state)
    management_pack = state.get("management_communication_pack") or build_management_communication_pack(state)

    question_answers = _question_answers(layer1_pack, official_pack, management_pack)
    proactive_discoveries = _proactive_discoveries(official_pack, management_pack)
    narrative_registry = _narrative_registry(proactive_discoveries)
    management_claims = _management_claims(management_pack)
    analyst_concerns = _analyst_concerns(management_pack)
    unknowns = _unknowns(layer1_pack, official_pack, management_pack, question_answers)
    extractor_handoffs = _handoff_to_financial_extractor(layer1_pack, question_answers, proactive_discoveries)

    pack = {
        "schema_version": EVIDENCE_COMMUNICATION_PACK_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "agent_run": {
            "run_id": state.get("run_id"),
            "company_id": ((financial_pack.get("company") or {}).get("company_id") or state.get("company_query")),
            "company_name": ((financial_pack.get("company") or {}).get("legal_name") or state.get("company_query")),
            "source_policy": "official_and_management_communication_only",
            "status": "generated",
            "compatibility_note": (
                "V1 normalizes existing official_report_evidence_pack and management_communication_pack into a unified pack. "
                "Old split packs are transitional compatibility outputs."
            ),
        },
        "source_inventory": _source_inventory(official_pack, management_pack),
        "question_answers": question_answers,
        "proactive_discoveries": proactive_discoveries,
        "narrative_registry": narrative_registry,
        "management_claims": management_claims,
        "analyst_concerns": analyst_concerns,
        "unknowns": unknowns,
        "handoff_to_financial_extractor": extractor_handoffs,
        "quality_flags": _quality_flags(official_pack, management_pack, question_answers),
        "transitional_source_packs": {
            "official_report_evidence_pack": official_pack,
            "management_communication_pack": management_pack,
        },
        "summary": {
            "question_answer_count": len(question_answers),
            "proactive_discovery_count": len(proactive_discoveries),
            "narrative_count": len(narrative_registry),
            "analyst_concern_count": len(analyst_concerns),
            "financial_extractor_handoff_count": len(extractor_handoffs),
        },
    }
    return pack


def build_evidence_communication_report(pack: dict[str, Any]) -> str:
    agent_run = pack.get("agent_run") or {}
    lines = [
        f"# Evidence & Communication Extraction：{agent_run.get('company_name') or agent_run.get('company_id') or 'Unknown Company'}",
        "",
        "## 1. 问题复核",
        "",
    ]
    for answer in pack.get("question_answers") or []:
        lines.extend(
            [
                f"### {answer.get('question_id')}. {answer.get('question')}",
                "",
                f"- 状态：`{answer.get('status')}`",
                f"- 当前回答：{answer.get('short_answer') or '未披露'}",
                f"- 官方证据：{_short_evidence(answer.get('official_evidence'))}",
                f"- 管理层沟通：{_short_evidence(answer.get('management_communication'))}",
                f"- 仍未知：{_join(answer.get('still_unknown'))}",
                "",
            ]
        )
    lines.extend(["## 2. 主动发现", ""])
    for item in pack.get("proactive_discoveries") or []:
        lines.extend(
            [
                f"### {item.get('title') or item.get('discovery_id')}",
                "",
                f"- 类型：`{item.get('type')}`",
                f"- 读法：{item.get('summary') or '未披露'}",
                f"- 为什么重要：{item.get('why_it_matters') or '未披露'}",
                f"- 仍未知：{_join(item.get('unknowns'))}",
                "",
            ]
        )
    lines.extend(["## 3. 回流给 Financial Extractor", ""])
    for handoff in pack.get("handoff_to_financial_extractor") or []:
        lines.append(
            f"- `{handoff.get('priority') or 'P2'}` {handoff.get('request') or handoff.get('handoff_id')}：{_join(handoff.get('missing_metrics'))}"
        )
    return "\n".join(lines).strip() + "\n"


def _question_answers(
    layer1_pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    official_by_id = {answer.get("question_id"): answer for answer in official_pack.get("question_answers") or []}
    management_reviews = management_pack.get("layer_issue_reviews") or []
    qa_topics = management_pack.get("qa_pressure_topics") or []
    answers = []
    for question in layer1_pack.get("research_questions") or []:
        question_id = question.get("question_id")
        official = _official_for_question(question, official_by_id)
        management = _management_for_question(question, management_reviews, qa_topics)
        official_evidence = _official_evidence_items(question_id, official)
        communication_evidence = _management_evidence_items(question_id, management)
        still_unknown = _unique(
            list(question.get("still_unknown") or [])
            + list(official.get("still_unknown") or [])
            + list(management.get("still_unknown") or management.get("follow_up_needed") or [])
        )
        status = _answer_status(question, official, management, still_unknown)
        answers.append(
            {
                "question_id": question_id,
                "question": question.get("question"),
                "status": status,
                "short_answer": _short_answer(question, official, management),
                "why_it_matters": question.get("current_answer"),
                "financial_trigger": question.get("financial_triggers") or [],
                "official_evidence": official_evidence,
                "management_communication": communication_evidence,
                "consistency_check": {
                    "vs_financial_metrics": "partially_consistent" if status == "partial" else "not_tested",
                    "vs_official_filing": official.get("impact_on_layer1") or "not_tested",
                },
                "our_inference": _inference(official, management),
                "still_unknown": still_unknown,
                "handoff_to_financial_extractor": question.get("handoff_to_financial_extractor") or [],
                "confidence": _confidence(status, official_evidence, communication_evidence),
            }
        )
    return answers


def _official_for_question(question: dict[str, Any], official_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for candidate in question.get("suggested_official_question_ids") or []:
        if candidate in official_by_id:
            return official_by_id[candidate]
    return {}


def _management_for_question(
    question: dict[str, Any],
    reviews: list[dict[str, Any]],
    topics: list[dict[str, Any]],
) -> dict[str, Any]:
    text = f"{question.get('question') or ''} {' '.join(question.get('still_unknown') or [])}".lower()
    candidates: list[dict[str, Any]] = []
    for item in reviews + topics:
        haystack = " ".join(str(item.get(key) or "") for key in ("issue_text", "topic", "analyst_concern", "management_response_read")).lower()
        score = sum(1 for token in _topic_tokens(text) if token and token in haystack)
        if score:
            candidates.append({"score": score, **item})
    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
    return candidates[0] if candidates else {}


def _official_evidence_items(question_id: str, official: dict[str, Any]) -> list[dict[str, Any]]:
    rendered = official.get("rendered_answer") or {}
    items = []
    if rendered.get("filing_facts"):
        items.append(_evidence(question_id, "filing_fact", rendered.get("filing_facts"), official, rendered))
    if rendered.get("official_explanation"):
        items.append(_evidence(question_id, "management_explanation", rendered.get("official_explanation"), official, rendered))
    if rendered.get("our_judgment"):
        items.append(_evidence(question_id, "our_inference", rendered.get("our_judgment"), official, rendered))
    for warning in official.get("warning_signals") or []:
        items.append(_evidence(question_id, "risk_disclosure", warning, official, rendered))
    return items


def _management_evidence_items(question_id: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    if not item:
        return []
    evidence = []
    if item.get("analyst_concern"):
        evidence.append(_comm_evidence(question_id, "analyst_concern", item.get("analyst_concern"), item))
    if item.get("management_response_read") or item.get("management_explanation"):
        evidence.append(
            _comm_evidence(
                question_id,
                "management_claim",
                item.get("management_response_read") or item.get("management_explanation"),
                item,
            )
        )
    return evidence


def _evidence(
    question_id: str,
    label: str,
    text: Any,
    official: dict[str, Any],
    rendered: dict[str, Any],
) -> dict[str, Any]:
    return {
        "evidence_id": f"{question_id}_{label}_{_stable_id(text)}",
        "label": label,
        "source_type": "official_filing_or_release",
        "document_id": rendered.get("source_trace") or official.get("source_trace") or "",
        "paraphrase": str(text),
        "quote_snippet": "",
        "linked_metrics": official.get("linked_metrics") or [],
        "confidence": 0.75 if label == "filing_fact" else 0.55,
    }


def _comm_evidence(question_id: str, label: str, text: Any, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": f"{question_id}_{label}_{_stable_id(text)}",
        "label": label,
        "source_type": "management_communication",
        "document_id": item.get("source_id") or item.get("source_trace") or item.get("evidence") or "",
        "speaker": item.get("speaker") or "",
        "block_id": item.get("block_id") or "",
        "paraphrase": str(text),
        "quote_snippet": "",
        "answer_quality": item.get("answer_quality") or "",
        "confidence": 0.55,
    }


def _proactive_discoveries(official_pack: dict[str, Any], management_pack: dict[str, Any]) -> list[dict[str, Any]]:
    discoveries = []
    for item in official_pack.get("decision_relevant_narratives") or []:
        discoveries.append(
            {
                "discovery_id": item.get("narrative_id") or item.get("title") or f"official_{len(discoveries)+1}",
                "title": item.get("title") or item.get("narrative_id") or "官方文件叙事",
                "type": item.get("narrative_type") or item.get("type") or "official_narrative",
                "change_status": item.get("change_status") or "unknown",
                "summary": item.get("our_inference") or item.get("summary") or item.get("why_it_matters") or "",
                "why_it_matters": item.get("why_it_matters") or "",
                "evidence_items": item.get("evidence_bundle") or [],
                "linked_questions": item.get("linked_metrics") or [],
                "creates_new_question": bool(item.get("unknowns") or item.get("still_unknown")),
                "new_question_text": item.get("new_question_text") or "",
                "unknowns": item.get("still_unknown") or item.get("unknowns") or [],
                "source_lane": "official_filing_evidence",
            }
        )
    for item in management_pack.get("new_narratives") or []:
        discoveries.append(
            {
                "discovery_id": item.get("narrative_id") or item.get("title") or f"management_{len(discoveries)+1}",
                "title": item.get("title") or item.get("topic") or "管理层沟通叙事",
                "type": item.get("narrative_type") or "management_communication",
                "change_status": item.get("change_status") or "new_unproven",
                "summary": item.get("summary") or item.get("management_response_read") or "",
                "why_it_matters": item.get("why_it_matters") or item.get("summary") or "",
                "evidence_items": item.get("evidence_bundle") or [],
                "linked_questions": item.get("linked_questions") or [],
                "creates_new_question": bool(item.get("follow_up_needed") or item.get("still_unknown")),
                "new_question_text": "",
                "unknowns": item.get("follow_up_needed") or item.get("still_unknown") or [],
                "source_lane": "management_communication",
            }
        )
    return discoveries


def _narrative_registry(discoveries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "narrative_id": item.get("discovery_id"),
            "title": item.get("title"),
            "type": item.get("type"),
            "change_status": item.get("change_status"),
            "summary": item.get("summary"),
            "why_it_matters": item.get("why_it_matters"),
            "evidence_items": item.get("evidence_items") or [],
            "linked_questions": item.get("linked_questions") or [],
            "creates_new_question": item.get("creates_new_question"),
            "new_question_text": item.get("new_question_text"),
            "monitoring_metrics": _monitoring_metrics(item),
            "unknowns": item.get("unknowns") or [],
        }
        for item in discoveries
    ]


def _management_claims(management_pack: dict[str, Any]) -> list[dict[str, Any]]:
    claims = []
    for item in (management_pack.get("layer_issue_reviews") or []) + (management_pack.get("new_narratives") or []):
        text = item.get("management_response_read") or item.get("management_explanation") or item.get("summary")
        if not text:
            continue
        claims.append(
            {
                "claim_id": item.get("issue_id") or item.get("narrative_id") or f"claim_{len(claims)+1}",
                "claim_type": "management_claim",
                "text": text,
                "answer_quality": item.get("answer_quality") or "",
                "source_trace": item.get("source_trace") or item.get("evidence") or "",
                "unknowns": item.get("still_unknown") or item.get("follow_up_needed") or [],
            }
        )
    return claims


def _analyst_concerns(management_pack: dict[str, Any]) -> list[dict[str, Any]]:
    concerns = []
    for item in management_pack.get("qa_pressure_topics") or []:
        concerns.append(
            {
                "concern_id": item.get("topic_id") or item.get("topic") or f"concern_{len(concerns)+1}",
                "topic": item.get("topic"),
                "analyst_concern": item.get("analyst_concern"),
                "management_response_read": item.get("management_response_read"),
                "answer_quality": item.get("answer_quality"),
                "follow_up_needed": item.get("follow_up_needed") or [],
                "source_trace": item.get("source_trace") or item.get("evidence") or "",
            }
        )
    return concerns


def _unknowns(
    layer1_pack: dict[str, Any],
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    question_answers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unknowns = []
    for answer in question_answers:
        for item in answer.get("still_unknown") or []:
            unknowns.append(
                {
                    "unknown_id": f"{answer.get('question_id')}_{_stable_id(item)}",
                    "unknown": item,
                    "linked_question": answer.get("question_id"),
                    "source": "question_answer",
                }
            )
    for gap in layer1_pack.get("disclosure_gaps") or []:
        unknowns.append(
            {
                "unknown_id": gap.get("gap_id") or f"gap_{len(unknowns)+1}",
                "unknown": ", ".join(gap.get("missing_metrics") or [gap.get("gap_id") or "gap"]),
                "linked_question": "disclosure_gap",
                "source": "layer1_disclosure_gap",
            }
        )
    for flag in (official_pack.get("quality_flags") or []) + (management_pack.get("quality_flags") or []):
        unknowns.append(
            {
                "unknown_id": flag.get("flag_id") or flag.get("flag") or f"quality_{len(unknowns)+1}",
                "unknown": flag.get("message") or flag.get("flag") or str(flag),
                "linked_question": "quality_flag",
                "source": "quality_flags",
            }
        )
    return _unique_unknowns(unknowns)


def _handoff_to_financial_extractor(
    layer1_pack: dict[str, Any],
    question_answers: list[dict[str, Any]],
    discoveries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    handoffs = list(layer1_pack.get("handoff_to_financial_extractor") or [])
    for answer in question_answers:
        for item in answer.get("handoff_to_financial_extractor") or []:
            handoffs.append(
                {
                    "handoff_id": str(item),
                    "priority": "P1",
                    "request": f"补充 {item}。",
                    "missing_metrics": [item],
                    "why_it_matters": answer.get("question"),
                    "linked_questions": [answer.get("question_id")],
                    "source": "evidence_communication_question_answer",
                }
            )
    for discovery in discoveries:
        for unknown in discovery.get("unknowns") or []:
            if not unknown:
                continue
            handoffs.append(
                {
                    "handoff_id": f"{discovery.get('discovery_id')}_{_stable_id(unknown)}",
                    "priority": "P2",
                    "request": f"如果官方后续披露，补充：{unknown}",
                    "missing_metrics": [unknown],
                    "why_it_matters": discovery.get("why_it_matters") or discovery.get("summary"),
                    "linked_questions": discovery.get("linked_questions") or [],
                    "source": "proactive_discovery",
                }
            )
    return _unique_handoffs(handoffs)


def _source_inventory(official_pack: dict[str, Any], management_pack: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = []
    for source in official_pack.get("source_catalog") or []:
        inventory.append({"lane": "official_filing_evidence", **source})
    for source in management_pack.get("source_catalog") or []:
        inventory.append({"lane": "management_communication", **source})
    return inventory


def _quality_flags(
    official_pack: dict[str, Any],
    management_pack: dict[str, Any],
    question_answers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flags = []
    flags.extend(official_pack.get("quality_flags") or [])
    flags.extend(management_pack.get("quality_flags") or [])
    for answer in question_answers:
        if answer.get("status") in {"unknown", "partial"} and not answer.get("official_evidence") and not answer.get("management_communication"):
            flags.append(
                {
                    "flag_id": f"{answer.get('question_id')}_no_evidence",
                    "severity": "medium",
                    "message": f"{answer.get('question')} 缺少官方或管理层沟通证据。",
                }
            )
    return flags


def _answer_status(
    question: dict[str, Any],
    official: dict[str, Any],
    management: dict[str, Any],
    unknowns: list[Any],
) -> str:
    official_status = official.get("answer_status")
    answer_quality = management.get("answer_quality")
    if official_status == "contradicted" or answer_quality == "contradicted_by_filings_or_metrics":
        return "conflicted"
    if official_status == "answered" and not unknowns:
        return "answered"
    if official or management:
        return "partial"
    return question.get("status") or "unknown"


def _short_answer(question: dict[str, Any], official: dict[str, Any], management: dict[str, Any]) -> str:
    rendered = official.get("rendered_answer") or {}
    return (
        rendered.get("our_judgment")
        or rendered.get("official_explanation")
        or management.get("management_response_read")
        or management.get("management_explanation")
        or question.get("current_answer")
        or ""
    )


def _inference(official: dict[str, Any], management: dict[str, Any]) -> str:
    rendered = official.get("rendered_answer") or {}
    if rendered.get("our_judgment"):
        return rendered.get("our_judgment")
    if official and management:
        return "官方文件和管理层沟通均提供部分解释，但仍需与第一层数字持续交叉验证。"
    if official:
        return "官方文件提供部分解释，但管理层沟通证据不足或未匹配。"
    if management:
        return "管理层沟通提供方向性解释，但仍需官方文件和数字验证。"
    return ""


def _confidence(status: str, official_items: list[dict[str, Any]], management_items: list[dict[str, Any]]) -> dict[str, Any]:
    if status == "answered" and official_items:
        return {"label": "high", "reason": "有官方文件证据支持。"}
    if official_items and management_items:
        return {"label": "medium", "reason": "官方文件和管理层沟通均有证据，但仍未完全回答。"}
    if official_items or management_items:
        return {"label": "medium", "reason": "有单侧证据，需继续验证。"}
    return {"label": "low", "reason": "当前统一证据包未找到直接证据。"}


def _monitoring_metrics(item: dict[str, Any]) -> list[str]:
    text = " ".join(str(item.get(key) or "") for key in ("title", "summary", "why_it_matters")).lower()
    metrics = []
    if any(token in text for token in ("first-party", "自营", "brand")):
        metrics.extend(["first_party_revenue", "first_party_operating_income", "inventory"])
    if any(token in text for token in ("temu", "global", "全球")):
        metrics.extend(["temu_revenue", "temu_operating_income", "temu_gmv"])
    if any(token in text for token in ("cash", "现金", "vie")):
        metrics.extend(["restricted_cash", "cash_transfer_restriction", "vie_assets"])
    return metrics


def _topic_tokens(text: str) -> list[str]:
    raw = [
        "利润率",
        "margin",
        "现金",
        "cash",
        "自营",
        "first-party",
        "brand",
        "temu",
        "global",
        "营销",
        "marketing",
        "gmv",
        "take",
        "sbc",
        "稀释",
        "治理",
        "non-gaap",
    ]
    return [token for token in raw if token in text]


def _short_evidence(items: Any) -> str:
    rows = items or []
    if not rows:
        return "未找到直接证据"
    return "；".join(str(item.get("paraphrase") or item.get("label") or item) for item in rows[:2])


def _join(items: Any) -> str:
    values = [str(item) for item in (items or []) if item]
    return "；".join(values) if values else "未披露"


def _unique(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result = []
    for item in items:
        key = str(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _unique_unknowns(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in items:
        key = str(item.get("unknown_id") or item.get("unknown") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _unique_handoffs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in items:
        key = str(item.get("handoff_id") or item.get("request") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _stable_id(value: Any) -> str:
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:10]
