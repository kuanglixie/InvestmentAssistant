# Stock Investment Deep Research Multi-Agent System Requirements

## 1. Purpose

Build a multi-agent research system using the LangChain/LangGraph ecosystem to support deep value-investing research on public companies.

The system should improve on generic deep-research reports from tools like ChatGPT or Gemini by making the research process more reliable, auditable, self-checking, source-grounded, and customizable to the investor's own framework.

The system is not intended to research thousands of companies automatically. It should support:

- Deep research on roughly one or two companies per day when needed.
- Ongoing monitoring of about 10-20 companies.
- Long-term value investing decisions, likely buying only one or two companies per year.
- Avoiding frequent trading.
- Research depth and evidence quality over speed or volume.

The system should support both U.S. and Chinese companies.

## 2. Core Principles

### 2.0 Investment Principle

The user's top-level investment principle is:

> Right business model, right people, and right price.

The research system should organize its final investment judgment around these three gates:

- Right business model: the company has an understandable, durable, high-quality business model with evidence of economic moat and attractive long-term economics.
- Right people: the company is led and governed by capable, honest, owner-oriented people and an organization that can sustain the business quality.
- Right price: the stock price provides an attractive margin of safety relative to conservative intrinsic value estimates and long-term owner earnings.

The system should not treat any one gate as sufficient by itself. A company with a wonderful business but the wrong people or an excessive price should remain unapproved. A cheap company with weak business quality or poor leadership should also remain unapproved.

### 2.1 Reliability First

Financial and business research must rely on high-quality sources whenever possible.

Preferred sources include:

- Official company investor relations pages.
- SEC filings for U.S. companies.
- Official annual reports, quarterly reports, and earnings releases.
- Reliable financial databases.
- Other primary or highly trusted sources.

Lower-trust sources such as Yahoo Finance, forums, Reddit, YouTube, or social media may be useful, but they should be clearly labeled and should not silently replace primary sources.

### 2.2 Auditability

Every agent report should include:

- Sources used.
- Important extracted facts.
- Citations or links back to source documents.
- Confidence level.
- Known limitations.
- Disagreements between sources.
- Data lineage for important numbers and conclusions.

The system should make it possible to trace a conclusion back to the data and reasoning that produced it.

### 2.3 Self-Control and Cross-Verification

The system should not rely on a single agent's answer. Important outputs should be checked by other agents.

Examples:

- A primary financial extraction agent pulls numbers from official reports.
- A verification agent checks the same numbers against other reliable sources.
- A metrics agent calculates ratios using fixed formulas.
- A reasoning or audit agent checks whether those metrics are being interpreted correctly.

### 2.4 Extensibility

The system should be designed so more agents can be added later.

Each agent should be able to gain new capabilities over time, including:

- New tools.
- New data sources.
- New formulas.
- New report templates.
- New investment frameworks.
- New learning material provided by the user.

### 2.5 Agent Learning and Knowledge Tracking

Each agent should be able to improve by reading high-quality material provided by the user.

The system must track:

- What material was provided.
- Which agent learned from it.
- What key lessons or rules were extracted.
- When the material was added.
- Whether the material affects formulas, reasoning, report structure, or source preferences.

The user should be able to provide materials such as books, articles, memos, annual reports, investment letters, valuation notes, or checklists.

The system should not silently change its behavior after reading material. It should keep a visible learning record.

## 3. Initial Agent Requirements

### 3.1 Financial Reports Agent

Purpose:

Extract historical financial numbers from official company reports.

Main responsibilities:

- Pull financial data from reliable primary sources.
- Prefer official investor relations sites, SEC filings, annual reports, 10-Ks, 10-Qs, earnings releases, and equivalent Chinese company disclosures.
- Extract key financial statements and important line items.
- Support multi-year historical analysis, such as the last five or ten years.
- Produce a structured financial report with citations.

Important requirement:

This agent must be strict about data quality. It should only choose reliable sources for primary financial data.

