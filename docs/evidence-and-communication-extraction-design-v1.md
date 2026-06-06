# Evidence & Communication Extraction Design V1

状态：MVP 已接入主流程；旧 split packs 仍作为迁移兼容输入保留。

本文件把原来的 `Official Report Evidence Agent` 和 `Management Communication Agent` 合并为一个 **非数字证据抽取层**。它不替代 `Financial Extraction Agent`，而是消费第一层数字和问题，把官方文件、业绩稿、电话会和管理层沟通材料里的解释、叙事、风险、未披露事项抽成结构化证据。

## 1. 目标

这个 extraction 层有两个同等重要的任务：

1. **问题复核**：对第一层财务数字留下的问题，官方记录和管理层沟通到底证明了什么、解释了什么、只是声称了什么、仍然没有回答什么？
2. **主动发现**：即使第一层没有触发红旗，也要从官方文件和管理层沟通中发现新的业务模式变化、战略 initiative、公司特有 KPI、治理变化、监管/法律事项、会计估计变化、风险升级和潜在机会问题。

它的输出应服务于：

- `Financial Research Draft`
- HTML visual report
- 下一轮 financial extractor backlog
- feedback loop router
- 后续人工复核

它不是估值模型，不生成买卖建议，不重新计算财务指标。

## 2. 与 Financial Extraction 的边界

`Financial Extraction` 只负责数字事实：

- 三张表主干
- 收入拆分
- 成本、费用、利润桥
- 现金流和营运资本桥
- 资产负债表、债务、SBC、股数、non-GAAP bridge

`Evidence & Communication Extraction` 负责文字和解释证据：

- 官方文件如何解释这些数字
- 附注、MD&A、风险因素、proxy 是否支持或限制第一层判断
- 管理层在电话会、业绩稿、deck、newsroom 中如何叙事
- 分析师追问什么，管理层是否正面回答
- 哪些问题仍然未知，应该回流给 financial extractor

缺失数字不能靠 narrative 补。管理层说法不能变成 filing fact。

## 3. Source Scope

本层内部保留两条 lane，但输出一个统一 pack。

### Lane A：Official Filing Evidence

允许来源：

- 20-F / 10-K / annual report
- 10-Q / quarterly 6-K / interim report
- material 6-K / 8-K
- earnings release 的叙事、CEO/CFO quote、non-GAAP 调节说明
- proxy / AGM / shareholder meeting materials
- MD&A / OFR
- footnotes
- risk factors
- liquidity and capital resources
- critical accounting estimates
- audit report / ICFR / CAM
- segment、geography、product、KPI disclosure

### Lane B：Management Communication Evidence

允许来源：

- earnings call transcripts，包括 prepared remarks 和 Q&A
- shareholder letter
- investor presentation / earnings deck
- investor day / capital markets day deck and transcript
- conference / fireside chat transcript
- management interview transcript / podcast transcript
- official newsroom / product announcement
- analyst questions，作为 concern signal，不作为事实

### 不允许来源

- media
- sell-side
- expert network
- channel check
- social media
- user reviews
- alternative data
- AI summary

这些以后可以作为第四层或 alternative-data 层，不混入本层。

## 4. Pipeline 位置

当前主流程：

```text
1. Source Collection
2. Financial Extraction
3. Financial Metrics / Diagnostics
4. Financial Report Pack
5. Layer-One Question Pack
6. Evidence & Communication Extraction
7. Feedback Loop Router
8. Financial Research Draft
9. HTML Visual Report
```

本层输入第一层的 metrics、diagnostic findings、question dockets 和 disclosure gaps；输出统一的 `evidence_communication_pack.json`。

本层不自己执行回流。它负责产出 `handoff_to_financial_extractor`、`unknowns` 和 `proactive_discoveries`；后续 `Feedback Loop Router` 负责把这些对象路由回 Financial Extraction、Metrics、Layer 1、Evidence/Communication、外部数据或人工复核，并写出 `feedback_loop_pack.json`。

MVP 阶段当前保留现有：

- `official_report_evidence_pack.json`
- `management_communication_pack.json`

