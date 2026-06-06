# Financial Agents V1

Status: Active design document.  
Primary methodology source: `docs/references/value-investor-financial-reports-sec-reading-method.zh.md`.

Implementation design: `docs/financial-report-reading-system-design-v1.md`.

Financial extraction instruction: `docs/financial-extraction-agent-instruction-v1.md`.

Financial metrics instruction: `docs/financial-metrics-agent-instruction-v1.md`.

This document defines how the financial-report side of Investor Assistant should read official filings, extract numbers, calculate financial-quality metrics, and produce the Financial Results Report.

## 1. Goal

The Financial Agents do not decide buy/sell. Their job is to turn trusted official disclosures into a source-linked financial evidence package.

The core questions are:

- 收入增长来自哪里？
- 毛利率和经营利润率有没有变化？
- 利润是否真的变成现金？
- 现金流是否靠真实经营能力，而不是账期、押金、应付或一次性项目撑起来？
- 增长需要消耗多少资本？
- 资产负债表有没有压力？
- 股权激励和摊薄是否侵蚀股东回报？

Valuation questions such as EV, owner earnings yield, FCF yield, estimated return, DCF, and margin of safety belong to the Valuation Agent. The Financial Metrics Agent only prepares the financial-quality inputs.

## 2. Source Hierarchy

For financial numbers, official disclosures are the source of truth.

| Source type | Use | Source-of-truth status |
| --- | --- | --- |
| SEC filing / exchange filing | Financial statements, risks, governance, material events | Yes |
| Company IR annual report / official announcement | Cross-validation and official supplemental reading | Yes, but regulator filing wins if there is conflict |
| XBRL / inline XBRL | Structured number extraction | Yes, but key numbers should be reconciled to tables/text where possible |
| Official earnings release / official investor presentation | Quarterly trend update, non-GAAP bridge, management short commentary | Useful for trend update; does not replace annual report |
| Third-party database / media / AI summary | Fast locator or sanity check | No; cannot be final evidence for financial numbers |

## 3. File Reading Scope

The reading anchor is always the annual filing:

- U.S. domestic issuer: Form 10-K.
- Foreign private issuer such as PDD: Form 20-F.
- HK / China companies: official annual report from exchange or company IR.

Other files are not a second main line. They are update or material-event radar.

| File | How to read | Enters final Financial Results Report when |
| --- | --- | --- |
| Annual report / 10-K / 20-F | Main reading, must be deep enough to establish the financial story | Always |
| Latest 10-Q / quarterly 6-K | Trend update | Revenue, margin, cash flow, risk, guidance, or management framing changes the annual view |
| 8-K / 6-K current report | Material-event scan | Acquisition, financing, debt, restatement, auditor change, management change, major contract, impairment, regulation, or similar event changes risk/value |
| Proxy / AGM materials | Governance scan | Incentives, control, related-party transactions, board structure, or vote results affect long-term value |
| S-1 / F-1 / prospectus | Conditional historical source | Company is newly listed, is raising capital, or original business/VIE/capital-use promises matter |
| Official earnings release / investor presentation | Official attachment scan | It conflicts with filings, provides a key KPI, or changes trend interpretation |

Rule: collection can be broad, but report inclusion must be narrow.

Earnings call transcripts are outside this method. They belong to the Official Event Transcript Agent because they involve management tone, Q&A pressure, and prepared-remark interpretation.

## 4. Agent Responsibilities

### Company Resolver

Confirms identity:

- legal name,
- ticker,
- market and exchange,
- CIK or filing identifier,
- listing type,
- reporting currency,
- trading currency,
- official IR URL and filing systems.

### Source Discovery / Document Collector

Discovers official sources and caches documents locally.

It should classify files into:

- annual report,
- quarterly update,
- official earnings attachment,
- current report,
- proxy / AGM,
- prospectus,
- governance / management / auditor / financing material-event file,
- low-value wrapper or helper file.

### Financial Extraction Agent

Extracts official facts only from approved financial extraction documents. It should not use third-party mirrors as source of truth.

Detailed field list, extraction order, output schema, and review flags are defined in `docs/financial-extraction-agent-instruction-v1.md`.

It should now output hard financial worksheet coverage, not only headline facts:

- revenue component bridge,
- expense bridge,
- cost subcomponent detail,
- below-operating bridge,
- working-capital bridge,
- cash-availability bridge,
- shares / SBC / capital-return bridge.

### IR / Official PDF Cross-Validation Agent

Cross-checks key extracted facts against official annual-report PDFs or other approved official company reports.

### Financial Verification Agent

Compares duplicate official facts and records conflicts. Material conflicts around 2% or more should be flagged for human review.

### Financial Metrics Agent

Calculates financial-quality metrics from extracted official facts.

