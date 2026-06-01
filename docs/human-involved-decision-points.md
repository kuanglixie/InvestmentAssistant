# Human-Involved Decision Points

## Purpose

This document records places where the multi-agent stock research system should stop, explain the situation, and ask for a human decision before continuing.

The goal is not to ask for approval on every small implementation choice. The goal is to protect research quality when the system reaches a boundary where automation should not silently decide:

- which source is trustworthy enough;
- which formula or assumption is allowed;
- whether a conflict is material;
- whether weak evidence may enter a report;
- whether a provisional result is acceptable.

These decision points should eventually become explicit LangGraph interrupt nodes or equivalent workflow gates. Each decision should be saved into the run state and data linkage so later reports can show who approved what, when, and under which limits.

## General Rules

1. Default to the user's standing policy when it exists.
2. If a requested action would violate or stretch the standing policy, stop and ask.
3. If the system proceeds after approval, label the output as approved, provisional, or rejected according to the decision.
4. Do not use a human approval to hide uncertainty. The report must still show source quality, limitations, and open issues.
5. Every human decision should create an audit record.

Suggested audit record:

```json
{
  "decision_id": "HDP-001",
  "run_id": "20260528T155057Z-pdd",
  "agent_id": "financial_extraction",
  "trigger": "SEC source unavailable for most recent financial report",
  "question_shown": "...",
  "human_choice": "use_company_ir_provisionally",
  "allowed_scope": "extract Q1 2026 financial facts from PDD IR only until SEC 6-K is available",
  "disallowed_scope": "do not use third-party mirrors for financial extraction",
  "created_at": "2026-05-28T00:00:00Z"
}
```

## Decision Point HDP-001: Financial Report Source Substitution

Status: active design rule.

### Trigger

The user asks for the latest or most recent financial report, but the system cannot obtain the expected SEC filing.

Examples:

- SEC filing is not yet available.
- SEC index is stale.
- SEC request fails because of network, rate limit, or environment error.
- The company has announced results on IR, but the corresponding SEC 6-K / 10-Q / 20-F is not found yet.
- The system finds a third-party mirror of a financial release before it finds the SEC filing.

### Why Human Decision Is Required

For PDD and U.S.-listed ADRs, the user's standing source policy is:

- SEC filings are the financial-report source of record.
- Company investor relations can be used for official cross-validation.
- Third-party data is not trusted for financial-report extraction.

If the SEC source is missing, using another source is not just a technical fallback. It changes the evidence standard. The system must not make that change silently.

### Default Behavior

If no human approval is available:

1. Do not extract financial facts from third-party mirrors.
2. Do not promote third-party data into financial results.
3. Record the SEC fetch/index problem.
4. Continue with the latest available SEC-sourced data if useful.
5. Mark the most recent period as `pending_official_sec_source`.

### Human Choices

The system may offer these choices:

1. Wait / retry SEC later.
   Safest default. No new financial facts are extracted until the SEC source is available.

2. Use company IR provisionally.
   Allowed only if the source is the company's official IR website or official company-hosted report. The report must label the facts as provisional and later reconcile them against SEC.

3. Use a named third-party source only as a lead.
   The source can be stored as a link or note, but its numbers cannot enter financial extraction unless the user explicitly approves a narrow one-time exception.

4. Abort latest-period extraction.
   The report keeps older official results and records that the latest report could not be sourced under the current policy.

### Recommended User Prompt

```text
I could not find the SEC filing for the latest financial report yet.

Your current policy says SEC filings are the financial-report source of record, and company IR is only for official cross-validation.

How should I proceed?

1. Wait/retry SEC later.
2. Use the official company IR release provisionally and reconcile to SEC later.
3. Record third-party pages only as source candidates, not financial data.
4. Skip the latest-period extraction for now.
```

### Output Requirements If Approved

If the user approves a non-SEC source:

- The source must be named in the report.
- The source must be labeled as `human_approved_provisional_source`.
- The facts must retain source URL, local path, retrieval time, and approval record.
- The report must include a reconciliation task against SEC.
- Once the SEC filing becomes available, SEC replaces the provisional source unless the user explicitly decides otherwise.

### Disallowed Without New Human Approval

- Reusing this approval for a different company.
- Reusing this approval for a different reporting period.
- Adding a new third-party financial-report source to the pipeline.
- Treating a newswire mirror, finance portal, analyst site, or transcript provider as the financial-report source of record.

## Future Decision Points To Add

Candidate future entries:

- Formula changes, including owner earnings, ROIC, incremental ROIC, and excess-cash treatment.
- Material source conflicts above the 2% threshold.
- Whether low-quality public-voice evidence can affect a business-model or customer-happiness conclusion.
- Whether valuation assumptions are acceptable for a base/bear/bull model.
- Whether a candidate lesson from learning materials can become an approved agent rule.
- Whether a new data connector can be added for financial, qualitative, or alternative-data evidence.
