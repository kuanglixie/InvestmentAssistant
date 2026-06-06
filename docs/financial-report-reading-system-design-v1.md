# Financial Report Reading System Design V1

Status: Active design proposal.  
Parent design: `docs/financial-agents-v1.md`.  
Methodology reference: `docs/references/value-investor-financial-reports-sec-reading-method.zh.md`.
Last updated: 2026-06-04.

This design decides what should be deterministic Python, what should be an Agent Skill, and how the financial-report reading workflow should be split.

## 1. Design Principle

Use Python for facts, formulas, rules, and structured report packs. Use Agent Skills only for source-constrained interpretation and narrative writing.

The Skill / LLM layer must not calculate numbers, change formulas, choose new sources of truth, or invent facts.

| Layer | Form | Responsibility | Main output |
| --- | --- | --- | --- |
| Source collection | Python | Find official filings, earnings releases, transcripts, proxy/AGM materials, decks, and cache documents | `source_inventory` |
| Document classification | Python rules | Decide financial extraction, evidence extraction, transcript parsing, material-event scan, or ignore | `document_policy` |
| Financial extraction | Python parsers | Extract official numeric facts with lineage; no narrative interpretation | `financial_facts.json` |
| Financial verification | Python | Flag source conflicts, missing primary evidence, unit/currency problems, and extraction gaps | `verification_results` |
| Metrics calculation | Python | Calculate versioned financial-quality formulas | `financial_metrics` |
| Layer-one question builder | Python rules | Answer standard financial questions, surface hard-data anomalies, and create handoffs | `layer1_question_pack.json` |
| Evidence & communication extraction | Python extraction + Agent Skill | Read official-file evidence and management communication to answer layer-one questions and proactively discover new narratives/problems | `evidence_communication_pack.json` |
| Feedback loop router | Python rules | Route second-layer unknowns and new questions back to financial extraction, metrics, Layer 1, evidence reading, external data, or human review | `feedback_loop_pack.json` |
| Material-event scan | Python rules + optional Skill summary | Detect important non-core filing events and feed evidence extraction | `material_event_scan` |
| Research draft builder | Python renderer + constrained Skill where needed | Build broad/deep source-linked research draft from packs | `financial_research_draft.md` |
| HTML visual report | Python renderer | Turn the draft into a focused readable report | `financial_visual_report.html` |

## 2. Target Workflow

```text
Company Resolver
  -> Source Discovery / Document Collector
  -> Document Policy / File Classification
  -> Financial Extraction Agent
  -> Cross-Validation / Verification
  -> Financial Metrics Calculator
  -> Material Event Scanner
  -> Financial Report Pack Builder
  -> Layer-One Question Builder
  -> Evidence & Communication Extraction
  -> Feedback Loop Router
  -> Financial Research Draft Builder
  -> HTML Visual Report Renderer
```

The main architecture rule:

> Reports should consume structured packs. Questions and evidence should be generated before report writing, not discovered only inside the final report.

The key redesign is that the system must produce intermediate research objects before any final narrative:

```text
financial_facts.json
financial_report_pack.json
layer1_question_pack.json
evidence_communication_pack.json
feedback_loop_pack.json
financial_research_draft.md
financial_visual_report.html
```

Current implementation note: the main graph and `rerun-financial-report` now write `layer1_question_pack.json`, `evidence_communication_pack.json`, and `feedback_loop_pack.json` before rendering the financial research draft. The legacy `official_report_evidence_pack.json` and `management_communication_pack.json` remain as transitional source packs inside the unified evidence/communication layer.

## 3. Key Modules

### Annual Report Baseline Builder

Purpose: establish the annual-report baseline before quarterly updates or event scans influence the read.

Form: Python section selection + optional Skill summary.

Answers:

- 公司靠什么赚钱？
- 增长来自哪里？
- 利润能不能变成现金？
- 有哪些主要风险？
- 数字有没有明显不舒服的地方？

