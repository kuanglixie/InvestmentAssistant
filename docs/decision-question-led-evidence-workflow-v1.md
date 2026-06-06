# Decision-Question-Led Evidence Workflow V1

Status: short design draft
Last updated: 2026-06-06

This document defines the first practical workflow shape for the Investment Assistant.

The goal is to move the system away from agent-led report generation and toward a clear research workflow built around sources, decision questions, evidence, workpapers, QA, and gaps.

## Core Idea

V1 should be a decision-question-led evidence workflow.

The system should not start by asking each agent to write its own report. It should first establish what sources exist, then define the investment questions, then create an evidence plan, then extract reusable evidence, then build theme workpapers, then run QA and gap triage before any higher-level judgment.

Short version:

```text
Source Map
  -> Decision Questions
  -> Evidence Plan
  -> Filing Deep Read
  -> Evidence Registry
  -> Theme Workpapers
  -> QA / Contradiction Check
  -> Gap Triage
  -> Pillar Judgment
  -> CIO Memo
```

## Why This Workflow

The current risk is that too many agents independently read documents, extract facts, and write reports. That creates repeated work and unclear progress.

This workflow makes the research artifact the center:

- `source_map.json` tells us what material exists.
- `question_pack.json` tells us what the research is trying to answer.
- `evidence_plan.json` tells us what evidence is needed.
- `filing_deep_read_pack.json` mines official-filing evidence before prose workpapers.
- `evidence_registry.json` stores reusable structured evidence.
- `theme_workpaper_pack.json` answers focused research themes.
- `qa_gap_triage.json` tells us what is weak, contradicted, or still unanswered, and contains the routed research backlog.

Agents become workers that update these artifacts. They are not the main organizing unit.

## Step 1: Source Map

Purpose:

Build broad source coverage before deep reading.

Inputs:

- Company input: ticker, issuer name, market, brands, subsidiaries, business aliases.

Outputs:

- `source_map.json`
- `source_inventory`
- `missing_source_log`
- `source_tier_mix`
- `coverage_summary`

Rules:

- Layer 1 does not analyze.
- It only finds, downloads, parses, and standardizes source metadata.
- Every source must have `source_id`, `source_type`, `source_tier`, URL or local path, period, publication date, collection status, parse status, and section availability where possible.

## Step 2: Decision Questions

Purpose:

Convert the investment decision into a structured question map.

The top-level decision questions are:

1. Is this the right business?
2. Are these the right people?
3. Is this the right risk?
4. Is this the right price?

Each top-level question should be decomposed into concrete research questions.

Examples:

- Is growth real, durable, and profitable?
- Does profit convert into cash?
- Does growth require heavy capital consumption?
- Is the business model understandable?
- Who pays, why do they pay, and what would make them leave?
- Does management allocate capital for per-share value?
- Are minority shareholders treated fairly?
- What risks could permanently impair value?
- What expectations are already embedded in the price?

Outputs:

- `question_pack.json`
- `question_id`
- `question_priority`
- `question_owner_theme`
- `decision_link`

## Step 3: Evidence Plan

Purpose:

Define what evidence would answer each question before extraction starts.

Outputs:

- `evidence_plan.json`

Each question should specify:

- evidence needed,
- likely source types,
- source tier requirements,
- period coverage needed,
- what would support the answer,
- what would contradict the answer,
- what would remain unknown.

Example:

```json
{
  "question_id": "financial.cash_conversion",
  "question": "Does reported profit convert into cash?",
  "needed_evidence": [
    "net_income",
    "operating_cash_flow",
    "capex",
    "working_capital_bridge",
    "restricted_cash",
    "merchant_deposits_or_customer_payables_if_relevant"
  ],
  "preferred_sources": ["20-F", "10-K", "10-Q", "6-K", "earnings_release"],
  "contradiction_tests": [
    "profit grows but operating cash flow deteriorates",
    "cash growth is driven mainly by working capital float",
    "restricted cash rises faster than unrestricted cash"
  ]
}
```

## Step 4: Filing Deep Read

Purpose:

Mine the official-filing and official-derived evidence base before any narrative workpaper is written.

This is the main intermediate step that prevents shallow reports. It is not a polished report and it is not a final judgment. It is a structured workbench for deeper extraction.

Inputs:

- `source_map.json`
- `decision_question_pack.json`
- `evidence_plan.json`
- existing official evidence engines, including financial report pack, BMUE pack, and official report evidence pack

Outputs:

- `filing_deep_read_pack.json`
- `section_map`
- `source_refs`
- `evidence_cards`
- `claim_ledger`
- `numeric_fact_refs`
- `management_explanations`
- `risk_disclosures`
- `unknowns`
- `contradiction_matrix`
- `question_coverage`
- `gap_requests`

Rules:

- Preserve facts, management explanations, system inferences, and unknowns separately.
- Prefer official filing and official company evidence for the core fact layer.
- Do not use valuation commentary or third-party opinions as financial evidence.
- Every evidence card should carry upstream artifact references when it comes from an existing engine.
- Contradiction checks should be explicit even when the conclusion remains partial.

V1.25 adapters:

- Financial Evidence Adapter: exposes financial facts, metrics, verification records, and human-review flags as reusable evidence.
- BMUE Adapter: exposes business model evidence cards, contradictions, unknowns, and handoffs.
- Official Evidence Adapter: exposes official-report Q&A, narratives, evidence bundles, and still-unknown items.
- People Adapter: exposes Right People control, incentive, capital allocation, red-flag, and open-question evidence.
- Valuation Adapter: exposes Right Price metrics only to valuation questions.
- Gap Router: merges deep-read gaps, registry adapter gaps, QA gaps, and feedback-loop requests into a research backlog.

Pass condition:

- The theme workpaper can answer from a deeper evidence base rather than directly summarizing old reports.
- P0 financial and business-model questions have evidence cards or explicit gaps.
- Material contradictions and missing disclosures are visible before confidence is assigned.

## Step 5: Evidence Registry

Purpose:

Create a reusable structured evidence layer.

V1 does not need a graph database. It only needs registry records with relationship fields.

Outputs:

- `evidence_registry.json`

Recommended record:

```json
{
  "evidence_id": "",
  "question_ids": [],
  "source_id": "",
  "source_tier": 1,
  "source_type": "",
  "locator": "",
  "excerpt": "",
  "structured_fact": {},
  "evidence_kind": "fact | audited_number | management_claim | management_explanation | external_evidence | system_inference | hypothesis | unknown",
  "supports": [],
  "contradicts": [],
  "confidence": "high | medium | low",
  "requires_human_review": false
}
```

Rules:

- Facts, claims, explanations, inferences, hypotheses, and unknowns must stay separate.
- Unsupported judgments are hypotheses.
- Third-party opinions can create questions, but cannot become core facts without verification.

## Step 6: Theme Workpapers

Purpose:

Answer focused investment themes using the evidence registry.

Theme workpapers should not start from scratch. They should consume:

- `source_map.json`
- `question_pack.json`
- `evidence_plan.json`
- `filing_deep_read_pack.json`
- `evidence_registry.json`

Initial theme workpapers:

- Financial Reality & Accounting Quality.
- Business Model & Unit Economics.
- Management / Governance / Capital Allocation.
- Customer / Supplier / Ecosystem.
- Competitive Position.
- Growth Runway.
- Risk / Fragility / Red Flags.
- Valuation Assumptions.

Each workpaper should include:

- questions answered,
- evidence used,
- mechanism explanation,
- contradiction checks,
- remaining gaps,
- handoff questions.

## Step 7: QA / Contradiction Check

Purpose:

Prevent false confidence.

QA should check:

- Are citations traceable?
- Are source tiers correctly labeled?
- Are conclusions supported by evidence?
- Did the workpaper search for counterevidence?
- Are management claims separated from facts?
- Are third-party opinions kept out of the core fact layer?
- Are important missing sources disclosed?

Output:

- `qa_gap_triage.json`
- `research_backlog`

## Step 8: Gap Triage

Purpose:

Decide what to do next.

Every major answer should end with:

- what is answered,
- what is unanswered,
- whether the gap matters,
- next step.

Possible next steps:

- `stop`
- `monitor`
- `collect_more_sources`
- `extract_more_evidence`
- `build_deeper_workpaper`
- `human_review_required`
- `ready_for_pillar_judgment`

## Step 9: Pillar Judgment

Purpose:

Only after source coverage, evidence extraction, workpapers, QA, and gap triage should the system move into judgment.

Pillar judgments:

- Right Business.
- Right People.
- Right Risk.
- Right Price.

The Pillar Judgment Agents consume workpapers. They should not invent facts or silently introduce new sources.

## V1 Acceptance Criteria

V1 is working when:

1. A company run produces a source map before deep extraction.
2. Every major extraction links back to a question.
3. Every important claim links back to evidence.
4. Evidence records distinguish facts, management claims, inferences, hypotheses, and unknowns.
5. Theme workpapers consume the registry instead of rereading everything independently.
6. QA can cap confidence when contradiction checks are missing.
7. Gap triage clearly says whether to stop, dig deeper, or escalate to human review.

## Design Decision

Use the term:

**Decision-Question-Led Evidence Workflow**

Chinese shorthand:

**投资决策问题驱动的证据底稿流程**

Avoid:

- `Questionnaire`: sounds too rigid and checklist-like.
- `Evidence Graph`: useful as a concept, but too heavy as a V1 implementation requirement.
- `Agent-led workflow`: creates too much duplicated reading and unclear ownership.
