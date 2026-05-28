# Business Model / Moat Agent V1

Generated: 2026-05-26

## Purpose

The Business Model / Moat Agent exists to answer the first part of the user's investment principle:

> right business model, right people, right price

For V1, the agent should not merely describe the company. It should convert official-report narrative into a testable economic engine:

- who pays,
- why they pay,
- what the company provides,
- what costs and capital are required,
- what could make customers or merchants stay,
- what could allow competitors to attack the economics,
- whether financial evidence supports or contradicts the story.

## Current V1 Scope

Current V1 uses official reports first:

- 10-K / 20-F / annual report business overview,
- MD&A / operating and financial review,
- segment notes,
- revenue notes,
- risk factors,
- extracted annual and quarterly financial facts,
- calculated financial metrics.

The agent currently produces:

- official-report source summary,
- business-model claims,
- revenue-engine findings,
- moat hypotheses,
- financial evidence signals,
- business evolution notes,
- anti-moat risk items,
- right-business-model checklist,
- missing-evidence list.

## Candidate Learning Sources

Two user-provided business-model research materials are now tracked as candidate learning material:

- Source ID: `thread_value_investor_business_model_playbook`
- Local doc: `docs/value-investor-business-model-research-playbook.md`
- Incremental focus: filing-first ROI sequence, unit economics, decision criteria, source hierarchy.

- Source ID: `thread_gemini_business_model_due_diligence_cn`
- Local doc: `docs/gemini-business-model-due-diligence-cn-notes.md`
- Incremental focus: scuttlebutt, fieldwork, industry clusters, scale economies shared, expert networks, channel checks, compliance controls.

Status: candidate lessons only.

Because the learning activation rule says only approved lessons may change behavior, these playbooks have not been silently activated as operating rules.

## Target Decision Questions

Once approved and implemented more deeply, the agent should answer:

1. What is the customer value proposition?
2. What are the unit economics?
3. What protects returns from competition?
4. How does management allocate capital?
5. What can break the model quickly enough to impair intrinsic value?

The Gemini notes add two extra emphases:

- analyze both industry structure and company-specific value creation,
- test whether scale economies are shared with customers in a self-reinforcing value loop.

## Decision Criteria

The agent should eventually score or classify:

- business-model clarity,
- economic viability,
- durability,
- capital efficiency,
- governance quality,
- accounting trustworthiness,
- valuation sufficiency.

These criteria should be source-linked and industry-relative. The system should avoid universal thresholds for things like gross margin, churn, inventory days, or capital intensity.

## Proposed Subagent Structure

The current V1 structure already has the beginning of this pipeline. The target structure is:

1. Official Report Reader.
2. Business Model Mapper.
3. Revenue Engine Analyst.
4. Unit Economics Analyst.
5. Industry / Competitor Mapper.
6. Moat Hypothesis Analyst.
7. Financial Evidence Analyst.
8. Anti-Moat / Kill Criteria Analyst.
9. External Triangulation Planner.
10. Evidence Auditor.
11. Final Business Model / Moat Report.

## Official Report Reader Target Output

The current Official Report Reader is too thin. Its upgraded job should be to extract a source-grounded business-model dossier from official reports.

Accuracy rule:

- Every field must be tied to a source snippet, source document, and source section, or be marked `not_disclosed`.
- The reader should separate `directly_stated` facts from `inferred_from_multiple_disclosures`.
- It should not use forum, media, or third-party evidence.
- It should not conclude that a moat exists; it should only provide official-report evidence for later subagents.

Target structured output:

| Output Field | What It Should Capture | Accuracy Control |
| --- | --- | --- |
| legal_and_reporting_scope | Legal issuer, holding-company structure, operating entities, VIE/ADR/listing context, reporting currency, fiscal year | Must come from cover page, definitions, structure, or risk sections |
| business_description | What the company says it does and which products/platforms/services matter | Direct snippets from business overview |
| segment_structure | Reported segments, whether segments are disclosed or not disclosed, geography/product split | Mark `not_disclosed` if no segment table exists |
| revenue_model | Revenue streams, who pays, why they pay, revenue recognition, major customer/merchant/payment flows | Source from revenue notes and business overview |
| customer_groups | Buyer/customer/user groups and their stated value proposition | Direct official-report language only |
| supplier_or_partner_dependencies | Merchants, suppliers, logistics partners, payment partners, distribution channels, platform partners | Separate dependency from strategic partnership |
| cost_and_capital_drivers | Disclosed cost categories, fulfillment/logistics, technology, sales/marketing, working capital, CapEx intensity | No invented unit economics |
| disclosed_kpis | Active users, merchants, orders, take rate, retention, GMV, ARPU, or other KPIs if disclosed | Include definition and whether definition changed |
| management_framing | How management describes strategy, priorities, and growth engine | Label as management narrative |
| competitive_position_claims | Official claims about scale, value, technology, ecosystem, supply chain, brand, or cost advantage | Convert to hypotheses, not conclusions |
| risk_factor_map | Risks that can break the model: competition, regulation, quality, logistics, fraud, supplier/customer concentration, capital controls | Keep broad risk-factor language separate from observed evidence |
| business_evolution | How official story changed across annual reports | Compare latest with older filings |
| missing_disclosures | Important items not disclosed: standalone Temu economics, merchant profitability, cohort retention, segment ROIC, etc. | Explicitly list as evidence gaps |

For PDD, the reader should be able to produce a clean table answering:

- What is PDD Holdings legally?
- What are Pinduoduo and Temu?
- Who pays PDD?
- What do merchants pay for?
- What do buyers/customers get?
- Are Pinduoduo and Temu reported separately?
- What parts of the flywheel are directly stated?
- What parts are only management narrative?
- What is not disclosed but necessary for investment judgment?

## Research Escalation Logic

The playbook's core workflow is staged escalation:

1. Filing stack and accounting deep dive.
2. Unit economics and driver tree.
3. Industry and competitor/value-chain mapping.
4. Scenario modeling and reverse DCF.
5. Governance and capital allocation.
6. Product/pricing/customer-journey testing.
7. Targeted interviews.
8. Site visits and fieldwork.
9. Alternative data.
10. Management / IR clarification.

The agent should escalate only when the previous stage leaves a valuation-relevant uncertainty unresolved.

For fieldwork-heavy cases, the agent should first define the exact hypothesis to test, such as whether a claimed cost advantage, logistics density advantage, product-quality advantage, or customer-retention advantage is visible outside the filing.

## Evidence Rules

Every major business-model or moat claim should carry:

- source path or URL,
- evidence type,
- confidence,
- source quality,
- failure mode,
- valuation relevance,
- whether human review is required.

The final report should distinguish:

- fact,
- calculation,
- interpretation,
- hypothesis,
- unresolved issue,
- human-review gate.

## Near-Term Implementation Tasks

1. Add a formal business-model decision-criteria object to `business_model_findings`.
2. Add a unit-economics / driver-tree scaffold, starting with what can be inferred from official reports.
3. Link each moat hypothesis to financial evidence, public voice evidence, and later competitor evidence.
4. Add explicit kill criteria and anti-moat questions.
5. Add source-linked evidence cards to the data-linkage appendix.
6. Only activate the new playbook lessons after user approval.
7. Add scuttlebutt source lines for customers, suppliers/distributors, competitors, and former employees.
8. Add compliance/MNPI flags for expert-network, channel-check, and primary-research evidence.
