# Evidence Workpaper Layer Design V1

Status: primary Layer 2 design doc
Last updated: 2026-06-04

本文定义 Investment Assistant 的第二层：`Evidence Workpaper Agents / 底稿层`。

这层不是为了先写漂亮报告，而是为了形成可复用、可追溯、可交叉验证的研究底稿包。后面的 `Right Business`、`Right People`、`Right Risk`、`Right Price`、Bull/Bear 和 CIO Memo 都应该消费这些底稿，而不是直接从原始 source 或模型记忆中生成判断。

## 1. Layer Position

系统分层：

```text
Source Collectors
  ↓
Evidence Workpaper Agents / 底稿层
  ↓
Pillar Judgment Agents / 判断层
  ↓
Bull / Bear Debate
  ↓
CIO Memo
  ↓
Human Decision
```

底稿层的边界：

- 它整理事实、证据、管理层说法、系统推测、矛盾点和未知事项。
- 它可以给 conservative preliminary read，但不能做最终投资 gate。
- 它不能输出 Buy / Sell / Hold。
- 它不能把 management claim、third-party commentary 或 alternative-data signal 升级成 filing fact。
- 它的核心产物是 `pack.json`；`report.md` 只是 human-readable render。

## 2. Core Principle

```text
Source is evidence.
Question is structure.
Pack is the durable asset.
Report is a render.
Judgment is downstream.
```

底稿层不应该按 source 写成：

- Annual report says...
- Earnings call says...
- Website says...

它应该按投资问题写成：

- 这家公司真实的财务结果和会计质量如何？
- 它怎么赚钱，单位经济性是否成立？
- 生态里的客户、供应商、商家、广告主、开发者是否也受益？
- 谁控制公司，资本配置是否为外部股东创造 per-share value？
- 竞争格局和替代品说明什么？
- 未来增长从哪里来，是否已经接近饱和？
- 哪些 fragility 会破坏模型？
- Right Price 需要哪些估值假设输入？

## 3. Recommended Workpaper Set

正式采用 `8 个 Evidence Workpaper + 1 个横向 Evidence Registry`。

| Priority | Workpaper | Role |
| --- | --- | --- |
| P0 | Financial Reality & Accounting Quality Workpaper | 解释真实财务结果、会计质量、现金转化、资本效率、资产负债表、摊薄和异常项。 |
| P0 | Business Model & Unit Economics Workpaper | 解释怎么赚钱、谁付钱、价格/fee/take rate、成本结构、recurring/transactional/subsidy-driven，以及 unit economics。 |
| P0 | Customer / Supplier / Ecosystem Workpaper | 验证生态参与者是否愿意持续参与：客户、商家、供应商、广告主、开发者、内容方、物流/基础设施伙伴。 |
| P0 | Management / Governance / Capital Allocation Workpaper | 解释谁控制公司、激励是否一致、治理是否健康、资本配置和管理层沟通是否可信。 |
| P1 | Competitive Position Workpaper | 整理竞争格局、替代品、价格压力、可复制性、对手商业模式和对手经济性。 |
| P1 | Growth Runway Workpaper | 整理未来增长来源、增长约束、saturation、增长质量，以及增长是否能创造价值。 |
| P1 | Risk / Fragility / Red Flag Workpaper | 汇总会破坏业务模型或投资前提的风险、脆弱点、红旗和 kill-risk candidates。 |
| P2 | Valuation Assumption Workpaper | 准备 Right Price 需要的 normalized earnings、FCF、owner earnings、reinvestment、scenario 和 sensitivity inputs。 |
| Infra | Evidence Registry / Source Quality Auditor | 横向维护 source inventory、evidence cards、citation ids、reliability、freshness、conflicts 和 coverage gaps。 |

相对旧版本的改进：

- `Financial Evidence` 改成 `Financial Reality & Accounting Quality`，因为它不只是数字摘录，还要解释 accounting quality 和 financial reality。
- `Business Model` 改成 `Business Model & Unit Economics`，因为 fee、take rate、gross/net、subsidy 和成本结构是核心。
- 新增 `Customer / Supplier / Ecosystem`，这是验证平台型和网络型公司的关键底稿。
- `Moat Evidence` 改成 `Competitive Position`，因为 moat 是判断结果，不适合作为底稿层名称。
- `Valuation Input` 改成 `Valuation Assumption`，强调它准备 assumptions，不做 Right Price gate。

