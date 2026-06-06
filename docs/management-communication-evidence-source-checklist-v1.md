# 第三层：管理层沟通与叙事材料 Source Checklist V1

配套设计文档：`docs/management-communication-agent-design-v1.md`。本文件只定义第三层 source 清单；agent 的输入输出、流程、质量判断和实现路线以配套设计文档为准。

## 定位

第三层按“文件类型”定义，不再在同一份文件里拆分事实和叙事。它的任务是读取管理层沟通材料，判断公司如何讲述业务、战略、利润率压力、资本配置和风险，并观察管理层是否正面回答市场关心的问题。

第三层不替代第一层的财务数字，也不替代第二层的官方 filing 证据。它主要回答：

1. 管理层希望投资者相信什么。
2. 管理层叙事是否解释、强化、削弱或回避第一层和第二层留下的问题。
3. 分析师 / 投资者追问集中在哪里，管理层回答质量如何。

## 硬边界：按文件路由

一份文件只进入一个层级。

- 第一层：结构化财务抽取和指标计算。若季度数字只能从 earnings release 抽取，第一层可以使用它作为数字来源，但不生成叙事判断。
- 第二层：监管 filings、年度/季度报告、附注、审计、风险、重大事项、治理事实，以及 earnings release 的管理层叙事。
- 第三层：管理层沟通材料和叙事材料。

不要在同一份文件中拆成“事实归第二层、叙事归第三层”。这会让实现和 review 变复杂。

## 第三层 Source 清单

### 1. Earnings Call Transcripts

优先级：最高。

用途：
- 拆分 prepared remarks 和 Q&A。
- Prepared remarks 看管理层主动强调什么。
- Q&A 看分析师真正追问什么，以及管理层是否正面回答、回避、重复口号或给出可验证机制。

注意：
- Transcript 中的财务数字不能覆盖第一层 / 第二层 source of record。
- 如果 transcript 数字与官方 filing 或第一层结构化数字冲突，标记为冲突。

### 2. Shareholder Letter

优先级：高。

用途：
- 读取管理层长期叙事、资本配置哲学、战略重点和风险框架。
- 对比不同年度 shareholder letter 的措辞变化。
- 判断管理层是否持续坚持同一套经营原则，或出现战略迁移。

### 3. Investor Presentation / Earnings Deck

优先级：高。

用途：
- 看管理层如何组织故事：哪些图表放在前面，哪些 KPI 被反复展示，哪些业务线被弱化。
- 识别新增 KPI、KPI 口径变化、业务线拆分、增长来源和管理层选择强调的指标。
- 判断 deck 是否比 filings 更积极，或是否回避 filings 中出现的压力点。

### 4. Investor Day / Capital Markets Day Deck

优先级：中高。

用途：
- 读取长期战略、长期利润率框架、资本配置框架、业务模式变化和管理层目标。
- 适合跟踪供应链、自营品牌、全球化、组织变化、新业务投入周期。
- 这些长期目标不能当成已发生事实，必须用后续 filings 和季度结果验证。

### 5. Investor Day / Capital Markets Day Transcript and Q&A

优先级：中高。

用途：
- 读取管理层对长期战略问题的现场回答。
- 观察长期利润率框架、资本配置框架、业务模式转型是否被追问，以及管理层回答是否具体。

### 6. Conference / Fireside Chat Transcripts

优先级：中。

用途：
- 捕捉管理层对竞争、监管、利润率、供应链、产品策略的非正式解释。
- 看管理层是否在不同场合重复同一套叙事，或出现措辞变化。

### 7. Management Interview Transcripts / Podcasts

优先级：中。

用途：
- 读取管理层对组织、文化、长期战略、产品、竞争和资本配置的解释。
- 只能作为管理层叙事证据，不能作为财务事实来源。

### 8. Company Official Newsroom / Product Announcements

优先级：中。

用途：
- 跟踪新业务、新产品、新市场、商家政策、物流 / 供应链项目、合规动作。
- 对 PDD 这类公司，可用于跟踪 first-party brand、供应链扶持、农业项目、Temu 市场扩张等。

注意：
- 官方新闻可以证明“公司宣布了什么”，不能证明财务效果。

### 9. Analyst Questions

优先级：辅助但重要。

用途：
- 分析师问题本身不是事实来源，但能反映市场最关心的未解问题。
- 如果多个分析师反复追问同一主题，例如利润率、Temu 单位经济性、供应链投入、监管、first-party 风险，说明它应进入后续验证清单。
- 还可以判断管理层是否正面回答，或只给方向性表述。

## 第二层保留的 Source

为了避免重复，以下文件不进入第三层：

- 20-F / 10-K / Annual Report。
- 10-Q / formal quarterly report。
- 6-K / 8-K material event filing。
- Earnings Release：第一层可以抽结构化季度数字；第二层读取整份 release 的管理层叙事、CEO / CFO quote、non-GAAP 解释和季度口径；第三层不读取。
- Proxy / AGM / Shareholder Meeting Materials：第二层读取董事会、投票、控制权、薪酬、关联交易、股权计划和股东会事项。
- Prospectus / S-1 / F-1 / 424B。
- Audit report / ICFR / CAM。
- Footnotes / notes / MD&A / OFR。
- Debt, tax, VIE, restricted cash, legal, commitments, accounting policy and critical estimate disclosures。

## 暂不纳入第三层的外部 sources

这些 sources 以后可以做第四层，不建议混入第三层：

- 媒体报道。
- 卖方报告。
- 专家网络访谈。
- 用户评论、商家评论、Reddit / 社区内容。
- 替代数据，例如 app ranking、web traffic、SKU、物流、卫星、招聘数据。
- 竞争对手访谈、渠道检查、scuttlebutt、实地调研。

原因：这些 sources 已经不是管理层沟通，而是外部验证或一手研究。如果混在第三层里，会让证据权重变乱。

## 推荐输出结构

每个主题用同一套结构：

```text
主题：
关联的第一层 / 第二层问题：
管理层怎么说：
管理层强调了什么：
回答质量：
与财务数字或 filing 证据是否一致：
仍需验证：
```

回答质量建议分为：

- `specific_with_numbers`：管理层给出具体数字或可验证机制。
- `specific_without_numbers`：解释具体，但缺少量化。
- `directional_only`：只有方向性表述。
- `avoided`：没有正面回答。
- `contradicted_by_filings_or_metrics`：与第一层 / 第二层证据冲突。
