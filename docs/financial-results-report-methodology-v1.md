# Financial Results Report Methodology V1

> Status: Archived implementation note.
> The active Financial Agents design now lives in `docs/financial-agents-v1.md`.
> This file is retained for implementation history and details about the current report artifact.

This document summarizes how the current Financial Results Report is generated, what metrics it calculates, and what investment questions it is designed to answer.

## 1. Purpose

The Financial Results Report is not meant to decide whether to buy or sell a stock. Its job is to turn official financial disclosures into an evidence-based financial quality report.

The report tries to answer these questions:

- Where is revenue growth coming from?
- Is growth profitable, or is the company buying growth with weak margins?
- Are gross margin and operating margin improving or deteriorating as the company scales?
- Is reported profit converting into real cash flow?
- How much capital does growth require?
- Is free cash flow strong after capital expenditures?
- Is share-based compensation meaningful enough to dilute economic earnings?
- Is the balance sheet strong enough to survive stress?
- What rough cash earnings yield does the current market price imply?

In Chinese, the core questions are:

- 收入增长来自哪里？
- 毛利率、经营利润率有没有变化？
- 现金流质量好不好？
- 这个公司赚的钱是真钱吗？
- 增长需要消耗多少资本？
- 规模变大以后利润率是上升还是下降？
- 股权激励和摊薄是否影响股东真实回报？
- 资产负债表有没有明显风险？

## 2. Source Control

For financial numbers, the system prioritizes official sources.

For PDD and other SEC filers, the primary source is SEC EDGAR filings:

- 20-F / 10-K annual reports
- 6-K interim earnings releases and financial tables
- XBRL / inline XBRL facts when available
- Official annual-report PDFs from company investor relations can be used for cross-validation

For Tencent and similar non-US companies, the system uses official company reports and official filing sources when available.

Third-party financial databases are not treated as source of truth for reported financial numbers. They may be added later only as sanity checks, not as primary evidence.

The document collector may also download prospectus, governance, shareholder meeting, financing, auditor-change, and management-change filings. These are useful for deep research, but they do not automatically enter the financial number extraction layer unless the document is classified as a financial extraction document.

## 3. Report Generation Flow

The current pipeline works in this order:

1. Company identity resolution  
   Confirm the legal company, ticker, market, exchange, CIK or equivalent identifier, and known official source locations.

2. Source discovery and document collection  
   Find official filings and reports, download/cache them locally, and classify them by document type.

3. Financial extraction  
   Extract key financial facts from trusted official documents using XBRL, inline XBRL, filing tables, or official report text.

4. Verification and conflict handling  
   Compare facts across official documents where possible. Conflicts are recorded. Material conflicts should be reviewed before relying on the number.

5. Financial metric calculation  
   Convert extracted facts into margins, cash conversion, capital intensity, owner earnings, and ROIC-style metrics.

6. Valuation metric calculation  
   The Valuation Agent combines financial metrics with market data to calculate enterprise value, owner earnings yield, FCF yield, and other price-dependent metrics.

7. Report building  
   Generate a readable Financial Results Report plus a separate source/data linkage record so that important claims can be traced back to source documents.

## 4. Main Extracted Facts

The report currently focuses on these financial facts when disclosed:

- Revenue
- Cost of revenue
- Gross profit
- Operating income
- Pretax income
- Net income
- Operating cash flow
- Capital expenditures
- Free cash flow
- Cash and cash equivalents
- Debt
- Investment portfolio, when disclosed
- Total assets
- Total liabilities
- Share-based compensation
- Depreciation and amortization
- Diluted shares / ADS count
- Sales and marketing expense
- Research and development expense
- General and administrative expense
- Selected operating KPIs, when disclosed

Free cash flow is derived as:

```text
Free Cash Flow = Operating Cash Flow - Capital Expenditures
```

## 5. Main Calculated Metrics

The report ranks metrics around financial quality questions rather than showing formulas randomly.

### Growth Quality

Metrics:

- Revenue growth
- Operating income growth
- Free cash flow growth
- Incremental operating margin
- Incremental free cash flow margin

Question answered:

Is the company growing in a financially healthy way?

### Margin Profile

Metrics:

- Gross margin
- Operating margin
- Net margin
- Free cash flow margin

Question answered:

Does scale improve profitability, or does the company need more spending to keep growing?

### Cash Quality

Metrics:

- Operating cash flow / net income
- Free cash flow / net income
- Owner earnings / net income
- Free cash flow margin

Question answered:

Is reported profit becoming real cash?

### Owner Earnings

V1 formula:

```text
Owner Earnings = Operating Cash Flow - Share-Based Compensation - Depreciation and Amortization
```

V1 uses depreciation and amortization as a conservative placeholder for maintenance CapEx. This is not final. A better maintenance CapEx estimate is a planned future improvement.

Question answered:

What cash earnings might belong to owners after adjusting for stock compensation and maintenance-capital needs?

### Capital Intensity

Metrics:

- CapEx / revenue
- CapEx / operating cash flow
- Free cash flow margin

Question answered:

How much capital is required to support growth?

### ROIC And Incremental ROIC Proxy

Metrics:

- Unlevered ROIC proxy
- Incremental ROIC proxy

Question answered:

Does the business appear to generate attractive returns on the capital it uses?

V1 does not apply a hard ROIC threshold. It calculates the metric and leaves interpretation to the analyst.

### Balance Sheet Risk

Metrics:

- Cash
- Debt
- Net cash / net debt
- Liabilities / assets

Question answered:

Can the company survive a difficult period without financial stress?

### Share-Based Compensation Burden

Metrics:

- SBC / revenue
- SBC / operating cash flow
- SBC / net income
- Diluted share trend

Question answered:

How much of the economic return is being paid to employees through equity, and is shareholder dilution meaningful?

### Yield-Style Valuation Metrics

These metrics are now owned by the Valuation Agent. When market data is available, the system calculates:

- Enterprise value
- Owner earnings yield
- Free cash flow yield
- Investment-adjusted operating yield, when investment portfolio data is available

Basic EV formula:

```text
Enterprise Value = Market Cap - Cash + Debt
```

For companies with large investment portfolios, the report may also show an investment-adjusted operating yield. This is a rough operating-business yield proxy, not a complete sum-of-the-parts valuation.

The Financial Metrics Agent answers whether the business quality is good. The Valuation Agent answers whether the current stock price offers enough potential return.

## 6. Human Review Rules

The system should stop or flag for human review when:

- A financial source conflict is material, currently around 2% or more for key numbers.
- A formula changes.
- A source is lower quality than the approved source hierarchy.
- A valuation assumption is required.
- A key number cannot be traced to an official filing or approved official report.

Rounding differences can be accepted if clearly explained.

## 7. V1 Limitations

Current limitations:

- Maintenance CapEx is not yet deeply estimated.
- Owner earnings is still a V1 approximation.
- Excess cash treatment is simple.
- Investment portfolio adjustment is only a rough operating-yield proxy.
- Segment-level and unit-economic metrics are limited by company disclosure.
- Third-party sanity checks are not yet part of the trusted financial-number pipeline.
- The report does not make buy/sell decisions.

The report should be read as an evidence and calculation layer. Business model, management quality, customer happiness, competitor comparison, and final valuation judgment belong to downstream reports.
