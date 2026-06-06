from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from stock_research.cli import run_research, write_lesson_report
from stock_research.alternative_data.agent import collect_alternative_data_signals_for_request
from stock_research.companies import resolve_company_from_registry
from stock_research.diagnostics import run_v1_financial_diagnostics
from stock_research.extraction.xbrl import extract_financial_facts_from_documents, verify_financial_facts
from stock_research.extraction.tencent_reports import (
    extract_tencent_annual_report_text_facts,
    extract_tencent_interim_report_text_facts,
)
from stock_research.env import load_dotenv
from stock_research.material_events import scan_material_events
from stock_research.metrics.v1 import (
    calculate_v1_financial_metrics,
    calculate_v1_metrics,
    calculate_v1_valuation_metrics,
    quarterly_fact_rows,
)
from stock_research.monitoring.watchlist import run_watchlist_monitor
from stock_research.report_pack import build_financial_report_pack
from stock_research.reports.financial_interpretation import build_financial_easy_reading_report
from stock_research.reports.financial_research_draft import build_financial_research_draft
from stock_research.reports.financial_visual import build_financial_visual_report
from stock_research.qualitative.annual_report import official_report_business_model_analysis
from stock_research.qualitative.business_model_evidence import (
    build_business_model_evidence_pack,
    build_business_model_evidence_report,
    build_business_model_unit_economics_chinese_report,
    build_business_model_unit_economics_pack,
    build_business_model_unit_economics_report,
)
from stock_research.qualitative.business_model_sources import build_business_model_source_coverage
from stock_research.qualitative.external_moat import build_external_moat_validation_plan
from stock_research.qualitative.executive_transcripts import (
    collect_executive_video_transcripts,
    parse_bilibili_subtitle_payload,
    parse_youtube_transcript_payload,
)
from stock_research.qualitative.business_model_video_questions import (
    business_model_question_results_from_segments,
)
from stock_research.qualitative.official_events import collect_official_event_transcripts
from stock_research.qualitative.public_voice import collect_public_voice_evidence
from stock_research.qualitative.right_people import build_right_people_analysis
from stock_research.qualitative.video_manifest import (
    build_video_uid,
    canonicalize_url,
    youtube_video_id,
)
from stock_research.sources.document_policy import (
    classify_sec_document_text,
    is_deep_research_document,
    is_financial_extraction_document,
)
from stock_research.sources.sec import SecClient
from stock_research.valuation.market_data import (
    parse_google_pdd_quote_text,
    parse_google_hkd_cny_text,
    parse_google_tencent_quote_text,
    parse_google_usd_cny_text,
    parse_pdd_share_structure_text,
    parse_tencent_share_structure_text,
    validate_market_inputs,
    validate_tencent_market_inputs,
)
from stock_research.valuation.market_inputs import load_manual_market_inputs, market_cap_in_cny


