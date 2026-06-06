# Business Model Evidence Agent MVP

Status: primary design doc
Supersedes: prior `Business Model / Moat Agent V1` draft

Layer 2 target design: `docs/business-model-unit-economics-workpaper-design-v1.md`.

Migration note: this document defines the current Business Model Evidence Agent MVP and Q1-Q9 structure. The target Layer 2 workpaper is `Business Model & Unit Economics Workpaper`, which expands this MVP into BMQ-01 through BMQ-18, stronger source/audit labels, revenue stream maps, unit-economics proxies, and financial cross-check lineage.

## 1. Goal

Build a Business Model Evidence Agent for the investment assistant system.

The agent should not simply summarize company filings. It should answer fixed investment questions about how a company makes money, why the model works, and where the model is fragile.

The output should be organized by investment questions, not by source type.

This agent does not output Buy / Sell / Hold. It only outputs business-model evidence, uncertainty, preliminary diagnosis, and handoff questions for downstream agents.

## 2. Core Principle

Source is evidence. Question is structure.

Bad output structure:

- Annual report says...
- Earnings call says...
- Website says...

Good output structure:

- How does the company make money?
- Who pays, who uses, who supplies?
- Why do customers pay?
- What drives revenue growth?
- What drives margins?
- What are the fragile points?

Each question should contain evidence from different source types, with source reliability labels.

## 3. Role In The Investment Assistant

The agent sits in the evidence layer:

```text
Business Model Evidence Agent
   -> Right Business Agent
   -> Bull / Bear Agents
   -> CIO Investment Memo Agent
   -> Final Investment Decision
```

It should support the user's core investing principle:

```text
right business model
right people
right price
```

For MVP, this agent focuses on the first part: business-model evidence. Moat judgment and final business-quality classification belong to later layers unless explicitly marked as preliminary.

## 4. Inputs

The agent should accept:

```yaml
company:
  name: string
  ticker: string
  market: string

documents:
  official_filings:
    - path_or_url
  earnings_calls:
    - path_or_url
  investor_presentations:
    - path_or_url
  product_pages:
    - url
  pricing_pages:
    - url
  competitor_filings:
    - path_or_url

existing_outputs:
  financial_evidence_agent_output:
    path_or_json
```

For MVP, support local files first. Web crawling can be added later.

## 5. Source Types And Reliability

Every extracted evidence item must include source metadata.

```yaml
source_type:
  - official_filing
  - revenue_recognition_note
  - segment_disclosure
  - management_communication
  - product_page
  - pricing_page
  - competitor_filing
  - third_party_media
  - alternative_data
```

Reliability rules:

```yaml
official_filing: high
revenue_recognition_note: high
segment_disclosure: high
product_page: high_for_product_facts
pricing_page: high_for_pricing_facts
management_communication: medium
competitor_filing: medium_high
third_party_media: low_medium
alternative_data: medium_or_low
```

Policy:

1. Core business-model claims must be supported by official filings, revenue recognition notes, segment disclosure, product pages, or pricing pages.
2. Management claims must be labeled as `management_claim`.
3. Third-party commentary can generate hypotheses but cannot be used as final evidence by itself.
4. If sources conflict, official filings win.
5. If evidence is weak, the agent must output uncertainty instead of guessing.
6. The agent should distinguish fact, calculation, interpretation, hypothesis, unresolved issue, and human-review gate.

### 5.1 Source Priority And Prototype Coverage

The Business Model Evidence Agent should use more than financial reports. Financial reports explain how the model shows up in numbers, but other sources are needed to test product reality, pricing, customer behavior, merchant economics, competition, and fragility.

Saved tracker: `docs/business-model-data-source-coverage-tracker-v1.md`.

Prototype status labels:

- `core_implemented`: already part of the main `stock_research` pipeline.
- `prototype_exists`: working or fixture/live-smoke prototype exists, but not necessarily integrated into the MVP output schema.
- `registry_or_source_plan`: source registry, policy, or planned collector exists, but collection/output is not yet robust.
- `not_yet`: no meaningful repo prototype found.