## 4. Shared Output Contract

每个 workpaper 都应该输出一个结构化 pack 和一个 markdown report。

Recommended artifacts:

```text
<workpaper_name>_pack.json
<workpaper_name>_report.md
```

共同顶层结构：

```json
{
  "agent": "",
  "version": "0.1",
  "company": {
    "name": "",
    "ticker": "",
    "market": ""
  },
  "run_context": {
    "run_id": "",
    "generated_at": "",
    "period_covered": "",
    "source_policy": ""
  },
  "summary": {
    "preliminary_read": "",
    "confidence": "high | medium | low",
    "coverage": "complete | partial | thin | not_evaluated"
  },
  "source_inventory": [],
  "question_pack": [],
  "evidence_cards": [],
  "claim_or_fact_registry": [],
  "cross_checks": [],
  "conflicts": [],
  "unknowns": [],
  "handoff_questions": [],
  "quality_flags": []
}
```

### 4.1 Source Inventory

`source_inventory` 记录进入该 workpaper 的所有 source，不管最后有没有被引用。它应优先继承 Layer 1 `source_collection_pack.json` 的 source metadata，而不是在底稿层重新判断 source provenance。

Recommended fields:

```json
{
  "source_id": "",
  "source_name": "",
  "source_type": "",
  "source_group": "official_company | official_external | market_alternative_data | third_party_opinion",
  "source_tier": 1,
  "reliability": "tier_1_official_company",
  "issuer_or_publisher": "",
  "period": "",
  "publication_date": "",
  "filing_date": "",
  "local_path": "",
  "url": "",
  "collection_status": "available | missing | partial | stale | rights_limited",
  "parse_status": "not_started | metadata_only | parsed | partial_parse | parse_failed",
  "rights_status": "",
  "sections": [],
  "notes": ""
}
```

Layer 2 may assess whether a source answers a specific investment question, but it should not silently upgrade the source tier. For example, a news article can generate a question, but it remains a Tier 4 third-party opinion until verified by Tier 1 or Tier 2 evidence.

### 4.2 Evidence Card

`evidence_cards` 是底稿层最重要的原子单位。

Recommended fields:

```json
{
  "evidence_id": "",
  "question_ids": [],
  "claim_or_fact": "",
  "evidence_type": "filing_fact | audited_number | management_explanation | management_claim | product_fact | pricing_fact | policy_fact | competitor_fact | alternative_signal | third_party_commentary | system_inference | unknown",
  "source_id": "",
  "source_type": "",
  "reliability": "",
  "citation": "",
  "excerpt": "",
  "interpretation": "",
  "confidence": "high | medium | low",
  "requires_human_review": false
}
```

### 4.3 Question Pack

`question_pack` 是每个 workpaper 的结构主线。

Recommended fields:

```json
{
  "question_id": "",
  "question": "",
  "why_it_matters": "",
  "finding": "",
  "confidence": "high | medium | low",
  "evidence_ids": [],
  "counterevidence_ids": [],
  "cross_check_ids": [],
  "open_issues": [],
  "handoff_questions": []
}
```

### 4.4 Claim Or Fact Registry

`claim_or_fact_registry` 让后续 agent 能看到每个重要判断的来源等级。

Recommended labels:

- `filing_fact`
- `audited_number`
- `calculated_metric`
- `management_explanation`
- `management_claim`
- `product_fact`
- `pricing_fact`
- `policy_fact`
- `competitor_fact`
- `alternative_signal`
- `third_party_commentary`
- `system_inference`
- `unknown`

Core rule:

```text
management_claim cannot masquerade as fact.
alternative_signal cannot become final evidence without triangulation.
official filing wins when sources conflict.
```

## 5. Evidence Registry / Source Quality Auditor

`Evidence Registry / Source Quality Auditor` 是横向基础设施，不是一个投资判断 agent。

Purpose:

- 统一维护 source inventory。
- 给每个 source 和 evidence card 分配 stable id。
- 记录 source reliability、freshness、coverage 和 rights constraints。
- 发现同一 claim 在不同 workpaper 之间的重复、冲突和引用不一致。
- 标记哪些 source 只是 lead，哪些 source 可以支持 final workpaper evidence。

Suggested outputs:

- `evidence_registry.json`
- `source_inventory.json`
- `source_quality_audit.md`

Important checks:

- 是否每个重要 finding 都有 evidence card。
- 是否有 unsupported claim。
- 是否有 source reliability 被错误提升。
- 是否有 stale source。
- 是否有 conflicting evidence 没有进入 `conflicts`。
- 是否有 report prose 中出现但 pack 中没有的 claim。

## 6. Workpaper Designs

### 6.1 Financial Reality & Accounting Quality Workpaper

Purpose:

解释公司的真实财务表现和会计质量。它是底稿层的模板。

Primary questions:

1. 收入增长来自哪里？
2. 毛利率和经营利润率有没有变化？
3. 利润是否真的变成现金？
4. 现金流是否靠真实经营能力，而不是账期、押金、应付或一次性项目撑起来？
5. 增长需要消耗多少资本？
6. 资产负债表有没有压力？
7. 股权激励和摊薄是否侵蚀股东回报？
8. 会计政策、收入确认、gross/net、capitalization、impairment 是否有红旗？
9. 最近趋势是改善、稳定还是恶化？

Primary sources:

- 10-K / 20-F / annual report
- 10-Q / 6-K / interim report
- earnings release
- XBRL / inline XBRL
- financial statements
- footnotes
- MD&A / OFR
- auditor report / ICFR / CAM
- material-event filings

Core outputs:

- `financial_reality_pack.json`
- `financial_reality_report.md`
- official fact table
- metrics table
- diagnostic question answers
- abnormality investigations
- accounting quality flags
- financial cross-checks for other workpapers

Hard exclusions:

- no buy / sell / hold
- no DCF
- no market-price-dependent expected return
- no margin of safety
- no third-party database as source of truth

Downstream handoff:

- Business Model: test operating leverage, cash generation, asset-light / asset-heavy claims.
- Management: test capital allocation, dilution, SBC, buyback/dividend behavior.
- Growth: test whether growth converts to profit and cash.
- Risk: test balance-sheet, accounting, cash-transfer, working-capital and dilution risks.
- Valuation Assumption: provide normalized earnings, FCF, owner-earnings inputs.

### 6.2 Business Model & Unit Economics Workpaper

Purpose:

解释公司怎么赚钱、为什么能赚钱、谁付钱、谁使用、谁供给、收入和成本如何形成，以及 unit economics 是否有证据支持。

Primary questions:

1. How does the company make money?
2. Who pays, who uses, and who supplies?
3. What exactly is being paid for?
4. Is revenue advertising, commission, transaction fee, subscription, licensing, product sale, service, financing, or other?
5. How does revenue recognition work?
6. What drives revenue growth: users, volume, ARPU, price, take rate, ad load, mix, geography, new products?
7. What drives gross margin and operating margin?
8. Is the model recurring, transactional, cyclical, or subsidy-driven?
9. Which parts of the model are fragile?
10. What does Financial Reality confirm or contradict?

Primary sources:

- revenue recognition notes
- segment / geography / product disclosure
- annual report business description
- product pages
- pricing pages
- fee schedules
- merchant terms / seller terms
- platform policies
- earnings call management explanation
- investor presentation / investor day
- competitor filings and product/pricing pages
- financial reality pack

Core outputs:

- `business_model_unit_economics_pack.json`
- `business_model_unit_economics_report.md`
- revenue stream map
- payer / user / supplier map
- pricing and fee evidence cards
- unit-economics proxy map
- subsidy / discount / marketing dependency review
- financial cross-checks
- handoff questions to Competitive Position, Growth, Risk, Management, and Valuation Assumption

Important boundary:

This workpaper can say "the model appears recurring / transaction-driven / subsidy-sensitive based on evidence." It should not say "this is a high-quality business" as a final gate. That belongs to Right Business.

### 6.3 Customer / Supplier / Ecosystem Workpaper

Purpose:

验证生态里的其他参与者是否也有理由持续参与。它补足 financial filings 和公司叙事的盲点。

This is the most important addition to the previous 7-workpaper list.

Primary questions:

1. Who are the key ecosystem participants?
2. What problem does the company solve for each participant?
3. Does each participant have a strong reason to stay?
4. Are customers satisfied enough to repeat?
5. Are suppliers, merchants, developers, content partners, advertisers, publishers, logistics partners, or infrastructure partners economically healthy?
6. Does one side of the ecosystem subsidize another side?
7. Are platform rules, fees, penalties, return policies, data policies, or ad systems creating hidden fragility?
8. Are complaints isolated, cyclical, or structural?
9. What evidence contradicts management's ecosystem narrative?

Primary sources:

- product pages and product flows
- customer pricing / membership / subscription pages
- merchant / seller / supplier terms
- platform policy pages
- fee schedules
- returns / refunds / shipping policy
- app store reviews and ratings
- customer support / complaint sources
- merchant forums and supplier complaints
- developer / publisher / advertiser docs
- official regulator / consumer-protection sources
- alternative data signals
- interviews or public Q&A, with reliability labels

Core outputs:

- `ecosystem_evidence_pack.json`
- `ecosystem_evidence_report.md`
- participant map
- value proposition by participant
- ecosystem health evidence cards
- merchant / supplier economics leads
- customer repeat / satisfaction signals
- platform policy fragility map
- evidence limitations and bias warnings

Important boundary:

This workpaper can use lower-reliability sources, but it must label them as pattern evidence or lead evidence. It cannot turn anonymous forum posts, reviews, or social posts into final facts.

Downstream handoff:

- Business Model: validate who pays and why.
- Competitive Position: test switching costs, network effects, supply advantages, and product parity.
- Growth: test whether ecosystem can support future expansion.
- Risk: flag platform, supplier, customer, regulatory, and reputation fragility.

### 6.4 Management / Governance / Capital Allocation Workpaper

Purpose:

整理控制权、治理结构、激励、资本配置、管理层沟通质量和 promise-vs-outcome evidence。

Primary questions:

1. Who controls the company?
2. What are the voting, economic, VIE, board, or founder-control structures?
3. Are incentives aligned with outside shareholders and per-share value?
4. What is the capital allocation record?
5. How has management used cash: reinvestment, buybacks, dividends, acquisitions, financing, cash build?
6. Is management communication direct, specific, and consistent?
7. Do management promises later match financial and operating results?
8. Are there governance, audit, related-party, compensation, turnover, integrity, or disclosure red flags?
9. What does Financial Reality confirm or contradict about management's capital allocation narrative?

Primary sources:

- proxy / AGM / shareholder meeting materials
- 20-F / 10-K governance and ownership sections
- beneficial ownership and voting power disclosures
- compensation and SBC disclosures
- related-party transaction disclosures
- board / committee / auditor disclosures
- material-event filings
- earnings calls
- investor day / conference Q&A
- shareholder letters
- executive interviews and podcasts
- financial reality pack

Core outputs:

- `management_governance_capital_allocation_pack.json`
- `management_governance_capital_allocation_report.md`
- control map
- incentive map
- capital allocation ledger
- communication claim registry
- promise-vs-outcome tracker
- governance and integrity red flags
- handoff questions to Right People, Risk, and Valuation Assumption

Important boundary:

This workpaper is not `Right People`. It prepares evidence for Right People. It can flag possible alignment or governance concerns, but the final gate belongs to the judgment layer.

### 6.5 Competitive Position Workpaper

Purpose:

整理竞争格局、替代品、对手商业模式、对手产品/价格、成本结构差异和可复制性证据。它避免在底稿层直接使用 "moat" 作为结论。

Primary questions:

1. Who are the direct and indirect competitors?
2. What jobs-to-be-done overlap with the target company?
3. How do competitors make money?
4. How do competitor pricing, fees, product quality, delivery, service, distribution, or bundling compare?
5. Are the target company's advantages observable in product, price, cost, scale, distribution, data, brand, regulation, ecosystem, or capital intensity?
6. Are advantages durable, eroding, or unproven?
7. What evidence would disconfirm a moat hypothesis?
8. Are competitors gaining share, copying features, compressing price, or forcing higher spending?

Primary sources:

- competitor annual reports / 10-K / 20-F
- competitor earnings releases / calls
- competitor investor presentations
- competitor product pages
- competitor pricing / fee / policy pages
- app store / search / web rank comparative signals
- fixed basket e-commerce observations where relevant
- management comments about competition, labeled as management claims
- regulator or industry filings where available

Core outputs:

- `competitive_position_pack.json`
- `competitive_position_report.md`
- competitor map
- battlefield analysis
- competitor business-model comparison
- product / pricing / policy comparison
- moat hypothesis evidence and counterevidence
- competitive pressure map
- downstream routing to Business Model, Growth, Risk, and Right Business

Important boundary:

This workpaper should not determine whether competitors are good investments. It only asks what competitors reveal about the target company's business model, position, growth, risk, and valuation assumptions.

### 6.6 Growth Runway Workpaper

Purpose:

整理未来增长来源、增长质量、增长约束和 saturation risk。它不是简单 TAM report，也不是乐观预测。

Primary questions:

1. What are the current growth drivers?
2. Which growth drivers are proven, emerging, speculative, or exhausted?
3. Is growth from user count, volume, ARPU, price, take rate, ad load, geographic expansion, new products, market share, or mix?
4. Does growth require subsidies, aggressive marketing, capex, working capital, regulation arbitrage, or partner economics deterioration?
5. Is the market saturated or still underpenetrated?
6. Are competitors or regulation compressing future runway?
7. Does growth translate into profit, cash flow, and return on capital?
8. What assumptions must be true for long-term growth?

Primary sources:

- business model workpaper
- financial reality pack
- ecosystem workpaper
- competitive position pack
- segment / geography disclosures
- product launch history
- investor presentations and investor day
- market statistics from reliable sources, where source rights allow
- alternative demand signals, with confidence limits

Core outputs:

- `growth_runway_pack.json`
- `growth_runway_report.md`
- growth driver map
- growth quality evidence
- saturation / penetration evidence
- reinvestment requirement evidence
- geographic / product expansion evidence
- growth-to-profit and growth-to-cash cross-checks
- handoff questions to Right Business, Right Price, and Risk

Important boundary:

This workpaper can prepare scenario inputs, but Right Price owns valuation judgment and required return.

### 6.7 Risk / Fragility / Red Flag Workpaper

Purpose:

汇总并专项扫描可能破坏业务模型、财务结果、管理层可信度、增长路径或估值假设的风险。

This workpaper should be an aggregator plus specialist scanner.

Primary questions:

1. What are the business-model fragile points?
2. What are the financial, accounting, cash-flow, balance-sheet, dilution, or working-capital risks?
3. What are the governance, control, related-party, audit, integrity, or capital-allocation red flags?
4. What regulatory, legal, tax, customs, data, consumer-protection, antitrust, labor, product-safety, or geopolitical risks matter?
5. What customer, supplier, platform, traffic-acquisition, merchant, developer, advertiser, or infrastructure dependencies matter?
6. Which risks are temporary, structural, existential, or impossible to evaluate?
7. Which risks are kill-risk candidates?
8. What evidence would reduce or increase each risk?

Primary sources:

- risk factors
- legal proceedings
- regulatory filings and official regulator pages
- material-event filings
- financial reality red flags
- business model fragile points
- ecosystem complaints and policy evidence
- competitive pressure evidence
- management governance red flags
- public voice and alternative data as lead evidence only

Core outputs:

- `risk_fragility_red_flag_pack.json`
- `risk_fragility_red_flag_report.md`
- risk inventory
- severity and evidence strength labels
- kill-risk candidate list
- risk mitigants
- unknowns and monitoring triggers
- downstream questions to Right Risk, Right Business, Right People, and Right Price

Important boundary:

This workpaper can rank preliminary severity. It should not decide whether the risk is "appropriately compensated." That belongs to Right Risk and Right Price.

### 6.8 Valuation Assumption Workpaper

Purpose:

准备 Right Price 所需的估值假设输入。它不是最终 valuation call。

Primary questions:

1. What normalized earnings, free cash flow, and owner earnings inputs are supportable?
2. What adjustments are needed for cash, debt, SBC, leases, working capital, one-time items, and restricted cash?
3. What reinvestment rate and capital intensity assumptions are supported?
4. What growth assumptions are consistent with the Growth Runway workpaper?
5. What margin assumptions are consistent with Business Model, Financial Reality, and Competitive Position?
6. What risk adjustments are required?
7. What scenario drivers matter most?
8. What assumptions are unsupported and need human review?

Primary sources:

- financial reality pack
- business model workpaper
- growth runway pack
- competitive position pack
- risk workpaper
- management / capital allocation workpaper
- market price and market data only when the pipeline explicitly enters Right Price preparation

