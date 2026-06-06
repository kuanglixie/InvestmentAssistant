# MVP Prototype Contract V1

Status: implemented MVP artifact line
Last updated: 2026-06-06

This document defines the practical MVP build line for the Decision-Question-Led Evidence Workflow.

It is intentionally narrower than the full system design. The goal is to make each prototype section clear enough to implement one by one without losing the main line.

## Core Rule

The MVP should be artifact-first, not agent-first.

Agents are workers. The durable products are the artifacts:

1. `source_map.json`
2. `decision_question_pack.json`
3. `evidence_plan.json`
4. `filing_deep_read_pack.json`
5. `evidence_registry.json`
6. `theme_workpaper_pack.json`
7. `qa_gap_triage.json`

Each artifact should have a clear scope, input, output, and stop condition.

Implementation note:

- Builder module: `src/stock_research/research_workflow/artifacts.py`
- Graph node: `research_workflow_artifacts`
- Output location: each run directory under `data/runs/<run_id>/`
- Implemented versions:
  - v1.0: `source_map.json`
  - v1.1: `decision_question_pack.json` and `evidence_plan.json`
  - v1.2: `evidence_registry.json`
  - v1.3: `theme_workpaper_pack.json` and `theme_workpaper_report.md`
  - v1.4: `qa_gap_triage.json` and `pillar_judgment_stub.json`
  - v1.25: `filing_deep_read_pack.json`, evidence adapters, and routed research backlog

## MVP Flow

```text
Company Input
  -> Source Map
  -> Decision Question Pack
  -> Evidence Plan
  -> Filing Deep Read
  -> Evidence Registry
  -> Theme Workpaper
  -> QA / Contradiction Check
  -> Gap Triage
  -> Pillar Judgment Stub
```

For the first prototype, PDD can remain the main test company because the SEC / IR source path is already the strongest.

## Section 0: Company Input / Run Context

Purpose:

Normalize the company identity before source collection.

Scope:

- Resolve company name, ticker, market, legal entity, listing type, CIK or exchange identifier, official IR URL, brands, and aliases.
- Preserve aliases without prematurely merging business units.

Input:

- User company input, such as `PDD`.
- Market, such as `us-adr`.
- Local company registry.

Output:

- `company_context`

Minimum fields:

```json
{
  "raw_input": "PDD",
  "company_id": "pdd",
  "legal_name": "PDD Holdings Inc.",
  "tickers": [{"symbol": "PDD", "market": "us-adr"}],
  "listing_type": "foreign_private_issuer",
  "sec_cik": "0001737806",
  "official_ir_url": "https://investor.pddholdings.com/",
  "brands": ["Pinduoduo", "Temu"],
  "business_aliases": []
}
```

Out of scope:

- No business judgment.
- No source quality judgment beyond identity confidence.

Pass condition:

- Downstream sections can reliably know which issuer and filing system to use.

## Section 1: Source Map

Purpose:

Build broad source coverage before any deep extraction.

Scope:

- Find official company sources.
- Find official external sources when configured.
- Register alternative and third-party sources as lower-tier leads when configured.
- Download, cache, fingerprint, parse, and record source metadata where possible.

Input:

- `company_context`
- Source discovery config.
- Existing downloader results, such as SEC / IR document records.

Output:

- `source_map.json`

Minimum fields:

```json
{
  "schema_version": "source_map_v1",
  "company_context": {},
  "source_inventory": [],
  "coverage_summary": {},
  "source_tier_mix": {},
  "missing_source_log": [],
  "acquisition_log": [],
  "rights_constraints": [],
  "quality_flags": []
}
```

Each `source_inventory` row should include:

- `source_id`
- `source_type`
- `source_group`
- `source_tier`
- `issuer`
- `period`
- `publication_date`
- `filing_date`
- `url`
- `local_path`
- `content_hash`
- `collection_status`
- `parse_status`
- `sections`