| Priority | Source | Business-Model Use | Reliability | Prototype Status |
| --- | --- | --- | --- | --- |
| P0 | Annual report / 20-F / 10-K | Defines official business description, issuer structure, revenue categories, risk factors, and baseline model | high | `core_implemented`: SEC/PDD/Tencent source discovery, XBRL/PDF extraction, official evidence, and annual-report business-model analysis exist in `src/stock_research/sources/`, `src/stock_research/extraction/`, `src/stock_research/official_evidence/`, and `src/stock_research/qualitative/annual_report.py`. |
| P0 | Revenue recognition notes | Tests who pays, for what, when revenue is recognized, gross/net treatment, and service/product economics | high | `core_implemented_partial`: official filings are collected and parsed; Business Model MVP still needs explicit source-type labeling for revenue-recognition evidence cards. |
| P0 | Segment / geography disclosure | Tests whether business lines, products, regions, or platforms are separated or blended | high | `core_implemented_partial`: financial extraction and annual-report analysis use segment/geography disclosures when available; MVP needs a clearer segment-disclosure evidence table. |
| P0 | Financial Evidence Agent output | Cross-checks claims about growth quality, cash generation, operating leverage, asset-light model, working capital, and capital intensity | high | `core_implemented`: `financial_report_pack.json`, financial diagnostics, material-event scan, and easy-reading reports are already generated. |
| P1 | Quarterly filings / 6-K / 10-Q / earnings releases | Captures latest trend, margin pressure, strategic investment, revenue mix change, and recent management explanation | high_to_medium | `core_implemented`: PDD 6-K/IR latest financial release discovery and material-event scan exist; management interpretation is handled separately from official filing facts. |
| P1 | Company product pages / app / website | Tests actual product, customer journey, value proposition, product surface, pricing visibility, discounts, delivery promises, and login friction | high_for_product_facts | `integrated_package`: Temu product/page-surface tracker exists in `src/stock_research/alternative_data/temu_product_intelligence/`; alternative-data e-commerce connector also normalizes fixed-basket observations. |
| P1 | Pricing pages / fee schedules / merchant terms | Tests who pays, fees, take rate, merchant obligations, returns/logistics burden, and whether economics depend on subsidies or penalties | high_for_pricing_facts | `registry_connected`: merchant fee / seller terms / platform policy targets are now connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; collection still uses web-reader/manual snapshots until a dedicated policy extractor exists. |
| P1 | Terms of service / merchant agreements / policy pages | Tests platform power, user/merchant obligations, dispute rules, return/refund friction, data/privacy, and regulatory fragility | high_for_policy_facts | `registry_connected`: official seller policy plus official customer shipping/returns/refund policy targets are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; no dedicated policy-page extractor yet. |
| P1 | Government / regulator / customs / consumer-protection sources | Tests de minimis/customs exposure, consumer-protection enforcement, product-safety obligations, DSA/platform obligations, data/privacy, and regulatory fragility | high_for_rule_or_enforcement_facts | `registry_connected`: CBP, FTC, EU DSA, and USCC official/regulator source targets are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; collection remains official-page snapshot/manual PDF snapshot first. |
| P2 | Earnings call transcripts | Tests management explanation, Q&A pressure, strategy framing, margin/growth commentary, and analyst challenge | medium | `prototype_exists`: earnings-call transcript provider chain exists in `prototypes/earnings-call-transcripts/` and is adopted by `config/qualitative/pdd_official_event_sources.v1.json`; used by `src/stock_research/qualitative/official_events.py`. |
| P2 | Investor presentations / investor day | Tests management's business-model framing, KPI narrative, strategic priorities, and claimed growth drivers | medium | `registry_connected`: PDD IR quarterly-results/presentation pages and local investor-deck intake are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; dedicated slide parser remains pending. |
| P2 | Competitor filings | Tests copyability, industry economics, alternative revenue models, margin structure, capital intensity, and relative moat | medium_high | `registry_connected`: Alibaba, JD, Amazon, and SHEIN official/regulator locator targets are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; robust competitor-filing parser remains pending. |
| P2 | Competitor product / pricing pages | Tests customer alternatives, price pressure, feature parity, delivery/service comparison, and whether the model is easy to copy | medium_high | `registry_connected`: Temu product intelligence is linked as a fixed-basket extension point for Amazon, AliExpress, and SHEIN comparator baskets; live competitor crawling remains controlled/manual-first. |
| P2 | Paid acquisition / promotion / search / web-rank signals | Tests whether growth is organic, bought through ads, coupon-driven, or weakening against competitors | medium_or_low | `registry_connected`: PDD digital demand monitor, Google Ads Transparency locator, and Google Trends connector are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; these remain pattern evidence, not CAC proof. |
| P3 | App Store / Google Play reviews and aggregate ratings | Tests customer happiness, delivery/refund/product-quality issues, trust, repeat-use clues, and app-level demand quality | low_medium_to_medium | `registry_connected`: Apple App Store, Google Play, the PDD digital demand monitor, and the main app-store connector are connected in `config/qualitative/pdd_business_model_source_coverage.v1.json`; live collection varies by source. |
| P3 | Public customer discussion: Reddit, forums, review sites, YouTube/Bilibili/Xiaohongshu/Zhihu | Generates pattern evidence about customer problems, loyalty, trust, product quality, refunds, and whether low price creates repeat behavior | low_medium | `prototype_exists_partial`: public voice registry and Reddit/forum connector exist; executive/video/Bilibili prototypes exist. Evidence remains lead/pattern evidence and needs triangulation. |
| P3 | Merchant / supplier / seller forums and complaint platforms | Tests seller profitability, platform rules, ads/traffic ROI, penalties, returns, logistics burden, and supply-side health | low_medium | `registry_or_source_plan`: merchant source lines and Reddit queries exist, but no strong merchant-economics collector/output is implemented yet. |
| P3 | Alternative demand data: app rank, search trends, web/domain rank, paid ads, product-surface signals | Tests demand momentum, paid-acquisition intensity, promotion dependence, competitor pressure, and whether growth is being bought | medium_or_low | `integrated_package`: `src/stock_research/alternative_data/digital_demand_monitor/` covers app/search/web/reviews/product metrics and paid-ad signals; main alternative-data connectors include Google Trends, YouTube, Reddit, App Store, and e-commerce basket, though live statuses vary. |
| P4 | Media, interviews, analyst reports, third-party summaries | Generates hypotheses and context; should not be final evidence without stronger support | low_medium | `prototype_exists_partial`: executive/interview source registry exists in `config/qualitative/pdd_executive_video_sources.v1.json`; Bilibili/video Q&A and webcast-transcript prototypes exist. Analyst-report workflow is not implemented. |