Output: `annual_report_baseline`.

### Financial Extraction Agent

Form: deterministic Python.  
Instruction: `docs/financial-extraction-agent-instruction-v1.md`.

Responsibilities:

- Extract annual and interim official facts.
- Preserve raw facts and selected facts separately.
- Derive only allowed facts: gross profit, free cash flow, debt from debt components.
- Keep missing fields missing.

Output: `raw_extracted_facts`, `selected_facts`, `extraction_summary`, `missing_high_priority_fields`.

### Financial Metrics Calculator

Form: deterministic Python.  
Instruction: `docs/financial-metrics-agent-instruction-v1.md`.

Responsibilities:

- Build annual baseline metrics.
- Build latest interim trend metrics.
- Attach source fact IDs.
- Keep valuation metrics out.

Metric families:

- Growth quality.
- Margin quality.
- Cash conversion / working-capital quality.
- Capital intensity / owner earnings proxy.
- Balance-sheet resilience.
- SBC / dilution burden.
- Tax, non-GAAP, and accounting quality.

Output: `financial_metrics`, `latest_interim_trend`, `missing_metric_inputs`.

### Diagnostic Rules

Form: deterministic Python rules.

Purpose: convert metrics into warning flags and follow-up checks.

Examples:

- Revenue grew but operating income declined.
- CFO / net income is below 1.
- Incremental operating margin is negative.
- SBC consumes a meaningful share of operating cash flow.
- Debt, restricted cash, or convertible notes are missing but likely important.

Output: `diagnostic_findings`.

### Layer-One Question Builder

Form: deterministic Python rules using `selected_facts`, `financial_metrics`, and `diagnostic_findings`.

Purpose: answer standard financial questions and turn hard-data anomalies into explicit research questions before evidence extraction starts.

This stage must happen before official-file and transcript reading. The report should not be the first place where questions appear.

Standard answers:

- 有没有增长？
- 增长来自哪里？
- 经济引擎是什么？
- 增长有没有兑现为利润？
- 边际经济性是否优于存量业务？
- 利润有没有变成现金？
- 现金流质量是否可持续？
- 资产负债表能不能支撑投入期？
- 管理层是否在创造每股价值？

Question handoffs:

- `handoff_to_evidence_communication`
- `handoff_to_financial_extractor`
- `handoff_to_material_event_scan`

Examples:

- Revenue grew while operating income declined.
- Incremental operating margin is negative or far below current operating margin.
- CFO / net income looks healthy, but working-capital tailwind is meaningful.
- Cash and short-term investments are large, but restricted cash or transferability can affect the read.
- Revenue components show a company-specific mix shift.

Output: `layer1_question_pack.json`.

Minimum schema:

```json
{
  "question_answers": [],
  "numeric_anomalies": [],
  "red_flags": [],
  "hard_data_insights": [],
  "disclosure_gaps": [],
  "handoff_to_evidence_communication": [],
  "handoff_to_financial_extractor": []
}
```

These insights are not causal explanations. They are questions and evidence needs to route into the next layer.

### Evidence & Communication Extraction

Form: official-file/text extraction, transcript/deck/newsroom collectors, and source-constrained Agent Skill.

Purpose: read non-numeric evidence after layer one has built the question pack. It has two equal responsibilities:

1. Answer or qualify the layer-one questions.
2. Proactively discover important narratives, risks, opportunities, KPI changes, governance changes, and new unanswered questions that layer one may not see.

Design: `docs/evidence-and-communication-extraction-design-v1.md`.

Responsibilities:

- Search official report sections such as MD&A, notes, segment disclosure, tax, debt, cash flow, audit report, ICFR, proxy/AGM, and material-event files.
- Read management communication such as earnings calls, Q&A, earnings releases, decks, shareholder letters, official newsroom, and investor day materials.
- Label each evidence item as `filing_fact`, `management_explanation`, `risk_disclosure`, `management_claim`, `analyst_concern`, `our_inference`, or `unknown`.
- Keep unresolved issues explicit instead of filling them with guesses.
- Judge answer quality: specific with numbers, specific without numbers, directional only, avoided, or contradicted by filings/metrics.
- Register important narratives: business model changes, company-specific KPIs, governance/proxy/AGM signals, restricted cash/VIE, audit/accounting reliability, tax, debt, legal and commitment matters.
- Create proactive discoveries even when layer one did not raise a question.
- Route missing numeric fields back to financial extraction.

Output: `evidence_communication_pack.json` and `evidence_communication_report.md`.

Compatibility note: existing `official_report_evidence_pack.json` and `management_communication_pack.json` can remain as transitional outputs, but the long-term report consumer should prefer the unified pack.

### Feedback Loop Router

Form: deterministic Python rules.

Purpose: close the loop after evidence extraction. If the official-file / communication layer creates new questions, unresolved unknowns, or missing numeric handoffs, they must not remain as prose-only notes. The router classifies each request into one of six destinations:

- `financial_extractor_requests`
- `metric_recalculation_requests`
- `layer1_requery_requests`
- `evidence_communication_followups`
- `external_data_requests`
- `human_review_requests`

The router also writes `feedback_requery_questions` back into `layer1_question_pack.json`, so the next run can see which questions should be re-answered after extraction or metric changes.

V1 policy: the feedback router routes and records. It does not invent missing facts, does not automatically re-run an infinite extraction loop, and does not convert management claims into financial facts.

Output: `feedback_loop_pack.json` and `feedback_loop_report.md`.

### Material Event Scanner

Form: Python document classification + optional Skill summary.

Purpose: scan non-core official filings without making them a second research main line.

Flag only events that can change financial risk or valuation:

- Acquisition / divestiture.
- Debt / financing / convertible bonds.
- Restatement / non-reliance.
- Auditor change.
- Management change.
- Material weakness / ICFR issue.
- Impairment / restructuring.
- Major contract.
- Regulatory event.
- Share plan or dilution event.

Output: `material_event_scan`.

### Financial Report Pack Builder

Form: deterministic Python.

Purpose: build the only structured input that a report-writing Skill may use.

Minimum pack fields:

- `company`
- `source_inventory`
- `annual_report_baseline`
- `annual_facts`
- `quarterly_facts`
- `financial_metrics`
- `latest_interim_trend`
- `diagnostic_findings`
- `layer1_question_pack_summary`
- `layer1_question_pack_path`
- `evidence_communication_pack_summary`
- `evidence_communication_pack_path`
- `financial_investigation_notes`
- `material_event_scan`
- `verification_results`
- `missing_facts`
- `extractor_backlog`
- `human_review_flags`

Output: `financial_report_pack.json`.

Boundary: `financial_report_pack.json` should stay the numeric/report-control pack. It should not embed the full `evidence_communication_pack.json`; use paths and summaries to avoid duplicate, oversized artifacts.

### Financial Research Draft Builder

Form: Python renderer plus constrained Skill only when source-linked synthesis is needed.

Purpose: build a broad and deep research draft from structured packs. This draft is the research workpaper, not the final polished report.

Rules:

- Use annual report / 10-K / 20-F as the baseline.
- Use quarterly updates only to confirm or change the annual view.
- Include material events only when they matter.
- Use `layer1_question_pack` as the question spine.
- Use `evidence_communication_pack` for official evidence, management communication, proactive discoveries, and unknowns.
- Keep extractor backlog in one fixed section instead of scattering "next steps" everywhere.
- Do not invent numbers.
- Do not recalculate metrics.
- Do not use third-party facts as source of truth.
- Keep valuation out unless provided by Valuation Agent.

Output: `financial_research_draft.md`.

### HTML Visual Report Renderer

Form: deterministic Python renderer.

