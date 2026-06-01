# Financial Extraction Agent Instruction V1

Status: Active instruction.  
Parent design: `docs/financial-agents-v1.md`.  
Methodology reference: `docs/references/value-investor-financial-reports-sec-reading-method.zh.md`.

This instruction defines what the Financial Extraction Agent should extract from official financial reports and how it should extract it.

## 1. Goal

The Financial Extraction Agent turns official financial disclosures into source-linked facts. It does not decide whether the company is good, cheap, or investable.

Its job is to answer one question:

> What official numbers and definitions are needed so the Financial Metrics Agent can judge growth quality, margin quality, cash conversion, capital intensity, balance-sheet pressure, dilution, and accounting quality?

Missing fields must stay missing. Do not fill financial facts from memory, third-party databases, media, or model inference.

## 2. Source Scope

Use only approved official sources for financial facts:

- Annual report / Form 10-K / Form 20-F.
- Latest 10-Q / quarterly 6-K or official interim report.
- Official earnings release or official financial-results exhibit.
- Official company annual-report PDF or exchange filing, when used for cross-validation.
- XBRL / inline XBRL facts, when available.

Do not extract financial facts from:

- Third-party financial databases.
- Media articles.
- Analyst reports.
- Earnings call transcripts.
- AI summaries.
- Social media, forums, videos, comments, or alternative data.

Those sources can be used by other agents as qualitative evidence, but they cannot become financial source-of-truth facts.

## 3. Document Treatment

Classify documents before extraction:

| Document type | Extraction role |
| --- | --- |
| Annual report / 10-K / 20-F | Primary annual extraction source |
| Latest 10-Q / quarterly 6-K / interim report | Trend update source |
| Official earnings release / financial tables | Quarterly extraction source and non-GAAP bridge source |
| 8-K / 6-K current report without financial tables | Material-event scan, not routine financial extraction |
| Proxy / AGM materials | Governance scan, not routine financial extraction |
| S-1 / F-1 / prospectus | Conditional historical extraction only when IPO origin, VIE, share structure, or original KPI definitions matter |

Collection can be broad, but financial extraction should be narrow.

## 4. Core Annual Facts To Extract

Each annual reading should try to extract the following fields when officially disclosed.

### Income Statement

Priority A:

- Revenue.
- Cost of revenue.
- Gross profit.
- Operating income / operating profit.
- Pretax income.
- Income tax expense.
- Net income.

Priority B:

- Revenue by segment, product, geography, or major category.
- Investment income, fair-value gains/losses, equity-method income.
- Impairment, restructuring, litigation, one-time gains/losses.
- Basic EPS and diluted EPS, if reliably disclosed.

### Expense Structure

Priority A:

- Sales and marketing expense.
- Research and development expense.
- General and administrative expense.
- Share-based compensation.
- Depreciation and amortization.

Priority B:

- Fulfillment cost.
- Payment processing cost.
- Server, bandwidth, cloud, logistics, merchant-support, subsidy, or other company-specific cost lines.
- Advertising expense, if separately disclosed.

These fields help explain whether growth is organic or bought with spending.

### Cash Flow

Priority A:

- Operating cash flow.
- Capital expenditures.
- Free cash flow, derived only as `operating_cash_flow - capital_expenditures`.

Priority B:

- Depreciation and amortization cash-flow addback.
- Working-capital changes.
- Receivables change.
- Inventory change.
- Accounts payable / merchant payable change.
- Accrued expenses change.
- Deferred revenue / customer advances / merchant deposits.
- Cash paid for taxes and interest, if disclosed.

Strong cash flow must be explainable. If CFO is strong because payables, deposits, deferred revenue, or other liabilities grew unusually fast, preserve that evidence.

### Balance Sheet

Priority A:

- Cash and cash equivalents.
- Short-term investments.
- Restricted cash, if disclosed.
- Total assets.
- Total liabilities.
- Interest-bearing debt.
- Current debt and non-current debt, if disclosed.

Priority B:

- Convertible bonds / convertible notes.
- Lease liabilities.
- Current assets and current liabilities.
- Long-term investments / investment portfolio.
- Debt maturity schedule.
- Interest rate and covenant information, if disclosed.

