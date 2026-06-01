# Financial Report Reading System Design V1

Status: Active design proposal.  
Parent design: `docs/financial-agents-v1.md`.  
Methodology reference: `docs/references/value-investor-financial-reports-sec-reading-method.zh.md`.

This design decides what should be deterministic Python, what should be an Agent Skill, and how the financial-report reading workflow should be split.

## 1. Design Principle

Use Python for facts, formulas, rules, and structured report packs. Use Agent Skills only for source-constrained interpretation and narrative writing.

The Skill / LLM layer must not calculate numbers, change formulas, choose new sources of truth, or invent facts.

| Layer | Form | Responsibility |
| --- | --- | --- |
| Source discovery | Python | Find official sources and cache documents |
| Document classification | Python rules | Decide extraction vs material-event scan vs ignore |
| Financial extraction | Python parsers | Extract official facts with lineage |
| Verification | Python | Flag source conflicts and missing primary evidence |
| Metrics calculation | Python | Calculate versioned financial-quality formulas |
| Diagnostic rules | Python rules | Turn metrics into stable warning flags |
| First-layer numeric discovery | Python rules + report renderer | Surface unusual hard-data patterns without explaining motives |
| Official report evidence | Python extraction + Agent Skill | Search official filings/reports for explanations and separate fact vs inference |
| Management communication | Transcript/deck collectors + Agent Skill | Judge management explanations, Q&A pressure, and narrative changes |
| Material-event scan | Python rules + optional Skill summary | Detect important non-core filing events |
| Report pack | Python | Build the structured input for report writing |
| Report interpretation | Agent Skill | Write concise, source-constrained narrative |

## 2. Target Workflow

```text
Company Resolver
  -> Source Discovery / Document Collector
  -> Document Policy / File Classification
  -> Annual Report Baseline Builder
  -> Financial Extraction Agent
  -> Cross-Validation / Verification
  -> Financial Metrics Calculator
  -> Diagnostic Rules
  -> First-Layer Numeric Discovery
  -> Official Report Evidence Agent
  -> Management Communication Agent
  -> Material Event Scanner
  -> Financial Report Pack Builder
  -> Financial Report Interpretation Skill
  -> Markdown Renderer
```

The main architecture rule:

> Python builds the evidence package. Skill writes from the package.

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

### First-Layer Numeric Discovery

Form: deterministic rules inside the report renderer.

Purpose: surface unusual patterns from hard financial data without explaining management motives.

Examples:

- Revenue grew while operating income declined.
- Incremental operating margin is negative or far below current operating margin.
- CFO / net income looks healthy, but working-capital tailwind is meaningful.
- Cash and short-term investments are large, but restricted cash or transferability can affect the read.
- Revenue components show a company-specific mix shift.

Output: `numeric_insights` in the easy-reading report. These insights are not causal explanations; they are questions to route to layer two or layer three.

### Official Report Evidence Agent

Form: Agent Skill.

Purpose: when a metric or diagnostic raises a question, go back to official filings/reports and try to find the best available explanation. It also discovers official filing narratives that may change the read even if they were not raised by layer one.

Design: `docs/official-report-evidence-agent-design-v1.md`.

Responsibilities:

- Search relevant official report sections such as MD&A, notes, segment disclosure, tax, debt, cash flow, audit report, ICFR, and material-event files.
- Explain abnormal metrics when official disclosure allows it.
- Label each claim as official file fact, management explanation, data-based inference, or unknown.
- Keep unresolved issues explicit instead of filling them with guesses.
- Register important official narratives: business model changes, company-specific KPIs, governance/proxy/AGM signals, restricted cash/VIE, audit/accounting reliability, tax, debt, legal and commitment matters.
- Route unresolved issues to layer three when management communication may help.

Output: `official_report_evidence_pack.json` and `official_report_evidence_report.md`.

### Management Communication Agent

Form: transcript/deck/newsroom collectors + Agent Skill.