Detailed formula families, annual-report anchoring, warning flags, and output schema are defined in `docs/financial-metrics-agent-instruction-v1.md`.

It owns:

- growth quality,
- margin profile,
- cash conversion and working-capital quality,
- capital intensity,
- owner earnings proxy amount,
- SBC and dilution burden,
- balance-sheet risk,
- ROIC / incremental ROIC proxy.

It does not own:

- enterprise value,
- owner earnings yield,
- FCF yield,
- estimated return,
- DCF,
- margin of safety.

Those belong to the Valuation Agent.

### Diagnostic Rules Agent

Turns calculated metric families into financial-quality questions, warning flags, and follow-up checks.

It owns the ranked financial-quality question layer, metric-to-question mapping, red-flag wording, missing evidence, follow-up checks, and annual-baseline versus latest-quarter diagnostic status.

It does not calculate formulas. Metrics come from the Financial Metrics Agent.

### Financial Evidence Investigation Skill

When diagnostics raise a question, this Skill goes back to official reports and tries to explain the abnormal data.

Detailed rules are defined in `docs/financial-evidence-investigation-skill-v1.md`.

It owns:

- searching relevant official report sections for explanations.
- separating official file facts, management explanations, data-based inference, and unknowns.
- turning follow-up checks into concise evidence notes.

It must not:

- calculate or change metrics.
- invent company-specific KPIs.
- use earnings-call transcripts.
- use media, sell-side, forum, or model-memory facts as financial-report evidence.
- present inference as fact.

### Material Event Scanner

Scans non-core official filings and exhibits without making them a second research main line.

Implemented in `src/stock_research/material_events/scanner.py`.

It promotes only material event types:

- accounting reliability / restatement / ICFR.
- auditor change.
- debt, financing, convertible notes, or offerings.
- management or board change.
- governance, control, proxy, or meeting actions.
- share plan or dilution events.
- capital allocation.
- acquisition, divestiture, impairment, restructuring, legal, or regulatory events.

It does not summarize every 6-K / 8-K / proxy / prospectus. If no event is detected, the final report should say the scan found no material event and move on.

### Financial Report Pack Builder

Builds `financial_report_pack.json`, the structured input for report writing.

Implemented in `src/stock_research/report_pack.py`.

The report-writing layer may summarize this pack, but must not:

- recalculate numbers.
- change formulas.
- invent facts.
- use third-party data as financial source of truth.
- pull earnings-call transcript content into the financial report method.
- include market-price-dependent valuation metrics or valuation commentary.
- include Yahoo / Google Finance / third-party financial database facts as core financial evidence.

Valuation / Right Price may consume the financial report pack, but valuation outputs should remain outside `financial_report_pack.json`.

### Financial Results Report Agent

Writes the Financial Results Report and links to the data-linkage appendix. The report should be readable, selective, and evidence-linked. It should not include Valuation Agent output, market/yield inputs, or third-party financial database sanity checks.

## 5. Core Fields To Extract

Each annual reading should try to extract these fields when officially disclosed. Missing fields stay missing; the system should not replace them with third-party estimates.

| Category | Fields | Use |
| --- | --- | --- |
| Income statement | Revenue, cost of revenue, gross profit, operating income, pretax income, net income | Growth, gross margin, operating margin, net margin |
| Cash flow | Operating cash flow, capital expenditures, free cash flow | Cash conversion and capital need |
| Balance sheet | Cash and equivalents, short-term investments, restricted cash, debt, total assets, total liabilities | Net cash, liquidity, balance-sheet pressure |
| Expense structure | Sales and marketing, R&D, G&A, fulfillment/payment/server/company-specific costs | Whether growth is organic or bought with spending |
| Dilution | SBC, basic shares, diluted shares, ADS count, share plan, buyback | Shareholder dilution and real per-share economics |
| Accounting estimates | D&A, impairment, fair value change, deferred tax, valuation allowance | Earnings quality and accounting judgment |
| Company KPIs | GMV, active buyers, orders, take rate, merchant count, DAU/MAU, ARR, etc. | Revenue-source explanation, only when officially disclosed |

The extractor should explicitly preserve bridge-ready fields when officially disclosed:

- Revenue components YoY/QoQ inputs: `online_marketing_services_revenue`, `transaction_services_revenue`, and other official revenue lines.
- Expense bridge inputs: `cost_of_revenue`, `gross_profit`, `sales_and_marketing_expense`, `research_and_development_expense`, `general_and_administrative_expense`, `operating_income`.
- Cost subcomponents: `fulfillment_expense`, `payment_processing_expense`, `server_and_bandwidth_costs`, `merchant_support_costs`, `platform_governance_costs`, `logistics_expense`.
- Below-operating bridge: `investment_income`, `interest_income`, `interest_expense`, `foreign_exchange_gain_loss`, `other_income_net`, `tax_expense`, `equity_method_income`.
- Working-capital bridge: receivables, prepayments, accounts payable, payable to merchants, accrued expenses, merchant deposits, deferred revenue, and cash-flow-statement changes.
- Cash availability: cash, restricted cash, short-term investments, long-term investments / investment portfolio, and text-evidence needs for VIE/remittance restrictions.
- Shares/SBC/capital return: SBC, diluted shares, ADS/ordinary-share structure, buybacks, dividends, equity-plan authorization.

