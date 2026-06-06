# Official Report Evidence Agent Design V1

状态：短版设计稿，供 review；尚未实现。

本文件定义 Investor Assistant 财报工作流的第二层。第一层负责从官方文件中确定性抽取和计算财务指标；第二层负责阅读官方文件文本，解释第一层留下的问题，并主动发现可能改变投资判断的重要官方叙事、事件和公司特有 KPI。

## 1. 核心目标

第二层不是重新计算指标，也不是估值或买卖建议。它是一个 **官方文件证据裁判 + 官方叙事发现器**。

它要完成三件事：

1. 回答第一层指标留下的问题。
2. 主动发现会影响投资判断的重要官方叙事、initiative、事件、管理层/治理变化和公司特有 KPI。
3. 更新第一层判断的置信度，并把官方文件无法回答的问题转交给 earnings call、专家访谈、渠道检查或实地研究层。

## 2. 与其他层的边界

### 第一层：Financial Metrics / Diagnostic Agent

第一层负责：

- 抽取财务事实。
- 计算收入、利润率、现金流、营运资本、资产负债表、SBC、non-GAAP 等指标。
- 发现异常和红旗。
- 给出 annual baseline 与 latest quarter trend status。

### 第二层：Official Report Evidence Agent

第二层负责：

- 从 20-F / 10-K / 10-Q / 6-K / 8-K / 附注 / MD&A / OFR / risk factors / liquidity 等官方文件里找证据。
- 区分文件事实、管理层解释、我们的推断和仍未知。
- 判断管理层解释是否能被第一层数字支持。
- 提取重要官方叙事和决策相关事件。

### 第三层：Management Communication / Transcript Agent

第三层才使用：

- earnings call transcript。
- shareholder letter。
- investor presentation / earnings deck。
- investor day / capital markets day deck。
- official newsroom / product announcement。
- Q&A。
- management interview。
- prepared remarks。
- tone / pressure / analyst challenge。

第二层不能使用这些来源。

## 3. 允许和禁止使用的来源

允许：

- 20-F / 10-K / annual report。
- 10-Q / quarterly 6-K / interim report。
- 8-K / material 6-K / official event filing。
- Earnings release：第一层可抽结构化数字；第二层读取 release 的管理层叙事、CEO / CFO quote、non-GAAP 解释和季度口径。
- Proxy / AGM / shareholder meeting materials：治理、控制权、关联交易、薪酬、稀释、股权计划、董事会和投票事项。
- MD&A / Operating and Financial Review。
- footnotes。
- risk factors。
- liquidity and capital resources。
- critical accounting estimates。
- segment / product / geography / customer / KPI disclosure。

禁止：

- earnings call transcript。
- shareholder letter。
- investor presentation / earnings deck。
- investor day / capital markets day deck。
- official newsroom / product announcement。
- investor day / conference / fireside chat transcript。
- Q&A transcript。
- interviews。
- media。
- sell-side。
- expert network。
- channel check。
- alternative data。
- field research。

## 4. 三条工作主线

### A. 第一层问题复核

从 `financial_report_pack.json` 中的 `diagnostic_findings`、red flags、trend status 和 material event scan 出发。

典型问题：

- 利润率为什么下降？
- 增量经营利润率为什么为负？
- 现金流是不是靠营运资本顺风？
- 受限现金、VIE、债务、税项、承诺是否重要？
- non-GAAP 调整是否合理？
- 公司特有 KPI 是否解释了财务变化？

每个问题都按固定结构输出：

- 文件事实。
- 管理层解释。
- 与第一层数字交叉验证。
- 我们的推断。
- 仍未知。
- 对第一层判断的影响。

### B. 决策相关官方叙事与事件发现

这一部分不是回答第一层问题，而是主动发现官方文件里可能改变投资判断的内容。

进入报告的条件：必须至少影响以下一项。

- 收入来源或增长空间。
- 利润率结构。
- 资本强度或现金流质量。
- 资产负债表安全性。
- 会计可靠性。
- 管理层执行、治理、控制权或稀释。
- 监管、法律、VIE、税项、跨境资金风险。
- 公司特有 KPI 的定义、口径或披露质量。

例子：

- 新战略 initiative。
- 商业模式从轻变重，或从平台变成更深供应链/履约/品牌控制。
- 管理层、董事会、审计师变化。
- 重大融资、回购、收购、处置或投资计划。
- 内控缺陷、重述、会计政策或关键估计变化。
- 新 KPI，或原有 KPI 的定义/披露变化。

