# 第三层：管理层沟通与叙事裁判 Agent Design V1

状态：短版设计稿，供 review；尚未实现。

本文件定义 Investor Assistant 财报工作流的第三层。现有 `management-communication-evidence-source-checklist-v1.md` 已经列出可用 source，本设计文档补充 agent 的目标、输入输出、处理流程和与第一/第二层的连接方式。

## 1. 定位

第三层不是重新计算财务指标，也不是重新阅读 20-F / 10-K / 6-K / 8-K。它读取 **管理层沟通材料**，判断管理层如何解释业务、战略、利润率压力、资本配置和风险，并评估这些解释是否能补充第一层和第二层留下的问题。

它要回答三类问题：

1. 管理层希望投资者相信什么。
2. 管理层是否正面解释了第一层 / 第二层留下的问题。
3. 管理层叙事里有没有新的战略、业务模式变化、KPI、承诺或风险信号。

第三层的证据权重低于第一层和第二层。它可以提高或降低我们对某个解释的信心，但不能覆盖结构化财务数字、官方 filing 事实或审计文件。

## 2. Source 边界

第三层按文件类型定义，不在同一份文件里拆分“事实归第二层、叙事归第三层”。

进入第三层：

- Earnings call transcripts，包括 prepared remarks 和 Q&A。
- Shareholder letter。
- Investor presentation / earnings deck。
- Investor day / capital markets day deck。
- Investor day / capital markets day transcript and Q&A。
- Conference / fireside chat transcript。
- Management interview transcript / podcast transcript。
- Company official newsroom / product announcement。
- Analyst questions，作为市场关注点和回答质量信号。

不进入第三层：

- Earnings release：第一层抽季度结构化数字，第二层读 release 叙事。
- Proxy / AGM / shareholder meeting materials：第二层读治理、投票、控制权、薪酬、关联交易和股权计划。
- 20-F / 10-K / 10-Q / 6-K / 8-K、附注、MD&A / OFR、审计、ICFR、CAM、债务、税项、VIE、承诺、法律事项和关键会计估计：第二层负责。
- 媒体、卖方报告、专家访谈、渠道检查、用户评论、替代数据和实地调研：以后可以作为第四层，不混入第三层。

## 3. 输入

第三层不应从空白开始读 transcript，而应消费前两层已经形成的问题和叙事。

必要输入：

- `financial_report_pack.json`：第一层指标、红旗、季度趋势和主要问题。
- `official_report_evidence_pack.json`：第二层对问题的官方文件回答、重要叙事、仍未知事项和需要第三层跟踪的问题。
- 第三层 source pack：transcript、deck、shareholder letter、newsroom / product announcement 等原文、元数据和来源质量标签。

推荐从第二层传入的主题：

- 利润率压力到底是主动投入，还是结构性竞争压力。
- 新增收入为什么没有转成新增经营利润。
- 现金流是否依赖营运资本顺风。
- 受限现金、VIE、资金可转移性和资本配置是否需要管理层进一步解释。
- first-party brand、供应链投入、商家支持、Temu / global business 是否改变商业模式、利润率或资本强度。
- 管理层 / 治理变化是否影响执行质量和资本配置纪律。

## 4. 核心任务

### A. 回答前两层留下的问题

对每个问题，第三层只做三件事：

- 管理层怎么解释。
- 这个解释是否具体、可验证、与第一层数字和第二层文件事实一致。
- 还有哪些问题没有被回答。

回答质量建议固定为五类：

- `specific_with_numbers`：给出数字、时间表、机制或可验证目标。
- `specific_without_numbers`：解释具体，但没有量化。
- `directional_only`：只有方向性表述，例如长期投入、高质量发展、生态建设。
- `avoided`：没有正面回答分析师问题。
- `contradicted_by_filings_or_metrics`：与第一层数字或第二层 filing 证据冲突。

### B. 发现新的管理层叙事

第三层还要主动登记不一定来自第一层问题、但可能改变基本面判断的内容：

- 新战略 initiative，例如 first-party brand、供应链投入、全球化、组织重塑。
- 新业务模式变化，例如平台更深介入履约、质量控制、品牌、库存或售后。
- 新 KPI 或 KPI 口径变化。
- 管理层反复强调或突然弱化的主题。
- 管理层在不同场合对同一问题的措辞变化。
- 官方产品、市场、政策或合规公告。

每条新叙事都要回答：它改变了哪一类判断，为什么重要，后续用什么数字验证。

### C. 分析 Q&A 压力

分析师问题不是事实来源，但它能告诉我们市场正在担心什么。第三层应记录：

- 哪些主题被反复追问。
- 管理层是否直接回答问题。
- 回答是否提供可验证机制，还是只重复口号。
- 管理层是否回避单位经济性、利润率、监管、资本配置或新业务风险。