Out of scope:

- No analysis.
- No conclusion.
- No source-derived investment judgment.

Pass condition:

- The run has a machine-readable source inventory.
- Missing and blocked sources are explicit.
- Every downstream evidence item can reference a `source_id`.

## Section 2: Decision Question Pack

Purpose:

Turn the final investment decision into concrete research questions.

Scope:

- Start from the four pillar questions:
  - Right Business
  - Right People
  - Right Risk
  - Right Price
- Decompose them into answerable sub-questions.
- Mark priority and owner theme.

Input:

- `company_context`
- `source_map.json`
- Standard investment question templates.
- Company-specific discovery hints, if any.

Output:

- `decision_question_pack.json`

Minimum fields:

```json
{
  "schema_version": "decision_question_pack_v1",
  "company_id": "pdd",
  "questions": [
    {
      "question_id": "financial.cash_conversion",
      "pillar": "right_business",
      "theme": "financial_reality",
      "priority": "P0",
      "question": "Does reported profit convert into cash?",
      "why_it_matters": "",
      "expected_evidence_types": []
    }
  ],
  "question_coverage_summary": {},
  "company_specific_questions": [],
  "open_question_log": []
}
```

Out of scope:

- No evidence extraction yet.
- No final answer.
- No confidence rating.

Pass condition:

- Every downstream extraction task can point to a `question_id`.
- The questions are decision-linked, not random summaries.

## Section 3: Evidence Plan

Purpose:

Define what evidence would answer each question before extraction starts.

Scope:

- For each question, specify source types, preferred source tiers, required periods, likely sections, supporting evidence, contradiction tests, and gap conditions.

Input:

- `source_map.json`
- `decision_question_pack.json`

Output:

- `evidence_plan.json`

Minimum fields:

```json
{
  "schema_version": "evidence_plan_v1",
  "plans": [
    {
      "question_id": "financial.cash_conversion",
      "preferred_source_tiers": [1],
      "preferred_source_types": ["20-F", "10-Q", "6-K", "earnings_release"],
      "required_sections": ["cash_flow", "footnotes", "mda"],
      "needed_evidence": ["net_income", "operating_cash_flow", "capex", "working_capital_bridge"],
      "support_tests": [],
      "contradiction_tests": [],
      "gap_conditions": []
    }
  ],
  "plan_coverage_summary": {},
  "source_gap_requests": []
}
```

Out of scope:

- No evidence extraction.
- No conclusion.

Pass condition:

- Every P0 question has at least one evidence plan.
- The plan says where to look and what would count as contradiction.

## Section 4: Filing Deep Read

Purpose:

Mine official-filing and official-derived evidence before the workpaper writes prose.

Scope:

- Build a section map from available Tier 1 sources.
- Convert existing mature engines into unified evidence cards through code-level adapters.
- Preserve facts, management explanations, system inferences, upstream references, and unknowns separately.
- Build a deterministic contradiction matrix and question coverage map.
- Produce gap requests for missing metrics, missing disclosures, human review, and follow-up extraction.

Input:

- `source_map.json`
- `decision_question_pack.json`
- `evidence_plan.json`
- existing packs in state:
  - `financial_report_pack`
  - `business_model_unit_economics_pack`
  - `official_report_evidence_pack`

Output:

- `filing_deep_read_pack.json`

Minimum fields:

```json
{
  "schema_version": "filing_deep_read_pack_v1",
  "prototype_version": "v1.25",
  "section_map": [],
  "source_refs": [],
  "evidence_cards": [],
  "claim_ledger": [],
  "numeric_fact_refs": [],
  "management_explanations": [],
  "risk_disclosures": [],
  "unknowns": [],
  "contradiction_matrix": [],
  "question_coverage": [],
  "gap_requests": [],
  "adapter_summaries": {}
}
```

Adapters implemented:

- Financial Evidence Adapter: financial facts, metrics, verification records, human-review flags.
- BMUE Adapter: business-model evidence cards, unknowns, contradictions, handoffs.
- Official Evidence Adapter: official-report Q&A, decision narratives, evidence bundles, still-unknown items.
- People Adapter: Right People control, incentive, capital allocation, red flags, open questions.
- Valuation Adapter: Right Price evidence only, outside the financial-evidence fact layer.
- Gap Router: deep-read gaps, registry adapter gaps, QA gaps, and feedback-loop requests into one research backlog.

Out of scope:

- No buy/sell conclusion.
- No third-party opinion as core financial fact.
- No valuation commentary inside Financial Evidence.
- No management claim promoted to fact.

Pass condition:

- Theme workpapers can consume a deeper evidence base instead of directly summarizing old reports.
- Material contradictions, missing disclosures, and unsupported claims are visible before confidence is assigned.
- All generated evidence carries a source id or upstream artifact reference.

## Section 5: Evidence Registry

Purpose:

Store reusable structured evidence across sources.

Scope:

- Extract facts, audited numbers, management claims, management explanations, external evidence, system inferences, hypotheses, and unknowns.
- Link each evidence item to `source_id` and `question_id`.
- Preserve locator and excerpt when available.

Input:

- `source_map.json`
- `decision_question_pack.json`
- `evidence_plan.json`
- Parsed documents and extracted tables/text.

Output:

- `evidence_registry.json`

Minimum fields:

```json
{
  "schema_version": "evidence_registry_v1",
  "evidence_items": [
    {
      "evidence_id": "",
      "question_ids": [],
      "source_id": "",
      "source_tier": 1,
      "source_type": "",
      "locator": "",
      "evidence_kind": "fact",
      "excerpt": "",
      "structured_fact": {},
      "supports": [],
      "contradicts": [],
      "confidence": "high",
      "requires_human_review": false
    }
  ],
  "registry_summary": {},
  "unknowns": []
}
```

Out of scope:

- No polished narrative.
- No buy/sell judgment.
- No unsupported inference.

Pass condition:

- Evidence can be reused by multiple theme workpapers.
- Facts and claims are separated.
- Unsupported judgments are downgraded to `hypothesis` or `unknown`.

## Section 6: Theme Workpaper

Purpose:

Answer one focused research theme using the evidence registry.

First MVP themes:

1. Financial Reality & Accounting Quality
2. Business Model & Unit Economics
3. Management / Governance / Capital Allocation

Later themes:

- Customer / Supplier / Ecosystem
- Competitive Position
- Growth Runway
- Risk / Fragility / Red Flags
- Valuation Assumptions

Input:

- `source_map.json`
- `decision_question_pack.json`
- `evidence_plan.json`
- `filing_deep_read_pack.json`
- `evidence_registry.json`

Output:

- `theme_workpaper_pack.json`
- `theme_workpaper_report.md`

Minimum pack fields:

```json
{
  "schema_version": "theme_workpaper_pack_v1",
  "theme": "financial_reality",
  "questions_answered": [],
  "evidence_used": [],
  "answers": [],
  "mechanism_explanations": [],
  "contradiction_checks": [],
  "unknowns": [],
  "handoff_questions": []
}
```

Out of scope:

- No final pillar judgment unless explicitly labeled preliminary.
- No new source collection without routing back to Source Map.

Pass condition:

- Every answer cites evidence.
- Every high-confidence answer has contradiction checks.
- Gaps are explicit.

## Section 7: QA / Contradiction Check

Purpose:

Prevent false confidence before judgment.

Scope:

- Check citations.
- Check source tier usage.
- Check whether conclusions are supported by evidence.
- Check whether contradiction tests were run.
- Cap confidence where evidence is thin.

Input:

- `theme_workpaper_pack.json`
- `evidence_registry.json`
- `source_map.json`

Output:

- `qa_gap_triage.json`

