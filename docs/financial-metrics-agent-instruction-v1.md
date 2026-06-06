# Financial Metrics Agent Instruction V1

Status: Active instruction.  
Parent design: `docs/financial-agents-v1.md`.  
Upstream instruction: `docs/financial-extraction-agent-instruction-v1.md`.  
Methodology reference: `docs/references/value-investor-financial-reports-sec-reading-method.zh.md`.

This instruction defines how the Financial Metrics Agent should turn extracted official financial facts into financial-quality metrics.

## 1. Goal

The Financial Metrics Agent calculates the numbers needed to answer:

> Given the official facts extracted from annual and interim reports, what do the numbers say about growth quality, margin quality, cash conversion, capital intensity, balance-sheet pressure, dilution, and accounting quality?

The agent calculates financial-statement quality metrics. It does not decide buy/sell, prove moat durability, judge management quality, write diagnostic questions, or calculate market-price-dependent valuation metrics.

## 2. Agent Boundary

### Inputs

- Selected official facts from the Financial Extraction Agent.
- Source lineage for each fact.
- Verification and conflict results.
- Document classification, especially annual report / quarterly update / material-event scan.
- Optional official KPI facts.

### Outputs

- Metric families with formula IDs.
- Annual and latest-interim results.
- Source fact IDs used in each calculation.
- Missing input list.
- Formula-level warning flags.
- Formula status and missing inputs for the Diagnostic Rules Agent.

### Excluded

The Financial Metrics Agent must not calculate:

- Enterprise value.
- FCF yield.
- Owner earnings yield / true yield.
- DCF.
- Margin of safety.
- Estimated return.
- One-dollar retained earnings test.

Those belong to the Valuation Agent because they require market price, FX, valuation assumptions, or multi-period market-cap data.

## 3. Annual Report Anchor

The first analytical baseline must come from the annual report / 10-K / 20-F.

SOP:

1. Build the latest annual fact map from annual official filings.
2. Build a multi-year annual history when available.
3. Answer the five annual-report questions before interpreting quarterly updates:
   - 公司靠什么赚钱？
   - 增长来自哪里？
   - 利润能不能变成现金？
   - 有哪些主要风险？
   - 数字有没有明显不舒服的地方？
4. Use latest 10-Q / quarterly 6-K only as a trend update.
5. Do not let a single quarter replace the annual baseline unless it clearly changes the annual view.

The metrics layer should therefore produce two views:

- **Annual baseline:** multi-year annual metrics from 10-K / 20-F / annual report.
- **Latest trend update:** latest interim / quarterly metrics where official data is available.

## 4. Calculation Principles

- Calculate from extracted official facts only.
- Keep missing inputs missing.
- Do not use third-party estimates to fill formulas.
- Do not silently change formulas.
- Distinguish reported facts, derived facts, proxy metrics, and judgmental adjustments.
- Attach source fact IDs to each metric result.
- Prefer ratios that answer an investment question over large ratio dumps.

Every metric should answer one of these questions:

1. Is growth high quality?
2. Are margins improving or deteriorating?
3. Does profit become cash?
4. Does growth require heavy capital?
5. Is the balance sheet resilient?
6. Are shareholders diluted?
7. Are accounting / non-GAAP adjustments hiding problems?

## 5. Metric Families

### Growth Quality

Purpose:

Check whether growth is real, profitable, and cash-backed.

Required facts:

- Revenue.
- Operating income.
- Operating cash flow.
- Free cash flow, if available or derived.
- Segment / revenue category facts, when disclosed.

Core calculations:

```text
Revenue Growth = (Revenue_t - Revenue_t-1) / Revenue_t-1
Operating Income Growth = (Operating Income_t - Operating Income_t-1) / abs(Operating Income_t-1)
FCF Growth = (FCF_t - FCF_t-1) / abs(FCF_t-1)
Incremental Operating Margin = Change in Operating Income / Change in Revenue
Incremental FCF Margin = Change in FCF / Change in Revenue
```

Warning flags:

- Revenue grows but operating income or FCF declines.
- Incremental operating margin is negative.
- Incremental FCF margin is negative.
- Revenue growth cannot be explained by segment, product, volume, pricing, take rate, or KPI data.
- Revenue category mix changes materially.