如果多个分析师连续追问同一主题，该主题应进入后续跟踪清单。

## 5. Agent 流程

建议实现为一个独立 agent，不直接修改第一层或第二层 pack。

```text
ManagementCommunicationAgent
├── Source Intake
│   ├── transcript / deck / letter / newsroom classifier
│   ├── source-quality label
│   └── period and event mapper
├── Transcript Normalizer
│   ├── prepared remarks splitter
│   ├── Q&A splitter
│   ├── speaker role tagging
│   └── analyst-question grouping
├── Topic Router
│   ├── layer-one open issues
│   ├── layer-two unresolved items
│   └── company-specific narrative watchlist
├── Claim Extractor
│   ├── management claim
│   ├── strategic commitment
│   ├── KPI mention
│   └── timing / magnitude / mechanism
├── Answer Quality Judge
│   ├── specific_with_numbers
│   ├── specific_without_numbers
│   ├── directional_only
│   ├── avoided
│   └── contradicted_by_filings_or_metrics
├── Consistency Checker
│   ├── compare with layer-one metrics
│   ├── compare with layer-two filing facts
│   └── flag tension or conflict
└── Report Builder
    ├── management_communication_pack.json
    └── management_communication_report.md
```

## 6. 输出

建议新增两个 artifact：

- `management_communication_pack.json`
- `management_communication_report.md`

JSON pack 是 source of truth；markdown report 只从 pack 渲染。

推荐 JSON 顶层结构：

```json
{
  "agent_run": {},
  "source_catalog": [],
  "layer_issue_reviews": [],
  "management_claims": [],
  "new_narratives": [],
  "qa_pressure_topics": [],
  "consistency_flags": [],
  "updates_to_layer2": [],
  "third_layer_watchlist": []
}
```

每个 `layer_issue_review` 建议固定为：

```json
{
  "issue_id": "string",
  "issue_text": "string",
  "management_explanation": "string",
  "answer_quality": "specific_with_numbers | specific_without_numbers | directional_only | avoided | contradicted_by_filings_or_metrics",
  "evidence": [],
  "consistency_with_layer1": "supports | weakens | clarifies | no_change | conflicts",
  "consistency_with_layer2": "supports | weakens | clarifies | no_change | conflicts",
  "still_unknown": [],
  "watch_items": []
}
```

推荐 markdown 结构：

1. 第三层：管理层沟通与叙事裁判（管理层沟通层）。
2. 前两层留下的问题：管理层怎么解释。
3. 管理层新叙事与战略变化。
4. Q&A 压力与回答质量。
5. 与第一层数字 / 第二层 filing 证据的一致性。
6. 仍未知和下一次电话会要追的问题。

正文优先用段落和短 bullet，不要把长解释塞进大表格。只有当同类短字段超过三项、且表格明显更容易比较时，才使用表格。

## 7. PDD Pilot 的优先主题

PDD 的第三层 V1 可以先覆盖以下主题：

1. 利润率压力：管理层是否把压力解释为供应链投入、商家支持、first-party brand、全球化履约，还是承认竞争压力。
2. First-party brand：是否说明库存风险、资本需求、投入节奏、回收周期、对平台模式轻重的影响。
3. 供应链投入和商家支持：是否说明投入金额、受益对象、验证指标和持续性。
4. Temu / global business：是否说明监管、关税、履约成本、市场扩张和单位经济性。
5. 交易服务收入：是否解释交易服务占比提升的来源，是否和商家数量、服务深度、take-rate 或跨境业务有关。
6. 现金和资本配置：是否解释大量现金、受限现金、回购 / 分红缺失和再投资优先级。
7. 管理层与组织变化：是否解释新 leadership、组织重塑、安全合规和社会责任如何影响执行。

## 8. 实现路线

第一步：复用现有 transcript / official event collector，把第三层 source 统一成 `management_communication_sources` 和 `management_communication_segments`。

第二步：先做 earnings call transcript V1。拆 prepared remarks 与 Q&A，输出 topic、claim、answer quality 和 source evidence。

第三步：把第二层的 `still_unknown` 和 `third_layer_follow_up` 路由到 transcript，并把回答结果回填到 easy reading report 的第三层 section。

第四步：加入 deck、shareholder letter、investor day、official newsroom / product announcement。

第五步：做跨季度 promise-vs-outcome 跟踪。管理层承诺过的投入、KPI、利润率恢复、战略进展，需要在后续第一层和第二层中验证。

## 9. 失败模式

- 把 transcript 里的数字当成 source of record，覆盖第一层结构化数字。
- 把方向性口号写成已证明事实。
- 用管理层解释替代第二层 filing 证据。
- 只总结 prepared remarks，不分析 Q&A 追问。
- 把 analyst question 当作事实来源。
- 把媒体、卖方、专家访谈和替代数据混入第三层，导致证据权重混乱。