Purpose: turn the research draft into a readable, focused report. It should preserve the workpaper separately and should not be the only artifact.

Rules:

- Pull highlights from the research draft rather than rereading raw files.
- Prefer charts, compact cards, and clear emphasis.
- Keep source and limitation links available but not visually noisy.
- Do not introduce new facts that are absent from upstream packs.

Output: `financial_visual_report.html`.

## 4. What Existing Files Cover

| File | Role |
| --- | --- |
| `financial-agents-v1.md` | Overall financial-agent scope |
| `financial-extraction-agent-instruction-v1.md` | What facts to extract and source rules |
| `financial-metrics-agent-instruction-v1.md` | Metric families, formulas, and metric-level warning flags |
| `src/stock_research/diagnostics/financial_rules.py` | Deterministic diagnostic rules that turn metrics into financial-quality questions |
| `evidence-and-communication-extraction-design-v1.md` | Unified non-numeric evidence and management communication extraction design |
| `official-report-evidence-agent-design-v1.md` | Legacy split-layer design; keep as reference only, do not build new runtime around it |
| `financial-evidence-investigation-skill-v1.md` | Legacy investigation instruction; useful concepts may be folded into unified evidence extraction |
| `management-communication-agent-design-v1.md` | Legacy split-layer design; keep as reference only, do not build new runtime around it |
| `management-communication-evidence-source-checklist-v1.md` | Source checklist still useful; should be reused by unified evidence extraction |
| `src/stock_research/material_events/scanner.py` | Deterministic material-event scanner for non-core official filings |
| `src/stock_research/report_pack.py` | FinancialReportPack builder, the structured input for draft/report writing |
| `financial-report-interpretation-skill-v1.md` | Report-writing Skill instruction and guardrails |
| `src/stock_research/reports/financial_interpretation.py` | Runtime Chinese easy-reading financial report writer from `financial_report_pack.json` |
| `src/stock_research/reports/financial_research_draft.py` | Research draft renderer from financial, official-evidence, and management-communication packs |
| `src/stock_research/reports/financial_visual.py` | HTML visual report renderer |
| `value-investor-financial-reports-sec-reading-method.zh.md` | Human methodology reference |

Remaining design/code gaps:

- Full LLM Skill integration remains optional. Runtime now has a deterministic Chinese easy-reading writer, so the report workflow no longer depends on LLM calculation or interpretation.
- `layer1_question_pack.json` is now a standalone first-class artifact, but the research draft still contains some older docket-building logic that should gradually move upstream or consume the pack more directly.
- Unified `evidence_communication_pack.json` is now implemented as the main non-numeric evidence pack; current runtime still writes separate official-evidence and management-communication packs as transitional source packs.
- Existing runtime still writes several transitional artifacts (`official_report_evidence_pack.json`, `management_communication_pack.json`, and parts of the easy-reading report) that should not become permanent parallel systems.
- Future refinement: make the HTML report a focused consumer of the research draft, while keeping the draft broad and evidence-heavy.

## 5. Recommended Build Order

1. Define `FinancialReportPack` schema.
   **Implemented in `src/stock_research/report_pack.py`; runtime writes `financial_report_pack.json`.**
2. Align `metrics/v1.py` with `financial-metrics-agent-instruction-v1.md`.
   **Initial V1 alignment is implemented for working capital, tax/non-GAAP/accounting quality, source-of-growth attribution, expanded balance-sheet checks, latest interim trend status, formula labels, and proxy review flags.**
3. Add deterministic `diagnostic_rules.py`.
   **Implemented as `src/stock_research/diagnostics/financial_rules.py`; it now owns the financial-quality questions.**
4. Add Financial Evidence Investigation Skill.
   **Instruction implemented as `docs/financial-evidence-investigation-skill-v1.md`; runtime integration remains pending.**
5. Add material-event scanner.
   **Implemented as `src/stock_research/material_events/scanner.py`.**