class ScaffoldRunTest(unittest.TestCase):
    def test_pdd_scaffold_run_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            old_offline = os.environ.get("STOCK_RESEARCH_OFFLINE")
            os.environ["STOCK_RESEARCH_OFFLINE"] = "1"
            try:
                result = run_research(company="PDD", market="us-adr", runs_dir=Path(temp_dir) / "runs")
            finally:
                if old_offline is None:
                    os.environ.pop("STOCK_RESEARCH_OFFLINE", None)
                else:
                    os.environ["STOCK_RESEARCH_OFFLINE"] = old_offline

            run_dir = Path(result["run_dir"])
            self.assertTrue((run_dir / "state.json").exists())
            self.assertTrue((run_dir / "audit_log.jsonl").exists())
            self.assertTrue((run_dir / "final_report.md").exists())
            self.assertTrue((run_dir / "financial_results_report.md").exists())
            self.assertTrue((run_dir / "financial_easy_reading_report.md").exists())
            self.assertTrue((run_dir / "financial_research_draft.md").exists())
            self.assertTrue((run_dir / "financial_visual_report.html").exists())
            self.assertTrue((run_dir / "financial_report_pack.json").exists())
            self.assertTrue((run_dir / "layer1_question_pack.json").exists())
            self.assertTrue((run_dir / "evidence_communication_pack.json").exists())
            self.assertTrue((run_dir / "evidence_communication_report.md").exists())
            self.assertTrue((run_dir / "feedback_loop_pack.json").exists())
            self.assertTrue((run_dir / "feedback_loop_report.md").exists())
            self.assertTrue((run_dir / "source_map.json").exists())
            self.assertTrue((run_dir / "decision_question_pack.json").exists())
            self.assertTrue((run_dir / "evidence_plan.json").exists())
            self.assertTrue((run_dir / "filing_deep_read_pack.json").exists())
            self.assertTrue((run_dir / "evidence_registry.json").exists())
            self.assertTrue((run_dir / "question_evidence_completion_pack.json").exists())
            self.assertTrue((run_dir / "theme_workpaper_pack.json").exists())
            self.assertTrue((run_dir / "theme_workpaper_report.md").exists())
            self.assertTrue((run_dir / "question_dossier_pack.json").exists())
            self.assertTrue((run_dir / "theme_workpaper_evidence_appendix.md").exists())
            self.assertTrue((run_dir / "qa_gap_triage.json").exists())
            self.assertTrue((run_dir / "pillar_judgment_stub.json").exists())
            self.assertTrue((run_dir / "official_report_evidence_pack.json").exists())
            self.assertTrue((run_dir / "official_report_evidence_report.md").exists())
            self.assertTrue((run_dir / "business_model_evidence.json").exists())
            self.assertTrue((run_dir / "business_model_evidence_report.md").exists())
            self.assertTrue((run_dir / "business_model_unit_economics_pack.json").exists())
            self.assertTrue((run_dir / "business_model_unit_economics_report.md").exists())
            self.assertTrue((run_dir / "business_model_unit_economics_report.zh.md").exists())
            self.assertTrue((run_dir / "business_model_report.md").exists())
            self.assertTrue((run_dir / "right_people_report.md").exists())
            self.assertTrue((run_dir / "right_people_report.zh.md").exists())
            self.assertTrue((run_dir / "data_linkage.md").exists())
            self.assertTrue((run_dir / "video_manifest.json").exists())
            self.assertTrue((run_dir / "agent_reports" / "company_resolver.md").exists())
            self.assertTrue((run_dir / "agent_reports" / "audit_review.md").exists())

            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["canonical_company"]["legal_name"], "PDD Holdings Inc.")
            self.assertEqual(state["market"], "us-adr")
            self.assertEqual(len(state["agent_reports"]), 33)
            self.assertEqual(state["financial_results_report_path"], str(run_dir / "financial_results_report.md"))
            self.assertEqual(
                state["financial_easy_reading_report_path"],
                str(run_dir / "financial_easy_reading_report.md"),
            )
            self.assertEqual(
                state["financial_research_draft_path"],
                str(run_dir / "financial_research_draft.md"),
            )
            self.assertEqual(
                state["financial_visual_report_path"],
                str(run_dir / "financial_visual_report.html"),
            )
            self.assertEqual(state["financial_report_pack_path"], str(run_dir / "financial_report_pack.json"))
            self.assertEqual(state["layer1_question_pack_path"], str(run_dir / "layer1_question_pack.json"))
            self.assertEqual(
                state["evidence_communication_pack_path"],
                str(run_dir / "evidence_communication_pack.json"),
            )
            self.assertEqual(
                state["evidence_communication_report_path"],
                str(run_dir / "evidence_communication_report.md"),
            )
            self.assertEqual(state["feedback_loop_pack_path"], str(run_dir / "feedback_loop_pack.json"))
            self.assertEqual(state["feedback_loop_report_path"], str(run_dir / "feedback_loop_report.md"))
            self.assertEqual(state["source_map_path"], str(run_dir / "source_map.json"))
            self.assertEqual(state["decision_question_pack_path"], str(run_dir / "decision_question_pack.json"))
            self.assertEqual(state["evidence_plan_path"], str(run_dir / "evidence_plan.json"))
            self.assertEqual(state["filing_deep_read_pack_path"], str(run_dir / "filing_deep_read_pack.json"))
            self.assertEqual(state["evidence_registry_path"], str(run_dir / "evidence_registry.json"))
            self.assertEqual(
                state["question_evidence_completion_pack_path"],
                str(run_dir / "question_evidence_completion_pack.json"),
            )
            self.assertEqual(state["theme_workpaper_pack_path"], str(run_dir / "theme_workpaper_pack.json"))
            self.assertEqual(state["theme_workpaper_report_path"], str(run_dir / "theme_workpaper_report.md"))
            self.assertEqual(state["question_dossier_pack_path"], str(run_dir / "question_dossier_pack.json"))
            self.assertEqual(
                state["theme_workpaper_evidence_appendix_path"],
                str(run_dir / "theme_workpaper_evidence_appendix.md"),
            )
            self.assertEqual(state["qa_gap_triage_path"], str(run_dir / "qa_gap_triage.json"))
            self.assertEqual(state["pillar_judgment_stub_path"], str(run_dir / "pillar_judgment_stub.json"))
            self.assertEqual(
                state["official_report_evidence_pack_path"],
                str(run_dir / "official_report_evidence_pack.json"),
            )
            self.assertEqual(
                state["official_report_evidence_report_path"],
                str(run_dir / "official_report_evidence_report.md"),
            )
            self.assertEqual(
                state["business_model_evidence_pack_path"],
                str(run_dir / "business_model_evidence.json"),
            )
            self.assertEqual(
                state["business_model_evidence_report_path"],
                str(run_dir / "business_model_evidence_report.md"),
            )
            self.assertEqual(
                state["business_model_unit_economics_pack_path"],
                str(run_dir / "business_model_unit_economics_pack.json"),
            )
            self.assertEqual(
                state["business_model_unit_economics_report_path"],
                str(run_dir / "business_model_unit_economics_report.md"),
            )
            self.assertEqual(
                state["business_model_unit_economics_chinese_report_path"],
                str(run_dir / "business_model_unit_economics_report.zh.md"),
            )
            self.assertEqual(state["business_model_report_path"], str(run_dir / "business_model_report.md"))
            self.assertEqual(state["right_people_report_path"], str(run_dir / "right_people_report.md"))
            self.assertEqual(
                state["right_people_chinese_report_path"],
                str(run_dir / "right_people_report.zh.md"),
            )
            self.assertEqual(state["data_linkage_report_path"], str(run_dir / "data_linkage.md"))
            self.assertEqual(state["video_manifest_path"], str(run_dir / "video_manifest.json"))
            self.assertIn("video_manifest", state)
            self.assertIn("alternative_data_findings", state)
            self.assertIn("valuation_metrics", state)
            self.assertIn("diagnostic_findings", state)
            self.assertIn("material_event_scan", state)
            self.assertIn("financial_report_pack", state)
            self.assertIn("layer1_question_pack", state)
            self.assertIn("evidence_communication_pack", state)
            self.assertIn("feedback_loop_pack", state)
            self.assertIn("source_map", state)
            self.assertIn("decision_question_pack", state)
            self.assertIn("evidence_plan", state)
            self.assertIn("filing_deep_read_pack", state)
            self.assertIn("evidence_registry", state)
            self.assertIn("question_evidence_completion_pack", state)
            self.assertIn("theme_workpaper_pack", state)
            self.assertIn("question_dossier_pack", state)
            self.assertIn("qa_gap_triage", state)
            self.assertIn("pillar_judgment_stub", state)
            self.assertIn("official_report_evidence_pack", state)
            self.assertIn("business_model_evidence_pack", state)
            self.assertIn("business_model_unit_economics_pack", state)
            self.assertGreaterEqual(state["video_manifest"]["record_count"], 5)
            self.assertIn(state["graph_backend"], {"langgraph", "local_sequential_fallback"})
            self.assertIn("learning_context", state)
            self.assertIn("ir_cross_validation", state)
            self.assertIn("external_moat_findings", state)
            self.assertIn("public_voice_findings", state)
            self.assertIn("executive_transcript_findings", state)
            self.assertIn("official_event_transcript_findings", state)
            self.assertIn("leadership_findings", state)
            self.assertIn("evidence_subagent_cluster", state["business_model_findings"])
            self.assertIn("source_coverage", state["business_model_findings"])
            self.assertGreaterEqual(
                state["business_model_findings"]["source_coverage"]["source_group_count"],
                4,
            )

            report = (run_dir / "final_report.md").read_text(encoding="utf-8")
            self.assertIn("PDD Holdings Inc.", report)
            self.assertIn("Audit Status", report)
            self.assertIn("Source Summary", report)
            self.assertIn("Learning Materials", report)
            self.assertIn("External Moat Validation Sources", report)
            self.assertIn("Business Model Subagent Cluster", report)
            self.assertIn("Public Voice / Forum Evidence", report)
            self.assertIn("Alternative Data Signals", report)
            self.assertIn("Executive Video Transcript Evidence", report)
            self.assertIn("Right Business / People / Price Checklist", report)
            self.assertIn("Right people / 正确的人和组织:", report)
            self.assertIn("Data Linkage", report)

            financial_report = (run_dir / "financial_results_report.md").read_text(encoding="utf-8")
            self.assertIn("Financial Results Report", financial_report)
            self.assertIn("Chinese easy-reading financial report", financial_report)
            self.assertIn("Financial Quality Questions", financial_report)
            self.assertIn("consolidated diagnostic view", financial_report)
            self.assertIn("Annual Financial History", financial_report)
            self.assertIn("Metric Pack Coverage", financial_report)
            self.assertIn("Excluded from this report", financial_report)
            self.assertNotIn("## Valuation Metrics", financial_report)
            self.assertNotIn("## Market Data / Yield Inputs", financial_report)
            self.assertNotIn("## Cross-Validation Status", financial_report)
            self.assertIn("Material Event Scan", financial_report)
            self.assertIn("Financial Report Pack", financial_report)
            self.assertIn("Extraction And Verification", financial_report)

            pack = json.loads((run_dir / "financial_report_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(pack["schema_version"], "financial_report_pack_v1")
            self.assertIn("material_event_scan", pack)
            self.assertIn("human_review_flags", pack)
            self.assertIn("financial_health", pack)
            self.assertIn("layer1_question_pack_summary", pack)
            self.assertIn("layer1_question_pack_path", pack)
            self.assertIn("evidence_communication_pack_summary", pack)
            self.assertIn("evidence_communication_pack_path", pack)
            self.assertIn("feedback_loop_pack_summary", pack)
            self.assertIn("feedback_loop_pack_path", pack)
            self.assertNotIn("evidence_communication_pack", pack)
            self.assertNotIn("feedback_loop_pack", pack)
            self.assertIn(pack["financial_health_status"], {"improving", "stable", "mixed", "deteriorating", "unknown"})
            self.assertIn("main_positive_evidence", pack["financial_health"])
            self.assertIn("main_negative_evidence", pack["financial_health"])
            self.assertNotIn("valuation_metrics", pack)

            evidence_pack = json.loads((run_dir / "official_report_evidence_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence_pack["schema_version"], "official_report_evidence_pack_v1")
            self.assertIn("question_answers", evidence_pack)
            self.assertIn("decision_relevant_narratives", evidence_pack)

            layer1_pack = json.loads((run_dir / "layer1_question_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(layer1_pack["schema_version"], "layer1_question_pack_v1")
            self.assertIn("standard_question_answers", layer1_pack)
            self.assertIn("research_questions", layer1_pack)
            self.assertIn("handoff_to_evidence_communication", layer1_pack)
            self.assertIn("feedback_requery_questions", layer1_pack)

            evidence_communication_pack = json.loads(
                (run_dir / "evidence_communication_pack.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence_communication_pack["schema_version"], "evidence_communication_pack_v1")
            self.assertIn("question_answers", evidence_communication_pack)
            self.assertIn("proactive_discoveries", evidence_communication_pack)
            self.assertIn("narrative_registry", evidence_communication_pack)
            self.assertIn("transitional_source_packs", evidence_communication_pack)

            evidence_communication_report = (run_dir / "evidence_communication_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Evidence & Communication Extraction", evidence_communication_report)
            self.assertIn("问题复核", evidence_communication_report)
            self.assertIn("主动发现", evidence_communication_report)

            feedback_loop_pack = json.loads((run_dir / "feedback_loop_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(feedback_loop_pack["schema_version"], "feedback_loop_pack_v1")
            self.assertIn("financial_extractor_requests", feedback_loop_pack)
            self.assertIn("metric_recalculation_requests", feedback_loop_pack)
            self.assertIn("layer1_requery_requests", feedback_loop_pack)
            self.assertIn("evidence_communication_followups", feedback_loop_pack)
            self.assertIn("summary", feedback_loop_pack)

            feedback_loop_report = (run_dir / "feedback_loop_report.md").read_text(encoding="utf-8")
            self.assertIn("Feedback Router", feedback_loop_report)
            self.assertIn("闭环状态", feedback_loop_report)

            source_map = json.loads((run_dir / "source_map.json").read_text(encoding="utf-8"))
            self.assertEqual(source_map["schema_version"], "source_map_v1")
            self.assertEqual(source_map["prototype_version"], "v1.0")
            self.assertIn("source_inventory", source_map)
            self.assertIn("coverage_summary", source_map)
            self.assertGreaterEqual(source_map["coverage_summary"]["source_count"], 1)

            decision_question_pack = json.loads(
                (run_dir / "decision_question_pack.json").read_text(encoding="utf-8")
            )
            self.assertEqual(decision_question_pack["schema_version"], "decision_question_pack_v1")
            self.assertEqual(decision_question_pack["prototype_version"], "v1.1")
            self.assertGreaterEqual(len(decision_question_pack["questions"]), 12)
            self.assertTrue(
                any(question["question_id"] == "financial.cash_conversion" for question in decision_question_pack["questions"])
            )

            evidence_plan = json.loads((run_dir / "evidence_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence_plan["schema_version"], "evidence_plan_v1")
            self.assertEqual(evidence_plan["prototype_version"], "v1.1")
            self.assertEqual(len(evidence_plan["plans"]), len(decision_question_pack["questions"]))

            filing_deep_read_pack = json.loads((run_dir / "filing_deep_read_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(filing_deep_read_pack["schema_version"], "filing_deep_read_pack_v1")
            self.assertEqual(filing_deep_read_pack["prototype_version"], "v1.25")
            self.assertIn("evidence_cards", filing_deep_read_pack)
            self.assertIn("contradiction_matrix", filing_deep_read_pack)
            self.assertIn("question_coverage", filing_deep_read_pack)
            self.assertIn("gap_requests", filing_deep_read_pack)
            self.assertIn("official_report_evidence", filing_deep_read_pack["adapter_summaries"])
            self.assertGreaterEqual(filing_deep_read_pack["summary"]["evidence_card_count"], 1)

            evidence_registry = json.loads((run_dir / "evidence_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence_registry["schema_version"], "evidence_registry_v1")
            self.assertEqual(evidence_registry["prototype_version"], "v1.2+v1.45")
            self.assertIn("evidence_items", evidence_registry)
            self.assertGreaterEqual(evidence_registry["registry_summary"]["evidence_item_count"], 1)
            self.assertIn("fact", evidence_registry["registry_summary"]["evidence_kind_counts"])
            self.assertIn("registry_gap_requests", evidence_registry)
            self.assertIn("leadership_findings", evidence_registry["source_artifacts"]["adapter_summaries"])
            self.assertIn("valuation_metrics", evidence_registry["source_artifacts"]["adapter_summaries"])
            self.assertIn("question_evidence_completion_pack", evidence_registry["source_artifacts"])
            self.assertGreaterEqual(evidence_registry["registry_summary"]["supplemental_evidence_count"], 0)

            completion_pack = json.loads((run_dir / "question_evidence_completion_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(completion_pack["schema_version"], "question_evidence_completion_pack_v1")
            self.assertEqual(completion_pack["prototype_version"], "v1.45")
            self.assertIn("coverage_gates", completion_pack)
            self.assertIn("targeted_read_tasks", completion_pack)
            self.assertIn("supplemental_evidence_items", completion_pack)
            self.assertGreaterEqual(completion_pack["summary"]["targeted_read_task_count"], 1)
            self.assertGreaterEqual(completion_pack["summary"]["supplemental_evidence_count"], 0)

            theme_workpaper_pack = json.loads((run_dir / "theme_workpaper_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(theme_workpaper_pack["schema_version"], "theme_workpaper_pack_v1")
            self.assertEqual(theme_workpaper_pack["prototype_version"], "v1.3")
            self.assertEqual(len(theme_workpaper_pack["workpapers"]), 5)
            workpaper_themes = {workpaper["theme"] for workpaper in theme_workpaper_pack["workpapers"]}
            self.assertIn("financial_reality", workpaper_themes)
            self.assertIn("risk_fragility", workpaper_themes)
            self.assertIn("valuation_assumptions", workpaper_themes)

            theme_workpaper_report = (run_dir / "theme_workpaper_report.md").read_text(encoding="utf-8")
            self.assertIn("Decision-Question-Led Evidence Workflow", theme_workpaper_report)
            self.assertIn("Version Map", theme_workpaper_report)
            self.assertIn("v1.35", theme_workpaper_report)
            self.assertIn("v1.45", theme_workpaper_report)
            self.assertIn("Evidence base summary:", theme_workpaper_report)
            self.assertIn("Evidence completion attempt:", theme_workpaper_report)
            self.assertFalse(any("\u3400" <= char <= "\u9fff" for char in theme_workpaper_report))

            question_dossier_pack = json.loads((run_dir / "question_dossier_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(question_dossier_pack["schema_version"], "question_dossier_pack_v1")
            self.assertEqual(question_dossier_pack["prototype_version"], "v1.35")
            self.assertEqual(
                question_dossier_pack["summary"]["question_count"],
                len(decision_question_pack["questions"]),
            )
            self.assertGreaterEqual(question_dossier_pack["summary"]["questions_with_evidence"], 1)
            self.assertGreaterEqual(question_dossier_pack["summary"]["total_evidence_links"], 1)
            cash_dossier = next(
                dossier
                for dossier in question_dossier_pack["dossiers"]
                if dossier["question_id"] == "financial.cash_conversion"
            )
            self.assertIn("evidence_coverage", cash_dossier)
            self.assertIn("source_coverage", cash_dossier)
            self.assertIn("supporting_evidence", cash_dossier)
            self.assertIn("materiality_ranking", cash_dossier)
            self.assertIn("contradictions_and_tensions", cash_dossier)
            self.assertIn("gap_severity_ranking", cash_dossier)
            self.assertIn("financial_bridge_tables", cash_dossier)
            self.assertIn("question_completion", cash_dossier)
            self.assertIn("coverage_gate", cash_dossier["question_completion"])
            self.assertIn("supplemental_evidence", cash_dossier["question_completion"])
            self.assertIn("machine_contract", cash_dossier["question_completion"])
            self.assertIn("remaining_gap_status", cash_dossier["question_completion"]["machine_contract"])

            evidence_appendix = (run_dir / "theme_workpaper_evidence_appendix.md").read_text(encoding="utf-8")
            self.assertIn("Theme Workpaper Evidence Appendix", evidence_appendix)
            self.assertIn("Evidence completion attempt", evidence_appendix)
            self.assertIn("Material evidence ranking", evidence_appendix)
            self.assertIn("All non-metadata supporting evidence", evidence_appendix)
            self.assertFalse(any("\u3400" <= char <= "\u9fff" for char in evidence_appendix))

            qa_gap_triage = json.loads((run_dir / "qa_gap_triage.json").read_text(encoding="utf-8"))
            self.assertEqual(qa_gap_triage["schema_version"], "qa_gap_triage_v1")
            self.assertEqual(qa_gap_triage["prototype_version"], "v1.4")
            self.assertIn("gap_decisions", qa_gap_triage)
            self.assertIn("triage_summary", qa_gap_triage)
            self.assertIn("research_backlog", qa_gap_triage)
            self.assertEqual(qa_gap_triage["triage_summary"]["failed_citation_count"], 0)
            self.assertIn("backlog_items", qa_gap_triage["research_backlog"])

            pillar_stub = json.loads((run_dir / "pillar_judgment_stub.json").read_text(encoding="utf-8"))
            self.assertEqual(pillar_stub["schema_version"], "pillar_judgment_stub_v1")
            self.assertEqual(pillar_stub["prototype_version"], "v1.4")
            self.assertIn("right_business", pillar_stub["pillar_readiness"])
            self.assertIn("No buy/sell/hold", pillar_stub["scope_limit"])

            evidence_report = (run_dir / "official_report_evidence_report.md").read_text(encoding="utf-8")
            self.assertIn("官方报告证据与解释", evidence_report)
            self.assertIn("第一层问题复核", evidence_report)
            self.assertIn("决策相关官方叙事", evidence_report)

            business_model_evidence = json.loads(
                (run_dir / "business_model_evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(business_model_evidence["agent"], "business_model_evidence_agent")
            self.assertEqual(len(business_model_evidence["questions"]), 9)
            self.assertIn("financial_cross_check", business_model_evidence)
            self.assertIn("questions_for_other_agents", business_model_evidence)

            business_model_unit_economics = json.loads(
                (run_dir / "business_model_unit_economics_pack.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                business_model_unit_economics["workpaper_type"],
                "business_model_unit_economics",
            )
            self.assertEqual(len(business_model_unit_economics["question_answers"]), 18)
            self.assertIn("revenue_streams", business_model_unit_economics)
            self.assertIn("unit_economics_proxies", business_model_unit_economics)
            self.assertIn("unknowns", business_model_unit_economics)
            self.assertIn("handoff", business_model_unit_economics)

            business_model_unit_economics_report = (
                run_dir / "business_model_unit_economics_report.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Business Model & Unit Economics Workpaper", business_model_unit_economics_report)
            self.assertIn("Question Overview", business_model_unit_economics_report)
            self.assertIn("Financial Cross-Checks", business_model_unit_economics_report)

            business_model_unit_economics_zh_report = (
                run_dir / "business_model_unit_economics_report.zh.md"
            ).read_text(encoding="utf-8")
            self.assertIn("商业模式与单位经济底稿", business_model_unit_economics_zh_report)
            self.assertIn("问题总览", business_model_unit_economics_zh_report)
            self.assertIn("财务交叉验证", business_model_unit_economics_zh_report)

            business_model_evidence_report = (
                run_dir / "business_model_evidence_report.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Business Model Evidence Report", business_model_evidence_report)
            self.assertIn("How Does the Company Make Money", business_model_evidence_report)
            self.assertIn("Financial Evidence Cross-Check", business_model_evidence_report)

            easy_report = (run_dir / "financial_easy_reading_report.md").read_text(encoding="utf-8")
            self.assertIn("财务报告易读版", easy_report)
            if "事实抽取失败" in easy_report:
                self.assertIn("缺少核心财务事实", easy_report)
                self.assertIn("没有生成完整财务报告", easy_report)
            else:
                self.assertIn("一页结论", easy_report)
                self.assertIn("核心判断", easy_report)
                self.assertIn("关键证据", easy_report)
                self.assertIn("下一步要证伪", easy_report)
                self.assertIn("财务证据", easy_report)
                self.assertIn("披露边界与口径", easy_report)
                self.assertIn("三年财务趋势", easy_report)
                self.assertIn("季度趋势与拐点", easy_report)
                self.assertIn("资产负债表与现金缓冲", easy_report)
                self.assertIn("关键问题与红旗", easy_report)
                self.assertIn("来源与范围", easy_report)
                self.assertIn("需要人工复核的关键点", easy_report)
                self.assertIn("当前判断", easy_report)
                self.assertIn("判断", easy_report)
                self.assertLess(easy_report.index("## 后续跟踪清单"), easy_report.index("### 披露边界与口径"))

            research_draft = (run_dir / "financial_research_draft.md").read_text(encoding="utf-8")
            self.assertIn("Pipeline 中间产物", research_draft)
            self.assertIn("业务模型事实地图", research_draft)
            self.assertIn("反馈闭环路由", research_draft)

            business_model_report = (run_dir / "business_model_report.md").read_text(encoding="utf-8")
            self.assertIn("Business Model / Moat Report", business_model_report)
            self.assertIn("Fixed Business-Model Evidence Questions", business_model_report)
            self.assertIn("Official Report Evidence", business_model_report)
            self.assertIn("Business Model Source Coverage", business_model_report)
            self.assertIn("merchant_platform_policy", business_model_report)
            self.assertIn("regulatory_trade_policy", business_model_report)
            self.assertIn("competitor_official_filings", business_model_report)
            self.assertIn("app_store_demand_quality", business_model_report)
            self.assertIn("investor_presentations_and_events", business_model_report)
            self.assertIn("Business-Model Open Issues", business_model_report)

            right_people_report = (run_dir / "right_people_report.md").read_text(encoding="utf-8")
            self.assertIn("Right People / Management Quality Report", right_people_report)
            self.assertIn("Evidence Framework", right_people_report)
            self.assertIn("Evidence Buckets", right_people_report)
            self.assertIn("Right People Decision", right_people_report)
            self.assertIn("Scorecard", right_people_report)
            self.assertIn("Management Quality Evidence", right_people_report)
            self.assertIn("Right People Checklist", right_people_report)

            right_people_zh_report = (run_dir / "right_people_report.zh.md").read_text(encoding="utf-8")
            self.assertIn("正确的人 / 管理层质量报告", right_people_zh_report)
            self.assertIn("证据分类框架", right_people_zh_report)
            self.assertIn("证据分类", right_people_zh_report)
            self.assertIn("正确的人决策", right_people_zh_report)
            self.assertIn("评分卡", right_people_zh_report)
            self.assertIn("关键证据摘录", right_people_zh_report)
            self.assertIn("官方申报文件摘录", right_people_zh_report)
            self.assertIn("财务行为证据", right_people_zh_report)
            self.assertIn("管理层质量证据", right_people_zh_report)
            self.assertIn("正确的人检查清单", right_people_zh_report)

            linkage = (run_dir / "data_linkage.md").read_text(encoding="utf-8")
            self.assertIn("Source Inventory", linkage)
            self.assertIn("Document Inventory", linkage)
            self.assertIn("Annual Key Fact Source Lineage", linkage)
            self.assertIn("Selected Financial Fact Linkage", linkage)
            self.assertIn("Official IR Cross-Validation Linkage", linkage)
            self.assertIn("Valuation Metric Linkage", linkage)
            self.assertIn("Alternative Data Linkage", linkage)
            self.assertIn("Executive Transcript Evidence Linkage", linkage)
            self.assertIn("Right People Linkage", linkage)

    def test_alternative_data_agent_normalizes_seed_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            seed_path = run_dir / "alternative_data_seed_observations.json"
            seed_path.write_text(
                json.dumps(
                    {
                        "observations": [
                            {
                                "source": "google_trends",
                                "brand": "Temu",
                                "collected_at": "2026-05-27T00:00:00Z",
                                "raw_payload": {
                                    "date": "2026-05-24",
                                    "keyword": "Temu",
                                    "value": 61,
                                    "unit": "index_0_100",
                                    "region": "US",
                                },
                            },
                            {
                                "source": "youtube",
                                "brand": "Temu",
                                "collected_at": "2026-05-27T00:00:00Z",
                                "raw_payload": {
                                    "date": "2026-05-24",
                                    "query": "Temu review",
                                    "video_count": 184,
                                    "view_count_sum": 10_000,
                                    "comment_count_sum": 500,
                                    "region": "US",
                                },
                            },
                            {
                                "source": "reddit",
                                "brand": "Temu",
                                "source_url": "https://reddit.example/post",
                                "collected_at": "2026-05-27T00:00:00Z",
                                "raw_payload": {
                                    "created_at": "2026-05-25T00:00:00Z",
                                    "text": "Temu refund took forever but delivery was fast.",
                                    "author_id": "user-1",
                                    "upvotes": 21,
                                    "comments": 7,
                                },
                            },
                            {
                                "source": "ecommerce_crawler",
                                "brand": "Temu",
                                "collected_at": "2026-05-27T00:00:00Z",
                                "raw_payload": {
                                    "date": "2026-05-24",
                                    "category": "home_goods",
                                    "price": 8.99,
                                    "discount_pct": 0.3,
                                    "coupon_available": True,
                                    "delivery_min_days": 6,
                                    "delivery_max_days": 10,
                                    "rating": 4.4,
                                    "review_count": 1200,
                                    "region": "US",
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            findings = collect_alternative_data_signals_for_request(
                {
                    "company": "PDD",
                    "brands": ["Temu"],
                    "competitors": ["Amazon", "Shein"],
                    "region": "US",
                    "time_window": "weekly",
                    "lookback_weeks": 52,
                    "keywords": ["Temu", "Temu refund"],
                },
                run_dir=str(run_dir),
            )

            metric_names = {metric["metric_name"] for metric in findings["normalized_metrics"]}
            self.assertEqual(findings["status"], "collected")
            self.assertIn("demand.search.google_trends.brand", metric_names)
            self.assertIn("demand.social.youtube.video_count", metric_names)
            self.assertIn("trust.negative_keyword.refund", metric_names)
            self.assertIn("value.coupon.intensity", metric_names)
            self.assertEqual(findings["text_event_count"], 1)
            self.assertTrue((run_dir / "alternative_data_metrics.json").exists())

    def test_company_registry_resolves_watchlist_companies(self) -> None:
        pdd = resolve_company_from_registry("PDD", market="us-adr")
        tencent = resolve_company_from_registry("Tencent", market="hk")
        google = resolve_company_from_registry("Google", market="us")

        self.assertEqual(pdd["sec_cik_padded"], "0001737806")
        self.assertEqual(tencent["legal_name"], "Tencent Holdings Limited")
        self.assertEqual(google["legal_name"], "Alphabet Inc.")

    def test_lessons_report_and_monitor_write_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lesson_result = write_lesson_report(output_path=Path(temp_dir) / "lessons.md")
            self.assertEqual(lesson_result["agents"], 10)
            self.assertTrue((Path(temp_dir) / "lessons.md").exists())

            monitor_result = run_watchlist_monitor(output_dir=Path(temp_dir) / "monitoring")
            self.assertEqual(monitor_result["companies_checked"], 3)
            self.assertTrue(Path(monitor_result["report_path"]).exists())
            self.assertTrue(Path(monitor_result["snapshot_path"]).exists())

    def test_pdd_external_moat_source_plan_records_quality_controls(self) -> None:
        company = {"company_id": "pdd", "legal_name": "PDD Holdings Inc."}
        business_model_findings = {
            "missing_evidence": [
                "Customer happiness and repeat-purchase quality outside official reports.",
                "Merchant profitability after ads, discounts, logistics, and platform rules.",
            ],
            "official_report_analysis": {
                "subagent_reports": [
                    {
                        "name": "Moat Hypothesis Analyst",
                        "findings": [
                            {
                                "hypothesis": "Two-sided marketplace network effect between buyers and merchants.",
                                "status": "partially_supported",
                            }
                        ],
                    }
                ]
            },
        }

        plan = build_external_moat_validation_plan(
            company=company,
            business_model_findings=business_model_findings,
        )

        self.assertEqual(plan["status"], "source_plan_ready_pending_collection")
        self.assertTrue(plan["planned_only"])
        self.assertGreaterEqual(len(plan["hypotheses"]), 5)
        self.assertGreaterEqual(len(plan["source_lines"]), 5)
        self.assertGreaterEqual(plan["review_needed_decision_count"], 1)
        self.assertIn("official_report_gaps", plan)
        self.assertIn("evidence_output_schema", plan)
        self.assertTrue(
            [
                line
                for line in plan["source_lines"]
                if line["source_line_id"] == "merchant_seller_feedback"
            ]
        )

    def test_pdd_business_model_source_coverage_connects_priority_gaps(self) -> None:
        coverage = build_business_model_source_coverage(
            company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."}
        )

        group_ids = {group["group_id"] for group in coverage["source_groups"]}
        self.assertEqual(coverage["status"], "business_model_source_coverage_v1")
        self.assertIn("merchant_platform_policy", group_ids)
        self.assertIn("official_customer_policy", group_ids)
        self.assertIn("regulatory_trade_policy", group_ids)
        self.assertIn("competitor_official_filings", group_ids)
        self.assertIn("competitor_product_pricing", group_ids)
        self.assertIn("app_store_demand_quality", group_ids)
        self.assertIn("paid_acquisition_and_promotion_signals", group_ids)
        self.assertIn("investor_presentations_and_events", group_ids)
        self.assertGreaterEqual(coverage["source_target_count"], 24)
        self.assertTrue(
            [
                target
                for group in coverage["source_groups"]
                for target in group["source_targets"]
                if target["source_id"] == "temu_product_intelligence_extension"
                and target.get("local_prototype_path")
            ]
        )

    def test_business_model_evidence_pack_maps_fixed_questions(self) -> None:
        source_document = {
            "document_id": "fixture:pdd-20f",
            "document_type": "20-F:primary",
            "source_url": "https://www.sec.gov/example",
        }
        fields = [
            {
                "field_id": "revenue_model",
                "status": "directly_stated",
                "summary": "Revenue comes from transaction services and online marketing services provided to third-party merchants.",
                "source_document": source_document,
                "source_section": "revenue recognition",
                "evidence": ["Our revenues primarily consist of transaction services and online marketing services."],
            },
            {
                "field_id": "customer_groups",
                "status": "directly_stated",
                "summary": "Buyers and merchants are the key participants.",
                "source_document": source_document,
                "source_section": "business overview",
                "evidence": ["The platform connects buyers and merchants."],
            },
            {
                "field_id": "supplier_or_partner_dependencies",
                "status": "directly_stated",
                "summary": "PDD depends on merchants, logistics vendors, and fulfillment partners.",
                "source_document": source_document,
                "source_section": "business overview",
                "evidence": ["Temu works with logistics vendors and fulfillment partners."],
            },
            {
                "field_id": "segment_structure",
                "status": "not_disclosed",
                "summary": "Segment structure not disclosed.",
                "source_document": source_document,
                "source_section": "segment notes",
                "evidence": [],
            },
            {
                "field_id": "management_framing",
                "status": "directly_stated",
                "summary": "Management frames the model around value-for-money and a buyer-merchant flywheel.",
                "source_document": source_document,
                "source_section": "business overview",
                "evidence": ["The platform offers value-for-money merchandise."],
            },
            {
                "field_id": "cost_and_capital_drivers",
                "status": "directly_stated",
                "summary": "Cost drivers include sales and marketing, R&D, logistics, and cost of revenues.",
                "source_document": source_document,
                "source_section": "operating review",
                "evidence": ["Sales and marketing expenses and research and development affect results."],
            },
            {
                "field_id": "risk_factor_map",
                "status": "directly_stated",
                "summary": "Risk factors include competition, quality, logistics, regulation, and trade.",
                "source_document": source_document,
                "source_section": "risk factors",
                "evidence": ["Risk factors include competition, quality, logistics, regulatory and trade matters."],
            },
        ]
        state = {
            "company_query": "PDD",
            "market": "us-adr",
            "canonical_company": {
                "legal_name": "PDD Holdings Inc.",
                "company_id": "pdd",
                "market": "us-adr",
                "tickers": [{"symbol": "PDD"}],
            },
            "business_model_findings": {
                "official_report_analysis": {
                    "official_report_dossier": {"fields": fields},
                    "business_model_deep_dive": {
                        "answer_cards": [
                            {
                                "question_id": "economic_engine",
                                "current_answer": "PDD is a merchant-funded demand aggregation and commerce-services platform.",
                                "official_support": ["Revenue is split between online marketing and transaction services."],
                                "quantitative_support": ["Revenue mix is roughly balanced between the two sources."],
                                "source_evidence": ["Revenue evidence."],
                            },
                            {
                                "question_id": "anti_moat",
                                "current_answer": "Low price may be bought through quality, logistics, regulation, or merchant pressure.",
                                "official_support": ["Risk factors flag competition and quality issues."],
                                "quantitative_support": ["Operating income weakened despite revenue growth."],
                                "source_evidence": ["Risk evidence."],
                            },
                        ]
                    },
                    "operating_kpi_analysis": {
                        "latest_by_metric": {
                            "active_merchants": {
                                "source_document": source_document,
                                "evidence": "Active merchants increased to 16.8 million.",
                            }
                        }
                    },
                },
                "source_coverage": {
                    "status": "business_model_source_coverage_v1",
                    "registry_path": "config/qualitative/pdd_business_model_source_coverage.v1.json",
                    "source_group_count": 8,
                    "source_target_count": 27,
                    "top_connected_gaps": [{"group_id": "merchant_platform_policy", "priority": "P1"}],
                },
                "missing_evidence": ["Merchant profitability after ads, discounts, logistics, and platform rules."],
            },
            "financial_report_pack": {
                "schema_version": "financial_report_pack_v1",
                "financial_health_status": "mixed",
                "financial_health": {
                    "status": "mixed",
                    "main_positive_evidence": "Cash conversion is above 1x.",
                    "main_negative_evidence": "Incremental operating margin is negative.",
                    "next_verification_point": "Watch next-quarter incremental operating margin.",
                },
                "diagnostic_findings": {
                    "questions": [
                        {
                            "question_id": "growth_quality",
                            "status": "answered",
                            "current_answer": "Revenue grew but operating income declined.",
                            "warning_flags": ["Incremental operating margin is negative."],
                        },
                        {
                            "question_id": "profitability_with_scale",
                            "status": "answered",
                            "current_answer": "Operating margin declined with scale.",
                            "warning_flags": ["Incremental operating margin is below latest operating margin."],
                        },
                    ]
                },
                "missing_facts": {
                    "by_metric_family": {
                        "source_of_growth_attribution_v1": [
                            "official segment/product/geography/take-rate revenue component facts"
                        ]
                    }
                },
            },
            "official_event_transcript_findings": {"source_results": []},
            "executive_transcript_findings": {"source_results": []},
        }

        pack = build_business_model_evidence_pack(state)
        report = build_business_model_evidence_report(pack)
        unit_pack = build_business_model_unit_economics_pack(state, pack)
        unit_report = build_business_model_unit_economics_report(unit_pack)
        unit_zh_report = build_business_model_unit_economics_chinese_report(unit_pack)

        self.assertEqual(pack["agent"], "business_model_evidence_agent")
        self.assertEqual(len(pack["questions"]), 9)
        self.assertEqual(pack["source_coverage"]["p0_source_status"]["revenue_recognition_notes"], "covered")
        self.assertEqual(pack["source_coverage"]["p0_source_status"]["segment_geography_disclosure"], "partial_or_missing")
        self.assertIn("financial_cross_check", pack)
        self.assertIn("Business Model Evidence Report", report)
        self.assertIn("How Does the Company Make Money", report)
        self.assertEqual(unit_pack["workpaper_type"], "business_model_unit_economics")
        self.assertEqual(unit_pack["schema_version"], "business_model_unit_economics_workpaper_v0.1")
        self.assertEqual(len(unit_pack["question_answers"]), 18)
        self.assertEqual(unit_pack["question_answers"][0]["question_id"], "BMQ-01")
        self.assertEqual(unit_pack["question_answers"][-1]["question_id"], "BMQ-18")
        self.assertIn("source_inventory", unit_pack)
        self.assertIn("evidence_cards", unit_pack)
        self.assertIn("revenue_streams", unit_pack)
        self.assertIn("unit_economics_proxies", unit_pack)
        self.assertIn("cross_checks", unit_pack)
        self.assertIn("unknowns", unit_pack)
        self.assertIn("handoff", unit_pack)
        self.assertGreaterEqual(len(unit_pack["evidence_cards"]), 1)
        self.assertIn("Business Model & Unit Economics Workpaper", unit_report)
        self.assertIn("Revenue Architecture", unit_report)
        self.assertIn("Downstream Handoff", unit_report)
        self.assertIn("商业模式与单位经济底稿", unit_zh_report)
        self.assertIn("收入结构", unit_zh_report)
        self.assertIn("下游交接", unit_zh_report)

    def test_official_report_reader_builds_source_grounded_dossier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pdd-annual.htm"
            path.write_text(
                """
                <html><body>
                PDD Holdings is a multinational commerce group that owns and operates a portfolio of businesses.
                We aim to bring more businesses and people into the digital economy.
                Our platforms are the Pinduoduo platform and the Temu platform. PDD Holdings is our Cayman Islands holding company.
                Pinduoduo provides buyers with value-for-money merchandise and interactive shopping experiences.
                Pinduoduo's buyer base helps attract merchants, while the scale of the platform's sales volume
                encourages merchants to offer more competitive prices and customized products and services to buyers,
                thus forming a virtuous cycle.
                Despite their differentiated geographical coverage, Pinduoduo and Temu have the same value propositions
                and operational model. Both platforms primarily serve merchants in China.
                We help merchants streamline their manufacturing and operations, leading to more competitive prices
                and reduced waste.
                We believe our business model has significant operating leverage and enables us to realize structural cost savings.
                Our revenues primarily consist of transaction services and online marketing services and others
                provided to third-party merchants who sell their products on our platforms.
                Active merchants are merchant accounts that had one or more orders shipped to a buyer on our platforms.
                Temu works with logistics vendors and fulfillment partners.
                Revenue recognition revenues are principally comprised of online platform services.
                Cost of revenues, sales and marketing expenses, and research and development affect results.
                Risk factors include competition, counterfeit products, quality, logistics, regulatory, trade,
                data privacy, and intellectual property matters.
                Fourth Quarter 2021 Highlights
                GMV in the twelve-month period ended December 31, 2021 was RMB2,441.0 billion.
                The quarter ended December 31, 2021 included user engagement metrics.
                Average monthly active users in the quarter was 733.4 million.
                Active buyers in the twelve-month period ended December 31, 2021 was 868.7 million.
                Annual spending per active buyer in the twelve-month period ended December 31, 2021 was RMB2,810.0.
                Average transaction services revenues per active merchant increased from RMB6,627 in 2023
                to RMB12,399 in 2024.
                The number of our active merchants increased from 14.2 million in 2023 to 15.8 million in 2024.
                In 2019, 2020 and 2021, the number of total orders placed on our Pinduoduo mobile platform
                was 19.7 billion, 38.3 billion and 61.0 billion, respectively.
                </body></html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:pdd-annual.htm",
                "document_type": "20-F:primary",
                "filing_date": "2026-04-29",
                "report_date": "2025-12-31",
                "local_path": str(path),
                "source_url": "https://www.sec.gov/example",
            }

            analysis = official_report_business_model_analysis(
                company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
                documents=[document],
                extracted_facts=[],
                metrics=[],
            )

            dossier = analysis["official_report_dossier"]
            fields = {field["field_id"]: field for field in dossier["fields"]}

            self.assertEqual(dossier["field_count"], 13)
            self.assertEqual(fields["business_description"]["status"], "directly_stated")
            self.assertEqual(fields["revenue_model"]["status"], "directly_stated")
            self.assertEqual(fields["segment_structure"]["status"], "not_disclosed")
            self.assertTrue(fields["business_description"]["evidence"])
            self.assertIn("source_document", fields["business_description"])
            self.assertIn("not_disclosed", dossier["status_counts"])
            kpis = analysis["operating_kpi_analysis"]
            latest = kpis["latest_by_metric"]
            self.assertEqual(kpis["record_count"], 11)
            self.assertEqual(latest["gmv"]["value"], 2_441_000_000_000)
            self.assertEqual(latest["active_buyers"]["value"], 868_700_000)
            self.assertEqual(latest["average_monthly_active_users"]["value"], 733_400_000)
            self.assertEqual(latest["active_merchants"]["value"], 15_800_000)
            self.assertEqual(
                latest["average_transaction_services_revenue_per_active_merchant"]["value"],
                12_399,
            )
            self.assertEqual(latest["total_orders_placed"]["value"], 61_000_000_000)
            self.assertEqual(len(kpis["defined_only_markers"]), 1)
            management = analysis["management_framing_analysis"]
            self.assertEqual(management["status"], "completed")
            self.assertGreaterEqual(management["theme_count"], 5)
            self.assertTrue(management["themes"][0]["evidence"])
            self.assertIn("management claim", management["scope"])

    def test_public_voice_source_plan_records_forum_adapters(self) -> None:
        findings = collect_public_voice_evidence(
            company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
            offline=True,
        )

        self.assertEqual(findings["status"], "offline_source_plan_ready")
        self.assertGreaterEqual(findings["source_count"], 8)
        self.assertGreaterEqual(findings["manual_or_blocked_source_count"], 1)
        self.assertEqual(findings["evidence_item_count"], 0)
        self.assertIn("audit_policy", findings)
        self.assertTrue(
            [
                result
                for result in findings["source_results"]
                if result["source_id"] == "reddit_temu_customer_discussions"
            ]
        )

    def test_executive_transcript_parsers_and_offline_plan(self) -> None:
        youtube_xml = """
        <transcript>
          <text start="1.2" dur="2.5">We believe the platform creates value for merchants.</text>
          <text start="3.8" dur="1.0">Price and quality matter for users.</text>
        </transcript>
        """
        youtube_segments = parse_youtube_transcript_payload(youtube_xml)
        self.assertEqual(len(youtube_segments), 2)
        self.assertEqual(youtube_segments[0]["start_seconds"], 1.2)
        self.assertIn("platform creates value", youtube_segments[0]["text"])

        bilibili_segments = parse_bilibili_subtitle_payload(
            {
                "body": [
                    {"from": 0.0, "to": 2.0, "content": "平台要长期为用户创造价值"},
                    {"from": 2.0, "to": 4.0, "content": "商家和消费者都很重要"},
                ]
            }
        )
        self.assertEqual(len(bilibili_segments), 2)
        self.assertEqual(bilibili_segments[1]["duration_seconds"], 2.0)
        self.assertIn("商家", bilibili_segments[1]["text"])
        question_results = business_model_question_results_from_segments(
            source={
                "source_id": "sample_bilibili_video",
                "name": "Sample Bilibili business model video",
                "platform": "bilibili",
                "url": "https://www.bilibili.com/video/BVsample/",
            },
            segments=bilibili_segments,
        )
        self.assertEqual(len(question_results), 21)
        self.assertIn("evidence_found", {item["answer_status"] for item in question_results})

        findings = collect_executive_video_transcripts(
            company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
            offline=True,
        )
        self.assertEqual(findings["status"], "offline_source_plan_ready")
        self.assertGreaterEqual(findings["source_count"], 1)
        self.assertTrue(
            [
                result
                for result in findings["source_results"]
                if result["source_id"] == "bilibili_people_daily_colin_huang_interview"
            ]
        )
        self.assertIn("video_manifest", findings)
        self.assertIn("business_model_question_pack", findings)
        self.assertEqual(findings["business_model_question_pack"]["question_count"], 21)
        manifest_records = findings["video_manifest"]["records"]
        self.assertTrue(
            [
                record
                for record in manifest_records
                if record["video_uid"] == "video:bilibili:bv1jf41127tx"
            ]
        )

    def test_manual_bilibili_transcript_file_runs_question_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            transcript_path = temp_path / "bilibili-export.txt"
            transcript_path.write_text(
                "拼多多平台长期关注消费者和商家。供应链效率和性价比是商业模式的一部分。",
                encoding="utf-8",
            )
            registry_path = temp_path / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "company_id": "pdd",
                        "default_rate_limit_seconds": 0,
                        "default_max_evidence_items": 12,
                        "sources": [
                            {
                                "source_id": "manual_bilibili_sample",
                                "name": "Manual Bilibili sample transcript",
                                "adapter": "manual_transcript_file",
                                "platform": "bilibili",
                                "source_quality_tier": 4,
                                "language": "Chinese",
                                "use_case_tags": ["business_model"],
                                "url": "https://www.bilibili.com/video/BVsample/",
                                "local_transcript_path": str(transcript_path),
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            findings = collect_executive_video_transcripts(
                company={"company_id": "pdd"},
                cache_root=temp_path / "cache",
                registry_path=registry_path,
                offline=False,
            )
        result = findings["source_results"][0]
        self.assertEqual(result["status"], "manual_transcript_file_collected")
        self.assertEqual(len(result["business_model_question_results"]), 21)
        self.assertGreater(result["question_answer_count"], 0)

    def test_video_manifest_stable_ids(self) -> None:
        self.assertEqual(youtube_video_id("https://www.youtube.com/watch?v=42LEstZIskM"), "42LEstZIskM")
        self.assertEqual(canonicalize_url("https://youtu.be/42LEstZIskM?t=120"), "https://www.youtube.com/watch?v=42LEstZIskM")
        self.assertEqual(
            build_video_uid(
                platform="youtube",
                native_id="42LEstZIskM",
                canonical_url="https://www.youtube.com/watch?v=42LEstZIskM",
            ),
            "video:youtube:42lestziskm",
        )

    def test_official_event_transcript_source_plan_is_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry_path = temp_path / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "status": "test_provider_chain",
                        "company_id": "pdd",
                        "provider_chain": ["alpha_vantage_api", "local_or_user_provided_transcript"],
                        "audit_policy": {"no_fabrication_rule": "Never invent missing transcript text."},
                        "sources": [
                            {
                                "source_id": "pdd_alpha_vantage_test_backfill",
                                "name": "PDD Alpha Vantage test backfill",
                                "adapter": "alpha_vantage_backfill",
                                "provider": "alpha_vantage",
                                "platform": "alpha_vantage_api",
                                "symbol": "PDD",
                                "start_quarter": "2026Q1",
                                "end_quarter": "2026Q1",
                                "cached_record_globs": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            findings = collect_official_event_transcripts(
                company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
                cache_root=temp_path / "official_event_transcripts",
                offline=True,
                registry_path=registry_path,
            )

        self.assertEqual(findings["status"], "offline_provider_chain_ready")
        self.assertEqual(findings["source_count"], 1)
        self.assertEqual(findings["alpha_vantage_source_count"], 1)
        self.assertEqual(findings["transcript_source_count"], 0)
        self.assertEqual(findings["transcript_record_count"], 0)
        self.assertIn("audit_policy", findings)
        self.assertEqual(findings["business_model_question_pack"]["question_count"], 21)
        self.assertEqual(findings["business_model_question_pack"]["source_question_set_count"], 1)
        self.assertEqual(
            findings["business_model_question_pack"]["answer_status_counts"],
            {"not_answered_no_transcript": 21},
        )
        self.assertIn("video_manifest", findings)
        self.assertEqual(findings["video_manifest"]["record_count"], 0)

    def test_official_event_source_candidates_filter_press_release_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry_path = temp_path / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "status": "test_source_candidates",
                        "company_id": "pdd",
                        "provider_chain": ["link_only_source_candidates"],
                        "sources": [
                            {
                                "source_id": "pdd_test_source_candidates",
                                "name": "PDD test source candidates",
                                "adapter": "source_candidates",
                                "provider": "source_candidate_registry",
                                "candidates": [
                                    {
                                        "provider": "stockanalysis",
                                        "source_url": "https://stockanalysis.com/stocks/pdd/transcripts/",
                                    },
                                    {
                                        "provider": "globenewswire_release",
                                        "source_url": "https://www.globenewswire.com/news-release/example.html",
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            findings = collect_official_event_transcripts(
                company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
                cache_root=temp_path / "official_event_transcripts",
                offline=True,
                registry_path=registry_path,
            )

            result = findings["source_results"][0]
            candidate_path = Path(result["cache_paths"][0])
            candidates = json.loads(candidate_path.read_text(encoding="utf-8"))["candidates"]

        self.assertEqual(result["source_candidate_count"], 1)
        self.assertEqual(result["blocked_source_candidate_count"], 1)
        self.assertEqual(candidates[0]["provider"], "stockanalysis")

    def test_official_event_local_transcript_file_collects_question_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            transcript_path = temp_path / "pdd_2025q4_transcript.txt"
            transcript_path.write_text(
                "\n\n".join(
                    [
                        "Jiazhen Zhao: We continue long-term investment in supply chain, merchant support, logistics, and high-quality development.",
                        "Lei Chen: Consumer value, quality, trust, and shopping experience remain central as competition intensifies.",
                        "Analyst: How should investors think about Temu global expansion and regulatory pressure?",
                    ]
                ),
                encoding="utf-8",
            )
            registry_path = temp_path / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "status": "test_local_transcript",
                        "company_id": "pdd",
                        "provider_chain": ["local_or_user_provided_transcript"],
                        "sources": [
                            {
                                "source_id": "pdd_local_test_transcript",
                                "name": "PDD local test transcript",
                                "adapter": "local_transcript_file",
                                "provider": "local_test",
                                "platform": "local_file",
                                "symbol": "PDD",
                                "quarter": "2025Q4",
                                "local_transcript_path": str(transcript_path),
                                "source_type": "local_user_provided_transcript",
                                "confidence": "medium",
                                "can_store": True,
                                "can_redistribute": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            findings = collect_official_event_transcripts(
                company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
                cache_root=temp_path / "official_event_transcripts",
                offline=True,
                registry_path=registry_path,
            )

            record_path = Path(findings["source_results"][0]["transcript_records"][0]["record_path"])
            self.assertTrue(record_path.exists())
            self.assertTrue((record_path.parent / "business_model_question_results.json").exists())

        self.assertEqual(findings["status"], "earnings_call_transcripts_collected")
        self.assertEqual(findings["transcript_record_count"], 1)
        self.assertGreaterEqual(findings["transcript_segment_count"], 3)
        self.assertGreater(findings["evidence_item_count"], 0)
        self.assertIn("evidence_found", findings["business_model_question_pack"]["answer_status_counts"])
        result = findings["source_results"][0]
        self.assertEqual(result["quarter"], "2025Q4")
        self.assertEqual(len(result["business_model_question_results"]), 21)

    def test_dotenv_loader_sets_missing_values_without_override(self) -> None:
        prior = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                env_path = Path(temp_dir) / ".env"
                env_path.write_text(
                    'GEMINI_API_KEY="test-key"\nSEC_USER_AGENT="custom ua"\n',
                    encoding="utf-8",
                )
                loaded = load_dotenv(env_path)
                self.assertEqual(os.environ["GEMINI_API_KEY"], "test-key")
                self.assertEqual(loaded["GEMINI_API_KEY"], "test-key")
        finally:
            os.environ.pop("GEMINI_API_KEY", None)
            if prior is not None:
                os.environ["GEMINI_API_KEY"] = prior

    def test_deep_filing_stack_policy_keeps_prospectus_and_auditor_materials(self) -> None:
        prospectus = classify_sec_document_text(
            filename="pdd-f1.htm",
            form="F-1",
            role="primary",
            text="Risk Factors Use of proceeds Management Discussion and Analysis",
        )
        auditor = classify_sec_document_text(
            filename="auditor-change.htm",
            form="6-K",
            role="exhibit_1",
            text="Change in registrant's certifying accountant and independent registered public accounting firm.",
        )
        capital_markets = classify_sec_document_text(
            filename="offering.htm",
            form="424B5",
            role="primary",
            text="Prospectus supplement for an offering of American depositary shares.",
        )

        self.assertEqual(prospectus["category"], "KEEP_CORE_PROSPECTUS")
        self.assertEqual(auditor["category"], "KEEP_MONITORING_AUDITOR_ACCOUNTING")
        self.assertEqual(capital_markets["category"], "KEEP_MONITORING_FINANCING_CAPITAL_MARKETS")

    def test_deep_filing_stack_documents_do_not_enter_financial_number_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sec = SecClient(cache_dir=Path(temp_dir) / "sec")
            filing = {
                "accession_number": "0000000000-18-000001",
                "filing_date": "2018-06-29",
                "report_date": None,
                "form": "F-1",
                "primary_document": "pdd-f1.htm",
                "primary_doc_description": "F-1",
                "archive_url": "https://www.sec.gov/Archives/edgar/data/1/000000000018000001/pdd-f1.htm",
                "cik": "1",
                "cik_padded": "0000000001",
                "download_priority": 5,
            }
            document = sec.save_filing_bytes(
                filing,
                "pdd-f1.htm",
                b"<html><body>Prospectus Risk Factors Use of proceeds VIE ownership</body></html>",
                role="primary",
            )
            document.update(
                {
                    "source_id": "sec_edgar_pdd",
                    "document_type": "F-1:primary",
                }
            )

        self.assertTrue(SecClient.is_deep_research_filing(filing))
        self.assertTrue(is_deep_research_document(document))
        self.assertFalse(is_financial_extraction_document(document))

    def test_xbrl_mapping_keeps_pretax_and_sbc_concepts_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fixture.htm"
            path.write_text(
                """
                <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:xbrli="http://www.xbrl.org/2003/instance">
                  <xbrli:context id="Duration_1_1_2021_To_12_31_2021">
                    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001737806</xbrli:identifier></xbrli:entity>
                    <xbrli:period><xbrli:startDate>2021-01-01</xbrli:startDate><xbrli:endDate>2021-12-31</xbrli:endDate></xbrli:period>
                  </xbrli:context>
                  <ix:nonFraction name="us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments" contextRef="Duration_1_1_2021_To_12_31_2021" unitRef="Unit_Standard_CNY" scale="0">9455427000</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest" contextRef="Duration_1_1_2021_To_12_31_2021" unitRef="Unit_Standard_CNY" scale="0">9702255000</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:ShareBasedCompensation" contextRef="Duration_1_1_2021_To_12_31_2021" unitRef="Unit_Standard_CNY" scale="0">13380000</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:AllocatedShareBasedCompensationExpense" contextRef="Duration_1_1_2021_To_12_31_2021" unitRef="Unit_Standard_CNY" scale="0">6841573000</ix:nonFraction>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:fixture.htm",
                "document_type": "20-F:primary",
                "downloaded_file": "fixture.htm",
                "form": "20-F",
                "local_path": str(path),
                "source_id": "sec_edgar_test",
                "filing_date": "2022-04-25",
                "report_date": "2021-12-31",
            }

            extraction = extract_financial_facts_from_documents([document])
            raw_metrics = {fact["metric"] for fact in extraction["raw_facts"]}

            self.assertIn("pretax_income", raw_metrics)
            self.assertIn("pretax_income_after_equity_method", raw_metrics)
            self.assertIn("stock_based_compensation", raw_metrics)
            self.assertNotIn("stock_based_compensation_expense_allocated", raw_metrics)
            self.assertFalse(
                [
                    result
                    for result in verify_financial_facts(extraction["raw_facts"])
                    if result.get("status") == "material_conflict"
                ]
            )

    def test_xbrl_extraction_adds_deeper_balance_sheet_share_and_cash_quality_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "deeper_fixture.htm"
            path.write_text(
                """
                <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:xbrli="http://www.xbrl.org/2003/instance">
                  <xbrli:context id="Duration_1_1_2025_To_12_31_2025">
                    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001737806</xbrli:identifier></xbrli:entity>
                    <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>
                  </xbrli:context>
                  <xbrli:context id="Instant_12_31_2025">
                    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001737806</xbrli:identifier></xbrli:entity>
                    <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period>
                  </xbrli:context>
                  <ix:nonFraction name="us-gaap:Revenues" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">1000</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:CostOfRevenue" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">400</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:OperatingIncomeLoss" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">300</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">250</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:NetCashProvidedByUsedInOperatingActivities" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">220</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:PaymentsToAcquirePropertyPlantAndEquipment" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">50</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:ShareBasedCompensation" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">30</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:DepreciationAndAmortization" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">40</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:WeightedAverageNumberOfSharesOutstandingBasic" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_shares" scale="0">5900</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:EarningsPerShareDiluted" contextRef="Duration_1_1_2025_To_12_31_2025" unitRef="Unit_pure" scale="0">3.21</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:CashAndCashEquivalentsAtCarryingValue" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">500</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:ShortTermInvestments" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">700</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:AssetsCurrent" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">1400</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:LiabilitiesCurrent" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">600</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:Assets" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">1800</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:Liabilities" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">800</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:AccountsReceivableNetCurrent" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">120</ix:nonFraction>
                  <ix:nonFraction name="us-gaap:AccountsPayableCurrent" contextRef="Instant_12_31_2025" unitRef="Unit_Standard_CNY" scale="0">210</ix:nonFraction>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:deeper_fixture.htm",
                "document_type": "20-F:primary",
                "downloaded_file": "deeper_fixture.htm",
                "form": "20-F",
                "local_path": str(path),
                "source_id": "sec_edgar_test",
                "filing_date": "2026-04-25",
                "report_date": "2025-12-31",
            }

            extraction = extract_financial_facts_from_documents([document])
            facts = {fact["metric"]: fact for fact in extraction["selected_facts"]}
            flag_ids = {flag["flag_id"] for flag in extraction["summary"]["review_flags"]}
            worksheet_coverage = {
                row["worksheet_id"]: row
                for row in extraction["summary"]["hard_financial_worksheet_coverage"]
            }

            self.assertEqual(facts["free_cash_flow"]["value"], 170)
            self.assertEqual(facts["basic_shares"]["value"], 5_900_000)
            self.assertEqual(facts["diluted_eps"]["value"], 3.21)
            self.assertEqual(facts["short_term_investments"]["value"], 700)
            self.assertEqual(facts["current_assets"]["value"], 1400)
            self.assertEqual(facts["current_liabilities"]["value"], 600)
            self.assertEqual(facts["accounts_receivable"]["value"], 120)
            self.assertEqual(facts["accounts_payable"]["value"], 210)
            self.assertIn("interest_bearing_debt_not_explicitly_extracted", flag_ids)
            self.assertIn("cost_subcomponent_detail_gap", flag_ids)
            self.assertEqual(worksheet_coverage["expense_bridge"]["status"], "core_supported")
            self.assertEqual(
                worksheet_coverage["cost_subcomponents"]["status"],
                "optional_detail_missing",
            )
            self.assertIn(
                "server_and_bandwidth_costs",
                worksheet_coverage["cost_subcomponents"]["missing_supporting_metrics"],
            )
            self.assertEqual(
                extraction["summary"]["coverage"]["question_coverage"][2]["question_id"],
                "cash_quality",
            )

    def test_xbrl_extraction_skips_sec_index_helper_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.html"
            path.write_text(
                """
                <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:xbrli="http://www.xbrl.org/2003/instance">
                  <xbrli:context id="Duration_1_1_2021_To_12_31_2021">
                    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001737806</xbrli:identifier></xbrli:entity>
                    <xbrli:period><xbrli:startDate>2021-01-01</xbrli:startDate><xbrli:endDate>2021-12-31</xbrli:endDate></xbrli:period>
                  </xbrli:context>
                  <ix:nonFraction name="us-gaap:Revenues" contextRef="Duration_1_1_2021_To_12_31_2021" unitRef="Unit_Standard_CNY" scale="0">1</ix:nonFraction>
                </html>
                """,
                encoding="utf-8",
            )

            extraction = extract_financial_facts_from_documents(
                [
                    {
                        "document_id": "fixture:index.html",
                        "document_type": "6-K:exhibit_1",
                        "downloaded_file": "0000000000-index.html",
                        "form": "6-K",
                        "local_path": str(path),
                        "source_id": "sec_edgar_test",
                    }
                ]
            )

            self.assertEqual(extraction["summary"]["raw_fact_count"], 0)

    def test_earnings_release_table_extraction_writes_quarterly_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "earnings.htm"
            path.write_text(
                """
                <html>
                <body>
                PDD Holdings Announces Third Quarter 2025 Unaudited Financial Results.
                The Company announced financial results for the third quarter ended September 30, 2025.
                <table>
                  <tr><td></td><td>For the three months ended September 30,</td></tr>
                  <tr><td></td><td>2024</td><td>2025</td><td>2025 US$</td></tr>
                  <tr><td>Revenues</td><td>99,000</td><td>108,000</td><td>15,000</td></tr>
                  <tr><td>Costs of revenues</td><td>(39,000)</td><td>(46,000)</td><td>(6,000)</td></tr>
                  <tr><td>Operating profit</td><td>24,000</td><td>25,000</td><td>3,000</td></tr>
                  <tr><td>Net income</td><td>24,900</td><td>29,300</td><td>4,100</td></tr>
                </table>
                <table>
                  <tr><td></td><td>As of</td></tr>
                  <tr><td></td><td>December 31, 2024</td><td>September 30, 2025</td><td>US$</td></tr>
                  <tr><td>Cash and cash equivalents</td><td>57,000</td><td>92,000</td><td>12,000</td></tr>
                </table>
                <table>
                  <tr><td></td><td>For the three months ended September 30,</td></tr>
                  <tr><td>Net cash generated from operating activities</td><td>27,000</td><td>45,000</td><td>6,000</td></tr>
                </table>
                <table>
                  <tr><td>Weighted-average number of ordinary shares outstanding (in thousands):</td></tr>
                  <tr><td>-Diluted</td><td>5,900</td><td>5,950</td><td>5,950</td></tr>
                </table>
                </body>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:earnings.htm",
                "document_type": "6-K:exhibit_3",
                "downloaded_file": "earnings.htm",
                "form": "6-K",
                "local_path": str(path),
                "research_category": "KEEP_CORE_INTERIM_EARNINGS",
                "source_id": "sec_edgar_test",
                "filing_date": "2025-11-18",
                "report_date": "2025-09-30",
            }

            extraction = extract_financial_facts_from_documents([document])
            rows = quarterly_fact_rows(extraction["selected_facts"])

            self.assertEqual(rows[0]["quarter"], "2025 Q3")
            self.assertEqual(rows[0]["revenue"], 108_000_000)
            self.assertEqual(rows[0]["gross_profit"], 62_000_000)
            self.assertEqual(rows[0]["operating_income"], 25_000_000)
            self.assertEqual(rows[0]["net_income"], 29_300_000)
            self.assertEqual(rows[0]["operating_cash_flow"], 45_000_000)
            self.assertEqual(rows[0]["cash"], 92_000_000)
            self.assertEqual(rows[0]["diluted_shares"], 5_950_000)

    def test_earnings_release_extraction_handles_million_unit_release_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "earnings_millions.htm"
            path.write_text(
                """
                <html>
                <body>
                PDD Holdings Announces First Quarter 2026 Unaudited Financial Results.
                The Company announced financial results for the first quarter ended March 31, 2026.
                Revenues from online marketing services and others were RMB49.9 billion.
                Revenues from transaction services were RMB56.3 billion.
                <table>
                  <tr><td>PDD HOLDINGS INC.</td></tr>
                  <tr><td>CONDENSED CONSOLIDATED STATEMENTS OF INCOME</td></tr>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td></td><td>For the three months ended March 31,</td></tr>
                  <tr><td></td><td>2025</td><td>2026</td><td>2026 US$</td></tr>
                  <tr><td>Revenues</td><td>95,672</td><td>106,229</td><td>15,400</td></tr>
                  <tr><td>Costs of revenues</td><td>(40,946)</td><td>(46,893)</td><td>(6,798)</td></tr>
                  <tr><td>Fulfillment expenses</td><td>(1,100)</td><td>(1,300)</td><td>(188)</td></tr>
                  <tr><td>Payment processing fees</td><td>(900)</td><td>(1,050)</td><td>(152)</td></tr>
                  <tr><td>Server and bandwidth costs</td><td>(700)</td><td>(820)</td><td>(119)</td></tr>
                  <tr><td>Merchant support costs</td><td>(600)</td><td>(780)</td><td>(113)</td></tr>
                  <tr><td>Platform governance costs</td><td>(500)</td><td>(690)</td><td>(100)</td></tr>
                  <tr><td>Operating profit</td><td>16,086</td><td>19,566</td><td>2,837</td></tr>
                  <tr><td>Interest and investment income/(loss), net</td><td>223</td><td>(632)</td><td>(92)</td></tr>
                  <tr><td>Foreign exchange loss</td><td>(242)</td><td>(145)</td><td>(21)</td></tr>
                  <tr><td>Other income/(loss), net</td><td>3,261</td><td>(2,031)</td><td>(295)</td></tr>
                  <tr><td>Profit before income tax and share of results of equity investees</td><td>19,328</td><td>16,758</td><td>2,430</td></tr>
                  <tr><td>Share of results of equity investees</td><td>(105)</td><td>(96)</td><td>(14)</td></tr>
                  <tr><td>Income tax expenses</td><td>(4,481)</td><td>(4,115)</td><td>(597)</td></tr>
                  <tr><td>Net income</td><td>14,742</td><td>12,547</td><td>1,819</td></tr>
                </table>
                <table>
                  <tr><td>PDD HOLDINGS INC.</td></tr>
                  <tr><td>CONDENSED CONSOLIDATED BALANCE SHEETS</td></tr>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td></td><td>December 31, 2025</td><td>March 31, 2026</td><td>US$</td></tr>
                  <tr><td>Cash and cash equivalents</td><td>108,901</td><td>123,041</td><td>17,837</td></tr>
                  <tr><td>Restricted cash</td><td>73,831</td><td>76,213</td><td>11,052</td></tr>
                  <tr><td>Receivables from online payment platforms</td><td>5,109</td><td>5,758</td><td>835</td></tr>
                  <tr><td>Short-term investments</td><td>313,408</td><td>313,030</td><td>45,380</td></tr>
                  <tr><td>Prepayments and other current assets</td><td>7,527</td><td>8,745</td><td>1,268</td></tr>
                  <tr><td>Total current assets</td><td>518,000</td><td>525,000</td><td>76,100</td></tr>
                  <tr><td>Total Assets</td><td>630,045</td><td>637,704</td><td>92,448</td></tr>
                </table>
                <table>
                  <tr><td>PDD HOLDINGS INC.</td></tr>
                  <tr><td>CONDENSED CONSOLIDATED BALANCE SHEETS</td></tr>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td></td><td>December 31, 2025</td><td>March 31, 2026</td><td>US$</td></tr>
                  <tr><td>Current liabilities</td></tr>
                  <tr><td>Customer advances and deferred revenues</td><td>3,379</td><td>3,521</td><td>510</td></tr>
                  <tr><td>Payable to merchants</td><td>107,407</td><td>109,151</td><td>15,825</td></tr>
                  <tr><td>Accrued expenses and other liabilities</td><td>81,658</td><td>77,309</td><td>11,210</td></tr>
                  <tr><td>Merchant deposits</td><td>17,708</td><td>17,905</td><td>2,597</td></tr>
                  <tr><td>Lease liabilities</td><td>2,499</td><td>2,502</td><td>363</td></tr>
                  <tr><td>Total current liabilities</td><td>188,000</td><td>190,000</td><td>27,550</td></tr>
                  <tr><td>Non-current liabilities</td></tr>
                  <tr><td>Lease liabilities</td><td>2,880</td><td>2,620</td><td>380</td></tr>
                  <tr><td>Total Liabilities</td><td>216,660</td><td>214,277</td><td>31,064</td></tr>
                </table>
                <table>
                  <tr><td>PDD HOLDINGS INC.</td></tr>
                  <tr><td>CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS</td></tr>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td>Net cash generated from operating activities</td><td>15,517</td><td>16,445</td><td>2,384</td></tr>
                </table>
                <table>
                  <tr><td>Weighted-average number of ordinary shares outstanding (in millions):</td></tr>
                  <tr><td>-Diluted</td><td>5,932</td><td>5,920</td><td>5,920</td></tr>
                </table>
                <table>
                  <tr><td>PDD HOLDINGS INC.</td></tr>
                  <tr><td>RECONCILIATION OF GAAP AND NON-GAAP RESULTS</td></tr>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td></td><td>For the three months ended March 31,</td></tr>
                  <tr><td></td><td>2025</td><td>2026</td><td>2026 US$</td></tr>
                  <tr><td>Share-based compensation expenses</td><td>1,800</td><td>2,100</td><td>304</td></tr>
                  <tr><td>Non-GAAP operating profit</td><td>17,886</td><td>21,666</td><td>3,141</td></tr>
                  <tr><td>Non-GAAP net income</td><td>16,542</td><td>14,647</td><td>2,123</td></tr>
                </table>
                </body>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:earnings_millions.htm",
                "document_type": "company_release:earnings",
                "downloaded_file": "earnings_millions.htm",
                "form": "IR",
                "local_path": str(path),
                "research_category": "KEEP_CORE_INTERIM_EARNINGS",
                "source_id": "sec_edgar_test",
                "filing_date": "2026-05-27",
                "report_date": "2026-03-31",
            }

            extraction = extract_financial_facts_from_documents([document])
            facts = {
                fact["metric"]: fact
                for fact in extraction["selected_facts"]
                if fact.get("end_date") == "2026-03-31"
            }

            self.assertEqual(facts["revenue"]["value"], 106_229_000_000)
            self.assertEqual(facts["online_marketing_services_revenue"]["value"], 49_900_000_000)
            self.assertEqual(facts["transaction_services_revenue"]["value"], 56_300_000_000)
            self.assertEqual(facts["fulfillment_expense"]["value"], 1_300_000_000)
            self.assertEqual(facts["payment_processing_expense"]["value"], 1_050_000_000)
            self.assertEqual(facts["server_and_bandwidth_costs"]["value"], 820_000_000)
            self.assertEqual(facts["merchant_support_costs"]["value"], 780_000_000)
            self.assertEqual(facts["platform_governance_costs"]["value"], 690_000_000)
            self.assertEqual(facts["investment_income"]["value"], -632_000_000)
            self.assertEqual(facts["foreign_exchange_gain_loss"]["value"], -145_000_000)
            self.assertEqual(facts["other_income_net"]["value"], -2_031_000_000)
            self.assertEqual(facts["pretax_income"]["value"], 16_758_000_000)
            self.assertEqual(facts["tax_expense"]["value"], 4_115_000_000)
            self.assertEqual(facts["equity_method_income"]["value"], -96_000_000)
            self.assertEqual(facts["cash_and_short_term_investments"]["value"], 436_071_000_000)
            self.assertEqual(facts["restricted_cash"]["value"], 76_213_000_000)
            self.assertEqual(facts["receivables_from_online_payment_platforms"]["value"], 5_758_000_000)
            self.assertEqual(facts["prepayments_and_other_current_assets"]["value"], 8_745_000_000)
            self.assertEqual(facts["payable_to_merchants"]["value"], 109_151_000_000)
            self.assertEqual(facts["merchant_deposits"]["value"], 17_905_000_000)
            self.assertEqual(facts["lease_liabilities_current"]["value"], 2_502_000_000)
            self.assertEqual(facts["lease_liabilities_noncurrent"]["value"], 2_620_000_000)
            self.assertEqual(facts["current_assets"]["value"], 525_000_000_000)
            self.assertEqual(facts["current_liabilities"]["value"], 190_000_000_000)
            self.assertEqual(facts["total_liabilities"]["value"], 214_277_000_000)
            self.assertEqual(facts["diluted_shares"]["value"], 5_920_000_000)
            self.assertEqual(facts["non_gaap_adjustment_share_based_compensation"]["value"], 2_100_000_000)
            self.assertEqual(facts["non_gaap_operating_income"]["value"], 21_666_000_000)
            self.assertEqual(facts["non_gaap_net_income"]["value"], 14_647_000_000)
            worksheet_coverage = {
                row["worksheet_id"]: row
                for row in extraction["summary"]["hard_financial_worksheet_coverage"]
            }
            self.assertEqual(
                worksheet_coverage["cost_subcomponents"]["status"],
                "optional_detail_supported",
            )
            self.assertIn(
                "payment_processing_expense",
                worksheet_coverage["cost_subcomponents"]["available_supporting_metrics"],
            )

    def test_pdd_20f_html_table_fallback_extracts_annual_components_and_bridges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pdd-20251231x20f.htm"
            path.write_text(
                """
                <html>
                <body>
                PDD Holdings Inc. annual report.
                <table>
                  <tr><td></td><td>For the years ended December 31,</td></tr>
                  <tr><td></td><td>2023</td><td>2024</td><td>2025</td><td>2025 US$</td></tr>
                  <tr><td></td><td>RMB</td><td>RMB</td><td>RMB</td><td>US$</td></tr>
                  <tr><td>Online marketing services and others</td><td>153,540,553</td><td>197,934,192</td><td>217,783,028</td><td>31,142,559</td></tr>
                  <tr><td>Transaction services</td><td>94,098,652</td><td>195,901,905</td><td>214,062,685</td><td>30,610,557</td></tr>
                </table>
                <table>
                  <tr><td></td><td>For the years ended December 31,</td></tr>
                  <tr><td></td><td>2023</td><td>2024</td><td>2025</td><td>2025 US$</td></tr>
                  <tr><td></td><td>RMB</td><td>RMB</td><td>RMB</td><td>US$</td></tr>
                  <tr><td>Revenues</td><td>247,639,205</td><td>393,836,097</td><td>431,845,713</td><td>61,753,116</td></tr>
                  <tr><td>Costs of revenues</td><td>(91,723,577)</td><td>(153,900,374)</td><td>(188,801,753)</td><td>(26,999,993)</td></tr>
                  <tr><td>Sales and marketing expenses</td><td>(82,188,870)</td><td>(111,300,533)</td><td>(125,287,932)</td><td>(17,915,936)</td></tr>
                  <tr><td>General and administrative expenses</td><td>(4,075,622)</td><td>(7,552,967)</td><td>(8,157,733)</td><td>(1,166,880)</td></tr>
                  <tr><td>Research and development expenses</td><td>(10,952,374)</td><td>(12,659,361)</td><td>(16,496,164)</td><td>(2,359,357)</td></tr>
                  <tr><td>Operating profit</td><td>58,698,762</td><td>108,422,862</td><td>93,102,131</td><td>13,310,950</td></tr>
                  <tr><td>Interest and investment income, net</td><td>10,238,080</td><td>20,553,493</td><td>25,583,848</td><td>3,658,442</td></tr>
                  <tr><td>Interest expenses</td><td>(43,987)</td><td>—</td><td>—</td><td>—</td></tr>
                  <tr><td>Foreign exchange gain/(loss)</td><td>35,721</td><td>587,866</td><td>(1,966,622)</td><td>(281,223)</td></tr>
                  <tr><td>Other income, net</td><td>2,952,579</td><td>3,119,847</td><td>2,726,933</td><td>389,946</td></tr>
                  <tr><td>Profit before income tax and share of results of equity investees</td><td>71,881,155</td><td>132,684,068</td><td>119,446,290</td><td>17,080,593</td></tr>
                  <tr><td>Income tax expenses</td><td>(11,849,904)</td><td>(20,266,781)</td><td>(21,732,756)</td><td>(3,107,743)</td></tr>
                  <tr><td>Share of results of equity investees</td><td>(4,707)</td><td>17,225</td><td>129,005</td><td>18,447</td></tr>
                  <tr><td>Net income</td><td>60,026,544</td><td>112,434,512</td><td>97,842,539</td><td>13,991,297</td></tr>
                </table>
                <table>
                  <tr><td></td><td>As of December 31,</td></tr>
                  <tr><td></td><td>Notes</td><td>2024</td><td>2025</td><td>2025 US$</td></tr>
                  <tr><td>Current assets</td></tr>
                  <tr><td>Cash and cash equivalents</td><td></td><td>57,768,053</td><td>108,900,587</td><td>15,572,577</td></tr>
                  <tr><td>Restricted cash</td><td></td><td>68,426,368</td><td>73,830,824</td><td>10,557,667</td></tr>
                  <tr><td>Receivables from online payment platforms</td><td></td><td>3,679,309</td><td>5,109,129</td><td>730,596</td></tr>
                  <tr><td>Short-term investments</td><td>4</td><td>273,791,856</td><td>313,407,682</td><td>44,816,702</td></tr>
                  <tr><td>Prepayments and other current assets</td><td>5</td><td>4,413,466</td><td>7,526,542</td><td>1,076,280</td></tr>
                  <tr><td>Total current assets</td><td></td><td>415,648,232</td><td>518,979,892</td><td>74,213,136</td></tr>
                  <tr><td>Total assets</td><td></td><td>505,034,316</td><td>630,044,327</td><td>90,095,139</td></tr>
                  <tr><td>Current liabilities</td></tr>
                  <tr><td>Customer advances and deferred revenues</td><td></td><td>2,947,041</td><td>3,378,789</td><td>483,160</td></tr>
                  <tr><td>Payable to merchants</td><td></td><td>91,655,947</td><td>107,407,160</td><td>15,359,020</td></tr>
                  <tr><td>Accrued expenses and other liabilities</td><td>9</td><td>69,141,831</td><td>81,657,839</td><td>11,676,915</td></tr>
                  <tr><td>Merchant deposits</td><td></td><td>16,460,600</td><td>17,708,197</td><td>2,532,238</td></tr>
                  <tr><td>Convertible bonds, current portion</td><td>10</td><td>5,309,597</td><td>—</td><td>—</td></tr>
                  <tr><td>Lease liabilities</td><td>7</td><td>2,105,978</td><td>2,498,643</td><td>357,301</td></tr>
                  <tr><td>Total current liabilities</td><td></td><td>188,422,853</td><td>213,737,168</td><td>30,564,007</td></tr>
                  <tr><td>Non-current liabilities</td></tr>
                  <tr><td>Lease liabilities</td><td>7</td><td>3,191,565</td><td>2,880,152</td><td>411,856</td></tr>
                  <tr><td>Total liabilities</td><td></td><td>191,614,418</td><td>216,617,320</td><td>30,975,863</td></tr>
                </table>
                <table>
                  <tr><td></td><td>For the years ended December 31,</td></tr>
                  <tr><td></td><td>2023</td><td>2024</td><td>2025</td><td>2025 US$</td></tr>
                  <tr><td>CASH FLOW FROM OPERATING ACTIVITIES</td></tr>
                  <tr><td>Changes in operating assets and liabilities:</td></tr>
                  <tr><td>Receivables from online payment platforms</td><td>(3,326,421)</td><td>48,814</td><td>(1,523,543)</td><td>(217,864)</td></tr>
                  <tr><td>Prepayments and other current assets</td><td>(2,121,308)</td><td>(782,012)</td><td>(3,654,188)</td><td>(522,542)</td></tr>
                  <tr><td>Customer advances and deferred revenues</td><td>754,955</td><td>802,431</td><td>431,748</td><td>61,739</td></tr>
                  <tr><td>Payable to merchants</td><td>11,623,138</td><td>16,885,188</td><td>15,327,685</td><td>2,191,830</td></tr>
                  <tr><td>Accrued expenses and other liabilities</td><td>34,258,159</td><td>13,781,239</td><td>12,359,644</td><td>1,767,405</td></tr>
                  <tr><td>Merchant deposits</td><td>1,820,517</td><td>(418,146)</td><td>1,247,597</td><td>178,404</td></tr>
                  <tr><td>Lease liabilities</td><td>(977,788)</td><td>(1,879,851)</td><td>(2,116,609)</td><td>(302,671)</td></tr>
                  <tr><td>Fair value change of investments</td><td>(1,013,475)</td><td>(6,816,454)</td><td>(10,405,890)</td><td>(1,488,022)</td></tr>
                </table>
                </body>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "fixture:pdd-20251231x20f.htm",
                "document_type": "20-F:primary",
                "downloaded_file": "pdd-20251231x20f.htm",
                "form": "20-F",
                "local_path": str(path),
                "research_category": "KEEP_CORE_ANNUAL_REPORT",
                "source_id": "sec_edgar_test",
                "filing_date": "2026-04-29",
                "report_date": "2025-12-31",
            }

            extraction = extract_financial_facts_from_documents([document])
            facts = {
                (fact["metric"], fact.get("end_date")): fact
                for fact in extraction["selected_facts"]
            }

            self.assertEqual(facts[("online_marketing_services_revenue", "2025-12-31")]["value"], 217_783_028_000)
            self.assertEqual(facts[("transaction_services_revenue", "2025-12-31")]["value"], 214_062_685_000)
            self.assertEqual(facts[("foreign_exchange_gain_loss", "2025-12-31")]["value"], -1_966_622_000)
            self.assertEqual(facts[("convertible_debt_current", "2025-12-31")]["value"], 0)
            self.assertEqual(facts[("debt_current", "2025-12-31")]["value"], 0)
            self.assertEqual(facts[("lease_liabilities_current", "2025-12-31")]["value"], 2_498_643_000)
            self.assertEqual(facts[("lease_liabilities_noncurrent", "2025-12-31")]["value"], 2_880_152_000)
            self.assertEqual(
                facts[("change_in_receivables_from_online_payment_platforms", "2025-12-31")]["value"],
                -1_523_543_000,
            )
            self.assertEqual(facts[("fair_value_change_of_investments", "2025-12-31")]["value"], -10_405_890_000)

    def test_financial_extraction_rejects_third_party_release_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "globenewswire_mirror.htm"
            path.write_text(
                """
                <html>
                <body>
                PDD Holdings Announces First Quarter 2026 Unaudited Financial Results.
                <table>
                  <tr><td>(Amounts in millions of RMB and US$)</td></tr>
                  <tr><td></td><td>For the three months ended March 31,</td></tr>
                  <tr><td></td><td>2025</td><td>2026</td><td>2026 US$</td></tr>
                  <tr><td>Revenues</td><td>95,672</td><td>106,229</td><td>15,400</td></tr>
                  <tr><td>Operating profit</td><td>16,086</td><td>19,566</td><td>2,837</td></tr>
                  <tr><td>Net income</td><td>14,742</td><td>12,547</td><td>1,819</td></tr>
                </table>
                </body>
                </html>
                """,
                encoding="utf-8",
            )
            document = {
                "document_id": "pdd_globenewswire:2026-05-27:q1_2026_results",
                "document_type": "company_release:earnings",
                "downloaded_file": "globenewswire_mirror.htm",
                "form": "IR",
                "local_path": str(path),
                "research_category": "KEEP_CORE_INTERIM_EARNINGS",
                "source_id": "pdd_official_globenewswire_release",
                "filing_date": "2026-05-27",
                "report_date": "2026-03-31",
            }

            extraction = extract_financial_facts_from_documents([document])

            self.assertEqual(extraction["summary"]["raw_fact_count"], 0)
            self.assertEqual(extraction["summary"]["selected_fact_count"], 0)

    def test_manual_market_inputs_convert_market_cap_to_cny(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manual_inputs.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "companies": {
                            "pdd": {
                                "as_of_date": "2026-05-25",
                                "currency": "USD",
                                "source": "manual test fixture",
                                "market_cap": 1000,
                                "usd_cny_fx": 7,
                                "review_status": "approved",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            inputs = load_manual_market_inputs("pdd", path=path)
            converted = market_cap_in_cny(inputs)

            self.assertEqual(inputs["status"], "input_available")
            self.assertFalse(inputs["review_required"])
            self.assertEqual(converted["status"], "calculated")
            self.assertEqual(converted["value"], 7000)

    def test_valuation_metrics_calculate_when_manual_inputs_are_available(self) -> None:
        facts = [
            _metric_fact("operating_cash_flow", 200, period_type="annual"),
            _metric_fact("stock_based_compensation", 20, period_type="annual"),
            _metric_fact("depreciation_and_amortization", 30, period_type="annual"),
            _metric_fact("net_income", 150, period_type="annual"),
            _metric_fact("free_cash_flow", 120, period_type="annual"),
            _metric_fact("cash", 100, period_type="instant"),
            _metric_fact("debt", 10, period_type="instant"),
            _metric_fact("investment_portfolio", 500, period_type="instant"),
        ]
        market_inputs = {
            "status": "input_available",
            "inputs": {
                "as_of_date": "2026-05-25",
                "currency": "USD",
                "source": "manual test fixture",
                "market_cap": 1000,
                "usd_cny_fx": 7,
                "review_status": "approved",
            },
            "missing": [],
            "review_status": "approved",
            "review_required": False,
        }

        financial_metrics = {
            metric["formula_id"]: metric
            for metric in calculate_v1_financial_metrics(facts)
        }
        valuation_metrics = {
            metric["formula_id"]: metric
            for metric in calculate_v1_valuation_metrics(
                facts,
                market_inputs=market_inputs,
                financial_metrics=list(financial_metrics.values()),
            )
        }
        combined_metrics = {
            metric["formula_id"]: metric
            for metric in calculate_v1_metrics(facts, market_inputs=market_inputs)
        }
        enterprise_value = valuation_metrics["enterprise_value_v1"]["annual_results"][0]
        true_yield = valuation_metrics["true_yield_v1"]["annual_results"][0]
        fcf_yield = valuation_metrics["free_cash_flow_yield_v1"]["annual_results"][0]
        adjusted_yield = valuation_metrics["investment_adjusted_operating_yield_v1"]["annual_results"][0]

        self.assertIn("owner_earnings_v1", financial_metrics)
        self.assertNotIn("financial_quality_questions_v1", financial_metrics)
        self.assertNotIn("enterprise_value_v1", financial_metrics)
        self.assertIn("enterprise_value_v1", valuation_metrics)
        self.assertIn("enterprise_value_v1", combined_metrics)
        self.assertEqual(enterprise_value["value"], 6910)
        self.assertAlmostEqual(true_yield["value"], 150 / 6910)
        self.assertAlmostEqual(fcf_yield["value"], 120 / 6910)
        self.assertEqual(adjusted_yield["operating_enterprise_value"], 6410)
        self.assertAlmostEqual(adjusted_yield["value"], 150 / 6410)
        self.assertAlmostEqual(adjusted_yield["free_cash_flow_yield"], 120 / 6410)
        self.assertFalse(enterprise_value["review_required"])
        owner_result = financial_metrics["owner_earnings_v1"]["annual_results"][0]
        cash_conversion = financial_metrics["cash_conversion_ratio_v1"]["annual_results"][0]
        self.assertEqual(owner_result["display_name"], "owner earnings proxy")
        self.assertTrue(owner_result["review_required"])
        self.assertEqual(cash_conversion["display_name"], "CFO / net income")

    def test_financial_metrics_cover_working_capital_tax_growth_sources_and_trend(self) -> None:
        facts = [
            *_annual_metric_facts(
                2024,
                {
                    "revenue": 1_000,
                    "gross_profit": 500,
                    "operating_income": 200,
                    "pretax_income": 180,
                    "tax_expense": 30,
                    "net_income": 150,
                    "operating_cash_flow": 160,
                    "capex": 20,
                    "free_cash_flow": 140,
                    "cash_paid_for_taxes": 25,
                    "cash": 300,
                    "restricted_cash": 40,
                    "short_term_investments": 120,
                    "current_assets": 600,
                    "current_liabilities": 300,
                    "total_assets": 1_200,
                    "total_liabilities": 500,
                    "debt": 100,
                    "debt_current": 20,
                    "debt_noncurrent": 80,
                    "accounts_receivable": 100,
                    "inventory": 50,
                    "accounts_payable": 80,
                    "payable_to_merchants": 120,
                    "merchant_deposits": 40,
                    "deferred_revenue": 20,
                    "accrued_expenses": 60,
                    "online_marketing_services_revenue": 700,
                    "transaction_services_revenue": 300,
                    "diluted_shares": 1_000,
                },
            ),
            *_annual_metric_facts(
                2025,
                {
                    "revenue": 1_200,
                    "gross_profit": 600,
                    "operating_income": 210,
                    "pretax_income": 200,
                    "tax_expense": 40,
                    "net_income": 140,
                    "operating_cash_flow": 180,
                    "capex": 30,
                    "free_cash_flow": 150,
                    "cash_paid_for_taxes": 30,
                    "cash": 360,
                    "restricted_cash": 60,
                    "short_term_investments": 130,
                    "current_assets": 720,
                    "current_liabilities": 360,
                    "total_assets": 1_400,
                    "total_liabilities": 560,
                    "debt": 100,
                    "debt_current": 25,
                    "debt_noncurrent": 75,
                    "accounts_receivable": 150,
                    "inventory": 55,
                    "accounts_payable": 120,
                    "payable_to_merchants": 190,
                    "merchant_deposits": 55,
                    "deferred_revenue": 35,
                    "accrued_expenses": 80,
                    "online_marketing_services_revenue": 750,
                    "transaction_services_revenue": 450,
                    "diluted_shares": 1_020,
                },
            ),
            *_quarter_metric_facts(
                "2025-01-01",
                "2025-03-31",
                {
                    "revenue": 300,
                    "operating_income": 60,
                    "net_income": 45,
                    "operating_cash_flow": 50,
                    "cash": 365,
                    "total_assets": 1_420,
                    "total_liabilities": 565,
                    "diluted_shares": 1_020,
                },
            ),
            *_quarter_metric_facts(
                "2026-01-01",
                "2026-03-31",
                {
                    "revenue": 315,
                    "operating_income": 40,
                    "net_income": 42,
                    "operating_cash_flow": 35,
                    "cash": 370,
                    "total_assets": 1_450,
                    "total_liabilities": 590,
                    "diluted_shares": 1_030,
                    "online_marketing_services_revenue": 170,
                    "transaction_services_revenue": 145,
                    "non_gaap_operating_income": 52,
                    "non_gaap_net_income": 60,
                    "non_gaap_adjustment_share_based_compensation": 12,
                    "non_gaap_adjustment_fair_value_changes": 4,
                },
            ),
        ]

        metrics = {
            metric["formula_id"]: metric
            for metric in calculate_v1_financial_metrics(facts)
        }

        working_capital = metrics["working_capital_quality_v1"]["annual_results"][-1]
        tax_quality = metrics["tax_non_gaap_accounting_quality_v1"]
        source_growth = metrics["source_of_growth_attribution_v1"]["annual_results"][-1]
        balance_sheet = metrics["balance_sheet_risk_v1"]["annual_results"][-1]
        interim_trend = metrics["latest_interim_trend_v1"]
        diagnostic_findings = run_v1_financial_diagnostics(
            extracted_facts=facts,
            metrics=list(metrics.values()),
        )

        self.assertEqual(working_capital["status"], "calculated")
        self.assertAlmostEqual(working_capital["current_ratio"], 2.0)
        self.assertIn("payable_to_merchants", {row["metric"] for row in working_capital["component_details"]})
        self.assertEqual(tax_quality["status"], "calculated")
        self.assertAlmostEqual(tax_quality["annual_results"][-1]["effective_tax_rate"], 0.2)
        self.assertAlmostEqual(
            tax_quality["latest_interim_non_gaap"]["non_gaap_net_income_uplift"],
            (60 - 42) / 42,
        )
        self.assertEqual(source_growth["status"], "calculated")
        self.assertAlmostEqual(source_growth["value"], 1.0)
        self.assertEqual(balance_sheet["debt_maturity_profile"]["current_debt"], 25)
        self.assertAlmostEqual(balance_sheet["restricted_cash_to_cash"], 60 / 360)
        self.assertEqual(interim_trend["overall_status"], "trend_changed")
        self.assertIn(
            "tax_non_gaap_accounting_quality",
            [question["question_id"] for question in diagnostic_findings["questions"]],
        )
        self.assertNotIn("financial_quality_questions_v1", metrics)

    def test_material_event_scan_and_report_pack_capture_review_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            filing_path = Path(temp_dir) / "auditor-change.htm"
            filing_path.write_text(
                """
                <html><body>
                Changes in Registrant's Certifying Accountant.
                The company appointed a new independent registered public accounting firm.
                </body></html>
                """,
                encoding="utf-8",
            )
            documents = [
                {
                    "document_id": "fixture-6k-auditor-change",
                    "source_id": "sec_edgar_fixture",
                    "document_type": "6-K:exhibit_1",
                    "form": "6-K",
                    "filing_date": "2026-01-10",
                    "local_path": str(filing_path),
                    "source_url": "https://www.sec.gov/fixture",
                }
            ]
            material_scan = scan_material_events(documents)
            facts = [
                *_annual_metric_facts(
                    2024,
                    {
                        "revenue": 1_000,
                        "gross_profit": 500,
                        "operating_income": 200,
                        "pretax_income": 180,
                        "tax_expense": 30,
                        "net_income": 150,
                        "operating_cash_flow": 160,
                        "capex": 20,
                        "free_cash_flow": 140,
                        "stock_based_compensation": 15,
                        "depreciation_and_amortization": 25,
                        "cash": 300,
                        "total_assets": 1_200,
                        "total_liabilities": 500,
                    },
                ),
                *_annual_metric_facts(
                    2025,
                    {
                        "revenue": 1_100,
                        "gross_profit": 530,
                        "operating_income": 210,
                        "pretax_income": 190,
                        "tax_expense": 35,
                        "net_income": 155,
                        "operating_cash_flow": 170,
                        "capex": 25,
                        "free_cash_flow": 145,
                        "stock_based_compensation": 20,
                        "depreciation_and_amortization": 30,
                        "cash": 320,
                        "total_assets": 1_250,
                        "total_liabilities": 520,
                    },
                ),
            ]
            metrics = calculate_v1_financial_metrics(facts)
            diagnostics = run_v1_financial_diagnostics(extracted_facts=facts, metrics=metrics)
            state = {
                "run_id": "fixture-run",
                "run_dir": temp_dir,
                "company_query": "FixtureCo",
                "canonical_company": {"legal_name": "FixtureCo Inc."},
                "market": "us",
                "source_candidates": [],
                "approved_sources": [],
                "documents": documents,
                "extracted_facts": facts,
                "raw_extracted_facts": facts,
                "extraction_summary": {"coverage": {"priority_a": {"missing": []}, "priority_b": {"missing": []}}},
                "metrics": metrics,
                "valuation_metrics": [],
                "diagnostic_findings": diagnostics,
                "material_event_scan": material_scan,
                "verification_results": [],
                "ir_cross_validation": {},
            }

            self.assertEqual(material_scan["status"], "material_events_found")
            self.assertEqual(material_scan["coverage_status"], "event_documents_scanned")
            self.assertGreaterEqual(material_scan["high_priority_event_count"], 1)
            pack = build_financial_report_pack(state)
            self.assertEqual(pack["schema_version"], "financial_report_pack_v1")
            self.assertEqual(pack["material_event_scan"]["material_event_count"], 1)
            self.assertEqual(pack["financial_health_status"], "deteriorating")
            self.assertTrue(
                any(flag.get("source") == "material_event_scan" for flag in pack["human_review_flags"])
            )
            easy_report = build_financial_easy_reading_report(
                pack,
                audit_status="Draft pending audit review",
            )
            self.assertIn("财务报告易读版", easy_report)
            self.assertIn("重大事项扫描", easy_report)
            self.assertIn("关键问题与红旗", easy_report)
            self.assertIn("当前判断", easy_report)
            self.assertIn("fixture-6k-auditor-change", easy_report)

    def test_financial_research_draft_keeps_evidence_layers_separate(self) -> None:
        draft = build_financial_research_draft(
            {
                "company": {"legal_name": "FixtureCo Inc."},
                "generated_at": "2026-06-01T00:00:00Z",
                "run_id": "fixture-run",
                "annual_facts": [
                    {
                        "year": 2024,
                        "revenue": 100_000_000_000,
                        "operating_income": 20_000_000_000,
                        "net_income": 18_000_000_000,
                        "operating_cash_flow": 25_000_000_000,
                    },
                    {
                        "year": 2025,
                        "revenue": 110_000_000_000,
                        "operating_income": 18_000_000_000,
                        "net_income": 16_000_000_000,
                        "operating_cash_flow": 23_000_000_000,
                        "online_marketing_services_revenue": 52_000_000_000,
                        "transaction_services_revenue": 58_000_000_000,
                        "cash": 42_000_000_000,
                        "restricted_cash": 12_000_000_000,
                        "short_term_investments": 55_000_000_000,
                        "current_assets": 120_000_000_000,
                        "current_liabilities": 50_000_000_000,
                    },
                ],
                "quarterly_facts": [
                    {
                        "quarter": "2026 Q1",
                        "period_end": "2026-03-31",
                        "revenue": 30_000_000_000,
                        "transaction_services_revenue": 16_000_000_000,
                        "online_marketing_services_revenue": 14_000_000_000,
                    }
                ],
                "financial_metrics": [
                    {
                        "formula_id": "operating_profit_bridge_v1",
                        "annual_results": [
                            {
                                "status": "calculated",
                                "revenue_delta": 10_000_000_000,
                                "operating_income_delta": -2_000_000_000,
                                "incremental_operating_margin": -0.2,
                                "bridge_rows": [
                                    {"metric": "revenue", "delta": 10_000_000_000, "role": "positive_driver"},
                                    {
                                        "metric": "operating_income",
                                        "delta": -2_000_000_000,
                                        "role": "result",
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "formula_id": "working_capital_quality_v1",
                        "annual_results": [
                            {
                                "status": "calculated",
                                "working_capital_cash_tailwind_to_revenue": 0.06,
                            }
                        ],
                    },
                ],
                "fact_extraction_summary": {
                    "selected_fact_count": 70,
                    "raw_fact_count": 90,
                    "disclosure_gap_registry": [
                        {
                            "gap_id": "temu_standalone_economics",
                            "status": "not_disclosed",
                            "missing_metrics": ["temu_revenue"],
                            "why_it_matters": "Standalone economics are not disclosed.",
                        }
                    ],
                },
            },
            official_evidence_pack={
                "source_catalog": [{"source_document_type": "20-F", "source_document": "fixture-20f"}],
                "question_answers": [
                    {
                        "question_title": "利润率为什么下降",
                        "answer_status": "partial",
                        "impact_on_layer1": "clarifies",
                        "rendered_answer": {
                            "filing_facts": "费用率上升。",
                            "official_explanation": "管理层称投入增加。",
                            "our_judgment": "只能部分解释。",
                            "source_trace": "fixture-20f",
                        },
                        "still_unknown": ["投入回收期"],
                    }
                ],
            },
            management_communication_pack={
                "source_catalog": [{"source_document": "fixture-call", "period": "2026Q1"}],
                "qa_pressure_topics": [
                    {
                        "topic": "自营品牌",
                        "analyst_concern": "是否是战略转向。",
                        "management_response_read": "管理层称会更深介入供应链。",
                        "answer_quality": "partial",
                        "follow_up_needed": ["库存风险"],
                    }
                ],
            },
            feedback_loop_pack={
                "schema_version": "feedback_loop_pack_v1",
                "closed_loop_status": "routed_to_financial_extraction_then_layer1",
                "summary": {
                    "financial_extractor_request_count": 1,
                    "metric_recalculation_request_count": 0,
                    "layer1_requery_request_count": 1,
                    "evidence_communication_followup_count": 0,
                    "external_data_request_count": 0,
                    "human_review_request_count": 0,
                },
                "layer1_requery_requests": [
                    {
                        "question": "补齐 Temu 收入后，第一层是否能回答增长来源？",
                        "current_financial_pack_status": "requires_new_extraction_or_disclosure",
                        "source": "feedback_router",
                    }
                ],
                "financial_extractor_requests": [
                    {
                        "priority": "P1",
                        "request": "抽取 Temu standalone economics",
                        "missing_metrics": ["temu_revenue"],
                    }
                ],
            },
        )

        self.assertIn("财务研究底稿：FixtureCo Inc.", draft)
        self.assertIn("财务事实层", draft)
        self.assertIn("叙事证据层", draft)
        self.assertIn("关键问题台账", draft)
        self.assertIn("反馈闭环路由", draft)
        self.assertIn("temu_standalone_economics", draft)
        self.assertIn("库存风险", draft)

    def test_easy_reading_qa_pressure_includes_management_response(self) -> None:
        report = build_financial_easy_reading_report(
            {
                "company": {"legal_name": "FixtureCo Inc."},
                "diagnostic_findings": {"questions": []},
                "human_review_flags": [],
            },
            audit_status="Draft pending audit review",
            management_communication_pack={
                "source_catalog": [
                    {
                        "period": "2026Q1",
                        "status": "raw_transcript_not_independently_verified",
                    }
                ],
                "qa_pressure_topics": [
                    {
                        "topic": "自营品牌是否是重大战略转向",
                        "analyst_concern": "Citigroup 追问是否应理解为战略转向。",
                        "management_response_read": "管理层说平台会更深介入供应链，并投入 RMB 100B。",
                        "answer_quality": "specific_with_numbers",
                        "follow_up_needed": ["库存风险", "单独 P&L"],
                    }
                ],
            },
        )

        self.assertIn("管理层怎么回答", report)
        self.assertIn("平台会更深介入供应链", report)
        self.assertIn("回答具体，并且给出数字", report)

    def test_financial_visual_report_renders_svg_charts_and_gap_cards(self) -> None:
        report = build_financial_visual_report(
            {
                "company": {"legal_name": "FixtureCo Inc."},
                "generated_at": "2026-06-01T00:00:00Z",
                "financial_health_status": "mixed",
                "financial_health_score": 6.0,
                "annual_facts": [
                    {
                        "year": 2024,
                        "revenue": 100_000_000_000,
                        "operating_income": 20_000_000_000,
                        "net_income": 18_000_000_000,
                        "operating_cash_flow": 25_000_000_000,
                        "online_marketing_services_revenue": 60_000_000_000,
                        "transaction_services_revenue": 40_000_000_000,
                        "cash": 40_000_000_000,
                        "restricted_cash": 10_000_000_000,
                        "short_term_investments": 50_000_000_000,
                    },
                    {
                        "year": 2025,
                        "revenue": 110_000_000_000,
                        "operating_income": 18_000_000_000,
                        "net_income": 16_000_000_000,
                        "operating_cash_flow": 23_000_000_000,
                        "online_marketing_services_revenue": 52_000_000_000,
                        "transaction_services_revenue": 58_000_000_000,
                        "cash": 42_000_000_000,
                        "restricted_cash": 12_000_000_000,
                        "short_term_investments": 55_000_000_000,
                    },
                ],
                "quarterly_facts": [
                    {
                        "quarter": "2026 Q1",
                        "period_end": "2026-03-31",
                        "revenue": 30_000_000_000,
                        "net_income": 3_000_000_000,
                    }
                ],
                "financial_metrics": [
                    {
                        "formula_id": "operating_profit_bridge_v1",
                        "annual_results": [
                            {
                                "status": "calculated",
                                "bridge_rows": [
                                    {"metric": "revenue", "delta": 10_000_000_000, "role": "positive_driver"},
                                    {"metric": "cost_of_revenue", "delta": 7_000_000_000, "role": "profit_headwind_when_increases"},
                                    {"metric": "operating_income", "delta": -2_000_000_000, "role": "result"},
                                ],
                            }
                        ],
                    },
                    {
                        "formula_id": "below_operating_bridge_v1",
                        "latest_interim_result": {
                            "bridge_rows": [
                                {"metric": "operating_income", "delta": 1_000_000_000},
                                {"metric": "other_income_net", "delta": -2_000_000_000},
                                {"metric": "net_income", "delta": -1_000_000_000},
                            ]
                        },
                    },
                    {
                        "formula_id": "working_capital_quality_v1",
                        "annual_results": [
                            {
                                "status": "calculated",
                                "working_capital_cash_tailwind_to_revenue": 0.05,
                                "cash_source_liability_delta": 5_000_000_000,
                                "cash_use_asset_delta": 1_000_000_000,
                                "component_details": [
                                    {
                                        "metric": "payable_to_merchants",
                                        "role": "cash_source_liability",
                                        "delta": 5_000_000_000,
                                    }
                                ],
                            }
                        ],
                    },
                ],
                "fact_extraction_summary": {
                    "disclosure_gap_registry": [
                        {
                            "gap_id": "temu_standalone_economics",
                            "status": "not_disclosed",
                            "missing_metrics": ["temu_revenue"],
                            "why_it_matters": "Standalone economics are not disclosed.",
                        }
                    ]
                },
            },
            markdown_report_path="financial_easy_reading_report.md",
        )

        self.assertIn("财务可视化报告：FixtureCo Inc.", report)
        self.assertIn("<svg", report)
        self.assertIn("经营利润桥", report)
        self.assertIn("经营利润以下桥", report)
        self.assertIn("temu_standalone_economics", report)

    def test_material_event_scan_ignores_routine_earnings_release_debt_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            filing_path = Path(temp_dir) / "earnings-release.htm"
            filing_path.write_text(
                """
                <html><body>
                PDD Holdings Announces First Quarter 2026 Unaudited Financial Results.
                Non-GAAP financial measures exclude interest expenses related to the
                convertible bonds amortization to face value.
                </body></html>
                """,
                encoding="utf-8",
            )
            documents = [
                {
                    "document_id": "fixture-earnings-release",
                    "source_id": "sec_edgar_fixture",
                    "document_type": "6-K:exhibit_1",
                    "form": "6-K",
                    "filing_date": "2026-05-20",
                    "local_path": str(filing_path),
                    "source_url": "https://www.sec.gov/fixture",
                }
            ]

            material_scan = scan_material_events(documents)

            self.assertEqual(material_scan["status"], "no_material_events_found")
            self.assertEqual(material_scan["material_event_count"], 0)
            self.assertEqual(material_scan["coverage_status"], "routine_financial_documents_only")
            self.assertIn("routine official financial documents", material_scan["scan_scope_note"])

    def test_material_event_scan_uses_latest_annual_report_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            old_event_path = Path(temp_dir) / "old-auditor-change.htm"
            old_event_path.write_text(
                "Changes in Registrant's Certifying Accountant.",
                encoding="utf-8",
            )
            annual_path = Path(temp_dir) / "annual.htm"
            annual_path.write_text("Annual report", encoding="utf-8")
            new_event_path = Path(temp_dir) / "new-auditor-change.htm"
            new_event_path.write_text(
                "Changes in Registrant's Certifying Accountant.",
                encoding="utf-8",
            )
            documents = [
                {
                    "document_id": "old-event",
                    "source_id": "sec_edgar_fixture",
                    "document_type": "6-K:exhibit_1",
                    "form": "6-K",
                    "filing_date": "2025-01-01",
                    "local_path": str(old_event_path),
                },
                {
                    "document_id": "latest-annual",
                    "source_id": "sec_edgar_fixture",
                    "document_type": "20-F:primary",
                    "form": "20-F",
                    "filing_date": "2026-04-29",
                    "local_path": str(annual_path),
                },
                {
                    "document_id": "new-event",
                    "source_id": "sec_edgar_fixture",
                    "document_type": "6-K:exhibit_1",
                    "form": "6-K",
                    "filing_date": "2026-05-01",
                    "local_path": str(new_event_path),
                },
            ]

            material_scan = scan_material_events(documents)

            self.assertEqual(material_scan["cutoff_filing_date"], "2026-04-29")
            self.assertEqual(material_scan["material_event_count"], 1)
            self.assertEqual(material_scan["events"][0]["document_id"], "new-event")
            self.assertEqual(material_scan["coverage_status"], "event_documents_scanned")

    def test_market_data_parsers_extract_pdd_quote_fx_and_share_structure(self) -> None:
        share_structure = parse_pdd_share_structure_text(
            """
            ADSs are to our American depositary shares, each of which represents four Class A ordinary shares.
            The calculations in the table below are based on 5,693,585,848 Class A ordinary shares
            and no Class B ordinary Shares outstanding as of March 18, 2026.
            """,
            source_document="fixture:20-f",
        )
        google_quote = parse_google_pdd_quote_text(
            """
            PDD:NASDAQ PDD Holdings Inc - ADR $98.15 Closed: May 20, 4:00:00 PM GMT-4 · USD
            Mkt. cap 139.71B Shares outstanding 1.42B
            """
        )
        google_fx = parse_google_usd_cny_text(
            "USD / CNY United States Dollar / Chinese Yuan 6.7948 May 25, 4:02:00 AM UTC"
        )
        validation = validate_market_inputs(
            share_structure=share_structure,
            google_quote=google_quote,
            google_fx=google_fx,
            yahoo_quote={"price": 98.14, "currency": "USD"},
        )

        self.assertEqual(share_structure["ordinary_shares_per_ads"], 4)
        self.assertEqual(share_structure["ordinary_shares_outstanding"], 5_693_585_848)
        self.assertEqual(google_quote["price"], 98.15)
        self.assertEqual(google_quote["market_cap"], 139_710_000_000)
        self.assertEqual(google_fx["rate"], 6.7948)
        self.assertFalse(validation["missing"])
        self.assertFalse(validation["conflicts"])

    def test_market_data_parsers_extract_tencent_quote_fx_and_share_structure(self) -> None:
        share_structure = parse_tencent_share_structure_text(
            """
            As at 31 December 2025, the total number of issued Shares was 9,120,235,999.
            """,
            source_document="fixture:tencent-annual",
        )
        google_quote = parse_google_tencent_quote_text(
            """
            0700:HKG Tencent Holdings Ltd HK$432.80 arrow_downward -1.95%
            1D May 26, 9:32:59 AM GMT+8 · HKD
            Mkt. cap 3.95T Shares outstanding 9.52B
            """
        )
        google_fx = parse_google_hkd_cny_text(
            "HKD / CNY Hong Kong Dollar / Chinese Yuan 0.8672 1D May 26, 1:47:00 AM UTC"
        )
        validation = validate_tencent_market_inputs(
            share_structure=share_structure,
            google_quote=google_quote,
            google_fx=google_fx,
            yahoo_quote={"price": 432.2, "currency": "HKD"},
        )

        self.assertEqual(share_structure["ordinary_shares_outstanding"], 9_120_235_999)
        self.assertEqual(google_quote["price"], 432.8)
        self.assertEqual(google_quote["market_cap"], 3_950_000_000_000)
        self.assertEqual(google_fx["rate"], 0.8672)
        self.assertFalse(validation["missing"])
        self.assertFalse(validation["conflicts"])

    def test_tencent_annual_report_text_extraction_reads_core_facts(self) -> None:
        text = """
        Financial Summary
        Year ended 31 December
        2021 2022 2023 2024 2025
        RMB'Million RMB'Million RMB'Million RMB'Million RMB'Million
        Revenues 560,118 554,552 609,015 660,257 751,766
        Gross profit 245,944 238,746 293,109 349,246 422,593
        Operating profit 124,656 110,827 160,074 208,099 241,562
        Profit before income tax 248,062 210,225 161,324 241,485 277,249
        Profit attributable to equity holders of the Company 224,822 188,243 115,216 194,073 224,842
        Total assets 1,612,364 1,578,131 1,577,246 1,780,995 2,038,986
        Total liabilities 735,671 795,271 703,565 727,099 797,921
        Chairman's Statement

        Consolidated Income Statement
        For the year ended 31 December 2025
        Income tax expense 12(a) (47,448) (45,018)
        Consolidated Statement of Financial Position
        As at 31 December 2025
        Cash and cash equivalents 32 141,041 132,519
        LIABILITIES
        Borrowings 36 208,369 146,521
        Notes payable 37 126,204 130,586
        Borrowings 36 42,618 52,885
        Notes payable 37 10,542 8,623
        Total liabilities 797,921 727,099
        Consolidated Statement of Changes in Equity

        The following table reconciles our operating profit to our EBITDA and Adjusted EBITDA:
        Operating profit 60,338 63,554 51,478 241,562 208,099
        Depreciation of property, plant and equipment and investment properties 7,912 7,297 5,811 26,580 21,141
        Depreciation of right-of-use assets 1,638 1,511 1,595 6,219 6,191
        Amortisation of intangible assets and land use rights 8,553 8,478 7,546 33,229 28,881
        Equity-settled share-based compensation 5,922 6,341 5,662 25,660 20,702

        INVESTMENTS HELD
        As at 31 December 2025, our investment portfolio amounted to approximately RMB957,219 million (31 December 2024: RMB817,687 million) as recorded in the consolidated statement of financial position.

        Consolidated Statement of Cash Flows
        For the year ended 31 December 2025
        Net cash flows generated from operating activities 303,052 258,521
        Purchase of/prepayments for property, plant and equipment, construction in progress and investment properties (87,482) (62,927)
        Purchase of/prepayments for intangible assets (25,399) (26,394)
        Notes to the Consolidated Financial Statements
        """
        facts = extract_tencent_annual_report_text_facts(
            text,
            {
                "document_id": "tencent_ir:2025:annual",
                "source_id": "tencent_investor_relations",
                "report_kind": "annual",
                "fiscal_year": 2025,
                "document_type": "annual_report_pdf",
            },
        )
        by_metric_year = {(fact["metric"], fact["end_date"][:4]): fact["value"] for fact in facts}

        self.assertEqual(by_metric_year[("revenue", "2025")], 751_766_000_000)
        self.assertEqual(by_metric_year[("operating_cash_flow", "2025")], 303_052_000_000)
        self.assertEqual(by_metric_year[("cash", "2025")], 141_041_000_000)
        self.assertEqual(by_metric_year[("debt", "2025")], 387_733_000_000)
        self.assertEqual(by_metric_year[("capex", "2025")], 112_881_000_000)
        self.assertEqual(by_metric_year[("stock_based_compensation", "2025")], 25_660_000_000)
        self.assertEqual(by_metric_year[("depreciation_and_amortization", "2025")], 66_028_000_000)
        self.assertEqual(by_metric_year[("investment_portfolio", "2025")], 957_219_000_000)
        self.assertEqual(by_metric_year[("investment_portfolio", "2024")], 817_687_000_000)

    def test_tencent_interim_report_text_extraction_reads_quarter_and_half_year_facts(self) -> None:
        text = """
        Condensed Consolidated Income Statement
        For the three and six months ended 30 June 2025
        Unaudited Unaudited
        Three months ended 30 June Six months ended 30 June
        2025 2024 2025 2024
        Note RMB'Million RMB'Million RMB'Million RMB'Million
        Revenues
         Value-added Services 91,368 78,822 183,501 157,451
         Marketing Services 35,762 29,871 67,615 56,377
         FinTech and Business Services 55,536 50,440 110,443 102,742
         Others 1,838 1,984 2,967 4,048
        6 184,504 161,117 364,526 320,618
        Cost of revenues 7 (79,491) (75,222) (159,020) (150,853)
        Gross profit 105,013 85,895 205,506 169,765
        Operating profit 60,104 50,732 117,670 103,288
        Profit before income tax 67,395 58,534 130,837 115,354
        Income tax expense 11(a) (11,351) (10,168) (25,068) (24,337)
        Profit for the period 56,044 48,366 105,769 91,017
        Attributable to:
         Equity holders of the Company 55,628 47,630 103,449 89,519
         Non-controlling interests 416 736 2,320 1,498
        Condensed Consolidated Statement of Comprehensive Income

        Condensed Consolidated Statement of Financial Position
        As at 30 June 2025
        Unaudited Audited
        30 June 31 December
        2025 2024
        Cash and cash equivalents 182,057 132,519
        Total assets 2,013,310 1,780,995
        Borrowings 202,966 146,521
        Notes payable 119,338 130,586
        Borrowings 58,631 52,885
        Notes payable 12,880 8,623
        Total liabilities 810,461 727,099
        Condensed Consolidated Statement of Changes in Equity

        Condensed Consolidated Statement of Cash Flows
        For the six months ended 30 June 2025
        Unaudited
        Six months ended 30 June
        2025 2024
        Net cash flows generated from operating activities 151,265 126,458
        Purchase of/prepayments for property, plant and equipment, construction in progress and investment properties (45,558) (12,552)
        Purchase of/prepayments for intangible assets (11,899) (11,846)
        Notes to the Interim Financial Information
        """
        facts = extract_tencent_interim_report_text_facts(
            text,
            {
                "document_id": "tencent_ir:2025:interim",
                "source_id": "tencent_investor_relations",
                "report_kind": "interim",
                "fiscal_year": 2025,
                "document_type": "interim_report_pdf",
            },
        )
        by_metric_period = {
            (fact["metric"], fact["period_type"], fact["end_date"] or fact["instant"]): fact["value"]
            for fact in facts
        }

        self.assertEqual(by_metric_period[("revenue", "quarter", "2025-06-30")], 184_504_000_000)
        self.assertEqual(by_metric_period[("gross_profit", "half_year", "2025-06-30")], 205_506_000_000)
        self.assertEqual(by_metric_period[("operating_cash_flow", "half_year", "2025-06-30")], 151_265_000_000)
        self.assertEqual(by_metric_period[("capex", "half_year", "2025-06-30")], 57_457_000_000)
        self.assertEqual(by_metric_period[("cash", "instant", "2025-06-30")], 182_057_000_000)
        self.assertEqual(by_metric_period[("debt", "instant", "2025-06-30")], 393_815_000_000)

def _metric_fact(metric: str, value: int, *, period_type: str) -> dict:
    fact = {
        "fact_id": f"fixture:{metric}",
        "metric": metric,
        "value": value,
        "unit": "CNY",
        "period_type": period_type,
        "filing_date": "2026-04-01",
    }
    if period_type == "annual":
        fact.update({"start_date": "2025-01-01", "end_date": "2025-12-31"})
    else:
        fact.update({"instant": "2025-12-31"})
    return fact


def _annual_metric_facts(year: int, values: dict[str, int]) -> list[dict]:
    facts = []
    for metric, value in values.items():
        instant_metric = metric in {
            "cash",
            "restricted_cash",
            "short_term_investments",
            "current_assets",
            "current_liabilities",
            "total_assets",
            "total_liabilities",
            "debt",
            "debt_current",
            "debt_noncurrent",
            "accounts_receivable",
            "inventory",
            "accounts_payable",
            "accounts_payable_and_accrued_expenses",
            "payable_to_merchants",
            "merchant_deposits",
            "deferred_revenue",
            "accrued_expenses",
        }
        facts.append(
            {
                "fact_id": f"fixture:{year}:{metric}",
                "metric": metric,
                "value": value,
                "unit": "shares" if metric.endswith("_shares") or metric == "diluted_shares" else "CNY",
                "period_type": "instant" if instant_metric else "annual",
                "start_date": None if instant_metric else f"{year}-01-01",
                "end_date": f"{year}-12-31",
                "instant": f"{year}-12-31" if instant_metric else None,
                "filing_date": f"{year + 1}-04-01",
            }
        )
    return facts


def _quarter_metric_facts(start_date: str, end_date: str, values: dict[str, int]) -> list[dict]:
    instant_metrics = {
        "cash",
        "cash_and_short_term_investments",
        "short_term_investments",
        "restricted_cash",
        "current_assets",
        "current_liabilities",
        "total_assets",
        "total_liabilities",
        "debt",
        "debt_current",
        "debt_noncurrent",
    }
    facts = []
    for metric, value in values.items():
        is_instant = metric in instant_metrics
        facts.append(
            {
                "fact_id": f"fixture:{end_date}:{metric}",
                "metric": metric,
                "value": value,
                "unit": "shares" if metric.endswith("_shares") or metric == "diluted_shares" else "CNY",
                "period_type": "instant" if is_instant else "quarter",
                "start_date": None if is_instant else start_date,
                "end_date": end_date,
                "instant": end_date if is_instant else None,
                "filing_date": "2026-05-01",
            }
        )
    return facts


if __name__ == "__main__":
    unittest.main()