Core outputs:

- `valuation_assumption_pack.json`
- `valuation_assumption_report.md`
- normalized earnings bridge
- FCF / owner earnings bridge
- reinvestment and capital intensity assumptions
- scenario driver table
- sensitivity map
- unsupported assumptions and human review flags

Important boundary:

This workpaper should not output Buy / Sell / Hold. It should not claim margin of safety by itself. Right Price owns expected return, margin of safety, and price attractiveness.

## 7. Inter-Workpaper Dependencies

Recommended dependency map:

```text
Financial Reality
  -> Business Model
  -> Management / Capital Allocation
  -> Growth Runway
  -> Risk
  -> Valuation Assumption

Business Model
  -> Customer / Supplier / Ecosystem
  -> Competitive Position
  -> Growth Runway
  -> Risk
  -> Valuation Assumption

Customer / Supplier / Ecosystem
  -> Business Model
  -> Competitive Position
  -> Growth Runway
  -> Risk

Management / Governance / Capital Allocation
  -> Risk
  -> Valuation Assumption
  -> Right People

Competitive Position
  -> Growth Runway
  -> Risk
  -> Right Business

Growth Runway
  -> Valuation Assumption
  -> Right Business
  -> Right Price

Risk / Fragility / Red Flag
  -> Right Risk
  -> Right Business
  -> Right Price

Valuation Assumption
  -> Right Price
```

## 8. Handoff To Judgment Layer

### Right Business

Primary inputs:

- Financial Reality & Accounting Quality
- Business Model & Unit Economics
- Customer / Supplier / Ecosystem
- Competitive Position
- Growth Runway
- Risk / Fragility / Red Flag

Question:

```text
Is this a business we can understand, and does it have attractive economics through a cycle?
```

### Right People

Primary inputs:

- Management / Governance / Capital Allocation
- Financial Reality & Accounting Quality
- Risk / Fragility / Red Flag
- Business Model & Unit Economics when control or incentives affect the model

Question:

```text
Are the people in control likely to increase per-share intrinsic value while treating outside owners fairly?
```

### Right Risk

Primary inputs:

- Risk / Fragility / Red Flag
- Financial Reality & Accounting Quality
- Business Model & Unit Economics
- Customer / Supplier / Ecosystem
- Management / Governance / Capital Allocation
- Competitive Position

Question:

```text
Are the risks understandable, survivable, and appropriately compensated?
```

### Right Price

Primary inputs:

- Valuation Assumption
- Financial Reality & Accounting Quality
- Growth Runway
- Risk / Fragility / Red Flag
- Right Business
- Right People
- Right Risk

Question:

```text
Is the current price attractive relative to conservative intrinsic value and expected return?
```

## 9. MVP Build Order

Recommended order:

1. `Financial Reality & Accounting Quality`: already closest to production; keep as template.
2. `Business Model & Unit Economics`: current Q1-Q9 prototype should be evolved into this.
3. `Customer / Supplier / Ecosystem`: new workpaper; important for PDD/Temu and other platform companies.
4. `Management / Governance / Capital Allocation`: convert current Right People / Management Communication work into pure evidence workpaper first.
5. `Risk / Fragility / Red Flag`: start as an aggregator over Financial, Business Model, Ecosystem, and Management.
6. `Competitive Position`: connect competitor filings and product/pricing evidence.
7. `Growth Runway`: build after Business Model, Ecosystem, Competitive Position have enough evidence.
8. `Valuation Assumption`: build last, after core evidence workpapers are stable.
9. `Evidence Registry / Source Quality Auditor`: start lightweight immediately, then strengthen as packs standardize.

Rationale:

- The first four workpapers create the minimum useful evidence base.
- Risk can start as a cross-workpaper aggregation layer.
- Competitive Position and Growth Runway need more source diversity, so they should follow after Business Model and Ecosystem stabilize.
- Valuation Assumption should not pull valuation logic back into Financial Evidence.

## 10. Naming Standard

Preferred artifact names:

| Workpaper | Pack | Report |
| --- | --- | --- |
| Financial Reality & Accounting Quality | `financial_reality_pack.json` | `financial_reality_report.md` |
| Business Model & Unit Economics | `business_model_unit_economics_pack.json` | `business_model_unit_economics_report.md` |
| Customer / Supplier / Ecosystem | `ecosystem_evidence_pack.json` | `ecosystem_evidence_report.md` |
| Management / Governance / Capital Allocation | `management_governance_capital_allocation_pack.json` | `management_governance_capital_allocation_report.md` |
| Competitive Position | `competitive_position_pack.json` | `competitive_position_report.md` |
| Growth Runway | `growth_runway_pack.json` | `growth_runway_report.md` |
| Risk / Fragility / Red Flag | `risk_fragility_red_flag_pack.json` | `risk_fragility_red_flag_report.md` |
| Valuation Assumption | `valuation_assumption_pack.json` | `valuation_assumption_report.md` |
| Evidence Registry | `evidence_registry.json` | `source_quality_audit.md` |

Migration note:

- Existing `financial_report_pack.json` can remain until the financial layer is renamed.
- Existing `business_model_evidence.json` and `business_model_evidence_report.md` can remain during MVP, but the conceptual target is `business_model_unit_economics_pack.json`.

## 11. Existing Repo Mapping

Current related docs:

- `docs/investment-assistant-holistic-design-v1.md`
- `docs/financial-agents-v1.md`
- `docs/business-model-unit-economics-workpaper-design-v1.md`
- `docs/business-model-moat-agent-v1.md`
- `docs/business-model-data-source-coverage-tracker-v1.md`
- `docs/evidence-and-communication-extraction-design-v1.md`
- `docs/management-communication-agent-design-v1.md`
- `docs/right-people-agent-v1.md`
- `docs/alternative-data-agent-v1.md`
- `docs/valuation-methodology-v1.md`

Current implementation anchors:

- Financial workpaper family: `src/stock_research/report_pack.py`, `src/stock_research/reports/`, `src/stock_research/material_events/`
- Business Model prototype: `src/stock_research/qualitative/business_model_evidence.py`
- Official events / transcript source handling: `src/stock_research/qualitative/official_events.py`
- Alternative data signals: `src/stock_research/alternative_data/`
- Scaffold wiring: `src/stock_research/agents/v1.py`, `src/stock_research/graph.py`, `src/stock_research/storage.py`

## 12. Acceptance Criteria

Layer 2 is working if:

1. Each workpaper is organized by fixed investment questions, not source summaries.
2. Every important finding has traceable evidence cards.
3. Source reliability is explicit.
4. Facts, management claims, third-party comments, alternative signals, inferences, and unknowns are separated.
5. `pack.json` contains all important claims that appear in `report.md`.
6. Each workpaper outputs handoff questions for downstream agents.
7. Judgment agents can consume packs without going back to raw source unless they need audit.
8. No workpaper outputs Buy / Sell / Hold.
9. Valuation assumptions do not leak back into Financial Reality.
10. Weak evidence produces uncertainty, not confident prose.

## 13. Open Questions

- Should the repo rename existing artifacts immediately, or keep current names until each workpaper is implemented?
- Should `Evidence Registry` be built as a standalone agent, shared library, or post-run auditor?
- Should `Customer / Supplier / Ecosystem` be one workpaper for all companies, or have company-type templates for platform, SaaS, marketplace, bank, insurer, manufacturer, and biotech?
- Should `Risk / Fragility / Red Flag` run after every workpaper or only at the end of Layer 2?
- Which workpapers are mandatory before Right Business is allowed to run?
- Which sources require human approval because of licensing, scraping, privacy, retention, or source-rights constraints?

## 14. Decision

Adopt the following Layer 2 design as the working target:

```text
Evidence Registry / Source Quality Auditor

1. Financial Reality & Accounting Quality Workpaper
2. Business Model & Unit Economics Workpaper
3. Customer / Supplier / Ecosystem Workpaper
4. Management / Governance / Capital Allocation Workpaper
5. Competitive Position Workpaper
6. Growth Runway Workpaper
7. Risk / Fragility / Red Flag Workpaper
8. Valuation Assumption Workpaper
```

This replaces the older informal seven-workpaper list:

```text
Financial Evidence
Business Model Evidence
Management / Governance Evidence
Risk / Fragility Evidence
Moat / Competition Evidence
Growth Runway Evidence
Valuation Input
```

The old list had the right direction, but the new list has cleaner boundaries, less judgment leakage, and a stronger external ecosystem validation layer.