### 3.2 Financial Verification Agent

Purpose:

Cross-check the financial numbers extracted by the Financial Reports Agent.

Main responsibilities:

- Verify key numbers against other reliable sources.
- Compare against alternative databases where appropriate.
- Use sources such as official filings, company reports, reliable financial databases, and, when useful, sources like Yahoo Finance as secondary checks.
- Identify mismatches, missing values, restatements, or possible extraction errors.
- Produce a verification report.

Important requirement:

This agent should not merely repeat the first agent's output. It should independently check important numbers and flag disagreement.

### 3.3 Financial Metrics Calculation Agent

Purpose:

Calculate and interpret key financial metrics using fixed formulas and explicit reasoning.

Main responsibilities:

- Calculate financial metrics from verified data.
- Use fixed formulas that can be reviewed and improved over time.
- Explain the reasoning behind each metric.
- Avoid shallow ratio reporting; interpret what each metric means in the company's business context.
- Track formula versions and formula changes.
- Incorporate user-provided learning materials about financial analysis.

Important requirement:

The system should allow formulas and interpretations to improve over time while preserving an audit trail of what changed.

### 3.4 Business Model and Moat Agent

Purpose:

Analyze the company's business model and economic moat.

Main responsibilities:

- Explain how the company makes money.
- Identify revenue drivers, cost structure, customer segments, distribution channels, and competitive advantages.
- Examine whether the company has an economic moat.
- Connect qualitative moat claims to supporting financial metrics.
- Look for evidence such as pricing power, high returns on capital, switching costs, network effects, brand strength, scale advantages, regulatory advantages, or cost advantages.
- Produce a business model and moat report.

Important requirement:

Moat analysis should not be purely narrative. It should be supported by financial and operating evidence where possible.

### 3.5 Customer Happiness and Product Reception Agent

Purpose:

Understand whether customers are happy with the company's products or services.

Main responsibilities:

- Research customer reception across relevant channels.
- Review sources such as YouTube, forums, Reddit, product reviews, app stores, social media, customer interviews, and industry communities.
- Separate anecdotal evidence from stronger evidence.
- Identify recurring praise, complaints, churn signals, trust issues, and product quality trends.
- Produce a customer sentiment and product reception report.

Important requirement:

This agent should clearly label source quality because forums, Reddit, YouTube, and social media can be noisy or biased.

### 3.6 Leadership, People, and Organization Agent

Purpose:

Assess whether the company has the right people, leadership, and organization.

Main responsibilities:

- Research founders, executives, board members, and key leaders.
- Review interviews, conference talks, earnings calls, shareholder letters, podcasts, YouTube, Bilibili, and other long-form sources.
- Assess capital allocation, integrity, communication quality, operating culture, talent density, incentives, and long-term orientation.
- Look for evidence of strong or weak leadership.
- Produce a leadership and organization report.

Important requirement:

For Chinese companies, the system may need to use Chinese-language sources such as Bilibili and Chinese financial media. For U.S. companies, it may need to use English-language interviews, filings, and investor materials.

### 3.7 Valuation Agent

Purpose:

Determine whether the stock is available at the right price.

Main responsibilities:

- Evaluate appropriate valuation models for the company.
- Support models such as DCF, owner earnings, earnings multiples, free cash flow yield, sum-of-the-parts, asset value, or other frameworks as appropriate.
- Make assumptions explicit.
- Run sensitivity analysis.
- Compare valuation to business quality, growth, risk, and cyclicality.
- Produce a valuation report.

Important requirement:

The system needs to decide which valuation models are most suitable for the specific company and why.

### 3.8 Competitor Comparison Agent

Purpose:

Compare the target company with its competitors.

Main responsibilities:

- Identify relevant competitors.
- Run similar research across the competitors using agents 3.1-3.7 where appropriate.
- Compare financials, business model, moat, customer happiness, leadership, and valuation.
- Produce a comparative research report.

Important requirement:

Competitor companies should go through the same core research process before final comparison, at least at a level deep enough to support a fair conclusion.

## 4. Expected Outputs

Each agent should produce a report.

Reports should ideally include:

- Executive summary.
- Key findings.
- Evidence table.
- Source list.
- Confidence level.
- Open questions.
- Risks or warning signs.
- Suggested follow-up research.

The system should also produce a final integrated company research report that combines the outputs of all relevant agents.

## 5. Monitoring Requirements

The system should eventually support monitoring a watchlist of 10-20 companies.

For V1, restrict the watchlist to:

- PDD Holdings.
- Google / Alphabet.
- Tencent.

Potential monitoring topics:

- New filings.
- Earnings releases.
- Management changes.
- Major news.
- Customer sentiment changes.
- Product issues.
- Valuation changes.
- Competitor developments.
- Red flags.

Monitoring should be separate from full deep research. The system should be able to decide when a monitored company needs deeper follow-up.

For V1 monitoring:

- Cadence: weekly.
- Triggers: new filing and management change.
- Price-drop monitoring is intentionally out of scope for now.

## 6. Open Design Questions

### 6.1 Investment Framework

1. What is your current value-investing framework?
2. Are there investors or books that heavily shape your thinking, such as Buffett, Munger, Li Lu, Phil Fisher, Joel Greenblatt, Terry Smith, Peter Lynch, Howard Marks, or others?
3. Do you prefer quality-first investing, deep value, compounders, special situations, growth at a reasonable price, or a mix?
4. What usually makes you reject a company quickly?
5. What usually makes you become seriously interested in a company?

### 6.2 Company Coverage

1. Which 10-20 companies do you want to monitor first?
2. Which markets should be prioritized first: U.S., Hong Kong, mainland China A-shares, ADRs, or all of them?
3. Do you want the first prototype to support both English and Chinese sources immediately, or should we build one market first and add the other next?
4. Do you want the system to research private companies or only public companies?

### 6.3 Source Policy

1. Which sources do you trust most for U.S. companies?
2. Which sources do you trust most for Chinese companies?
3. Are paid data sources available, such as Bloomberg, FactSet, Capital IQ, Wind, Futu, Koyfin, TIKR, QuickFS, or others?
4. Should the system use free sources only at first?
5. Should unofficial sources be allowed only for qualitative research, or can they also be used as secondary financial checks?

### 6.4 Financial Data Requirements

1. Which financial statements and metrics matter most to you?
2. Do you want the system to extract five years, ten years, or all available history? Answer: all available public-company history by default.
3. Should the system normalize accounting differences between U.S. GAAP, IFRS, and Chinese accounting standards?
4. Should the system handle restatements and different fiscal year calendars?
5. Do you want raw extracted tables stored in a local database?

### 6.5 Metrics and Formula Management

1. What are the first metrics you want calculated?
2. Do you already have preferred formulas for owner earnings, return on invested capital, free cash flow, maintenance capex, or intrinsic value?
3. Should formulas be editable in configuration files, a database, or code?
4. Do you want formula versioning so past reports can be reproduced exactly?
5. Should agents explain both the formula result and the weakness of the formula?

### 6.6 Learning Materials

1. What learning materials do you want to provide first?
2. Should materials be assigned to specific agents by you, or should the system recommend which agent should learn from each material?
3. Should agents summarize what they learned before using the material in future reports?
4. Do you want approval before an agent updates its rules, formulas, or report templates based on new material? Answer: yes.
5. Should the system keep a separate "investment knowledge base" shared across agents?

### 6.7 Report Style

1. Do you prefer reports in Markdown, PDF, Word, web dashboard, or all of these? Answer for V1: Markdown only.
2. Should the final report be concise, long-form, or both?
3. Do you want a standard report template for every company?
4. Should each report include direct quotes from filings and interviews?
5. Do you want a final investment checklist with pass/fail/uncertain items?

### 6.8 Human Review and Control