Purpose: read management communication materials and judge whether management explains the issues left by layer one and layer two.

Design: `docs/management-communication-agent-design-v1.md`.  
Source checklist: `docs/management-communication-evidence-source-checklist-v1.md`.

Allowed sources:

- Earnings call transcripts, including prepared remarks and Q&A.
- Shareholder letters.
- Investor presentations / earnings decks.
- Investor day / capital markets day decks and transcripts.
- Conference / fireside chat transcripts.
- Management interview transcripts / podcasts.
- Company official newsroom / product announcements.
- Analyst questions as market-concern and answer-quality signals.

Responsibilities:

- Answer layer-two unresolved issues using management communication, without treating communication as audited fact.
- Judge answer quality: specific with numbers, specific without numbers, directional only, avoided, or contradicted by filings/metrics.
- Detect new management narratives, strategic commitments, KPI emphasis, tone changes, and repeated analyst pressure.
- Preserve the rule that transcript numbers do not override layer-one or layer-two source of record.

Output: `management_communication_pack.json` and `management_communication_report.md`.

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
- `financial_investigation_notes`
- `material_event_scan`
- `verification_results`
- `missing_facts`
- `human_review_flags`

Output: `financial_report_pack.json`.

### Financial Report Interpretation Skill

Form: Agent Skill.

Purpose: write the readable Financial Results Report from `financial_report_pack.json`, plus optional second-layer `official_report_evidence_pack.json` and third-layer `management_communication_pack.json` when available.

Rules:

- Use annual report / 10-K / 20-F as the baseline.
- Use quarterly updates only to confirm or change the annual view.
- Include material events only when they matter.
- Include official report evidence as layer two when available.
- Include management communication evidence as layer three when available; otherwise state that the layer has not run.
- Do not invent numbers.
- Do not recalculate metrics.
- Do not use third-party facts as source of truth.
- Keep valuation out unless provided by Valuation Agent.

## 4. What Existing Files Cover

| File | Role |
| --- | --- |
| `financial-agents-v1.md` | Overall financial-agent scope |
| `financial-extraction-agent-instruction-v1.md` | What facts to extract and source rules |
| `financial-metrics-agent-instruction-v1.md` | Metric families, formulas, and metric-level warning flags |
| `src/stock_research/diagnostics/financial_rules.py` | Deterministic diagnostic rules that turn metrics into financial-quality questions |
| `official-report-evidence-agent-design-v1.md` | Second-layer official filing/report evidence design |
| `financial-evidence-investigation-skill-v1.md` | Older instruction for answering abnormal metrics from official reports while separating fact, explanation, inference, and unknown |
| `management-communication-agent-design-v1.md` | Third-layer management communication agent design |
| `management-communication-evidence-source-checklist-v1.md` | Third-layer source checklist and source exclusions |
| `src/stock_research/material_events/scanner.py` | Deterministic material-event scanner for non-core official filings |
| `src/stock_research/report_pack.py` | FinancialReportPack builder, the structured input for report writing |
| `financial-report-interpretation-skill-v1.md` | Report-writing Skill instruction and guardrails |
| `src/stock_research/reports/financial_interpretation.py` | Runtime Chinese easy-reading financial report writer from `financial_report_pack.json` |
| `value-investor-financial-reports-sec-reading-method.zh.md` | Human methodology reference |

Remaining design/code gaps:

- Full LLM Skill integration remains optional. Runtime now has a deterministic Chinese easy-reading writer, so the report workflow no longer depends on LLM calculation or interpretation.
- Third-layer management communication pack is designed but not fully wired into the easy-reading report in production runs; the report must state this clearly when no pack exists.
- Future refinement: make the Chinese report shorter and more opinionated after reviewing sample outputs.

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

## 6. Key Decision

Do not create one giant agent that reads everything directly.

Instead:

- Python creates facts, metrics, flags, and report pack.
- Skill controls interpretation and report writing.
- LLM writes only from the pack under source and formula constraints.
