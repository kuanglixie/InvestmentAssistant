# Valuation Methodology V1

Status: Draft active document for the Valuation Agent.  
This document receives the price-dependent and estimated-return material that should no longer live inside the Financial Metrics Agent.

## 1. Purpose

The Valuation Agent answers the "right price" part of the user's principle:

> right business model, right people, right price

It should not decide buy/sell automatically. Its job is to convert financial-quality inputs, market data, and explicit assumptions into a valuation evidence package.

## 2. Inputs

The Valuation Agent consumes:

- official financial facts from the Financial Extraction Agent,
- financial-quality metrics from the Financial Metrics Agent,
- market cap / quote / FX / share-structure data from the Market Data Agent,
- business quality and durability evidence from the Business Model / Moat Agent,
- management and capital-allocation evidence from the Right People / Leadership Agent,
- user-reviewed valuation assumptions.

Important: market price, FX, discount rate, excess cash, maintenance CapEx, investment-portfolio haircut, and growth assumptions are valuation assumptions. They require clear source labeling and, where material, human review.

## 3. Current V1 Metrics

### Enterprise Value

Purpose:

Estimate the market-implied purchase cost of the operating business.

V1 formula:

```text
Enterprise Value = Market Capitalization + Interest-Bearing Debt - Cash and Cash Equivalents
```

Important caveats:

- Not all cash is excess cash.
- Some cash may be required operating cash.
- Some cash may be restricted or trapped overseas.
- Cross-border companies may face repatriation tax or capital-control friction.
- V1 subtracts all cash first, then flags where this may overstate cheapness.

Future improvement:

```text
Adjusted EV = Market Capitalization + Debt - Freely Distributable Excess Cash
```

### Owner Earnings Yield / True Yield

Purpose:

Convert owner earnings into a price-relative return measure.

Formula:

```text
Owner Earnings Yield = Owner Earnings Proxy / Enterprise Value
```

Current ownership:

- Owner Earnings Proxy is produced by the Financial Metrics Agent.
- Enterprise Value and Owner Earnings Yield are produced by the Valuation Agent.

Interpretation:

- A high yield may indicate a cheap price if owner earnings are durable.
- A low yield may still be acceptable if reinvestment opportunities are excellent and predictable.
- This metric is weak as a standalone tool for companies where most value lies in future growth.

### Free Cash Flow Yield

Formula:

```text
FCF Yield = Free Cash Flow / Enterprise Value
```

Use:

- Shows current cash generation relative to market-implied purchase price.
- Should be interpreted with CapEx cycle, working capital, and one-time items.

### Investment-Adjusted Operating Yield

Purpose:

For companies with large investment portfolios, approximate the yield of the consolidated operating business after subtracting official investment holdings from EV.

V1 formula:

```text
Operating EV = Enterprise Value - Official Investment Portfolio Carrying Value
Operating Owner Earnings Yield = Owner Earnings Proxy / Operating EV
Operating FCF Yield = Free Cash Flow / Operating EV
```

Caveats:

- This is not a full sum-of-the-parts valuation.
- It uses official carrying value, not independent market value.
- It applies no tax haircut, liquidity haircut, control premium, or trapped-cash adjustment in V1.
- It does not include look-through earnings from investees unless separately estimated.

### Five-Year One-Dollar Test

Purpose:

Check whether retained earnings have translated into shareholder value over time.

Candidate formula:

```text
One-Dollar Test = (Ending Market Capitalization - Beginning Market Capitalization) / Five-Year Total Retained Earnings
```

Use:

- Capital-allocation clue.
- Not a final judgment because market cap is affected by sentiment and valuation multiples.

Status:

- Pending market-cap history and retained-earnings history.

## 4. Future Valuation Methods

### Scenario Valuation / DCF

Purpose:

Estimate intrinsic value from future owner cash flows without false precision.

Requirements:

- Use at least conservative / base / upside cases.
- Make revenue growth, margins, reinvestment, discount rate, and terminal value explicit.
- Tie scenario confidence to business predictability and moat durability.
- Do not hide uncertainty behind one single DCF output.

Recommended output:

- Base case.
- Conservative case.
- Upside case.
- Key assumptions.
- Sensitivity table.
- Margin of safety.
- Probability-weighted expected return if useful.

### Look-Through Earnings

Purpose:

Capture economic value from partially owned businesses or equity holdings.

Use for:

- holding companies,
- conglomerates,
- companies with large strategic investments.

Rule:

Label look-through earnings as lower-confidence unless the sources are strong.

### Growth-Adjusted Estimated Return

Purpose:

Connect current yield to reinvestment quality.

Conceptual form:

```text
Estimated Return ~= Current Cash Yield + Sustainable Growth From Reinvestment
```

The agent should avoid mechanically adding recent high growth to current yield. It should separate:

- no-growth yield,
- reinvestment rate,
- incremental ROIC or reinvestment return,
- durability of reinvestment runway,
- inflation and currency context.

## 5. Human Review Gates

Human review is required when:

- excess cash treatment changes EV materially,
- maintenance CapEx assumption changes owner earnings materially,
- investment portfolio is adjusted for market value, tax, liquidity, or control,
- discount rate or terminal growth is selected,
- long-term growth scenario is introduced,
- probability weights are used,
- valuation source data conflicts,
- a formula changes.

## 6. Output

The Valuation Agent should output:

- market input summary,
- EV and adjusted EV where applicable,
- owner earnings yield,
- FCF yield,
- investment-adjusted operating yield where applicable,
- scenario valuation only when assumptions are explicit,
- margin-of-safety discussion,
- open valuation assumptions,
- source and formula linkage.

It should not output an automatic buy/sell decision.
