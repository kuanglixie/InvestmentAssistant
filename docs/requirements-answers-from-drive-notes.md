# Requirements Answers Extracted From Google Drive Notes

## 1. Source Folder

User-provided Google Drive folder:

https://drive.google.com/drive/u/0/folders/1wjHQ2QXtY--p9Q0iotipCxK4NyVEqo-1

Top-level folders observed:

- PDD
- 腾讯
- 茅台
- 泡泡玛特
- 巴菲特分析方法

The first pass focused on `巴菲特分析方法` because it directly answers the investment-framework questions in Section 6 of the requirements doc.

## 2. Source Documents Read

The following Google Docs were readable through the signed-in Chrome session:

| Title | Google Doc ID | Main relevance |
| --- | --- | --- |
| 巴菲特定性分析 | `1zE5vyoSdJietIyXhP-LPvZ9j-yjN_IjIF3jrWqVkIjY` | Investment framework, moat, management, business quality |
| 巴菲特定量分析 | `1HuMWM24UbfNV8vmSOqKLY-8jV2-jxpM39wXRNo5IQf8` | Metrics, ROIC controversies, gross margin interpretation |
| 巴菲特财务报表分析方法论 | `1iLIyVMtzrEB3N2jRQfHAnhWjie_kbNZSRrN9b_hEaFs` | Financial statement philosophy, owner earnings, ROIC, valuation caveats |

## 3. Draft Answers To Section 6

These are extracted or inferred from the Drive notes. They should be treated as candidate answers until the user approves them.

## 6.1 Investment Framework

### User's Top-Level Investment Principle

The user's investment principle is:

> Right business model, right people, and right price.

This should be the top-level structure for the final investment memo and checklist.

Initial mapping:

- Right business model: business model, economic moat, customer happiness, financial quality, and competitive position.
- Right people: leadership, organization, integrity, owner orientation, incentives, and capital allocation.
- Right price: valuation, margin of safety, scenario analysis, and expected long-term return.

### Current Value-Investing Framework

The framework appears to be quality-oriented value investing, influenced heavily by Buffett, Munger, Fisher, and owner-oriented business analysis.

Core ideas:

- Prefer a great business at a reasonable price over a mediocre business at a cheap price.
- Start with whether the business is understandable and inside the investor's circle of competence.
- Avoid false precision. Prefer being roughly right on business quality and economic reality over being precisely wrong in spreadsheets.
- Focus on long-term business economics, not short-term stock price movement.
- Treat accounting numbers as starting evidence, not final truth.
- Value depends on future owner cash flows, but those cash flows are only useful if they are predictable enough.
- Do not reject technology companies merely because the underlying technology changes quickly. The key question is whether the business model, customer value proposition, demand driver, and competitive advantage are stable and understandable enough.

### Investors / Books / Traditions That Shape The Framework

The Drive notes clearly emphasize:

- Warren Buffett.
- Charlie Munger.
- Philip Fisher.
- Benjamin Graham, mostly as an earlier influence that Buffett later evolved beyond.

Likely useful learning-material buckets:

- Buffett shareholder letters.
- Berkshire owner manual.
- Munger talks.
- Fisher-style scuttlebutt/customer/supplier/competitor research.
- User's own formula and checklist notes.

### What Makes A Company Rejected Quickly

Candidate rejection rules:

- Outside the investor's circle of competence.
- Business model too complex to understand with confidence.
- Business model or customer value proposition changes too quickly to estimate long-term economics. Fast-changing technology alone is not enough reason to reject a company if the business model remains stable.
- Commodity-like product or service without differentiation.
- No pricing power.
- No durable moat.
- Requires heavy leverage to earn acceptable returns.
- Looks cheap only because of accounting or asset-value appearance.
- Turnaround thesis where success depends on major improvement from a bad business.
- Management lacks integrity, clarity, or owner orientation.
- Management dilutes shareholders carelessly.
- Reported profits are heavily polluted by accounting choices, one-time gains, subsidies, or aggressive capitalization.
- High growth requires too much incremental capital.

### What Makes A Company Seriously Interesting

Candidate positive rules:

- Business is understandable.
- Long-term demand is stable or highly predictable.
- Technology may evolve quickly, but the core business model remains understandable and durable.
- The company has an economic franchise rather than a commodity business.
- Evidence of pricing power.
- High and durable returns on capital without excessive debt.
- Low incremental capital needs relative to growth.
- Strong mindshare, brand, switching costs, network effects, or scale advantages.
- Customers have strong reasons not to switch.
- Management communicates honestly and directly.
- Management behaves like owner-partners.
- Capital allocation increases per-share intrinsic value.
- The business can compound value over many years.

## 6.3 Source Policy

### U.S. Company Sources

Candidate trusted sources:

- SEC filings.
- Company investor relations pages.
- Official annual reports and quarterly reports.
- Official shareholder letters.
- Earnings call transcripts when sourced reliably.

### Chinese Company Sources

Still needs user confirmation, but likely trusted sources should include:

- HKEX filings and announcements for Hong Kong-listed companies.
- Company investor relations pages.
- Official annual reports.
- Exchange filings for mainland China A-share companies.
- SEC filings for ADRs or foreign private issuers where applicable.

### Unofficial Sources

Unofficial sources should be allowed for qualitative research, especially customer happiness, product reception, leadership interviews, and scuttlebutt-style checks.

They should not be used as primary sources for financial numbers.

Useful but lower-trust qualitative sources:

- YouTube.
- Bilibili.
- Reddit.
- Forums.
- Product reviews.
- App reviews.
- Interviews and podcasts.

Each should carry a source-quality label.

## 6.4 Financial Data Requirements

### Historical Period