1. Which steps require your approval before the system continues? Answer: formula changes, source conflicts, low-quality source usage, and important valuation assumptions.
2. Should the system ask you before using lower-quality sources? Answer: yes.
3. Should the system ask you before adding a new source to its trusted-source list?
4. Should the system flag uncertain conclusions instead of trying to force a final answer?
5. Do you want the system to produce an "investment memo" only after all agent checks pass?

### 6.9 Technical Architecture

1. Do you want this as a command-line tool first, a local web app, or both?
2. Should reports and data be stored locally, in a database, or in cloud storage?
3. Which LLM provider do you want to use first?
4. Do you have API keys for OpenAI, Anthropic, Google, or others?
5. Should the system use LangGraph for the multi-agent workflow and LangChain for tools, retrieval, and integrations?
6. Should the system run fully locally except for LLM/API calls?

### 6.10 Evaluation and Quality Control

1. How should we judge whether a research report is good?
2. What kinds of mistakes are unacceptable?
3. Should we build test cases using companies you already know well?
4. Should the system compare its outputs against your own past investment memos?
5. Should every final report include an audit section showing what was checked and what remains uncertain?

## 7. Proposed First Milestone

Build a small but real prototype around one company.

Suggested first milestone:

1. User chooses one U.S. company or one Chinese company.
2. System pulls official financial reports.
3. Financial Reports Agent extracts key numbers.
4. Financial Verification Agent cross-checks selected numbers.
5. Metrics Agent calculates a small set of formulas.
6. System produces an auditable Markdown report with sources, confidence, and open questions.

This first milestone should prove the core reliability and audit workflow before adding all other agents.

## 8. Current Decisions and User Answers

### 8.1 First Candidate Companies

The first prototype candidates are:

- PDD Holdings.
- Tencent.
- Google / Alphabet.

First technical prototype:

Start with PDD Holdings.

Rationale:

- The user chose PDD as the first prototype company.
- PDD is a useful early stress test because it requires handling a Chinese-origin business, ADR/company filings, platform accounting, stock-based compensation, cross-border cash, and qualitative research across English and Chinese sources.
- Google / Alphabet and Tencent remain useful follow-up targets after the first PDD workflow is working.

Expansion order:

1. PDD.
2. Tencent.
3. Google / Alphabet.

### 8.2 Market Coverage

The system should support both U.S. and Chinese companies.

This means the architecture should eventually handle:

- U.S. SEC filings and investor relations pages.
- Chinese-language company disclosures.
- Hong Kong exchange disclosures where relevant.
- ADR structures where relevant.
- English and Chinese source material.
- Differences between U.S. GAAP, IFRS, and Chinese accounting standards.

### 8.3 LLM Provider

The first LLM provider should be OpenAI.

The system should still be designed with an abstraction layer so another model provider can be added later if needed.

### 8.4 Data Sources for V1

V1 should use free and public sources only.

Paid sources such as Bloomberg, FactSet, Capital IQ, Wind, Futu, Koyfin, TIKR, or QuickFS should not be required for the first version.

### 8.5 Financial Metrics

The user provided a separate document describing the preferred financial metrics and formulas:

- https://docs.google.com/document/d/1iLIyVMtzrEB3N2jRQfHAnhWjie_kbNZSRrN9b_hEaFs/edit?tab=t.0

Extracted V1 metric requirements are tracked in:

- `docs/metrics-formula-requirements-v1.md`

The metrics agent should support configurable formulas, formula versioning, formula explanation, adjustment notes, and human review for controversial formula choices.

### 8.5.1 Financial History Default

The system should collect all available public-company history by default rather than limiting extraction to five or ten years.

Investment preference note:

- The user generally expects investable companies to be less than 50 years old.
- This should not truncate data collection. Instead, the system should flag company age and lifecycle stage as part of the investment-context section.

### 8.6 First Interface

Recommendation:

Start with a command-line tool first.

Reasoning:

- It is faster to build.
- It is easier to inspect and debug.
- It keeps the multi-agent workflow transparent.
- It lets us focus first on source quality, extraction, verification, and report generation.
- A local web app can be added after the core workflow is reliable.

The initial CLI should produce local Markdown reports and structured data files.

### 8.6.1 Report Output For V1

V1 should produce Markdown reports only.

Later exports can include PDF, Word, Google Docs, or a local web dashboard, but those should not be required for the first working version.

Report language and checklist:

- V1 reports should be bilingual.
- Every report should end with a checklist for right business model, right people, and right price.
- The system should not produce a final investment conclusion until the later research agents exist.

### 8.7 First Learning Materials

Good first examples of learning materials include:

- Warren Buffett shareholder letters.
- Charlie Munger talks and writings.
- Li Lu talks and writings.
- Phil Fisher-style business quality material.
- Howard Marks memos.
- The user's own notes, checklists, formulas, and investment memos.

The system should support adding these materials gradually and tracking which agents learned from which materials.

Learning approval rule:

- Agents may read learning materials and create candidate lessons.
- Candidate lessons should not automatically change agent behavior.
- The user must approve lessons before they become active rules, formulas, checklists, source preferences, or report-template changes.
- The system should preserve rejected lessons as reference-only notes when useful.
- Candidate lessons should be grouped by agent.
- Candidate lesson statuses should be `candidate`, `approved`, `rejected`, and `retired`.

### 8.8 Human Approval Rules

The system should stop and ask for human approval before proceeding when any of the following occur:

- Formula changes: adding, editing, retiring, or changing interpretation of a formula.
- Learning activation: promoting a candidate lesson into an active rule, formula, checklist, source preference, or report-template change.
- Source conflicts: important facts or financial numbers disagree across sources.
- Low-quality sources: an agent wants to use lower-trust sources for an important claim.
- Valuation assumptions: important assumptions such as discount rate, terminal growth, scenario probabilities, normalized margins, normalized owner earnings, or margin of safety materially affect the conclusion.

For these cases, the system should present:

- The issue.
- The options.
- The evidence.
- The default conservative choice.
- The consequence of approving or rejecting the choice.

The system should not silently continue through these gates.

### 8.9 Verification Rules

Financial verification should use these rules:

- Official filings and company IR are source of record.
- Third-party databases may be used only as sanity checks.
- A mismatch greater than 2% is material and requires human review.
- Rounding differences are accepted automatically if clearly explained and logged.

### 8.10 Confirmed Later Agent Order

After the financial foundation, the non-financial agents should be implemented as separate agents in this order:

1. Business Model / Moat Agent.
2. Leadership / People Agent.
3. Valuation Agent.
4. Customer Happiness Agent.
5. Competitor Comparison Agent.

Allowed later qualitative sources:

- Leadership / people research may use interviews, earnings calls, shareholder letters, YouTube, Bilibili, podcasts, and media reports with source-quality labels.
- Customer happiness research may use Reddit, YouTube, Bilibili, forums, app reviews, product reviews, and other customer/community channels with source-quality labels.

## 9. Updated Proposed First Milestone

Build a CLI prototype using PDD Holdings as the first target company.

V1 should:

1. Accept a company identifier from the command line.
2. Locate official company filings and investor relations documents from free/public sources.
3. Download or reference those documents.
4. Extract a small set of core financial numbers.
5. Store extracted facts with source citations.
6. Run an independent verification pass.
7. Calculate initial metrics after the user provides the metrics document.
8. Produce an auditable Markdown report.

The system should be built with LangGraph for the agent workflow and LangChain for model, tool, retrieval, and document-processing integrations.

## 10. Related Requirement Notes

Additional candidate answers extracted from the user's Google Drive notes are tracked separately in:

- `docs/requirements-answers-from-drive-notes.md`
- `docs/metrics-formula-requirements-v1.md`

These answers should be treated as draft requirements until the user reviews and approves them.