Minimum fields:

```json
{
  "schema_version": "qa_gap_triage_v1",
  "citation_checks": [],
  "source_tier_checks": [],
  "unsupported_claims": [],
  "missing_contradiction_checks": [],
  "confidence_caps": [],
  "quality_flags": [],
  "research_backlog": {}
}
```

Out of scope:

- No investment conclusion.
- No new evidence creation except QA flags.

Pass condition:

- Unsupported or weakly supported claims are flagged.
- Confidence is capped where contradiction checks are missing.

## Section 8: Gap Triage

Purpose:

Decide whether to stop, dig deeper, collect more sources, or move to judgment.

Scope:

- Classify gaps.
- Decide next action.
- Preserve human review gates.

Input:

- `qa_gap_triage.json`
- `theme_workpaper_pack.json`
- `source_map.json`

Output:

- gap decisions inside `qa_gap_triage.json`

Allowed next actions:

- `stop`
- `monitor`
- `collect_more_sources`
- `extract_more_evidence`
- `build_deeper_workpaper`
- `human_review_required`
- `ready_for_pillar_judgment`

Out of scope:

- No final buy/sell decision.

Pass condition:

- Every material gap has a next action.
- The system can explain why it is or is not ready for judgment.

## Section 9: Pillar Judgment Stub

Purpose:

Provide a minimal handoff target without overbuilding the judgment layer.

Scope:

- Consume validated workpapers.
- Produce preliminary readiness status for:
  - Right Business
  - Right People
  - Right Risk
  - Right Price

Input:

- validated `theme_workpaper_pack.json`
- `qa_gap_triage.json`

Output:

- `pillar_judgment_stub.json`

Minimum fields:

```json
{
  "schema_version": "pillar_judgment_stub_v1",
  "pillar_readiness": {
    "right_business": "ready | not_ready | needs_more_work",
    "right_people": "ready | not_ready | needs_more_work",
    "right_risk": "ready | not_ready | needs_more_work",
    "right_price": "ready | not_ready | needs_more_work"
  },
  "blocking_gaps": [],
  "required_workpapers": []
}
```

Out of scope:

- No final investment memo in the first prototype.
- No portfolio action.

Pass condition:

- The system can tell which pillar is ready and why.

## Build Order

Recommended MVP build order:

1. Build `source_map.json`.
2. Build `decision_question_pack.json`.
3. Build `evidence_plan.json`.
4. Build a first `evidence_registry.json` using financial evidence only.
5. Build Financial Reality theme workpaper.
6. Add QA / Gap Triage for Financial Reality.
7. Extend registry and workpaper flow to Business Model.
8. Extend to Right People.

## Current Repo Migration Notes

Existing artifacts can remain during migration:

- `source_discovery` and `documents` should feed the new `source_map.json`.
- `layer1_question_pack.json` should conceptually migrate toward `decision_question_pack.json`.
- `financial_report_pack.json` should conceptually migrate toward the Financial Reality theme workpaper.
- `business_model_evidence.json` and `business_model_unit_economics_pack.json` should conceptually migrate toward the Business Model theme workpaper.
- `evidence_communication_pack.json` can help seed the early `evidence_registry.json`, but should not remain the long-term central artifact.

Do not break the existing pipeline during the MVP migration. Add new artifacts first, then gradually route old sections through them.

## MVP Completion Criteria

The prototype is useful when one PDD run can produce:

1. `source_map.json`
2. `decision_question_pack.json`
3. `evidence_plan.json`
4. `filing_deep_read_pack.json`
5. `evidence_registry.json`
6. at least one `theme_workpaper_pack.json`
7. `qa_gap_triage.json`

The run should make it obvious:

- what sources were covered,
- what questions were asked,
- what evidence was found,
- what answers are supported,
- what claims are only hypotheses,
- what contradictions were checked,
- what gaps remain,
- what should happen next.