Follow-up checks:

- MD&A revenue explanation.
- Segment disclosure.
- Revenue recognition footnote.
- Company KPI definitions and discontinuations.
- Quarterly update for trend reversal or deterioration.

### Margin Quality

Purpose:

Check whether scale improves profitability or requires more spending.

Required facts:

- Revenue.
- Cost of revenue.
- Gross profit.
- Operating income.
- Net income.
- Sales and marketing.
- R&D.
- G&A.
- Company-specific cost lines, when available.

Core calculations:

```text
Gross Margin = Gross Profit / Revenue
Operating Margin = Operating Income / Revenue
Net Margin = Net Income / Revenue
FCF Margin = FCF / Revenue
Cost of Revenue Ratio = Cost of Revenue / Revenue
S&M Ratio = Sales and Marketing / Revenue
R&D Ratio = R&D / Revenue
G&A Ratio = G&A / Revenue
```

Warning flags:

- Revenue grows but gross margin falls.
- Operating margin falls faster than gross margin.
- Sales and marketing, subsidy, merchant support, fulfillment, payment, or infrastructure costs rise faster than revenue.
- Net margin improves mainly because of investment income, fair-value gains, tax benefits, or one-time items.

Follow-up checks:

- MD&A cost explanations.
- Cost of revenue footnote.
- Non-GAAP adjustment bridge.
- Fair-value / investment income / tax footnotes.

### Cash Conversion And Working-Capital Quality

Purpose:

Check whether reported profit becomes real operating cash.

Required facts:

- Net income.
- Operating cash flow.
- CapEx.
- Free cash flow.

Important additional facts:

- Receivables.
- Inventory.
- Payables / merchant payables.
- Accrued expenses.
- Deferred revenue.
- Customer advances.
- Merchant deposits.
- Cash taxes and cash interest, if disclosed.

Core calculations:

```text
CFO / Net Income = Operating Cash Flow / Net Income
FCF / Net Income = Free Cash Flow / Net Income
FCF Margin = Free Cash Flow / Revenue
Current Ratio = Current Assets / Current Liabilities
Net Working Capital / Revenue = (Current Assets - Current Liabilities) / Revenue
Component / Revenue = Receivables, Inventory, Payables, Merchant Deposits, Deferred Revenue, Accrued Expenses / Revenue
Component Growth Gap = Component Growth - Revenue Growth
Working-Capital Cash Tailwind / Revenue = (Cash-source liability delta - Cash-use asset delta) / Revenue
```

Runtime display label for `cash_conversion_ratio_v1`:

```text
CFO / net income
```

This avoids ambiguity because market sources sometimes use "cash conversion ratio" for other formulas.

Heuristic:

- `CFO / Net Income >= 1.0` is useful but not a hard pass/fail rule.
- If prior-year component balances exist, prefer component deltas over broad working-capital totals.
- Cash-source liabilities include payables, combined payables/accrued-liabilities lines, merchant payables, merchant deposits, deferred revenue, and accrued expenses.
- Cash-use assets include receivables and inventory.

Warning flags:

- Net income grows but CFO does not.
- CFO is strong mainly because payables, accrued expenses, merchant deposits, deferred revenue, or customer advances increased.
- Receivables or inventory grow faster than revenue.
- Free cash flow is strong only because CapEx is temporarily low.

Follow-up checks:

- Cash-flow statement.
- Working-capital notes.
- Revenue recognition footnote.
- Merchant / customer deposit liabilities.
- Subsequent quarterly cash-flow reversal.

### Capital Intensity And Owner Earnings Proxy

Purpose:

Check how much capital the business needs to grow and maintain itself.

Required facts:

- Operating cash flow.
- CapEx.
- Revenue.
- D&A.
- Share-based compensation.

Core calculations:

```text
CapEx / Revenue = CapEx / Revenue
CapEx / CFO = CapEx / Operating Cash Flow
FCF = Operating Cash Flow - CapEx
FCF Margin = FCF / Revenue
CapEx / D&A = CapEx / Depreciation and Amortization
Owner Earnings Proxy = Operating Cash Flow - Share-Based Compensation - Maintenance CapEx Proxy
```

V1 maintenance CapEx proxy:

```text
Maintenance CapEx Proxy ~= Depreciation and Amortization
```

This is only a proxy. The report must say so.

Runtime label: `owner earnings proxy`.

Human review is required for this metric because maintenance CapEx is not independently estimated in V1.

Warning flags:

- CapEx grows faster than revenue without explanation.
- CapEx / D&A is persistently high.
- Owner earnings proxy depends heavily on D&A as a rough maintenance CapEx estimate.
- Management claims asset-light economics while infrastructure, fulfillment, or capitalized software needs rise.

### ROIC And Incremental ROIC Proxy

Purpose:

Check whether the company appears to earn attractive returns on the capital tied up in the business.

Core calculations:

```text
NOPAT = Operating Income * (1 - Effective Tax Rate)
Effective Tax Rate = Tax Expense / Pretax Income
Invested Capital Proxy = Total Assets - Total Liabilities + Interest-Bearing Debt - Cash
ROIC Proxy = NOPAT / Average Invested Capital Proxy
Incremental ROIC Proxy = Change in NOPAT / Change in Invested Capital Proxy
```

Runtime labels:

- `unlevered ROIC proxy`
- `incremental ROIC proxy`

This is a financing-side invested-capital proxy. The report must flag limitations for cash-heavy, investment-heavy, lease-heavy, goodwill-heavy, or VIE-heavy companies.

Follow-up checks:

- CapEx note.
- PP&E / software / cloud / logistics infrastructure disclosure.
- MD&A investment discussion.
- Maintenance vs growth CapEx evidence.

### Balance-Sheet Resilience

Purpose:

Check whether the company can survive stress without financial pressure.

Required facts:

- Cash and equivalents.
- Short-term investments.
- Restricted cash, if disclosed.
- Debt.
- Total assets.
- Total liabilities.
- Current assets.
- Current liabilities.

Core calculations:

```text
Net Cash = Cash + Short-Term Investments - Debt
Debt / Cash = Debt / Cash
Cash / Total Liabilities = Cash / Total Liabilities
Liabilities / Assets = Total Liabilities / Total Assets
Current Ratio = Current Assets / Current Liabilities
```

Warning flags:

- Debt fact is missing for a leveraged company.
- Cash is large but restricted cash, trapped cash, short debt, or convertible debt is material.
- Current liabilities grow faster than revenue or cash.
- Convertible bonds may create dilution.

Follow-up checks:

- Debt maturity schedule.
- Restricted cash note.
- Convertible bond terms.
- Lease liabilities.
- Liquidity and capital resources section.

### SBC And Dilution Burden

Purpose:

Check whether operating growth benefits shareholders or is diluted away.

Required facts:

- Share-based compensation.
- Revenue.
- Operating cash flow.
- Net income.
- Basic shares.
- Diluted shares.
- ADS count / ordinary-shares-per-ADS, where relevant.

Core calculations:

```text
SBC / Revenue = Share-Based Compensation / Revenue
SBC / CFO = Share-Based Compensation / Operating Cash Flow
SBC / Net Income = Share-Based Compensation / Net Income
Diluted Share Growth = (Diluted Shares_t - Diluted Shares_t-1) / Diluted Shares_t-1
```

Warning flags:

- SBC is large relative to CFO or net income.
- Diluted shares keep increasing despite buybacks.
- Buybacks mostly offset compensation dilution rather than return capital.
- Share plan extension or new authorization increases future dilution risk.

Follow-up checks:

- Share-based compensation footnote.
- Share plan / proxy / AGM materials.
- Buyback and capital allocation disclosures.
- Per-ADS share bridge.

### Tax, Non-GAAP, And Accounting Quality

Purpose:

Check whether accounting estimates or adjusted metrics are making the business look better than GAAP results.

Required facts when available:

- Pretax income.
- Income tax expense.
- Cash taxes.
- Deferred tax assets / liabilities.
- Valuation allowance.
- GAAP operating income / net income.
- Non-GAAP operating income / net income.
- Adjustment items.

Core calculations:

```text
Effective Tax Rate = Income Tax Expense / Pretax Income
Cash Tax / Tax Expense = Cash Taxes Paid / Income Tax Expense
Cash Tax / Pretax Income = Cash Taxes Paid / Pretax Income
Investment Income / Pretax Income = Investment Income / Pretax Income
Impairment / Revenue = Impairment Charges / Revenue
Non-GAAP Net Income Uplift = (Non-GAAP Net Income - GAAP Net Income) / abs(GAAP Net Income)
Non-GAAP Adjustment Burden = sum(abs(Non-GAAP Adjustments)) / Revenue
```

Warning flags:

- Effective tax rate is unusually low or volatile.
- Cash taxes diverge materially from book taxes.
- Valuation allowance changes drive profit.
- Non-GAAP adjustments are large or recurring.
- Fair-value gains, investment income, impairment reversals, restructuring, or litigation adjustments recur.

Follow-up checks:

- Tax footnote.
- Critical accounting estimates.
- Non-GAAP reconciliation.
- Audit report / CAM.
- ICFR / material weakness disclosures.

## 6. Latest Quarter / Interim Update

After annual metrics are calculated, update only the trend:

- Revenue growth vs latest annual trend.
- Gross and operating margin change.
- CFO and FCF change.
- Cash and liability movement.
- Diluted share trend.
- Management explanations in official earnings release.

Quarterly data should not replace annual analysis unless it clearly changes the annual read.

Output one of three statuses:

- `trend_confirmed`: latest quarter supports the annual view.
- `trend_changed`: latest quarter changes the annual view.
- `trend_unclear`: data is partial or inconsistent.

Deterministic V1 rules:

- Revenue: compare latest quarter YoY growth with latest annual revenue growth. `trend_changed` if quarter growth is more than 10 percentage points weaker, turns negative while annual growth is positive, or is more than 15 percentage points stronger. `trend_confirmed` if the gap is within 5 percentage points.
- Margin: use operating margin. `trend_changed` if latest quarter margin is down more than 3 percentage points YoY, or more than 5 percentage points below the annual margin. `trend_confirmed` if YoY margin is down no more than 2 percentage points and no more than 3 percentage points below annual margin.
- Cash conversion: compare latest quarter CFO / net income with annual CFO / net income. `trend_changed` if quarterly conversion is below 0.8 while annual is at least 1.0, or if it is more than 0.5x below annual. `trend_confirmed` if it is at least 0.8 and within 0.3x of annual.
- Balance sheet: compare liabilities/assets and cash/liabilities. `trend_changed` if liabilities/assets is more than 5 percentage points above annual, or cash/liabilities falls below 80% of annual.
- Dilution: compare latest quarter diluted shares with same-quarter prior year. `trend_changed` if diluted shares rise more than 5%; `trend_confirmed` if change is within 2%.
- Overall: high-priority changed topics in revenue, margin, or cash conversion make overall `trend_changed`; two or more unclear high-priority topics make overall `trend_unclear`; all high-priority topics confirmed makes overall `trend_confirmed`.

## 7. Metric Result Schema

Each metric family should produce:

```json
{
  "formula_id": "margin_profile_v1",
  "status": "calculated | partial | missing_required_facts | not_calculable",
  "annual_results": [],
  "latest_interim_result": {},
  "missing": [],
  "warning_flags": [],
  "follow_up_checks": [],
  "source_fact_ids": [],
  "limitations": []
}
```

Each calculated result should include:

- year or period.
- value.
- unit.
- formula.
- components used.
- source fact IDs.
- assumption notes.

## 8. Human Review Triggers

Flag for review when:

- A metric uses a proxy assumption, such as D&A as maintenance CapEx.
- Required facts conflict by about 2% or more across official sources.
- The company changes KPI definition or stops reporting a key KPI.
- Non-GAAP adjustments are large or recurring.
- Working capital drives most cash-flow improvement.
- Debt, restricted cash, or convertible debt is missing but likely important.
- ROIC or incremental ROIC relies on incomplete invested-capital data.
- Formula definitions change.

The agent should continue calculating where possible, but the report must mark affected conclusions as lower confidence.

## 9. Output For Report Agent

The Financial Results Report Agent should receive:

1. Annual baseline metric summary.
2. Latest interim trend update.
3. Warning flags ranked by importance.
4. Missing high-priority facts.
5. Follow-up checks by statement / footnote location.
6. Source fact lineage for every key number.

The report should emphasize what changes the financial read, not every ratio calculated.
