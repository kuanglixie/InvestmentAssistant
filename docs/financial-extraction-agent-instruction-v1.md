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

V1 upgrade principle: the extractor should behave like a hard financial working-paper builder, not a headline metric copier. It must preserve enough official line items for downstream agents to build revenue, expense, below-operating, working-capital, cash-availability, and dilution/capital-return bridges.

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

For platform companies, do not treat `cost_of_revenue` as enough when the report separately discloses cost subcomponents. Preserve any official line item for:

- `fulfillment_expense`.
- `payment_processing_expense`.
- `server_and_bandwidth_costs`.
- `merchant_support_costs`.
- `platform_governance_costs`.
- `logistics_expense`.

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
- Cash-and-short-term-investments subtotal, only if official or derived from official `cash + short_term_investments`.
- Restricted-cash notes, VIE cash-transfer restrictions, dividend/remittance restrictions, and other cash-availability limits. Numeric amounts are extractor facts; restriction language belongs to official-report evidence, but the extraction summary should flag that text evidence is needed.

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
- Ordinary shares outstanding, ADS outstanding, and ordinary-shares-per-ADS ratio when relevant.

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
- Cost subcomponents when the official release table discloses them.

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
8. `hard_financial_worksheet_coverage`, grouped by the bridge/workpaper categories below.

The report should make clear what is extracted, what is derived, what is missing, and what requires human review.

## 10. Hard Module V2: Financial Fact Extractor

The first layer must be a hard fact module before it becomes an analysis module.

For any 20-F / 10-K, the extractor should first stabilize:

1. Five-year income statement.
2. Five-year balance sheet.
3. Five-year cash flow statement.
4. Revenue breakdown.
5. Non-GAAP reconciliation when officially disclosed.
6. Working-capital and cash-flow bridge.
7. Key notes for restricted cash, VIE, debt, tax, share-based compensation, and capital allocation.

### Metadata Contract

Every selected fact must preserve enough metadata for later audit:

```json
{
  "company": "PDD",
  "period_label": "FY2025",
  "canonical_metric": "revenue",
  "value": 431845713000,
  "currency": "RMB",
  "unit": "CNY",
  "value_scale": 1,
  "source_document_type": "20-F:primary",
  "source_table": "statement_of_operations",
  "accession_number": "0001104659-26-050727",
  "confidence_score": 0.98
}
```

The value should be stored in full units after any XBRL scale adjustment. Display conversion, such as RMB bn, belongs to the report renderer.

### Canonical Metric Map

The extractor must map company labels and XBRL tags into canonical names. Examples:

- `Revenue`, `Total revenues`, `Net sales` -> `revenue`.
- `Operating profit`, `Operating income (loss)` -> `operating_income`.
- `Online marketing services and others` -> `online_marketing_services_revenue`.
- `Transaction services` -> `transaction_services_revenue`.
- `Payables to merchants` -> `payable_to_merchants`.

If a label is not mapped, the fact can be stored as an auxiliary official fact, but it should not silently enter core metrics.

### Revenue Breakdown Extractor

For PDD and similar platforms, revenue breakdown is not optional when officially disclosed. The extractor should try to capture:

- Total revenue.
- Online marketing services and others.
- Transaction services.
- Year-over-year growth by component when disclosed.
- Component margin only if explicitly disclosed.

If only quarterly breakdown is available, label it as quarterly evidence and do not extrapolate it into annual structure.

### Cash Flow Bridge

Do not stop at `CFO / net income`. Preserve the bridge where disclosed:

- Net income.
- Share-based compensation.
- Depreciation and amortization.
- Change in payables / merchant payables.
- Change in accrued expenses.
- Change in merchant deposits.
- Change in deferred revenue / customer advances.
- Change in receivables and inventory.
- Operating cash flow.

This allows the report to distinguish cash generated by earnings from cash helped by operating float.

### Hard Financial Worksheet Coverage

The extraction summary must include `hard_financial_worksheet_coverage`. It organizes present and missing facts around the following working papers:

- `revenue_component_bridge`: revenue, online marketing services, transaction services, and other official revenue components. The extractor provides raw component facts; YoY/QoQ contribution math belongs to the Financial Metrics Agent.
- `expense_bridge`: revenue, cost of revenue, gross profit, S&M, R&D, G&A, and operating income.
- `cost_subcomponents`: fulfillment, payment processing, server/bandwidth, merchant support, platform governance, logistics, and similar official cost lines.
- `below_operating_bridge`: operating income, investment income, interest income/expense, FX, other income/loss, pretax income, tax, equity-method income/loss, and net income.
- `working_capital_bridge`: receivables, prepayments, accounts payable, payable to merchants, accrued expenses, merchant deposits, deferred revenue, and cash-flow-statement changes in those items.
- `cash_availability`: cash, restricted cash, short-term investments, long-term investments / investment portfolio, and text-evidence needs for VIE or remittance restrictions.
- `shares_sbc_capital_return_bridge`: SBC, diluted shares, basic shares, ADS/ordinary-share structure, repurchases, dividends, and equity-plan authorization.

Each worksheet should report available core metrics, missing core metrics, available supporting metrics, missing supporting metrics, period coverage, source fact IDs, text evidence needed, and a review note.

### Extraction Quality Gate

Before a full financial report is generated, the latest annual period must have:

- `revenue`.
- `operating_income`.
- `net_income`.
- `operating_cash_flow`.
- `cash`.

If any of these core facts is missing, the system should not generate a full investment report. It should output a short extraction-failure report listing the missing facts, source coverage, and next extraction fix. This avoids long reports that appear analytical but are missing the basic financial spine.