User-confirmed preference:

- Use all available public-company history by default.
- For companies with shorter public history, use all available public-company history.
- Long historical records matter because the framework prefers actual performance over projections.
- The user generally expects investable companies to be less than 50 years old, but this should be treated as an investment-context flag rather than a reason to truncate data collection.

### Accounting Normalization

Candidate requirement:

- Yes, the system should normalize across U.S. GAAP, IFRS, and Chinese accounting standards where important.
- More importantly, the system should bridge from accounting reality to economic reality.

Important normalization topics from the notes:

- R&D may need to be treated as investment in some businesses.
- Stock-based compensation should usually be treated as a real shareholder cost.
- Goodwill treatment should be explicit.
- Excess cash vs operating cash should be separated.
- Asset impairments should not magically erase past capital allocation mistakes.
- One-time gains, subsidies, investment income, and non-operating items should be separated from operating earnings.
- Effective tax rates should be normalized where current tax is not sustainable.
- Average invested capital may be more useful than period-end invested capital.

### Raw Extracted Tables

Candidate answer:

- Yes, store raw extracted tables locally.
- The system should preserve raw source tables, normalized facts, and formula outputs separately.
- This is necessary for auditability and reproducibility.

## 6.5 Metrics And Formula Management

The user will provide a separate metric/formula document, but the Drive notes already suggest several important metric families.

### Candidate Metrics

- ROIC / return on invested capital.
- Unlevered ROIC.
- ROE, especially where leverage is low.
- Owner earnings.
- Free cash flow.
- Free cash flow margin.
- Gross margin and gross margin durability.
- Operating margin.
- Incremental return on capital.
- Revenue quality and segment mix.
- True Yield / owner earnings yield compared with long-term government bond yield.
- Per-share intrinsic value growth.
- Share dilution from stock-based compensation.
- Fully diluted share count.

### Formula Governance

The notes make clear that formulas are judgment-heavy, especially ROIC.

V1 should therefore:

- Store formulas in versioned config.
- Store interpretation notes with formulas.
- Separate deterministic calculation from interpretation.
- Require human approval before changing formulas.
- Record controversial adjustments explicitly.

### Formula Controversies To Track

ROIC and related metrics should track choices around:

- Whether to capitalize R&D.
- How to treat stock-based compensation.
- Whether to include or exclude goodwill.
- How much cash is excess cash.
- Whether to reverse asset impairments into invested capital.
- Whether to use reported tax rates or normalized tax rates.
- Whether to use beginning, ending, or average invested capital.

Gross margin analysis should track:

- Accounting classification shifts between cost of goods sold and operating expenses.
- Net revenue vs gross revenue treatment for platform businesses.
- Fixed-cost absorption and utilization effects.
- Inventory write-down policies.
- Whether margin improvement comes from pricing power or temporary scale/utilization.

## 6.7 Report Style

User-confirmed V1 report preference:

- Markdown only for V1.

Candidate later report preferences inferred from the notes:

- Use both concise and long-form reporting.
- The final report should include a short decision-oriented summary plus deep appendices.
- Reports should include a checklist with pass/fail/uncertain items.
- Reports should distinguish facts, calculations, interpretation, and unresolved questions.
- Reports should explain accounting adjustments rather than hiding them inside final metrics.

## 6.8 Human Review And Control

User-confirmed human-review gates:

- Formula changes.
- Source conflicts.
- Use of low-quality sources for important claims.
- Important valuation assumptions.

Additional candidate human-review rules:

- Ask for approval before using low-quality sources for important conclusions.
- Ask for approval before adding a new source to the trusted-source list.
- Ask for approval before changing formulas.
- Ask for approval before activating lessons extracted from learning materials.
- Flag uncertainty instead of forcing an answer.
- Block final investment conclusions when primary financial data is missing or conflicting.

User-confirmed learning approval rule:

- Agents can read material and produce candidate lessons.
- Candidate lessons require user approval before becoming active agent behavior.
- This applies to rules, formulas, source preferences, checklists, interpretations, and report templates.

Human review is especially important for:

- ROIC adjustment choices.
- R&D capitalization assumptions.
- SBC treatment.
- Goodwill inclusion/exclusion.
- Excess cash assumptions.
- Valuation scenario probabilities.
- Management-quality judgments based on interviews or unofficial sources.

## 4. Recorded Defaults And Still-Open Implementation Items

The Drive notes and later user answers now establish these defaults:

- Top-level principle: right business model, right people, right price.
- V1 formulas are versioned and require approval before changes.
- Use all available public-company history by default.
- Markdown is the V1 report format.
- Chinese source hierarchy starts with official exchange disclosures and company IR; lower-trust qualitative sources need source-quality labels.

Still-open implementation items:

- Build the exact Tencent HKEX / Tencent IR source downloader.
- Build market-data inputs for price-dependent valuation metrics.
- Implement qualitative source collectors for moat, leadership, customer happiness, and management-change monitoring.

## 5. Confirmed Prototype Company

The user chose PDD Holdings as the first prototype company.

Implications:

- V1 should handle `PDD` as a U.S.-listed ADR / Chinese-origin company.
- Official financial sources should prioritize SEC filings and PDD investor relations.
- The metrics workflow should pay special attention to platform accounting, net vs gross revenue presentation, stock-based compensation, cash usability, and cross-border risk.
- Chinese-language qualitative sources may become useful earlier than originally expected.

## 6. Confirmed V1 Watchlist

For now, restrict the watchlist to:

- PDD Holdings.
- Google / Alphabet.
- Tencent.

PDD is the first deep-research prototype. Google / Alphabet and Tencent should remain available for watchlist monitoring, future comparison, and later workflow expansion.