Do not assume missing debt equals zero. If no explicit debt fact is found, report `debt` as missing or optional missing.

### Shareholder Dilution And Capital Allocation

Priority A:

- Basic share count.
- Diluted share count.
- ADS count and ordinary-shares-per-ADS ratio, when relevant.
- Share-based compensation.

Priority B:

- Buyback amount.
- Dividends.
- New share issuance.
- Share plan size, options, RSUs, remaining authorization, and plan expiration.

These fields support per-share economics and dilution analysis.

### Company-Specific KPIs

Extract company KPIs only when officially disclosed.

Examples:

- GMV.
- Active buyers.
- Active merchants.
- Orders.
- Annual spending per active buyer.
- Average transaction services revenue per active merchant.
- Take rate or monetization rate.
- DAU / MAU.
- ARR / subscription revenue.
- Segment users, merchants, subscribers, stores, deliveries, units, or bookings.

For every KPI, preserve:

- Metric definition.
- Reporting period.
- Unit.
- Whether the series is current or historical/stale.
- Any definition change or discontinuation.

Do not invent KPI values from charts or management wording unless the number is explicitly disclosed.

## 5. Quarterly / Interim Facts

Quarterly extraction should update the annual story, not recreate the whole annual report.

Extract:

- Revenue.
- Major revenue breakdowns.
- Gross profit.
- Operating income.
- Net income.
- Operating cash flow.
- Cash and short-term investments.
- Total assets and total liabilities, if disclosed.
- Diluted shares.
- Non-GAAP reconciliation items, if the release emphasizes non-GAAP results.

Flag if quarterly trend changes the annual view:

- Revenue growth accelerates or slows sharply.
- Gross margin or operating margin changes materially.
- CFO no longer supports net income.
- Management emphasizes new investment, subsidy, restructuring, impairment, or risk.
- Non-GAAP adjustments become large or recurring.

## 6. Non-GAAP And Adjusted Metrics

If an official earnings release provides non-GAAP metrics, extract the bridge rather than only the adjusted result.

Extract:

- GAAP metric.
- Non-GAAP metric.
- Adjustment items.
- Adjustment amount.
- Tax effect, if disclosed.
- Whether the adjustment appears recurring across periods.

Recurring adjustments should not be treated as one-time simply because management labels them adjusted.

## 7. Extraction Method

Preferred order:

1. Structured XBRL / inline XBRL facts.
2. Official filing tables.
3. Official annual-report PDF tables.
4. Official earnings-release tables.
5. Official report text, only when the number is explicit and source-linked.

For each extracted fact, preserve:

- `metric`.
- `label`.
- `value`.
- `unit`.
- `period_type`.
- `start_date`.
- `end_date` or `instant`.
- `source_id`.
- `document_id`.
- `document_type`.
- `filing_date`.
- `source_url`.
- `local_path`.
- `extraction_method`.
- `confidence`.
- `fact_id`.

For derived facts, preserve:

- Formula.
- Source fact IDs.
- Interpretation note.

Allowed derived facts:

- `gross_profit = revenue - cost_of_revenue`.
- `free_cash_flow = operating_cash_flow - capital_expenditures`.
- `debt = current_debt + non_current_debt`.

Do not derive valuation metrics here. Enterprise value, FCF yield, owner earnings yield, DCF, and margin of safety belong to the Valuation Agent.

## 8. Verification And Review Flags

Flag for review when:

- A key fact cannot be traced to an official source.
- Two official sources conflict by about 2% or more.
- The extraction source is lower quality than the approved hierarchy.
- A formula or metric definition changes.
- A KPI definition changes or the company stops reporting a KPI.
- Non-GAAP adjustments are large or recurring.
- There is an auditor change, restatement, material weakness, or non-reliance disclosure.
- Working capital explains too much of CFO improvement.
- Debt, restricted cash, or convertible bond data is missing for a leveraged company.

Rounding differences can be accepted only when clearly explained and logged.

## 9. Output Requirements

The agent should output:

1. Raw extracted facts.
2. Selected / deduplicated facts.
3. Extraction summary by metric and period type.
4. Missing high-priority fields.
5. Source lineage for key facts.
6. Derived facts with source fact IDs.
7. Review flags.

The report should make clear what is extracted, what is derived, what is missing, and what requires human review.

