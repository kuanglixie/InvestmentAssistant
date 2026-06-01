# Metrics And Formula Requirements V1

> Status: Formula appendix / historical requirement note.
> The active Financial Agents design lives in `docs/financial-agents-v1.md`.
> Price-dependent valuation formulas now live in `docs/valuation-methodology-v1.md`.
> Business-quality classification belongs to `docs/business-model-moat-agent-v1.md`.
> If this file conflicts with those active documents, the active documents win.

## 0. Current Ownership Override

Financial Metrics Agent owns pure financial-statement quality metrics:

- owner earnings proxy amount,
- cash conversion with working-capital review,
- margins,
- capital intensity,
- SBC and dilution burden,
- balance-sheet risk,
- ROIC and incremental ROIC proxy.

Valuation Agent owns market-price-dependent metrics:

- enterprise value,
- owner earnings yield / true yield,
- FCF yield,
- investment-adjusted operating yield,
- one-dollar test,
- DCF / scenario valuation,
- margin of safety,
- estimated return.

Business Model / Moat Agent owns business-quality classification:

- great business,
- good business,
- gruesome business,
- pricing power and durability interpretation.

V1 should not automatically introduce highly judgmental adjustments such as R&D capitalization, goodwill-adjusted ROIC, normalized tax, excess cash, or investment-portfolio haircuts unless they are explicitly reviewed.

## 1. Source Document

Primary user-provided metrics document:

https://docs.google.com/document/d/1iLIyVMtzrEB3N2jRQfHAnhWjie_kbNZSRrN9b_hEaFs/edit?tab=t.0

Document title observed:

- 巴菲特财务报表分析方法论

This file converts the document's ideas into candidate V1 requirements for the Metrics Agent. The formulas and thresholds should remain reviewable and versioned.

## 2. Philosophy

The Metrics Agent should not treat accounting numbers as final economic truth.

Core metric philosophy:

- Start from reported financial statements.
- Reconstruct economic reality where accounting rules distort business truth.
- Separate deterministic calculation from judgment-based adjustment.
- Track every formula version and adjustment assumption.
- Explain what each metric means and where it can mislead.
- Prefer long-term, per-share, owner-oriented economics over short-term accounting optics.

The metrics should support the user's top-level investment principle:

> Right business model, right people, and right price.

## 3. Core Metrics

### 3.1 Owner Earnings

Purpose:

Estimate the cash that truly belongs to shareholders after the company spends what is necessary to maintain its competitive position.

Candidate formula:

```text
Owner Earnings = Operating Cash Flow - Stock-Based Compensation - Maintenance CapEx
```

Initial V1 approximation:

```text
Maintenance CapEx ~= Depreciation and Amortization
Owner Earnings V1 = Operating Cash Flow - Stock-Based Compensation - Depreciation and Amortization
```

Important caveats:

- Depreciation and amortization may understate real maintenance needs in industries with fast asset replacement cycles.
- For technology companies with heavy AI, cloud, or GPU infrastructure needs, maintenance CapEx may be materially higher than accounting depreciation.
- The agent should distinguish maintenance CapEx from growth CapEx when evidence allows.
- Stock-based compensation is treated as a real shareholder cost because it dilutes owners.

Required output:

- Reported operating cash flow.
- Reported stock-based compensation.
- Maintenance CapEx estimate.
- Owner earnings result.
- Explanation of maintenance CapEx assumption.
- Confidence level.

### 3.2 Enterprise Value

Purpose:

Estimate the true cost of buying the business, considering debt and usable cash.

Candidate formula:

```text
Enterprise Value = Market Capitalization + Interest-Bearing Debt - Cash and Cash Equivalents
```

Important caveats:

- Not all cash is excess cash.
- Some cash may be required operating cash.
- Some cash may be restricted or trapped overseas.
- Cross-border businesses may face repatriation tax or capital-control friction.
- The formula should eventually subtract only freely distributable excess cash, not all balance-sheet cash.

V1 treatment:

- Calculate standard EV by subtracting all cash first.
- Also flag where operating cash, restricted cash, or trapped cash may make standard EV too optimistic.

### 3.3 True Yield

Purpose:

Convert owner earnings into an owner-oriented earnings yield that can be compared with alternatives such as long-term government bonds.

Agent ownership:

- `Owner Earnings` is a Financial Metrics Agent output.
- `Enterprise Value` and `True Yield` are Valuation Agent outputs because they depend on market price, FX, and market-cap assumptions.

Candidate formula:

```text
True Yield = Owner Earnings / Enterprise Value
```

Interpretation:

- If True Yield is meaningfully above long-term government bond yields, the stock may have a basic static margin of safety.
- If True Yield is only similar to bond yields, the company may still be attractive if ROIC is high and future growth is highly predictable.
- The metric is less useful as a standalone test for companies where most value lies in long-term growth or terminal value.

Required output:

- True Yield.
- Long-term government bond yield used as comparison.
- Static valuation interpretation.
- Dynamic growth interpretation.
- Sensitivity to Owner Earnings and EV assumptions.

### 3.4 Cash Conversion Ratio

Purpose:

Check whether reported accounting profits convert into real operating cash flow.

Candidate formula:

```text
Cash Conversion Ratio = Operating Cash Flow / Net Income
```

Target:

```text
Cash Conversion Ratio >= 1.0
```

Interpretation:

- A ratio above 1.0 suggests earnings are backed by cash generation.
- A ratio below 1.0 may indicate working-capital pressure, aggressive revenue recognition, inventory buildup, receivables growth, or other quality issues.

Required output:

- Operating cash flow.
- Net income.
- Ratio.
- Working-capital explanation if ratio is weak.

### 3.5 Five-Year One-Dollar Retained Earnings Test

Purpose:

Assess whether management creates at least one dollar of market value for every dollar retained in the business.

Candidate formula:

```text
One-Dollar Test = (Ending Market Capitalization - Beginning Market Capitalization) / Five-Year Total Retained Earnings
```

Target:

```text
One-Dollar Test >= 1.0
```

Interpretation:

- A result above 1.0 suggests retained earnings have created shareholder value.
- A result below 1.0 suggests capital allocation may be weak.

Important caveats:

- Market capitalization can be noisy and sentiment-driven.
- The result depends heavily on beginning and ending valuation multiples.
- This should be used as a management and capital-allocation clue, not as a final judgment by itself.

Required output:

- Beginning market capitalization.
- Ending market capitalization.
- Five-year retained earnings.
- Result.
- Caveat about market-cycle distortion.

### 3.6 Unlevered ROIC

Purpose:

Measure the quality of the business model without relying on leverage.

Interpretation:

- Sustained high unlevered ROIC supports the existence of a moat.
- High ROIC should be examined alongside reinvestment opportunity, growth durability, and competitive threats.
- V1 should calculate ROIC but should not apply a hard threshold.

Important caveats:

- Historical ROIC does not prove future moat durability.
- ROIC can be distorted by accounting treatment of R&D, goodwill, excess cash, impairments, and tax rates.
- ROIC can look artificially high after asset impairments.
- For technology or platform companies, R&D capitalization may provide a better view of economic returns.

Required output:

- Reported ROIC if available.
- System-calculated unlevered ROIC.
- Adjusted ROIC when assumptions are applied.
- Explanation of all adjustments.
- ROIC trend over time.

### 3.7 Intrinsic Value / DCF

Purpose:

Estimate business value from future cash flows.

Candidate principle:

```text
Intrinsic value = discounted value of future owner cash flows
```

Requirements:

- Do not rely on a single-point DCF as false precision.
- Make all assumptions explicit.
- Use scenarios for growth, margin, reinvestment, discount rate, and terminal value.
- Connect valuation confidence to business predictability and moat durability.

Recommended output:

- Base case.
- Conservative case.
- Upside case.
- Key assumptions.
- Sensitivity table.
- Margin of safety.
- Probability-weighted expected return where appropriate.

### 3.8 Look-Through Earnings

Purpose:

Capture economic value from partially owned businesses or equity holdings.

Candidate treatment:

- For companies holding meaningful stakes in other businesses, estimate the investor's share of retained earnings and owner earnings where available.
- Label this as lower-confidence unless sources are strong.

Useful for:

- Holding companies.
- Conglomerates.
- Companies with large strategic investments.

## 4. Business Quality Classifications

The Metrics Agent should help classify business models by capital intensity and incremental capital needs.

### 4.1 Great Business

Traits:

- Very high returns on capital.
- Growth requires little incremental capital.
- Strong pricing power.
- Can withstand inflation without large new capital investment.
- Generates excess cash that can be distributed or redeployed.

### 4.2 Good Business

Traits:

- Reasonable returns on capital.
- Growth requires meaningful reinvestment.
- Can compound value if reinvestment returns remain attractive.

### 4.3 Gruesome Business

Traits:

- Low returns on capital.
- Requires continuous reinvestment just to survive.
- Weak pricing power.
- Value-destroying over time.

## 5. Moat And Pricing Power Metrics

The metrics should support moat analysis, not replace it.

Important evidence:

- Durable gross margin.
- Durable operating margin.
- High and persistent ROIC.
- Low customer churn where available.
- Ability to raise prices without losing share.
- Ability to pass through cost inflation.
- Low incremental capital needs.
- Strong cash conversion.

