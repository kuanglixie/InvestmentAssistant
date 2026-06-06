from __future__ import annotations

from collections.abc import Callable

from stock_research.agents.v1 import (
    alternative_data_agent,
    audit_review,
    business_model_report_agent,
    business_model_evidence_agent,
    business_model_moat_agent,
    business_model_subagent_cluster_agent,
    company_resolver,
    competitor_comparison_agent,
    customer_happiness_agent,
    diagnostic_rules_agent,
    document_acquisition,
    executive_transcript_agent,
    external_moat_validation_agent,
    feedback_loop_agent,
    financial_extraction,
    financial_results_report_agent,
    financial_verification,
    ir_pdf_cross_validation_agent,
    evidence_communication_agent,
    learning_materials_agent,
    layer1_question_pack_agent,
    leadership_people_agent,
    material_event_scan_agent,
    market_data_agent,
    metrics_agent,
    official_event_transcript_agent,
    financial_report_pack_agent,
    public_voice_evidence_agent,
    research_workflow_artifacts_agent,
    report_builder,
    right_people_report_agent,
    source_discovery,
    valuation_agent,
)
from stock_research.state import ResearchState


Node = Callable[[ResearchState], ResearchState]


NODE_SEQUENCE: list[tuple[str, Node]] = [
    ("company_resolver", company_resolver),
    ("source_discovery", source_discovery),
    ("document_acquisition", document_acquisition),
    ("financial_extraction", financial_extraction),
    ("ir_pdf_cross_validation", ir_pdf_cross_validation_agent),
    ("financial_verification", financial_verification),
    ("market_data", market_data_agent),
    ("metrics", metrics_agent),
    ("diagnostic_rules", diagnostic_rules_agent),
    ("material_event_scan", material_event_scan_agent),
    ("alternative_data", alternative_data_agent),
    ("learning_materials", learning_materials_agent),
    ("business_model_moat", business_model_moat_agent),
    ("external_moat_validation", external_moat_validation_agent),
    ("public_voice_evidence", public_voice_evidence_agent),
    ("executive_transcripts", executive_transcript_agent),
    ("official_event_transcripts", official_event_transcript_agent),
    ("leadership_people", leadership_people_agent),
    ("valuation", valuation_agent),
    ("customer_happiness", customer_happiness_agent),
    ("business_model_subagent_cluster", business_model_subagent_cluster_agent),
    ("competitor_comparison", competitor_comparison_agent),
    ("financial_report_pack", financial_report_pack_agent),
    ("layer1_question_pack", layer1_question_pack_agent),
    ("evidence_communication", evidence_communication_agent),
    ("feedback_loop", feedback_loop_agent),
    ("business_model_evidence", business_model_evidence_agent),
    ("financial_results_report", financial_results_report_agent),
    ("business_model_report", business_model_report_agent),
    ("right_people_report", right_people_report_agent),
    ("research_workflow_artifacts", research_workflow_artifacts_agent),
    ("report_builder", report_builder),
    ("audit_review", audit_review),
]


class LocalSequentialGraph:
    """Small fallback runner so the scaffold works before dependencies are installed."""

    def __init__(self, nodes: list[tuple[str, Node]]) -> None:
        self.nodes = nodes

    def invoke(self, state: ResearchState) -> ResearchState:
        state["graph_backend"] = "local_sequential_fallback"
        for _name, node in self.nodes:
            state = node(state)
        return state


def build_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return LocalSequentialGraph(NODE_SEQUENCE)

    builder = StateGraph(ResearchState)
    for name, node in NODE_SEQUENCE:
        builder.add_node(name, node)

    builder.add_edge(START, NODE_SEQUENCE[0][0])
    for (current_name, _current_node), (next_name, _next_node) in zip(
        NODE_SEQUENCE,
        NODE_SEQUENCE[1:],
    ):
        builder.add_edge(current_name, next_name)
    builder.add_edge(NODE_SEQUENCE[-1][0], END)

    graph = builder.compile()

    class LangGraphWrapper:
        def invoke(self, state: ResearchState) -> ResearchState:
            state["graph_backend"] = "langgraph"
            return graph.invoke(state)

    return LangGraphWrapper()
