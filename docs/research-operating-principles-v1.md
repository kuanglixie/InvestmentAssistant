# Research Operating Principles V1

Status: living design draft
Last updated: 2026-06-05

This document defines the operating principles every Investment Assistant agent should follow. These principles apply across source collection, evidence workpapers, pillar judgments, bull/bear debate, and CIO memo generation.

The purpose is to prevent the system from becoming a shallow report generator. The assistant should behave like a disciplined research process: broad enough to avoid missing sources, question-led enough to stay focused, evidence-backed enough to remain auditable, and skeptical enough to avoid premature confidence.

## 1. Broad Before Deep

Principle:

Before drilling into one retrieval result, first establish source coverage.

Why it matters:

An agent can easily overfit to the first document or search result it finds. This creates false depth: the report looks detailed, but it may be built on an incomplete source set.

Operating rule:

- Layer 1 should first build a source inventory.
- Layer 2 should first inspect which source categories are available and missing.
- A workpaper should state whether it has annual reports, quarterly reports, transcripts, investor presentations, regulatory sources, competitor sources, and alternative/public voice sources where relevant.

Bad behavior:

- Start summarizing one annual report without knowing whether newer 6-Ks, earnings releases, or regulatory documents exist.
- Treat a single transcript as representative of management communication history.

Expected output:

- `source_inventory`
- `coverage_summary`
- `missing_source_log`
- `source_tier_mix`

## 2. Question Before Extraction

Principle:

Define the investment questions and evidence plan before extracting evidence.

Why it matters:

Without fixed questions, extraction becomes a source summary. The system may copy facts that are easy to extract while missing the questions that matter.

Operating rule:

- Every Layer 2 workpaper should begin with a `question_pack`.
- Each question should define what evidence would support, weaken, or leave the answer unknown.
- Extraction should map evidence back to question IDs.

Examples:

- Financial Evidence should not only extract revenue. It should answer whether growth converted into profit and cash.
- Business Model should not only summarize the business description. It should answer how money is made, who pays, why customers use it, and what could break the model.
- Right People should not only list executives. It should answer who controls the company, how they are incentivized, and whether capital allocation behavior matches owner orientation.

Expected output:

- `question_pack`
- `evidence_plan`
- `question_ids` on evidence cards

## 3. Evidence Before Conclusion

Principle:

Judgments without evidence are hypotheses, not conclusions.

Why it matters:

This is the main guardrail against hallucination and narrative contamination. If the system cannot point to evidence, it should lower the label from conclusion to hypothesis.

Operating rule:

- Every important claim must be linked to source evidence.
- The output must distinguish `fact`, `management_claim`, `management_explanation`, `external_evidence`, `system_inference`, `hypothesis`, and `unknown`.
- A conclusion requires enough evidence quality for the relevant question.

Allowed:

- "Hypothesis: Temu may have lower standalone profitability, but official reporting does not provide enough segment disclosure to prove this."

Not allowed:

- "Temu is structurally unprofitable" unless supported by reliable evidence.

Expected output:

- `evidence_cards`
- `claim_or_fact_registry`
- `confidence`
- `requires_human_review`

## 4. Mechanism Before Metric

Principle:

Do not only report numbers. Explain the economic mechanism behind the numbers.

Why it matters:

A metric without mechanism can mislead. Revenue growth, margin expansion, ROIC, free cash flow, and working capital can all look strong for very different reasons. Value investors need to understand the cause.

Operating rule:

- Financial metrics should be connected to drivers and bridges.
- Business model metrics should be connected to customer behavior, merchant economics, pricing power, fulfillment, working capital, or capital intensity.
- When a number improves, the agent should ask what caused it and whether that cause is durable.

Examples:

- Revenue growth should be split by revenue component where available.
- Operating profit should be bridged from revenue growth, gross margin, cost of revenue, sales and marketing, R&D, and G&A.
- Cash flow should distinguish operating earnings from working-capital float.
- ROIC should be connected to asset intensity, working capital, and reinvestment needs.

Expected output:

- `driver_bridge`
- `mechanism_explanation`
- `unit_economics_proxy`
- `durability_question`

## 5. Contradiction Before Confidence

Principle:

Do not assign high confidence until the agent has looked for contradiction or counterevidence.

Why it matters:

High confidence should be earned. A company can present a coherent story while filings, competitors, customers, merchants, regulators, or later results contradict it.

Operating rule:

- Each workpaper should include a contradiction check.
- Management claims should be tested against official numbers, later disclosures, competitor evidence, regulatory evidence, and external source signals when relevant.
- If no contradiction search was performed, confidence should be capped.

Examples:

- If management claims pricing power, check gross margin, customer complaints, competitor pricing, and discount intensity.
- If management claims long-term investment, check capex, R&D, share count, capital allocation, and later outcomes.
- If management claims the same operating model across business units, check segment disclosure, geography, logistics, and regulatory facts.

Expected output:

- `contradiction_checks`
- `counterevidence`
- `confidence_cap_reason`
- `open_disconfirming_tests`

## 6. Gap Before Next Step

Principle:

Every answer should end by stating what remains unanswered and whether it is worth further work.

Why it matters:

A good research agent should not hide uncertainty. It should make the next research decision easier: stop, monitor, collect another source, escalate to another workpaper, or ask for human judgment.

Operating rule:

- Every report section should include gaps or limits where material.
- Each workpaper should produce `unknowns` and `handoff_questions`.
- The system should say whether the gap is material enough to continue digging.

Gap types:

- `missing_source`
- `missing_metric`
- `insufficient_period_coverage`
- `management_claim_unverified`
- `conflicting_evidence`
- `rights_or_access_limited`
- `requires_human_review`

Expected output:

- `unknowns`
- `coverage_gaps`
- `handoff_questions`
- `recommended_next_step`

## System-Wide Enforcement

Every major agent should preserve these fields when possible:

```json
{
  "source_inventory": [],
  "question_pack": [],
  "evidence_cards": [],
  "mechanism_explanations": [],
  "contradiction_checks": [],
  "unknowns": [],
  "handoff_questions": [],
  "confidence_cap_reason": ""
}
```

If an agent cannot satisfy one principle, it should state the limitation explicitly rather than silently producing a confident answer.

## Short Form

1. Broad before deep: source coverage first.
2. Question before extraction: questions and evidence plan first.
3. Evidence before conclusion: unsupported judgments are hypotheses.
4. Mechanism before metric: explain why the number moved.
5. Contradiction before confidence: search for disconfirming evidence before high confidence.
6. Gap before next step: say what remains unknown and what to do next.

