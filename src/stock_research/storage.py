from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stock_research.state import ResearchState, utc_now_iso


def ensure_run_layout(run_dir: str | Path) -> Path:
    path = Path(run_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "agent_reports").mkdir(exist_ok=True)
    return path


def save_state(state: ResearchState) -> None:
    run_dir = ensure_run_layout(state["run_dir"])
    (run_dir / "state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def append_audit_event(state: ResearchState, event: dict[str, Any]) -> ResearchState:
    event = {"created_at": utc_now_iso(), **event}
    state.setdefault("audit_events", []).append(event)
    run_dir = ensure_run_layout(state["run_dir"])
    with (run_dir / "audit_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
    return state


def write_agent_report(state: ResearchState, agent_id: str, title: str, body: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "agent_reports" / f"{agent_id}.md"
    content = f"# {title}\n\n{body.strip()}\n"
    report_path.write_text(content, encoding="utf-8")
    state.setdefault("agent_reports", []).append(
        {
            "agent_id": agent_id,
            "title": title,
            "path": str(report_path),
            "created_at": utc_now_iso(),
        }
    )
    return state


def write_final_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "final_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["final_report_path"] = str(report_path)
    return state


def write_financial_results_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "financial_results_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["financial_results_report_path"] = str(report_path)
    return state


def write_financial_easy_reading_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "financial_easy_reading_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["financial_easy_reading_report_path"] = str(report_path)
    return state


def write_financial_report_pack(state: ResearchState) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "financial_report_pack.json"
    report_path.write_text(
        json.dumps(state.get("financial_report_pack") or {}, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    state["financial_report_pack_path"] = str(report_path)
    return state


def write_official_report_evidence_pack(state: ResearchState) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "official_report_evidence_pack.json"
    report_path.write_text(
        json.dumps(state.get("official_report_evidence_pack") or {}, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    state["official_report_evidence_pack_path"] = str(report_path)
    return state


def write_official_report_evidence_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "official_report_evidence_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["official_report_evidence_report_path"] = str(report_path)
    return state


def write_management_communication_pack(state: ResearchState) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "management_communication_pack.json"
    report_path.write_text(
        json.dumps(state.get("management_communication_pack") or {}, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    state["management_communication_pack_path"] = str(report_path)
    return state


def write_business_model_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "business_model_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["business_model_report_path"] = str(report_path)
    return state


def write_right_people_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "right_people_report.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["right_people_report_path"] = str(report_path)
    return state


def write_right_people_chinese_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "right_people_report.zh.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["right_people_chinese_report_path"] = str(report_path)
    return state


def write_data_linkage_report(state: ResearchState, content: str) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "data_linkage.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    state["data_linkage_report_path"] = str(report_path)
    return state


def write_video_manifest(state: ResearchState) -> ResearchState:
    run_dir = ensure_run_layout(state["run_dir"])
    report_path = run_dir / "video_manifest.json"
    report_path.write_text(
        json.dumps(state.get("video_manifest") or {}, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    state["video_manifest_path"] = str(report_path)
    return state


def complete_node(state: ResearchState, *, agent_id: str, title: str, report_body: str) -> ResearchState:
    write_agent_report(state, agent_id, title, report_body)
    append_audit_event(
        state,
        {
            "agent_id": agent_id,
            "event": "agent_completed",
            "message": f"{title} completed.",
        },
    )
    save_state(state)
    return state