## 6. Core Metrics

Metrics should be organized by question, not as a random ratio list.

| Question | Core metrics | What to check when abnormal |
| --- | --- | --- |
| Is growth high quality? | Revenue growth, operating income growth, FCF growth, incremental operating margin, incremental FCF margin | MD&A, segment notes, revenue recognition, pricing/volume/take-rate changes |
| Are margins improving? | Gross margin, operating margin, net margin, FCF margin | Competition, subsidies, fulfillment, payment, marketing, merchant support, R&D, one-time investment |
| Does profit become cash? | CFO / net income, FCF / net income, working-capital change | Receivables, inventory, payables, merchant deposits, accrued expenses, deferred revenue, one-time cash items |
| Does growth consume capital? | CapEx / revenue, CapEx / CFO, ROIC proxy, incremental ROIC proxy | Maintenance vs growth CapEx, infrastructure needs, asset growth |
| Do shareholders benefit? | SBC / revenue, SBC / CFO, SBC / net income, diluted share growth | Buyback offset, share plans, per-share economics |
| Is the balance sheet safe? | Net cash, debt / cash, current assets / current liabilities, liabilities / assets | Restricted cash, maturity schedule, convertible debt, lease liabilities |

Cash conversion rule:

- `CFO / net income >= 1.0` can be a useful heuristic.
- It is not a hard pass/fail threshold.
- Strong CFO must still be checked against working-capital sources such as merchant payables, accrued expenses, deposits, deferred revenue, inventory, and receivables.

Owner earnings rule:

```text
Owner Earnings Proxy = Operating Cash Flow - Share-Based Compensation - Maintenance CapEx Proxy
```

V1 may use:

```text
Maintenance CapEx Proxy ~= Depreciation and Amortization
```

This must be labelled as a proxy, not final economic truth.

## 7. Reading Workflow

```text
1. Confirm company identity: ticker, CIK, listing venue, FPI/US issuer type.
2. Discover official sources: SEC / exchange / company IR.
3. Classify documents: annual, quarterly update, current report, proxy, prospectus, official earnings attachment.
4. Extract core fields from annual report / 10-K / 20-F.
5. Calculate growth quality, margins, cash conversion, capital intensity, balance-sheet pressure, SBC dilution.
6. Run diagnostic rules to decide which questions are answered, partial, or need follow-up.
7. For abnormal diagnostics, run the Financial Evidence Investigation Skill on MD&A, footnotes, segment disclosure, tax, debt, cash flow, audit report, and ICFR.
8. Use latest 10-Q / quarterly 6-K to update trends.
9. Scan 8-K / 6-K, proxy / AGM, and S-1 / F-1 only for material events.
10. Run verification and human-review rules.
11. Output a source-linked Financial Results Report.
```

## 8. Report Output

The Financial Results Report should contain:

1. Company one-line understanding.
2. Core financial judgment: revenue, margins, cash flow, CapEx, balance sheet.
3. Earnings quality: cash conversion, working capital, non-GAAP, one-time adjustments.
4. Key risks that affect valuation or long-term operations.
5. Material-event scan: only meaningful changes from quarterly/current/proxy/prospectus files.
6. Evidence and number lineage.
7. Open questions and review items.

When an abnormal metric is discussed, the report must separate:

- official file facts.
- management explanations found in official reports.
- inference based on current data.
- unknowns that remain unresolved.

If the material-event scan finds nothing meaningful, the report may say:

> Recent 8-K / 6-K, proxy / AGM materials, and related official disclosures were scanned; no material item was found that changes the current financial read.

## 9. Human Review Rules

The system should flag or stop when:

- key official sources conflict by about 2% or more,
- a key number cannot be traced to an official filing or official report,
- a lower-tier source is used for an important claim,
- formula or metric definitions change,
- non-GAAP adjustments recur and should no longer be treated as one-time,
- valuation assumptions are required, such as excess cash, maintenance CapEx, or investment-portfolio haircut,
- auditor change, restatement, material weakness, or non-reliance appears.

Rounding differences may be accepted when clearly explained.

## 10. Boundaries

Financial Agents produce evidence, calculations, and review flags.

They do not:

- make buy/sell recommendations,
- prove moat durability,
- judge management quality,
- interpret customer happiness,
- produce final valuation or margin-of-safety conclusions.

Those tasks belong to downstream agents.