Pricing power is a key test:

```text
Can the company raise prices without meaningful volume, market share, or customer-trust damage?
```

## 6. Required Adjustments And Controversies

The Metrics Agent must track these judgment areas explicitly.

### 6.1 R&D Capitalization

Issue:

Accounting rules often expense R&D immediately, but for some companies R&D creates long-term assets.

Requirement:

- Calculate reported results.
- Optionally calculate R&D-capitalized adjusted results.
- Track assumed amortization period.
- Explain why the adjustment is or is not appropriate.

### 6.2 Stock-Based Compensation

Issue:

SBC is non-cash in the cash flow statement but economically costly to shareholders.

Requirement:

- Deduct SBC from owner earnings.
- Track fully diluted share count.
- Estimate dilution pressure.
- Check whether buybacks offset SBC dilution.

### 6.3 Maintenance CapEx

Issue:

D&A may not equal the cash required to maintain the business.

Requirement:

- Use D&A as V1 approximation.
- Flag cases where actual maintenance CapEx may differ materially.
- For infrastructure-heavy tech businesses, estimate replacement economics where possible.

### 6.4 Cash And Enterprise Value

Issue:

Cash may be trapped, restricted, or necessary for operations.

Requirement:

- Calculate standard EV.
- Estimate adjusted EV using excess cash where possible.
- Explain all assumptions.

### 6.5 Goodwill And Impairments

Issue:

Goodwill and impairment charges can distort capital-return metrics.

Requirement:

- Show ROIC with and without goodwill when relevant.
- Flag asset impairments.
- Avoid rewarding management by ignoring failed capital allocation.

### 6.6 Tax Normalization

Issue:

Current effective tax rates may not be sustainable.

Requirement:

- Report actual effective tax rate.
- Consider normalized tax rate for NOPAT and ROIC.
- Explain tax assumptions.

### 6.7 Scenario And Probability Thinking

Issue:

Static yield metrics can miss companies whose value lies in future growth.

Requirement:

- Use scenario analysis for growth companies.
- Consider probability-weighted outcomes when useful.
- Do not force a single valuation answer where uncertainty is high.

### 6.8 Black Swan / Catastrophic Risk Stress Test

Issue:

Historical ROIC may not reflect sudden non-linear risk.

Examples:

- Geopolitical risk.
- Antitrust.
- Regulatory shock.
- Supply-chain disruption.
- Technology disruption.

Requirement:

- Add a checklist section asking what the company is worth if the core moat is partially or severely impaired.
- Estimate remaining asset value or fallback business value where possible.

## 7. V1 Checklist

The V1 Metrics Agent should produce this table for each company when data is available.

| Dimension | Metric | Candidate target | Purpose |
| --- | --- | --- | --- |
| Cash generation | Owner Earnings | Stable long-term growth | Real owner cash generation |
| Purchase cost | Enterprise Value | Adjusted for debt and usable cash | True business purchase cost |
| Valuation | True Yield | Above long-term government bond yield, or justified by high-quality growth | Cross-asset return attractiveness |
| Earnings quality | Cash Conversion Ratio | >= 1.0 | Avoid paper profits |
| Capital allocation | Five-Year One-Dollar Test | >= 1.0 | Management use of retained earnings |
| Moat | Unlevered ROIC | No V1 threshold | Business quality and barrier depth |

## 8. Formula Versioning Requirement

Every metric should include:

- Formula ID.
- Formula version.
- Input facts and sources.
- Calculation output.
- Adjustment assumptions.
- Interpretation.
- Known weaknesses.

Example formula ID candidates:

- `owner_earnings_v1`
- `enterprise_value_v1`
- `true_yield_v1`
- `cash_conversion_ratio_v1`
- `one_dollar_test_5y_v1`
- `unlevered_roic_v1`
- `intrinsic_value_dcf_v1`

Ownership note:

- Financial Metrics Agent should own pure financial-statement quality metrics.
- Valuation Agent should own market-price-dependent metrics and estimated-return logic.

## 9. Remaining Formula Questions

The user still needs to confirm:

1. For technology companies, how many years should R&D be amortized when capitalized?
2. Should SBC always be fully deducted from owner earnings, or should there be any exceptions?
3. Should EV subtract all cash in V1, or should V1 immediately estimate excess cash?
4. What long-term government bond yield should be used for True Yield comparison for U.S. and Chinese companies?
5. Whether to introduce any ROIC threshold later, and whether it should vary by industry.
6. Should the One-Dollar Test use market capitalization, intrinsic value estimate, or both?
7. Should valuation use probability-weighted scenarios in V1, or begin with conservative/base/upside scenarios only?