新的统一 pack 已经成为 `Financial Research Draft` 的主输入之一。旧 split packs 当前由 `Evidence & Communication Extraction Agent` 内部生成并写出，主要用于迁移期测试、对照和避免 Easy Report / legacy report 断裂；新增概念优先进入 unified pack。

## 5. 输入

必要输入：

- `financial_report_pack.json`
- `layer1_question_pack.json`
- official filing source catalog
- official event / transcript source catalog
- company-specific watchlist

推荐输入字段：

```json
{
  "company_id": "pdd",
  "period": {
    "annual_end": "2025-12-31",
    "latest_quarter_end": "2026-03-31"
  },
  "financial_report_pack_path": "data/runs/.../financial_report_pack.json",
  "layer1_question_pack_path": "data/runs/.../layer1_question_pack.json",
  "questions": [],
  "financial_flags": [],
  "disclosure_gaps": [],
  "official_sources": [],
  "communication_sources": [],
  "company_watchlist": [
    "transaction services",
    "online marketing services",
    "Temu",
    "global business",
    "first-party brand",
    "merchant support",
    "supply-chain investment",
    "restricted cash",
    "VIE"
  ]
}
```

## 6. 输出

主输出：

- `evidence_communication_pack.json`
- `evidence_communication_report.md`
- handoffs consumed by `feedback_loop_pack.json`

Pack 顶层结构：

```json
{
  "agent_run": {
    "run_id": "",
    "company_id": "",
    "generated_at": "",
    "source_policy": "official_and_management_communication_only"
  },
  "source_inventory": [],
  "question_answers": [],
  "proactive_discoveries": [],
  "narrative_registry": [],
  "management_claims": [],
  "analyst_concerns": [],
  "unknowns": [],
  "handoff_to_financial_extractor": [],
  "quality_flags": []
}
```

闭环输出由下一节点负责：

```json
{
  "schema_version": "feedback_loop_pack_v1",
  "financial_extractor_requests": [],
  "metric_recalculation_requests": [],
  "layer1_requery_requests": [],
  "evidence_communication_followups": [],
  "external_data_requests": [],
  "human_review_requests": []
}
```

## 7. Evidence Labels

每条证据必须有一个主标签：

| Label | 定义 |
| --- | --- |
| `filing_fact` | 官方 filing、附注、表格、审计、proxy 中直接披露的事实 |
| `management_explanation` | MD&A、OFR、earnings release 中管理层对历史变化的解释 |
| `risk_disclosure` | 风险因素、法律事项、监管、VIE、税项、或有事项等风险披露 |
| `management_claim` | 电话会、deck、letter、newsroom 中的战略、承诺、目标或前瞻说法 |
| `analyst_concern` | 分析师问题体现的市场关注点，不是事实证据 |
| `our_inference` | 基于多个证据和第一层数字的推断，必须明确标注 |
| `unknown` | 当前允许来源没有回答，或证据不足以支持判断 |

禁止把 `management_claim` 写成 `filing_fact`。  
禁止用 risk factor 证明某件事已经发生。  
禁止在没有来源的情况下使用 “因为 / driven by / 导致”。

## 8. Question Answer Object

每个问题输出一个对象：

```json
{
  "question_id": "Q1",
  "question": "新增收入为什么没有带来新增经营利润？",
  "status": "answered | partial | unknown | conflicted",
  "short_answer": "",
  "why_it_matters": "",
  "financial_trigger": [],
  "official_evidence": [],
  "management_communication": [],
  "consistency_check": {
    "vs_financial_metrics": "consistent | mixed | contradicted | not_tested",
    "vs_official_filing": "consistent | mixed | contradicted | not_applicable"
  },
  "our_inference": "",
  "still_unknown": [],
  "handoff_to_financial_extractor": [],
  "confidence": {
    "label": "low | medium | high",
    "reason": ""
  }
}
```

`answered` 要求至少一个直接证据和没有重大冲突。  
`partial` 用于“管理层解释了方向，但没有量化或无法交叉验证”。  
`unknown` 是正常输出，不是失败。  
`conflicted` 用于官方事实或财务数字明显削弱管理层解释。