6. Build `financial_report_pack.json`.
   **Implemented through the `financial_report_pack` graph node and CLI rerun path.**
7. Add Financial Report Interpretation Skill.
   **Instruction implemented as `docs/financial-report-interpretation-skill-v1.md`; runtime deterministic Chinese easy-reading writer implemented in `src/stock_research/reports/financial_interpretation.py`.**
8. Promote Layer-One Question Builder to a first-class artifact.
   **Implemented as `src/stock_research/layer1_questions.py`; runtime writes `layer1_question_pack.json`.**
9. Implement unified Evidence & Communication Extraction.
   **Implemented as `src/stock_research/evidence_communication/agent.py`; runtime writes `evidence_communication_pack.json` and `evidence_communication_report.md`. Old split packs are written only during migration.**
10. Make Financial Research Draft consume packs only.
   **Partially implemented: the draft receives `financial_report_pack`, `layer1_question_pack`, and `evidence_communication_pack`; remaining cleanup is to remove older internal docket duplication once pack coverage is richer.**
11. Make HTML Visual Report consume the draft.
   **The HTML report should be the focused presentation layer, not the primary evidence-generation layer.**
12. Remove or demote legacy code paths.
   **After unified packs are validated, delete or demote code that only supports the old split flow and no longer contributes to the new research pipeline.**

## 6. Key Decision

Do not create one giant agent that reads everything directly.

Instead:

- Python creates facts, metrics, flags, question packs, evidence packs, and report packs.
- Evidence/communication Skills extract and label source-constrained evidence before report writing.
- The research draft is a broad workpaper generated from packs.
- The HTML report is a focused presentation generated from the draft.
- LLM writes only from upstream packs under source and formula constraints.

## 7. Migration And Legacy Cleanup Policy

The new design should not preserve every old artifact forever. Compatibility is useful during migration, but it should not create two competing financial-reading systems.

### Keep

- `financial_report_pack.json` as the canonical financial numeric pack.
- `layer1_question_pack.json` as the first-class question and hard-data insight pack.
- `evidence_communication_pack.json` as the unified non-numeric evidence pack.
- `financial_research_draft.md` as the broad workpaper.
- `financial_visual_report.html` as the focused presentation.

### Transitional Only

These can remain temporarily while the new pack is being validated:

- `official_report_evidence_pack.json`
- `official_report_evidence_report.md`
- `management_communication_pack.json`
- legacy easy-reading sections that duplicate the research draft

Once `evidence_communication_pack.json` covers the same information with better labels and source metadata, the split packs should either become compatibility exports generated from the unified pack or be removed from the main pipeline.

### Candidates To Delete Or Demote

Delete or demote code when all are true:

- The new pack carries the same or better information.
- Existing tests can be updated to assert the new artifact instead.
- No downstream report uses the old artifact as the only source.
- The old path encourages duplicate logic, duplicate reports, or inconsistent conclusions.

Likely candidates:

- Separate official-evidence and management-communication graph nodes as permanent pipeline stages.
- Report code that builds questions inside the report instead of consuming `layer1_question_pack.json`.
- Report code that reads raw filing/transcript-like inputs directly instead of consuming packs.
- Legacy docs that imply second and third layers are separate final report modules rather than lanes inside unified extraction.

### Do Not Delete Yet

Do not remove these until the replacement is implemented and verified:

- Source collectors and transcript collectors.
- Source checklist documents.
- Existing pack builders if tests or generated reports still depend on them.
- Any code needed to regenerate current PDD run artifacts during transition.

### Migration Gate

Before deleting a legacy path, the implementation should pass:

- PDD rerun writes `financial_report_pack.json`, `layer1_question_pack.json`, `evidence_communication_pack.json`, `financial_research_draft.md`, and `financial_visual_report.html`.
- The research draft uses the new packs as source of truth.
- The HTML report can render without reading split official/management packs directly.
- `tests.test_scaffold` passes after tests are updated to the new artifact names.
