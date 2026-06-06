from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_research.env import load_dotenv
from stock_research.alternative_data import collect_alternative_data_signals
from stock_research.comparator_evidence import run_comparator_evidence_pipeline
from stock_research.diagnostics import run_v1_financial_diagnostics
from stock_research.evidence_communication import (
    build_evidence_communication_pack,
    build_evidence_communication_report,
)
from stock_research.feedback_loop import (
    apply_feedback_to_layer1_question_pack,
    build_feedback_loop_pack,
    build_feedback_loop_report,
)
from stock_research.extraction.xbrl import extract_financial_facts_from_documents
from stock_research.graph import build_graph
from stock_research.layer1_questions import build_layer1_question_pack
from stock_research.learning.lessons import build_lesson_report, load_lesson_registry
from stock_research.material_events import scan_material_events
from stock_research.management_communication import build_management_communication_pack
from stock_research.metrics.v1 import calculate_v1_financial_metrics, calculate_v1_valuation_metrics
from stock_research.monitoring.watchlist import run_watchlist_monitor
from stock_research.official_evidence import (
    build_official_report_evidence_pack,
    build_official_report_evidence_report,
)
from stock_research.report_pack import build_financial_report_pack
from stock_research.reports.financial_interpretation import build_financial_easy_reading_report
from stock_research.reports.financial_research_draft import build_financial_research_draft
from stock_research.reports.financial_visual import build_financial_visual_report
from stock_research.reports.markdown import build_final_report, build_financial_results_report
from stock_research.sources.fmp import run_fmp_smoke_test
from stock_research.state import make_initial_state
from stock_research.storage import (
    ensure_run_layout,
    save_state,
    write_evidence_communication_pack,
    write_evidence_communication_report,
    write_feedback_loop_pack,
    write_feedback_loop_report,
    write_financial_easy_reading_report,
    write_financial_report_pack,
    write_layer1_question_pack,
    write_financial_research_draft,
    write_financial_results_report,
    write_financial_visual_report,
    write_final_report,
    write_management_communication_pack,
    write_official_report_evidence_pack,
    write_official_report_evidence_report,
)