## 9. Narrative Registry Object

本层不只回答第一层问题，也要登记重要新叙事、新风险和新机会问题。很多重要变化不会先出现在三张表里，而是先出现在业务描述、MD&A、业绩稿、电话会、proxy、risk factor 或 newsroom 里。

```json
{
  "narrative_id": "",
  "title": "",
  "type": "business_model | revenue_mix | strategy | cost_structure | cash_constraint | governance | accounting | regulation | KPI",
  "change_status": "new | changed | repeated | de_emphasized | unknown",
  "summary": "",
  "why_it_matters": "",
  "evidence_items": [],
  "linked_questions": [],
  "creates_new_question": true,
  "new_question_text": "",
  "monitoring_metrics": [],
  "unknowns": []
}
```

进入 narrative registry 的门槛：

- 可能改变收入来源或增长质量
- 可能改变利润率、成本结构或资本强度
- 可能改变现金可用性、VIE、债务、承诺或资本配置判断
- 可能影响会计可靠性、审计、内控或 non-GAAP 判断
- 可能影响治理、稀释、控制权或少数股东利益

主动发现示例：

- 新战略：first-party brand、供应链投入、RMB 100B plan、全球扩张。
- 新业务模式：平台是否更深介入库存、履约、质量控制、售后、品牌孵化。
- 新 KPI：交易服务、活跃商家、GMV、take rate、订单、履约成本。
- 风险升级：监管、产品安全、税务、VIE、跨境资金、诉讼。
- 治理变化：CEO / CFO / 董事会 / 审计师 / 股权计划 / ADS 权利。
- 叙事变化：从高增长转向高质量发展、从利润率转向生态投入、从轻平台转向供应链深耕。

## 10. Execution SOP

### Step 1：建立问题队列

问题队列由两部分组成：第一层 handoff 问题 + 本层主动发现问题。

从第一层导入：

- standard questions
- red flags
- diagnostic findings
- disclosure gaps
- extractor backlog

本层主动新增：

- official filing 中首次出现、显著加强或显著弱化的叙事。
- management communication 中首次出现、被反复强调或被分析师集中追问的主题。
- 与第一层数字没有直接对应，但可能改变投资判断的事项。
- 公司特有 KPI 的定义、口径、披露频率或缺失。
- 官方文件或电话会没有解释清楚、但足以形成下一轮研究问题的空白。

PDD MVP 至少覆盖：

- Q1 新增收入为什么没有带来新增经营利润
- Q2 利润率压力是主动投入还是结构性竞争压力
- Q3 经营现金流是否依赖营运资本顺风
- Q4 现金有多少真正可用
- Q5 自营品牌是否让平台模式变重
- Q6 交易服务占比提高意味着什么
- Q7 Temu / 全球业务是否是可验证增长引擎
- Q8 净利润和 non-GAAP 是否掩盖经营质量
- Q9 治理、SBC、稀释和每股价值风险

### Step 2：按问题路由来源

示例：

- margin question：MD&A / OFR、成本表、费用表、earnings release、earnings call Q&A
- cash question：cash flow note、working capital、merchant payable、restricted cash、liquidity、VIE
- strategy question：business section、6-K、earnings release、prepared remarks、Q&A、newsroom
- governance question：proxy / AGM、share plan、ADS rights、ICFR、audit
- proactive narrative discovery：business overview、MD&A / OFR、risk factor diff、earnings release、prepared remarks、Q&A、newsroom、proxy / AGM

### Step 3：抽取证据并打标签

每条 evidence 至少包括：

```json
{
  "evidence_id": "",
  "label": "filing_fact",
  "source_type": "20-F",
  "document_id": "",
  "filing_date": "",
  "period": "",
  "section": "",
  "speaker": "",
  "block_id": "",
  "paraphrase": "",
  "quote_snippet": "",
  "linked_metrics": [],
  "confidence": 0.0
}
```

`quote_snippet` 可以短，避免复制长篇原文。  
如果没有稳定页码，至少保留 section、anchor、block_id 或 source_id。