PDD pilot 中应特别关注：

- transaction services revenue。
- first-party brand。
- supply-chain investment。
- merchant support。
- global business / Temu。
- restricted cash。
- VIE。
- auditor / governance changes。
- 官方 KPI 披露缺口。

### B1. 与第三层的去重规则

为了让工程实现简单，第二层和第三层按文件类型分，不在同一份文件中拆分“事实”和“叙事”。

归第二层：

- 20-F / 10-K / annual report。
- 10-Q / formal quarterly report。
- 8-K / material 6-K / official event filing。
- Earnings release：第一层抽数字，第二层读叙事，第三层不读。
- Proxy / AGM / shareholder meeting materials。
- Prospectus / S-1 / F-1 / 424B。
- Audit report / ICFR / CAM。
- Footnotes / notes / MD&A / OFR。
- Debt, tax, VIE, restricted cash, legal, commitments, accounting policy and critical estimate disclosures。

归第三层：

- earnings call transcript。
- shareholder letter。
- investor presentation / earnings deck。
- investor day / capital markets day deck。
- official newsroom / product announcement。
- Q&A。
- investor day Q&A transcript。
- conference / fireside chat transcript。
- management interview transcript。

Earnings release 是明确例外：第一层为了计算季度数字，可以抽取结构化财务数据；第二层读取 release 文本中的管理层叙事；第三层不读取 earnings release。

### C. 置信度更新与下一层研究路由

第二层最后要回答：

- 哪些第一层判断被官方文件支持？
- 哪些第一层判断被削弱？
- 哪些只是被解释了，但仍没有被证明？
- 哪些问题官方文件仍然没有回答？
- 哪些问题应该交给 earnings call？
- 哪些问题应该交给 expert / channel check / field research？

第一份 deep research 文档中的 scuttlebutt、channel check、expert network、field research 不进入第二层输入，但会进入第二层输出的后续研究问题。

## 5. 证据标签

每条输出必须使用下面四类之一：

| 标签 | 含义 | 使用规则 |
| --- | --- | --- |
| `filing_fact` | 官方文件直接披露的数字、表格、合同、事项、风险或会计政策 | 可以直接支持判断 |
| `management_explanation` | 官方文件中管理层对变化原因或战略方向的解释 | 只能说明管理层怎么解释，不能单独证明 |
| `our_inference` | 基于文件事实、管理层解释和第一层数字形成的推断 | 必须标注为推断 |
| `unknown` | 官方文件没有足够信息回答 | 必须保持未知，不能脑补 |

辅助分类：

- `risk_disclosure`
- `accounting_policy`
- `critical_estimate`
- `KPI_definition`
- `covenant_or_restriction`
- `capital_allocation`
- `legal_or_regulatory_event`
- `management_or_governance_change`

## 6. 输出文件

建议新增两个 artifact：

- `official_report_evidence_pack.json`
- `official_report_evidence_report.md`

JSON pack 是 source of truth；markdown report 只从 pack 渲染。

不要直接覆盖第一层的 `financial_report_pack.json`。

## 7. 简化 JSON 结构

```json
{
  "agent_run": {
    "company_id": "PDD",
    "source_policy": "official_filings_only",
    "annual_report_used": true,
    "quarterly_reports_used": true,
    "event_reports_used": true
  },
  "question_answers": [
    {
      "question_id": "margin_decline",
      "answer_status": "answered | partial | unknown | contradicted",
      "short_answer": "...",
      "filing_facts": [],
      "management_explanations": [],
      "our_inference": {
        "text": "...",
        "confidence": "high | medium | low"
      },
      "still_unknown": [],
      "impact_on_layer1": "supports | weakens | clarifies | no_change",
      "evidence_bundle": []
    }
  ],
  "decision_relevant_narratives": [
    {
      "narrative_id": "pdd_first_party_brand",
      "narrative_type": "strategic_initiative | business_model_change | KPI | regulation | governance | accounting | capital_allocation",
      "change_status": "new | strengthened | repeated | de_emphasized",
      "title": "...",
      "filing_facts": [],
      "management_explanations": [],
      "why_it_matters": "...",
      "linked_layer1_metrics": [],
      "our_inference": "...",
      "still_unknown": [],
      "impact_on_investment_judgment": "supports | weakens | clarifies | creates_new_question",
      "follow_up_needed": []
    }
  ],
  "layer1_update": {
    "confidence_up": [],
    "confidence_down": [],
    "clarified": [],
    "still_unknown": [],
    "next_research_questions": []
  }
}
```