def make_run_id(company: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_company = "".join(ch.lower() if ch.isalnum() else "-" for ch in company).strip("-")
    return f"{timestamp}-{safe_company}"


def run_research(
    *,
    company: str,
    market: str,
    runs_dir: str | Path = "data/runs",
    requested_years: str = "all_available",
) -> dict[str, Any]:
    load_dotenv()
    run_id = make_run_id(company)
    run_dir = Path(runs_dir) / run_id
    ensure_run_layout(run_dir)
    state = make_initial_state(
        run_id=run_id,
        run_dir=str(run_dir),
        company=company,
        market=market,
        requested_years=requested_years,
    )
    save_state(state)
    graph = build_graph()
    final_state = graph.invoke(state)
    save_state(final_state)
    return {
        "run_id": final_state["run_id"],
        "run_dir": final_state["run_dir"],
        "final_report_path": final_state.get("final_report_path"),
        "financial_results_report_path": final_state.get("financial_results_report_path"),
        "financial_easy_reading_report_path": final_state.get("financial_easy_reading_report_path"),
        "financial_research_draft_path": final_state.get("financial_research_draft_path"),
        "financial_visual_report_path": final_state.get("financial_visual_report_path"),
        "layer1_question_pack_path": final_state.get("layer1_question_pack_path"),
        "evidence_communication_pack_path": final_state.get("evidence_communication_pack_path"),
        "evidence_communication_report_path": final_state.get("evidence_communication_report_path"),
        "feedback_loop_pack_path": final_state.get("feedback_loop_pack_path"),
        "feedback_loop_report_path": final_state.get("feedback_loop_report_path"),
        "source_map_path": final_state.get("source_map_path"),
        "decision_question_pack_path": final_state.get("decision_question_pack_path"),
        "evidence_plan_path": final_state.get("evidence_plan_path"),
        "filing_deep_read_pack_path": final_state.get("filing_deep_read_pack_path"),
        "evidence_registry_path": final_state.get("evidence_registry_path"),
        "question_evidence_completion_pack_path": final_state.get("question_evidence_completion_pack_path"),
        "theme_workpaper_pack_path": final_state.get("theme_workpaper_pack_path"),
        "theme_workpaper_report_path": final_state.get("theme_workpaper_report_path"),
        "question_dossier_pack_path": final_state.get("question_dossier_pack_path"),
        "theme_workpaper_evidence_appendix_path": final_state.get("theme_workpaper_evidence_appendix_path"),
        "qa_gap_triage_path": final_state.get("qa_gap_triage_path"),
        "pillar_judgment_stub_path": final_state.get("pillar_judgment_stub_path"),
        "official_report_evidence_report_path": final_state.get("official_report_evidence_report_path"),
        "business_model_evidence_pack_path": final_state.get("business_model_evidence_pack_path"),
        "business_model_evidence_report_path": final_state.get("business_model_evidence_report_path"),
        "business_model_unit_economics_pack_path": final_state.get("business_model_unit_economics_pack_path"),
        "business_model_unit_economics_report_path": final_state.get("business_model_unit_economics_report_path"),
        "business_model_unit_economics_chinese_report_path": final_state.get(
            "business_model_unit_economics_chinese_report_path"
        ),
        "business_model_report_path": final_state.get("business_model_report_path"),
        "right_people_report_path": final_state.get("right_people_report_path"),
        "right_people_chinese_report_path": final_state.get("right_people_chinese_report_path"),
        "data_linkage_report_path": final_state.get("data_linkage_report_path"),
        "graph_backend": final_state.get("graph_backend"),
    }


def list_runs(runs_dir: str | Path = "data/runs") -> list[str]:
    path = Path(runs_dir)
    if not path.exists():
        return []
    return sorted([item.name for item in path.iterdir() if item.is_dir()])


def show_run(run_id: str, runs_dir: str | Path = "data/runs") -> dict[str, Any]:
    state_path = Path(runs_dir) / run_id / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Run state not found: {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def rerun_financial_report(run_id: str, runs_dir: str | Path = "data/runs") -> dict[str, Any]:
    state_path = Path(runs_dir) / run_id / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Run state not found: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("documents"):
        extraction = extract_financial_facts_from_documents(state.get("documents", []))
        state["raw_extracted_facts"] = extraction["raw_facts"]
        state["extracted_facts"] = extraction["selected_facts"]
        state["extraction_summary"] = extraction["summary"]
    state["metrics"] = calculate_v1_financial_metrics(state.get("extracted_facts", []))
    state["diagnostic_findings"] = run_v1_financial_diagnostics(
        extracted_facts=state.get("extracted_facts", []),
        metrics=state.get("metrics", []),
    )
    state["material_event_scan"] = scan_material_events(state.get("documents", []))
    state["valuation_metrics"] = calculate_v1_valuation_metrics(
        state.get("extracted_facts", []),
        market_inputs=state.get("market_inputs", {}),
        financial_metrics=state.get("metrics", []),
    )
    state["financial_report_pack"] = build_financial_report_pack(state)
    write_financial_report_pack(state)
    state["layer1_question_pack"] = build_layer1_question_pack(state)
    write_layer1_question_pack(state)
    state["financial_report_pack"]["layer1_question_pack_summary"] = (
        state["layer1_question_pack"].get("summary") or {}
    )
    state["financial_report_pack"]["layer1_question_pack_path"] = state.get("layer1_question_pack_path")
    write_financial_report_pack(state)
    state["official_report_evidence_pack"] = build_official_report_evidence_pack(state)
    write_official_report_evidence_pack(state)
    evidence_report = build_official_report_evidence_report(state.get("official_report_evidence_pack", {}))
    write_official_report_evidence_report(state, evidence_report)
    state["management_communication_pack"] = build_management_communication_pack(state)
    write_management_communication_pack(state)
    state["evidence_communication_pack"] = build_evidence_communication_pack(state)
    write_evidence_communication_pack(state)
    evidence_communication_report = build_evidence_communication_report(state["evidence_communication_pack"])
    write_evidence_communication_report(state, evidence_communication_report)
    state["financial_report_pack"]["official_report_evidence_pack_path"] = state.get(
        "official_report_evidence_pack_path"
    )
    state["financial_report_pack"]["management_communication_pack_path"] = state.get(
        "management_communication_pack_path"
    )
    state["financial_report_pack"]["evidence_communication_pack_summary"] = (
        state["evidence_communication_pack"].get("summary") or {}
    )
    state["financial_report_pack"]["evidence_communication_pack_path"] = state.get(
        "evidence_communication_pack_path"
    )
    write_financial_report_pack(state)
    state["feedback_loop_pack"] = build_feedback_loop_pack(state)
    write_feedback_loop_pack(state)
    state["feedback_loop_pack"].setdefault("source_artifacts", {})["feedback_loop_pack_path"] = state.get(
        "feedback_loop_pack_path"
    )
    write_feedback_loop_pack(state)
    state["layer1_question_pack"] = apply_feedback_to_layer1_question_pack(
        state.get("layer1_question_pack", {}),
        state["feedback_loop_pack"],
    )
    write_layer1_question_pack(state)
    feedback_loop_report = build_feedback_loop_report(state["feedback_loop_pack"])
    write_feedback_loop_report(state, feedback_loop_report)
    state["financial_report_pack"]["layer1_question_pack_summary"] = (
        state["layer1_question_pack"].get("summary") or {}
    )
    state["financial_report_pack"]["layer1_question_pack_path"] = state.get("layer1_question_pack_path")
    state["financial_report_pack"]["feedback_loop_pack_summary"] = (
        state["feedback_loop_pack"].get("summary") or {}
    )
    state["financial_report_pack"]["feedback_loop_pack_path"] = state.get("feedback_loop_pack_path")
    write_financial_report_pack(state)
    report = build_financial_results_report(state, audit_status="Draft pending audit review")
    write_financial_results_report(state, report)
    easy_report = build_financial_easy_reading_report(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_easy_reading_report(state, easy_report)
    research_draft = build_financial_research_draft(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        layer1_question_pack=state.get("layer1_question_pack", {}),
        evidence_communication_pack=state.get("evidence_communication_pack", {}),
        feedback_loop_pack=state.get("feedback_loop_pack", {}),
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_research_draft(state, research_draft)
    visual_report = build_financial_visual_report(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        markdown_report_path=state.get("financial_easy_reading_report_path"),
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_visual_report(state, visual_report)
    final_report = build_final_report(state, audit_status="Draft pending audit review")
    write_final_report(state, final_report)
    save_state(state)
    return {
        "run_id": state["run_id"],
        "run_dir": state["run_dir"],
        "final_report_path": state.get("final_report_path"),
        "financial_results_report_path": state["financial_results_report_path"],
        "financial_easy_reading_report_path": state.get("financial_easy_reading_report_path"),
        "financial_research_draft_path": state.get("financial_research_draft_path"),
        "financial_visual_report_path": state.get("financial_visual_report_path"),
        "layer1_question_pack_path": state.get("layer1_question_pack_path"),
        "evidence_communication_pack_path": state.get("evidence_communication_pack_path"),
        "evidence_communication_report_path": state.get("evidence_communication_report_path"),
        "feedback_loop_pack_path": state.get("feedback_loop_pack_path"),
        "feedback_loop_report_path": state.get("feedback_loop_report_path"),
        "official_report_evidence_pack_path": state.get("official_report_evidence_pack_path"),
        "official_report_evidence_report_path": state.get("official_report_evidence_report_path"),
        "management_communication_pack_path": state.get("management_communication_pack_path"),
        "metric_families": len(state.get("metrics", [])),
        "diagnostic_status": (state.get("diagnostic_findings") or {}).get("status"),
        "material_event_status": (state.get("material_event_scan") or {}).get("status"),
        "financial_report_pack_path": state.get("financial_report_pack_path"),
    }


def rerun_alternative_data(run_id: str, runs_dir: str | Path = "data/runs") -> dict[str, Any]:
    state_path = Path(runs_dir) / run_id / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Run state not found: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["alternative_data_findings"] = collect_alternative_data_signals(state)
    save_state(state)
    findings = state["alternative_data_findings"]
    return {
        "run_id": state["run_id"],
        "run_dir": state["run_dir"],
        "status": findings.get("status"),
        "raw_observations": findings.get("raw_observation_count", 0),
        "normalized_metrics": findings.get("normalized_metric_count", 0),
        "text_events": findings.get("text_event_count", 0),
        "metric_store_path": findings.get("metric_store_path"),
        "text_event_store_path": findings.get("text_event_store_path"),
    }


def run_comparator_evidence(
    *,
    input_path: str | Path,
    output_dir: str | Path = "data/comparator_evidence",
    run_id: str | None = None,
) -> dict[str, Any]:
    return run_comparator_evidence_pipeline(
        input_path=input_path,
        output_dir=output_dir,
        run_id=run_id,
    )


def write_lesson_report(
    *,
    registry_path: str | Path = "config/learning/user_lessons.v1.json",
    output_path: str | Path = "data/learning_lessons_report.md",
) -> dict[str, Any]:
    report = build_lesson_report(registry_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    registry = load_lesson_registry(registry_path)
    return {
        "registry_path": str(registry_path),
        "output_path": str(output),
        "source_materials": len(registry.get("source_materials", [])),
        "agents": len(registry.get("agent_lessons", {})),
    }


def run_fmp_smoke(
    *,
    symbol: str,
    output_dir: str | Path = "data/fmp_smoke",
    limit: int = 5,
) -> dict[str, Any]:
    return run_fmp_smoke_test(symbol=symbol, output_dir=output_dir, limit=limit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create local data directories.")

    research_parser = subparsers.add_parser("research", help="Run the V1 research scaffold.")
    research_parser.add_argument("--company", required=True)
    research_parser.add_argument("--market", required=True)
    research_parser.add_argument("--runs-dir", default="data/runs")
    research_parser.add_argument("--requested-years", default="all_available")

    list_parser = subparsers.add_parser("list-runs", help="List local research runs.")
    list_parser.add_argument("--runs-dir", default="data/runs")

    show_parser = subparsers.add_parser("show-run", help="Show a run state JSON.")
    show_parser.add_argument("run_id")
    show_parser.add_argument("--runs-dir", default="data/runs")

    financial_parser = subparsers.add_parser(
        "rerun-financial-report",
        help="Recalculate metrics and rebuild the financial results report from an existing cached run.",
    )
    financial_parser.add_argument("run_id")
    financial_parser.add_argument("--runs-dir", default="data/runs")

    alternative_parser = subparsers.add_parser(
        "rerun-alternative-data",
        help="Rebuild the alternative-data signal pack from cached/manual observations for an existing run.",
    )
    alternative_parser.add_argument("run_id")
    alternative_parser.add_argument("--runs-dir", default="data/runs")

    comparator_parser = subparsers.add_parser(
        "comparator-evidence",
        help="Build a comparator evidence pack and Markdown report for a target company.",
    )
    comparator_parser.add_argument("--input", required=True, help="JSON or YAML comparator request path.")
    comparator_parser.add_argument("--output-dir", default="data/comparator_evidence")
    comparator_parser.add_argument("--run-id", default=None)

    lessons_parser = subparsers.add_parser("lessons", help="Write a Markdown lesson registry report.")
    lessons_parser.add_argument("--registry", default="config/learning/user_lessons.v1.json")
    lessons_parser.add_argument("--output", default="data/learning_lessons_report.md")

    monitor_parser = subparsers.add_parser("monitor", help="Run the cached watchlist monitor skeleton.")
    monitor_parser.add_argument("--watchlist", default="config/watchlist.json")
    monitor_parser.add_argument("--cache-root", default="data/raw")
    monitor_parser.add_argument("--output-dir", default="data/monitoring")

    fmp_parser = subparsers.add_parser("fmp-smoke", help="Smoke-test Financial Modeling Prep endpoints.")
    fmp_parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g. PDD.")
    fmp_parser.add_argument("--output-dir", default="data/fmp_smoke")
    fmp_parser.add_argument("--limit", type=int, default=5)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        ensure_run_layout("data/runs/.keep")
        print("Initialized local data directories.")
        return 0

    if args.command == "research":
        result = run_research(
            company=args.company,
            market=args.market,
            runs_dir=args.runs_dir,
            requested_years=args.requested_years,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "list-runs":
        print(json.dumps(list_runs(args.runs_dir), indent=2, ensure_ascii=False))
        return 0

    if args.command == "show-run":
        print(json.dumps(show_run(args.run_id, args.runs_dir), indent=2, ensure_ascii=False))
        return 0

    if args.command == "rerun-financial-report":
        print(
            json.dumps(
                rerun_financial_report(args.run_id, args.runs_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "rerun-alternative-data":
        print(
            json.dumps(
                rerun_alternative_data(args.run_id, args.runs_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "comparator-evidence":
        print(
            json.dumps(
                run_comparator_evidence(
                    input_path=args.input,
                    output_dir=args.output_dir,
                    run_id=args.run_id,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "lessons":
        print(
            json.dumps(
                write_lesson_report(registry_path=args.registry, output_path=args.output),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "monitor":
        print(
            json.dumps(
                run_watchlist_monitor(
                    watchlist_path=args.watchlist,
                    cache_root=args.cache_root,
                    output_dir=args.output_dir,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "fmp-smoke":
        print(
            json.dumps(
                run_fmp_smoke(
                    symbol=args.symbol,
                    output_dir=args.output_dir,
                    limit=args.limit,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