### 5.1.1 Remaining Priority Source Review

After connecting merchant/platform policy, competitor sources, investor materials, regulator/trade sources, customer policy, app-store demand quality, and paid-acquisition signals, the most important remaining sources are:

| Source | Importance | Difficulty | Recommendation |
| --- | --- | --- | --- |
| Dedicated policy-page parser | High | Medium | Implement after the current registry proves useful; it should extract policy headings, effective dates, fee/return terms, eligibility language, and country-specific variants. |
| Dedicated investor-presentation parser | Medium-high | Medium | Keep local/manual ingest now; implement slide/PDF page parser when there are enough decks or investor-day materials to justify it. |
| Competitor filing parser | Medium-high | Medium | Start from official IR/SEC downloads and reuse annual-report extraction patterns; defer deeper segment mapping until one competitor comparison report is requested. |
| Merchant-economics forum collector | Medium | Medium-high | Keep as lead evidence only; implement later because anonymous merchant claims require careful triangulation and retention/source-rights rules. |
| Licensed app / market-intelligence datasets | Medium | High | Defer until there is a budget/source-license decision; Sensor Tower, data.ai, Similarweb, Semrush, or marketplace seller-data products can be valuable but should not be treated as free/open evidence. |
| Analyst reports / expert networks | Medium | High | Defer; useful for hypotheses but requires license/compliance workflow and should not become primary evidence. |

### 5.2 Downloaded Financial-Report Cache Check

The source-priority table above describes capability. The local workspace also has evidence that financial-report sources have already been downloaded and used.

Current cache status:

| Company / Source | Local Cache Evidence | Download / Use Status |
| --- | --- | --- |
| PDD SEC filings | Original source repo cache: `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/sec/0001737806/documents/` | Downloaded. The cache contains 295 non-metadata SEC document files, including 8 `20-F` annual reports, 268 `6-K` files/exhibits, prospectuses, shelf/financing filings, and related capital-market filings. |
| PDD annual reports | Same SEC cache under `documents/20-F/` | Downloaded. Annual-report files exist for fiscal years represented by 2018 through 2025 `20-F` accessions, including `pdd-20241231x20f.htm` and `pdd-20251231x20f.htm`. |
| PDD processed run outputs | Original repo runs: `data/runs/20260529T033942Z-pdd/` and `data/runs/20260530T033052Z-pdd/`; consolidated repo also has `data/runs/20260530T033052Z-pdd/` | Used by pipeline. Runs recorded 295 documents, 43 downloaded financial/core documents, and generated `financial_report_pack.json`, `official_report_evidence_pack.json`, and `financial_easy_reading_report.md`. |
| Tencent official IR financial reports | Original source repo cache: `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/tencent_ir/financial_reports/` | Downloaded and text-converted. Cache contains 44 PDFs and 44 extracted text files covering annual and interim reports from 2004 through 2025. |
| PDD company IR cache | Original source repo path: `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/pdd_ir/` | Not materially cached as files in the current workspace. PDD financial-report evidence is primarily coming from SEC filing cache and run outputs. |

Repo organization note:

- Heavy raw caches were intentionally not copied into the consolidated repo because `data/raw` in the original source repo is hundreds of MB.
- The consolidated repo keeps source code, configs, docs, and prototype code. Raw report caches can be regenerated or copied selectively when needed.
- Runtime outputs under `data/runs/` are ignored by git and should be treated as local artifacts, not source-controlled code.

## 6. Fixed Questions

The Business Model Evidence Agent should answer these questions.

### Q1. How Does The Company Make Money?

Sub-questions:

- What are the main revenue streams?
- What products or services generate revenue?
- Is revenue based on product sales, subscription, advertising, commission, transaction fees, licensing, services, or other models?
- How does the company recognize revenue?

### Q2. Who Pays, Who Uses, And Who Supplies?

Sub-questions:

- Who is the paying customer?
- Who is the end user?
- Who provides supply, content, inventory, merchants, data, or infrastructure?
- Are the payer and user the same person?

### Q3. Why Do Customers Pay?

Sub-questions:

- What customer problem does the company solve?
- Does it save money, save time, reduce risk, increase revenue, provide convenience, entertainment, or status?
- Is the value proposition strong or weak?

### Q4. What Drives Revenue Growth?

Sub-questions:

- User growth?
- Volume growth?
- ARPU?
- Pricing?
- Take rate?
- Advertising load?
- Subscription members?
- Geographic expansion?
- New products?
- Market share gains?

### Q5. What Drives Margins And Cost Structure?

Sub-questions:

- What are the major cost categories?
- Are costs fixed or variable?
- Does the business have operating leverage?
- Should margins improve with scale?
- Is margin pressure strategic investment or structural deterioration?

### Q6. Is The Model Recurring, Transactional, Cyclical, Or Subsidy-Driven?

Sub-questions:

- Is revenue recurring or one-time?
- Is customer behavior repeatable?
- Is demand cyclical?
- Does growth depend on discounts, subsidies, or aggressive marketing?

### Q7. What Are The Fragile Points?

Sub-questions:

- Customer concentration?
- Supplier concentration?
- Platform dependence?
- Traffic acquisition dependence?
- Regulatory dependence?
- Subsidy dependence?
- Low switching cost?
- Commodity-like product?
- High capex or working capital needs?

### Q8. What Does Financial Evidence Confirm Or Contradict?

Use the existing Financial Evidence Agent output.

Examples:

- If the Business Model Evidence Agent says the model has operating leverage, check whether operating margin improved with revenue growth.
- If the model should be cash-generative, check whether operating cash flow and free cash flow support that.
- If the model is asset-light, check capex and working-capital intensity.
- If growth is high quality, check whether growth translated into profit and cash.

### Q9. What Should Other Agents Investigate?

Generate questions for:

- Moat Agent
- Growth Runway Agent
- Risk Agent
- Valuation Agent
- Management Agent

## 7. Output Schema

The agent should output JSON plus a markdown report.

### JSON Schema