每条 evidence 至少保留：

- evidence id。
- evidence type。
- source document type。
- source document。
- source section。
- filing date。
- period。
- accession number，如果有。
- local file path。
- paragraph anchor 或 page reference，如果有。
- quote or summary。
- linked layer1 metrics。
- cross validation status：`matched | tension | mismatch | not_tested`。

## 8. 阅读 SOP

1. 读取 `financial_report_pack.json`。
2. 从第一层 diagnostic questions、red flags、trend changes 和 material event scan 建立问题队列。
3. 从公司 watchlist、form type、prior narratives 建立主动 narrative scan 队列。
4. 把每个问题或 narrative route 到对应 section。
5. 在官方文件中做 section-aware retrieval。
6. 把 passage 分类为文件事实、管理层解释、风险披露、KPI 定义、会计政策、限制条款、事件或未知。
7. 用第一层数字交叉验证管理层解释。
8. 给每个问题标记 `answered`、`partial`、`unknown` 或 `contradicted`。
9. 只有通过 decision-relevance gate 的 narrative 才生成 narrative card。
10. 输出 JSON pack。
11. 渲染 markdown report。

## 9. 报告结构

```markdown
# Official Report Evidence And Explanation

## 1. 第一层问题复核

### 利润率为什么下降？
- 文件事实：
- 管理层解释：
- 与第一层数字交叉验证：
- 我们的推断：
- 仍未知：
- 对第一层判断的影响：

## 2. 决策相关官方叙事与事件

### Strategic initiatives
- 文件事实：
- 管理层解释：
- 为什么重要：
- 关联指标：
- 我们的推断：
- 仍未知：
- 后续跟踪：

### Business model / KPI / governance / regulation / accounting
...

## 3. Business Model And Moat Hypothesis

- 当前官方文件支持的商业模式假设：
- 官方证据：
- 官方文件不能证明什么：
- 下一层研究问题：

## 4. 对第一层判断的更新

- 提高置信度：
- 降低置信度：
- 已解释：
- 仍未知：
- 新增红旗：
- 下一次官方报告优先验证：

## 5. 下一层研究路由

- Earnings-call questions：
- Expert / channel-check questions：
- Field-research questions：
```

## 10. Implementation Roadmap

### Phase 1: Review And Finalize Design

- 确认 report structure。
- 确认 JSON schema。
- 决定是否替换现有 `financial_investigation_notes`，还是作为新 artifact 并行存在。

### Phase 2: Deterministic Foundation

- 建立 official filing section catalog。
- 建立 question-to-section routing rules。
- 建立 keyword families：margin、cash flow、restricted cash、VIE、debt、tax、non-GAAP、KPI、accounting estimates、governance、events。
- 做 schema validation。

### Phase 3: LLM Skill Layer

- passage classification。
- 文件事实 / 管理层解释 / 我们推断 / 仍未知拆分。
- narrative card 生成。
- 下一层研究问题生成。

### Phase 4: PDD Pilot

先用 PDD 验证：

- 2025 利润率下降是否能被官方文件解释。
- supply-chain investment 是否能解释利润率压力。
- 经营现金流是否依赖营运资本顺风。
- restricted cash / VIE 是否影响现金可用性判断。
- transaction services revenue 是否改变 business model read。
- first-party brand 和 merchant support 是否是重要官方 narrative。
- 还有哪些问题官方文件无法回答。

### Phase 5: Integration

- 在 run artifacts 中新增 `official_report_evidence_pack.json`。
- 生成 `official_report_evidence_report.md`。
- 让 easy-reading financial report 可以引用第二层摘要，但不混淆 source of truth。

## 11. 需要讨论的决策

- 第二层是否替代当前 `financial_investigation_notes`，还是先并行存在？
- V1 是否必须做 prior-period narrative diff，还是先用 current filing + company watchlist？
- evidence pack 中保存直接短引用，还是只保存摘要和 source anchor？
- 管理层 / 治理变化是否先由 material-event scanner 发现，再由第二层展开？
- PDD pilot 是否只用 latest annual + latest quarter，还是加入历史 6-K 来看叙事变化？