### Step 4：交叉验证

对每个问题，检查：

- 管理层解释是否能被第一层数字支持
- filing fact 是否支持 management explanation
- risk disclosure 是否只是风险，还是已经有当前期事实
- analyst concern 是否被直接回答
- 是否仍需要 financial extractor 补字段

### Step 5：输出 pack 和 report

Markdown report 只做审阅用。真正给下游 report 使用的是 JSON pack。

## 11. PDD Pilot 要求

PDD 第一版必须能抽出以下主题：

### 官方文件 / 业绩稿

- transaction services 与 online marketing 的收入结构
- 成本、费用、利润率压力的官方解释
- 受限现金、商家资金、VIE、资金转移限制
- first-party brand / RMB 100B plan
- Temu / global business 相关披露和未披露
- non-GAAP reconciliation
- SBC、股数、ADS、AGM、share plan、审计和内控

### 电话会 / 管理层沟通

- 管理层如何解释供应链投入
- 管理层如何解释 first-party brand
- 管理层是否解释利润率路径
- 管理层是否回答在线营销放缓、GMV、take rate、用户留存、Temu 经济性
- 分析师追问是否集中在同一批问题
- 管理层回答质量：给数字、具体但无数字、方向性、回避、冲突

### 回流给 financial extractor

- 成本细项
- 收入组件 YoY / QoQ
- 经营利润以下桥
- 营运资本桥
- 可动用现金 / VIE / 受限现金
- Temu 单独经济性
- 自营品牌单位经济性
- 股数 / SBC / 回购 / 分红桥

## 12. MVP Implementation Plan

### Phase 1：合并 pack schema

新增：

- `src/stock_research/evidence_communication/agent.py`
- `src/stock_research/evidence_communication/__init__.py`
- `docs/evidence-and-communication-extraction-design-v1.md`

输出：

- `evidence_communication_pack.json`
- `evidence_communication_report.md`

短期保留旧 pack 兼容：

- `official_report_evidence_pack.json`
- `management_communication_pack.json`

兼容规则：

- 新代码优先写入和读取 `evidence_communication_pack.json`。
- 旧 pack 只用于迁移期测试、对照和防止现有 report 断裂。
- 不允许在旧 pack 中继续新增新概念；新增字段必须先进入 unified pack。
- 当 `Financial Research Draft` 和 HTML report 不再依赖旧 pack 时，旧 pack 应从主流程删除或降级为兼容导出。

### Phase 2：问题驱动抽取

先实现 PDD Q1-Q9 的 deterministic routing + heuristic extraction。  
不要一开始做全行业泛化。

### Phase 3：接入 Financial Research Draft

让 `financial_research_draft.py` 优先读取 `evidence_communication_pack.json`。  
如果不存在，fallback 到旧的两个 pack。

当前状态：Phase 1-3 的 MVP 已接入。`layer1_question_pack.json` 和 `evidence_communication_pack.json` 会在主 graph 和 `rerun-financial-report` 中生成；Research Draft 会显示这些中间产物并继续兼容旧 pack。

### Phase 4：质量门槛

每个 `partial / answered` 项必须有：

- 证据标签
- 来源类型
- source id 或 block id
- 与第一层指标的关系
- 仍未知

## 13. Acceptance Criteria

PDD run 通过以下检查才算 MVP 完成：

- Q1-Q9 每个问题都有 evidence object。
- 每条 evidence 都有 label 和 source metadata。
- 管理层 claim 不会被标成 filing fact。
- risk disclosure 不会被写成已发生事实。
- 至少输出 5 条 narrative registry item。
- 至少输出 5 条 handoff_to_financial_extractor item。
- `Financial Research Draft` 可以从 unified pack 生成问题底稿。
- `tests.test_scaffold` 通过。

## 14. Non-goals

MVP 不做：

- 估值
- 买卖建议
- 第三方数据融合
- 媒体或卖方观点
- 专家访谈和渠道检查
- 自动判断目标价
- 长篇 transcript 摘要

本层只做证据抽取、标签、裁判和未解问题回流。