```json
{
  "company": {
    "name": "",
    "ticker": "",
    "market": ""
  },
  "agent": "business_model_evidence_agent",
  "version": "0.1",
  "summary": {
    "one_sentence_business_model": "",
    "business_model_quality": "high | medium | low | uncertain",
    "confidence": "high | medium | low"
  },
  "questions": [
    {
      "question_id": "Q1",
      "question": "How does the company make money?",
      "finding": "",
      "confidence": "high | medium | low",
      "evidence": [
        {
          "claim": "",
          "source_name": "",
          "source_type": "",
          "reliability": "",
          "citation": "",
          "excerpt": ""
        }
      ],
      "open_issues": []
    }
  ],
  "financial_cross_check": {
    "confirmed_by_financials": [],
    "contradicted_by_financials": [],
    "needs_investigation": []
  },
  "fragility_points": [
    {
      "risk": "",
      "evidence": "",
      "source_type": "",
      "severity": "high | medium | low"
    }
  ],
  "questions_for_other_agents": {
    "moat_agent": [],
    "growth_runway_agent": [],
    "risk_agent": [],
    "valuation_agent": [],
    "management_agent": []
  }
}
```

## 8. Markdown Report Template

```markdown
# Business Model Evidence Report: {{company_name}}

## 1. One-Sentence Business Model

{{one_sentence_business_model}}

## 2. How Does The Company Make Money?

### Finding
{{finding}}

### Evidence
| Claim | Source | Source Type | Reliability | Citation |
|---|---|---|---|---|

## 3. Who Pays, Who Uses, Who Supplies?

### Finding
{{finding}}

### Evidence
| Claim | Source | Source Type | Reliability | Citation |
|---|---|---|---|---|

## 4. Why Do Customers Pay?

### Finding
{{finding}}

### Evidence
| Claim | Source | Source Type | Reliability | Citation |
|---|---|---|---|---|

## 5. What Drives Revenue Growth?

### Finding
{{finding}}

### Evidence
| Driver | Evidence | Source | Reliability |
|---|---|---|---|

## 6. What Drives Margins And Cost Structure?

### Finding
{{finding}}

### Evidence
| Cost / Margin Driver | Evidence | Source | Reliability |
|---|---|---|---|

## 7. Recurring, Transactional, Cyclical, Or Subsidy-Driven?

{{finding}}

## 8. Fragile Points

| Fragile Point | Why It Matters | Evidence | Severity |
|---|---|---|---|

## 9. Financial Evidence Cross-Check

### Confirmed By Financials
{{confirmed}}

### Contradicted By Financials
{{contradicted}}

### Needs Further Investigation
{{needs_investigation}}

## 10. Questions For Other Agents

### Moat Agent
{{questions}}

### Growth Runway Agent
{{questions}}

### Risk Agent
{{questions}}

### Valuation Agent
{{questions}}

### Management Agent
{{questions}}

## 11. Overall Business Model Quality

Rating: {{high_medium_low_uncertain}}

Confidence: {{high_medium_low}}

Reason:
{{reason}}
```

## 9. MVP Implementation Plan

### Phase 1: Local Document Prototype

Implement:

```text
1. Load local documents.
2. Chunk documents.
3. Classify each chunk by source type.
4. Extract evidence relevant to each fixed question.
5. Generate structured JSON.
6. Generate markdown report.
```

No web crawling in Phase 1.

### Phase 2: Financial Cross-Check

Add support for reading Financial Evidence Agent output.

The Business Model Evidence Agent should compare qualitative claims against financial evidence.

Examples:

```text
Claim: business has operating leverage.
Check: operating margin trend, incremental operating margin.

Claim: business is asset-light.
Check: capex / revenue, working capital intensity.

Claim: growth is high quality.
Check: revenue growth vs OCF growth vs FCF growth.
```

### Phase 3: Source Expansion

Add:

```text
- product pages
- pricing pages
- competitor filings
- earnings call transcripts
- investor presentations
```

### Phase 4: Agent Handoff

The output should be usable by downstream agents:

```text
Right Business Agent
Moat Agent
Growth Runway Agent
Risk Agent
Valuation Agent
CIO Memo Agent
```

## 10. Acceptance Criteria

The prototype is successful if:

1. It does not produce a generic company summary.
2. It answers the fixed business-model questions.
3. Every important claim has source type and reliability label.
4. It separates official evidence from management narrative.
5. It flags uncertainty when evidence is weak.
6. It cross-checks business-model claims against financial evidence.
7. It produces both JSON and markdown outputs.
8. The output can be passed into downstream agents.

## 11. Example Command

