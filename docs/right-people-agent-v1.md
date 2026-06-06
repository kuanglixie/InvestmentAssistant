# Right People / Management Quality Agent V1

Primary methodology reference: `docs/right-people-methodology-v1.zh.md`.

## Goal

Evaluate whether management, governance, incentives, and capital allocation are good enough for long-term value-investing work.

The agent does not decide buy/sell. It answers whether the "right people" gate is supported, partially supported, needs review, or not evaluated.

## Core Questions

1. Who controls the company?
2. Are management incentives aligned with per-share value?
3. Has capital allocation been rational?
4. Do management communications match later financial outcomes?
5. Does the execution record support trust?
6. Are there unresolved integrity, governance, auditor, related-party, or disclosure red flags?

## Source Policy

Official filings and official financial reports are the source of record for:

- governance and control facts,
- board / officer disclosures,
- ownership and voting-power disclosures,
- SBC and dilution,
- buybacks, dividends, debt, cash use, and capital allocation,
- related-party transactions,
- auditor changes and accounting reliability issues.

Earnings calls and executive interviews may be used only for:

- management priorities,
- capital allocation language,
- strategic framing,
- tone and communication quality,
- promise-versus-outcome tracking.

They must not override official financial facts.

## Evidence Separation Rule

Every important observation should be labeled before it reaches the report:

- `fact`: filed, audited, directly observable, certified, or externally adjudicated evidence.
- `management_claim`: management's explanation, promise, priority, or strategic framing.
- `external_evidence`: independent validation or contradiction from regulators, courts, customers, employees, competitors, media, forums, or expert inputs.
- `inference`: the analyst/system conclusion after weighing facts, claims, and external evidence.

Core rule: never let a management claim masquerade as a fact.

## Source Hierarchy

1. High: 10-K, 20-F, audited annual reports, proxy/DEF 14A when applicable, S-1/F-1/424B4, governance documents, definitive agreements, enforcement orders, and final judgments.
2. Medium-high: 10-Q, 6-K, 8-K, 13D/13G, Forms 3/4/5, and director/officer change filings.
3. Medium: earnings calls, shareholder letters, investor days, conference decks, and executive interviews.
4. Low-to-medium: customer, supplier, merchant, employee, competitor, media, forum, app-review, and expert inputs.

Lower-tier sources can create review questions and external validation, but they should not override filed or audited facts.

## Required Analysis Sequence

1. Build the control map: votes, economics, board influence, VIE/control structure, controlled-company or home-country exemptions.
2. Build the incentive and dilution map: ownership, compensation metrics, SBC burden, net dilution, hedging/clawback policy where available.
3. Build the capital-allocation ledger: reinvestment, buybacks, dividends, acquisitions, financing, cash build, and share-count effects.
4. Audit management communication: promises, KPI framing, bad-news explanations, Q&A directness, and later outcomes.
5. Run red-flag sweep: related parties, auditor changes, restatements, non-reliance, material weaknesses, turnover, and litigation/regulatory records.
6. Add external validation only after source quality is labeled.

## V1 Subagents

### Governance / Control Reader

Reads annual reports / 20-F / 10-K and related official disclosures for board, directors, voting power, beneficial ownership, VIE, contractual arrangements, and control structure.

### Incentive Alignment Analyst

Uses SBC, dilution, ownership, and share-incentive disclosures to test whether management incentives are likely aligned with long-term per-share value.

### Capital Allocation Historian

Uses cash conversion, CapEx intensity, ROIC proxy, incremental ROIC proxy, buyback/dividend language, and management commentary to map how management uses capital.

### Management Communication Auditor

Uses cached earnings-call and executive-transcript evidence to identify repeated management claims about long-term investment, governance, capital allocation, competition, and priorities.

### Execution Track Record Analyst

Uses official financial metrics to test whether the organization has converted strategy into revenue growth, margins, cash flow, and return on capital.

### Integrity / Red Flag Scanner

Uses material-event scan, official-filing red-flag terms, and financial-verification conflicts to identify review-required issues.

## Current V1 Limits

- It does not yet parse a full named-person ownership and voting-power table.
- It does not yet produce a full pay-for-performance compensation table.
- It does not yet separate founder, board, CFO, and operating-team contributions.
- It does not yet run a full promise-versus-outcome timeline.
- It can flag official-filing terms such as related party or auditor, but those require human review in context.

## Output

The agent writes:

- `leadership_findings` in `state.json`,
- `right_people_report.md`,
- `right_people_report.zh.md`,
- `agent_reports/leadership_people.md`,
- `agent_reports/right_people_report.md`.

The final report checklist should cite the Right People Agent instead of saying "not evaluated yet."

## V3 Decision Layer

The current implementation adds a gatekeeping decision layer on top of the V1 subagents. It writes these structured sections into `leadership_findings`:

- `right_people_decision`: conservative gate status, weighted score, confidence, hard overrides, and unresolved gate items.
- `scorecard`: weighted dimensions for integrity/candor, incentive alignment, capital allocation, control/governance, execution quality, and behavior in stress.
- `control_map`: official-filing control terms, VIE/control review flags, control-gap status, and next extraction actions.
- `incentive_map`: SBC, dilution, compensation evidence, pay-for-performance unknowns, and per-share alignment status.
- `capital_allocation_ledger`: multi-year cash-flow, CapEx, FCF, owner-earnings proxy, share-count, ROIC, and incremental-return rows.
- `communication_audit`: management claim counts, claim timeline, first-pass promise/outcome checks, and Q&A/evasiveness status.
- `red_flag_matrix`: review flags with severity, evidence bucket, source, and hard-override status.

Decision statuses are intentionally conservative:

- `passes_v1_with_open_questions`
- `partial_pass_needs_deeper_review`
- `does_not_pass_pending_red_flag_review`
- `does_not_pass_v1_needs_review`

This layer is still not a buy/sell recommendation. It is a Right People gate for the broader “right business model, right people, right price” workflow.