```bash
python run_business_model_agent.py \
  --company "PDD Holdings" \
  --ticker "PDD" \
  --market "US" \
  --official-filings ./data/pdd/20f_2023.pdf ./data/pdd/20f_2024.pdf \
  --earnings-calls ./data/pdd/calls/ \
  --financial-evidence ./outputs/pdd_financial_evidence.json \
  --output-json ./outputs/pdd_business_model.json \
  --output-md ./outputs/pdd_business_model.md
```

## 12. Useful Content Preserved From The Prior Design

The prior `Business Model / Moat Agent V1` draft had several useful ideas. They are preserved here as supporting methodology, but the MVP output structure above is now the primary design.

### 12.1 Business Quality Classification

This classification belongs mostly to the downstream Right Business Agent, not the MVP evidence agent. The evidence agent may provide preliminary signals, but it should not overstate final quality.

#### Great Business

Traits:

- Very high returns on capital.
- Growth requires little incremental capital.
- Strong pricing power.
- Can withstand inflation without large new capital investment.
- Generates excess cash that can be distributed or redeployed.

Evidence needed:

- durable gross and operating margins,
- strong cash conversion,
- high and persistent ROIC,
- low incremental capital needs,
- evidence that customers accept price increases or value proposition remains strong,
- business-model evidence that competitors cannot easily copy the economics.

#### Good Business

Traits:

- Reasonable returns on capital.
- Growth requires meaningful reinvestment.
- Can compound value if reinvestment returns remain attractive.

Evidence needed:

- ROIC and incremental ROIC remain acceptable through cycles,
- reinvestment creates durable earnings power,
- balance sheet can fund growth without repeated dilution or financial stress.

#### Gruesome Business

Traits:

- Low returns on capital.
- Requires continuous reinvestment just to survive.
- Weak pricing power.
- Value-destroying over time.

Evidence needed:

- margins deteriorate with scale,
- cash conversion is weak after working-capital review,
- growth consumes heavy capital without attractive returns,
- competition or regulation prevents pricing power.

The agent should not classify a company only because one metric is high or low. Classification should be a synthesis of official financial evidence, business-model evidence, external moat validation, and competitor comparison.

### 12.2 Target Subagent Structure

The target long-term structure remains:

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

For MVP implementation, these should feed the fixed-question output schema rather than becoming the top-level report structure.

### 12.3 Official Report Reader Target Output

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

### 12.4 Research Escalation Logic

The workflow should escalate only when the previous stage leaves a valuation-relevant uncertainty unresolved.

Recommended order:

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

For fieldwork-heavy cases, the agent should first define the exact hypothesis to test, such as whether a claimed cost advantage, logistics density advantage, product-quality advantage, or customer-retention advantage is visible outside the filing.

### 12.5 PDD-Specific Initial Evidence Gaps

For PDD, the MVP should explicitly track whether evidence answers:

- What is PDD Holdings legally?
- What are Pinduoduo and Temu?
- Who pays PDD?
- What do merchants pay for?
- What do buyers/customers get?
- Are Pinduoduo and Temu reported separately?
- What parts of the flywheel are directly stated?
- What parts are only management narrative?
- What is not disclosed but necessary for investment judgment?

Known PDD gaps:

- standalone Temu economics,
- merchant profitability after ads, discounts, logistics, returns, and platform rules,
- Pinduoduo versus Temu economics,
- cohort retention and repeat-purchase quality,
- segment ROIC,
- whether scale economies are shared with customers in a self-reinforcing loop,
- competitor evidence from Alibaba, JD, Douyin, Shein, Amazon-like marketplaces, and other cross-border commerce models.

### 12.6 Candidate Learning Sources

Two user-provided business-model research materials remain tracked as candidate learning material:

- Source ID: `thread_value_investor_business_model_playbook`
- Local doc: `docs/value-investor-business-model-research-playbook.md`
- Incremental focus: filing-first ROI sequence, unit economics, decision criteria, source hierarchy.

- Source ID: `thread_gemini_business_model_due_diligence_cn`
- Local doc: `docs/gemini-business-model-due-diligence-cn-notes.md`
- Incremental focus: scuttlebutt, fieldwork, industry clusters, scale economies shared, expert networks, channel checks, compliance controls.

Status: candidate lessons only. Only approved lessons may change agent behavior.
