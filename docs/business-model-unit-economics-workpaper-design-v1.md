# Business Model & Unit Economics Workpaper Design V1

Status: primary specialized design doc for Layer 2
Last updated: 2026-06-04

本文定义 `Business Model & Unit Economics Workpaper Agent`。它是 `Evidence Workpaper Agents / 底稿层` 的专项设计文档，继承 `docs/evidence-workpaper-layer-design-v1.md` 的通用 contract。

本 agent 是证据工作底稿代理，不是判断代理。它不回答“应不应该买”、不回答“是不是伟大公司”，也不对企业做终局评级。它只回答一组固定投资研究问题，并把答案、证据、冲突、未知项和计算链条固化进 `pack.json`，以便下游的 `Right Business`、`Growth Runway`、`Competitive Position`、`Risk`、`Management`、`Valuation Assumption` 等代理重复消费。

## 1. Design Memo

这个 agent 的核心产物不是“总结一堆来源”，而是围绕以下问题组织研究：

- 公司如何赚钱？
- 谁付钱？
- 谁使用？
- 谁供给？
- 钱何时确认？
- gross/net 口径是什么？
- 规模扩大后 economics 怎样变化？
- 成本结构和利润率驱动是什么？
- 增长来自哪里？
- 脆弱点在哪里？

公共公司原始披露的组织方式天然支持这种设计：

- Regulation S-K Item 101 要求围绕收入生成活动、产品与服务、以及对关键产品/客户的依赖来描述业务。
- Item 303 的 MD&A 要求解释流动性、资本资源、经营结果以及管理层已知的趋势和不确定性。
- Form 20-F Item 5 要求管理层解释影响历史期财务状况和经营结果的因素。

收入确认与 gross/net 必须成为固定问题。IFRS 15 与 Topic 606 都把 principal/agent 判断建立在“转移给客户之前是否控制指定商品或服务”上；principal 记收入总额，agent 记手续费或佣金。如果这一步错了，take rate、毛利率、增长质量和估值口径会被系统性误读。

本 agent 还必须把来源位置和断言性质分开建模。同一份 10-K 或 20-F 里，既有经审计的财务报表和附注，也有未必经审计的叙述性内容。PCAOB 对财务报表、相关附注和相关附表的审计覆盖，和对同一文件中“其他信息”的考虑责任并不相同。10-Q 包含未经审计的季度财务报表；8-K Item 2.02 以及许多 6-K / 业绩材料又常常是 furnished 而不是 filed。换言之，“在 filing 里”不等于“经审计事实”。

因此，`pack.json` 必须是可再生、可追溯、可冲突检查的耐久资产，而不是把一段自然语言 memo 存盘。Inline XBRL 和 EDGAR API 可以作为人机双可读的提取层，但结构化抽取不能替代完整 filing。Schema 必须同时保存 `extracted_fact` 与 `source_locator`，并要求任何派生计算都能从原始披露点回溯。`report.md` 只负责渲染，不负责承载唯一事实。

### 1.1 Epistemic Contract And Abstention

本 agent 的认识论边界必须写进 prompt、schema 和 post-run validator。

When evidence is weak, conflicting, out of scope, or not disclosed, the correct behavior is abstention:

```text
Return structured uncertainty.
Do not guess.
Do not fill missing unit economics with industry averages unless explicitly labeled as an indirect proxy.
Do not promote management narrative into fact.
Do not silently smooth conflicts.
```

Abstention should be represented in the pack through:

- `question_answers[].status = "unknown" | "partial" | "not_applicable"`
- `unknowns[]`
- `contradictions[]`
- `confidence`
- `quality_flags`
- `needed_source`

This is not a failure mode. In investment research, correctly saying "not disclosed" or "cannot be supported from current evidence" is often more valuable than a confident but invented estimate.

## 2. Fixed Question List

问题清单应该固定、跨行业，并且每个问题都要有 `answered | partial | unknown | not_applicable` 状态。下游代理拿到的应该永远是稳定字段，而不是“有时有这个字段，有时没有”。

| ID | Fixed Question | Required Fields | Minimum Evidence | Main Downstream |
| --- | --- | --- | --- | --- |
| BMQ-01 | 公司有哪些收入流，分别占多大比重？ | `revenue_streams[]`, `mix_estimate` | 年报/季报分部、附注、业务描述 | Right Business, Valuation |
| BMQ-02 | 每个收入流里谁是 payer / user / supplier？ | `party_map` | 业务描述、产品页、合同/政策事实 | Competitive Position, Risk |
| BMQ-03 | 公司卖的到底是什么？商品、服务、广告库存、软件席位、利差、保单、制造产能，还是撮合权利？ | `offer_map` | 业务描述、附注、产品事实 | Right Business |
| BMQ-04 | 定价机制是什么？固定价、订阅、佣金、take rate、利差、保费、广告竞价、使用量计费？ | `pricing_map` | 产品/价格页、附注、业务描述 | Growth, Valuation |
| BMQ-05 | 收入何时确认，关键履约义务是什么？ | `revenue_recognition` | 收入确认会计政策、附注 | Valuation, Risk |
| BMQ-06 | 公司按 gross 还是 net 记录收入，依据是什么？ | `gross_net_treatment`, `principal_agent_basis` | Topic 606 / IFRS 15 相关政策与附注 | Valuation, Right Business |
| BMQ-07 | 披露的分部与业务模型是否一致？ | `segment_alignment` | segment note、业务描述 | Competitive Position |
| BMQ-08 | 公司公开披露了哪些运营指标可以充当单位经济学锚点？ | `disclosed_operating_metrics[]` | KPI 表、附注、业绩补充材料 | Growth, Valuation |
| BMQ-09 | 若未直接披露 unit economics，可用哪些明确标注为 proxy 的代理指标？ | `unit_econ_proxies[]`, `proxy_quality` | 报表、分部、KPI、价格 | Right Business, Valuation |
| BMQ-10 | 成本结构如何分层？获客、履约、内容、云/带宽、支付、资金成本、赔付、制造、物流、再保险？ | `cost_structure` | COGS、Opex、附注 | Risk, Valuation |
| BMQ-11 | 毛利率、营业利润率、分部利润率由什么驱动？ | `margin_drivers[]` | 报表趋势、分部、管理层解释 | Right Business, Valuation |
| BMQ-12 | 增长来自哪里？量、价、混合、地理扩张、新品、渠道扩张、并购、FX、会计口径变化？ | `growth_drivers[]` | MD&A/OFR、KPI、附注 | Growth Runway |
| BMQ-13 | 模型是否依赖补贴、返现、流量采买、激励、促销、准备金释放、低成本资金或一次性顺风？ | `subsidy_dependency[]` | 报表、营销费用、政策页、管理层口径 | Risk, Right Business |
| BMQ-14 | 经营杠杆、现金转换、营运资本、capex 强度是否支持该商业叙事？ | `cross_checks[]` | 报表三表、附注、分部 | Right Business, Valuation |
| BMQ-15 | SBC 与摊薄是否在“美化” economics？ | `sbc_dilution_check` | 报表、股本附注、proxy | Management, Valuation |
| BMQ-16 | 最脆弱的环节是什么？供给依赖、渠道依赖、流量依赖、监管依赖、会计估计依赖、信用/灾害/赔付波动？ | `fragile_points[]` | 风险因素、附注、分部、政策信号 | Risk |
| BMQ-17 | 哪些核心问题仍未知、披露不足、或存在冲突？ | `unknowns[]`, `contradictions[]` | 显式列缺口，不可省略 | All downstream |
| BMQ-18 | 哪些问题应转交下游代理继续追问？ | `handoff` | 从本底稿直接生成 | All downstream |

## 3. Model-Family Proxy Metric Library

为了跨行业通用，建议维护一个模型族代理指标库。必须严格区分“公司已披露”与“系统代理”。系统代理不可冒充公司披露值。

| Model Family | Preferred Proxy Metrics | Notes |
| --- | --- | --- |
| Marketplace / ecommerce platform | GMV, take rate, order frequency, fulfillment cost per order, subsidy per order, merchant count, buyer count | PDD/Temu, Amazon third-party, delivery/local services |
| Advertising / traffic platform | DAU/MAU, query volume, ad load, CPC/CPM, TAC, advertiser count | Google, Tencent advertising |
| SaaS / software | ARR, RPO, NRR/GRR, ARPU, seats, sales-efficiency proxy, gross margin | B2B SaaS, cloud software |
| Bank | asset yield, funding cost, NIM, non-interest income mix, efficiency ratio, provisions / credit cost | commercial bank, consumer finance |
| Insurance | premium growth, retention, loss ratio, expense ratio, combined ratio, reserve development | P&C, life, reinsurance |
| Manufacturing / hardware / consumer brand | ASP, volume, capacity utilization, channel structure, gross margin, inventory turnover, promotion intensity | manufacturers, consumer brands |

### 3.1 Dynamic Schema Mapping

The workpaper should use the same fixed BMQ question set across companies, but the extraction template and proxy metrics should adapt to the company's model family.

Examples:

- B2B SaaS: payer is usually the enterprise buyer or department budget owner; user is the employee/operator; supplier may be cloud infrastructure, app marketplace, data vendor, or implementation partner. Unit proxies include ARR, RPO, NRR/GRR, seats, ARPU, sales efficiency, gross margin, and payback.
- Marketplace / ecommerce: payer may be consumer, merchant, advertiser, or a mix; user may be consumer and merchant; supplier may be third-party seller, brand, factory, logistics partner, or payments provider. Unit proxies include GMV, take rate, AOV, order frequency, fulfillment cost, subsidies, merchant count, buyer count, DPO/DSO, and platform policy economics.
- Advertising platform: payer is advertiser; user is consumer/searcher/viewer; supplier may be publisher, creator, app developer, traffic acquisition partner, or OEM. Unit proxies include query volume, DAU/MAU, time spent, ad load, CPC/CPM, TAC, advertiser count, and publisher economics.
- Bank: payer/user are depositors, borrowers, merchants, cardholders, or counterparties depending on revenue stream; supplier is funding base and capital. Unit proxies include NIM, asset yield, funding cost, credit cost, efficiency ratio, and deposit beta.
- Insurance: payer/user is policyholder; supplier is underwriting capital, agents, brokers, reinsurers, and claims network. Unit proxies include premium growth, retention, loss ratio, expense ratio, combined ratio, reserve development, and reinsurance cost.
- Manufacturing / hardware / consumer brand: payer/user may be end customer, distributor, OEM, or retailer; supplier is raw materials, contract manufacturer, logistics, and channel. Unit proxies include ASP, volume, gross margin, utilization, inventory turns, channel mix, promotion intensity, and warranty/returns.

Dynamic mapping must not change the shared schema. It should only decide:

- which sources are mandatory,
- which unit-economics proxies are relevant,
- which cross-checks are meaningful,
- which unknowns should be expected,
- which handoff questions should be prioritized.

## 4. Source Priority And Evidence Labels

来源排序原则：

```text
法律约束更强的优先于营销约束。
审计覆盖更强的优先于未审计。
filed 优先于 furnished。
原始披露优先于提取层。
直接证据优先于间接信号。
```

银行和保险还需要把行业监管报表纳入核心来源层，例如 FFIEC Call Report、FR Y-9C、NAIC statutory blanks。

| Rank | Source Type | Examples | Default Role | Reliability | Rules |
| --- | --- | --- | --- | --- | --- |
| High | 主上市地年度监管申报 + 经审计财务报表与附注 | 10-K, 20-F, 40-F, annual report | 核心事实源 | A+ | 业务描述、分部、会计政策、审计数字的第一锚点 |
| High | 审计报告 / CAM / 关键会计附注 | audit opinion, CAM, revenue recognition, segment note, reserves | 口径与风险源 | A+ | 界定 audited vs narrative |
| High | 季度/中期监管申报 | 10-Q, interim report, 6-K with interim financials | 近期趋势源 | A | 趋势与近期变化；不得混同为 audited annual |
| High | 行业监管报表 | FFIEC Call Report, FR Y-9C, NAIC statutory blanks | 行业专用核心源 | A / A- | 银行/保险必须启用 |
| Medium-high | Filing 提取层 | Inline XBRL, EDGAR API | 解析加速层 | A- | 只能加速取数，不能替代原 filing |
| Medium-high | Proxy / 治理申报 | DEF 14A, AGM materials | 治理与激励源 | A- | 主要服务 Management / Governance / SBC / dilution |
| Medium | Furnished 业绩材料 | 8-K Item 2.02, 6-K, earnings release, supplement | 管理层陈述源 | B+ | 必须单独打 `management_claim` / `non_gaap` 标签 |
| Medium | 官网产品、价格、费用、政策页 | pricing page, fee schedule, terms, app store | 当前产品事实源 | B | live facts 必须加时间戳和快照 |
| Medium | 竞争对手一手来源 | competitor filing, product page, pricing page | 横向比较源 | B | 只能回答 competitor facts，不能反推本公司事实 |
| Low | Alternative data | traffic, downloads, hiring, price crawler, credit-card sample | 信号源 | C | 只能作 signal，不可单独定论 |
| Low | Third-party commentary | sell-side, industry interview, media profile | 解释与问题生成源 | C- | 只能作为线索；未被一手源证实不得升级为事实 |
| Lowest | Social / forum / aggregator | X, Reddit, blogs, secondary summary sites | 发现源 | D | 不得作为核心结论证据 |

### 4.1 Reliability Weights And Conflict Resolution

The implementation may convert source tiers into internal confidence weights, but these weights are only aids for routing and review. They do not override explicit source policy.

Suggested default weights:

| Tier | Source Class | Suggested Weight |
| --- | --- | --- |
| T1 | audited financial statements and footnotes | 1.00 |
| T2 | filed regulatory facts | 0.95 |
| T3 | management KPIs in earnings release / investor presentation | 0.85 |
| T4 | management claims in calls, interviews, letters | 0.70 |
| T5 | product / pricing / policy facts from company-controlled pages | 0.80 |
| T6 | alternative-data signals | 0.60 |
| T7 | competitor facts | 0.50 |
| T8 | third-party commentary / media / social | 0.30 |

Conflict rules:

1. Audited numbers and audited footnotes win over management claims.
2. Filed source facts win over furnished earnings materials when the same period and metric conflict.
3. Company live pages can support current product/pricing facts, but they cannot rewrite historical period economics unless archived snapshots exist.
4. Competitor facts can inform comparison and pressure, but they cannot establish facts about the target company.
5. Alternative data can corroborate or challenge a claim, but cannot become the sole support for a core business-model finding.
6. Third-party commentary can generate questions, but not final evidence.
7. If conflict cannot be resolved, write `contradictions[]` and lower confidence instead of blending prose.

### 4.2 Assertion Labels

本 agent 采用双轴标签系统：

- 轴 1：来源与审计边界，如 `filed_audited_financials`, `filed_narrative`, `furnished_earnings`, `company_live_page`, `alternative_data`。
- 轴 2：断言性质，如 `filing_fact`, `audited_number`, `management_claim`, `system_inference`, `unknown`。

| Assertion Label | Definition | Typical Source | Rule |
| --- | --- | --- | --- |
| `filing_fact` | 来自 filed narrative 的客观披露事实 | 10-K / 20-F / 10-Q / annual report正文 | 不是 audited 就不要冒充 audited |
| `audited_number` | 经审计报表、附注或审计意见覆盖的数字/披露 | 年报财报与附注 | 最高等级数值锚点 |
| `revenue_recognition_fact` | 履约义务、时点/期间确认、principal-agent、合同资产负债 | 收入确认附注 | 必须绑定会计政策原文位置 |
| `product_fact` | 产品、功能、渠道、交付方式等当前事实 | filing + 官网产品页 | live facts 加时间戳和快照 |
| `pricing_fee_policy_fact` | 定价、费率、佣金、政策、退款、补贴规则 | pricing page, fee schedule, terms | 必须记录生效时间 |
| `management_claim` | 管理层对因果、壁垒、效率、前景的陈述 | MD&A, earnings call, investor deck | 除非被报表/一手证据验证，否则仍是 claim |
| `competitor_fact` | 来自竞争对手一手来源的事实 | competitor filing, product/pricing page | 只用于横向比较 |
| `alternative_signal` | 间接、样本化、噪音较高的外部信号 | alternative-data vendor or collector | 只能 signal，不能定论 |
| `third_party_commentary` | 第三方解释、观点、总结 | research, media, expert interview | 永远不是 primary fact |
| `system_inference` | 系统基于多张证据卡推导出的结论 | calculation / reasoning | 必须列出 basis card ids 与置信度 |
| `unknown` | 无披露、披露不足、冲突未解 | system output | 必须显式输出，不能留白 |

## 5. Pack.json Design

`pack.json` 应该是问题目录、映射对象、证据卡图谱、计算链条和交接包的组合。

Core object map:

| Object | Purpose | Required Fields |
| --- | --- | --- |
| `revenue_stream` | 映射收入流 | `stream_name`, `payer`, `user`, `supplier`, `offer`, `pricing`, `recognition`, `gross_net`, `segment_refs`, `card_ids` |
| `unit_econ_proxy` | 映射单位经济学代理指标 | `metric_name`, `definition`, `formula`, `quality`, `series`, `card_ids` |
| `cost_bucket` | 映射成本结构 | `bucket_name`, `above_or_below_gross_profit`, `fixed_or_variable`, `linked_stream_ids`, `card_ids` |
| `margin_driver` | 映射利润驱动 | `driver`, `direction`, `mechanism`, `tested_by_cross_checks`, `card_ids` |
| `growth_driver` | 映射增长驱动 | `driver`, `type`, `durability`, `card_ids` |
| `subsidy_dependency` | 记录补贴/激励依赖 | `instrument`, `who_pays`, `where_seen`, `severity`, `card_ids` |
| `fragile_point` | 记录脆弱点 | `point`, `mechanism`, `evidence`, `monitoring_metric` |
| `cross_check` | 记录财务反证/支持测试 | `check_type`, `claim_tested`, `result`, `series`, `exceptions`, `card_ids` |
| `handoff_package` | 向下游代理转交问题 | `consumer_agent`, `facts_passed`, `questions_to_answer`, `priority` |

证据卡要做到“一张卡只承载一个原子 claim”。不要把“公司毛利提升源于 mix 改善、履约效率提升、补贴下降”塞进一张卡。正确做法是拆成三张卡，再用一个 `system_inference` 节点汇总。

Evidence card minimum fields:

| Dimension | Required Content |
| --- | --- |
| Identity | `card_id`, `claim_text`, `claim_normalized`, `importance` |
| Linkage | `question_ids`, `linked_stream_ids`, `linked_metric_ids` |
| Labels | `assertion_class`, `source_scope`, `audited_scope`, `support_level` |
| Evidence Payload | `source_id`, `locator`, `excerpt`, `structured_fact`, `period_covered` |
| Computation / Conflict | `calc_lineage`, `basis_card_ids`, `contradicts_card_ids` |
| Freshness | `observed_at`, `effective_from`, `stale_after`, `needs_refresh` |

### 5.1 Evidence Card Pipeline

Every important claim should pass through the same four-step pipeline:

1. Extract: locate the smallest useful text/table/fact span.
2. Classify: assign `assertion_class`, `source_scope`, `audited_scope`, and `support_level`.
3. Anchor: bind source metadata, locator, excerpt or structured fact, period, and freshness.
4. Score: assign confidence based on source tier, directness, corroboration, conflict state, and calculation lineage.

Evidence cards should be immutable once created. Later steps may add inference cards, contradiction records, or cross-checks, but they should not overwrite the original source-backed card. This makes audit and debugging possible when a later reasoning step is wrong.

Core implementation rule:

```text
Map stage: source readers create isolated evidence cards.
Reduce stage: question slots aggregate cards into revenue streams, unit proxies, drivers, cross-checks, unknowns, and handoffs.
```

This prevents the report from becoming a source-by-source summary.

### 5.2 Schema Skeleton

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "business_model_unit_economics_workpaper",
  "type": "object",
  "required": [
    "schema_version",
    "workpaper_type",
    "agent",
    "company",
    "scope",
    "source_inventory",
    "question_answers",
    "revenue_streams",
    "unit_economics_proxies",
    "cost_structure",
    "margin_drivers",
    "growth_drivers",
    "subsidy_dependencies",
    "fragile_points",
    "cross_checks",
    "evidence_cards",
    "handoff",
    "unknowns"
  ],
  "properties": {
    "schema_version": { "type": "string" },
    "workpaper_type": { "const": "business_model_unit_economics" },
    "agent": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": { "type": "string" },
        "version": { "type": "string" },
        "run_id": { "type": "string" }
      }
    },
    "company": {
      "type": "object",
      "required": ["issuer_name", "primary_ticker", "accounting_framework", "sector_family"],
      "properties": {
        "issuer_name": { "type": "string" },
        "primary_ticker": { "type": "string" },
        "exchange": { "type": "string" },
        "cik": { "type": ["string", "null"] },
        "lei": { "type": ["string", "null"] },
        "accounting_framework": {
          "type": "string",
          "enum": ["US_GAAP", "IFRS", "LOCAL_GAAP"]
        },
        "sector_family": { "type": "string" },
        "model_family": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "scope": {
      "type": "object",
      "required": ["as_of_date", "fiscal_period", "currency"],
      "properties": {
        "as_of_date": { "type": "string", "format": "date" },
        "fiscal_period": { "type": "string" },
        "currency": { "type": "string" },
        "lookback_years": { "type": "integer" },
        "included_source_ids": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "source_inventory": {
      "type": "array",
      "items": { "$ref": "#/$defs/source" }
    },
    "question_answers": {
      "type": "array",
      "items": { "$ref": "#/$defs/question_answer" }
    },
    "revenue_streams": {
      "type": "array",
      "items": { "$ref": "#/$defs/revenue_stream" }
    },
    "unit_economics_proxies": {
      "type": "array",
      "items": { "$ref": "#/$defs/unit_econ_proxy" }
    },
    "cost_structure": {
      "type": "array",
      "items": { "$ref": "#/$defs/cost_bucket" }
    },
    "margin_drivers": {
      "type": "array",
      "items": { "$ref": "#/$defs/driver" }
    },
    "growth_drivers": {
      "type": "array",
      "items": { "$ref": "#/$defs/driver" }
    },
    "subsidy_dependencies": {
      "type": "array",
      "items": { "$ref": "#/$defs/subsidy_dependency" }
    },
    "fragile_points": {
      "type": "array",
      "items": { "$ref": "#/$defs/fragile_point" }
    },
    "cross_checks": {
      "type": "array",
      "items": { "$ref": "#/$defs/cross_check" }
    },
    "evidence_cards": {
      "type": "array",
      "items": { "$ref": "#/$defs/evidence_card" }
    },
    "contradictions": {
      "type": "array",
      "items": { "$ref": "#/$defs/contradiction" }
    },
    "handoff": {
      "type": "array",
      "items": { "$ref": "#/$defs/handoff_package" }
    },
    "unknowns": {
      "type": "array",
      "items": { "$ref": "#/$defs/unknown" }
    },
    "render_manifest": {
      "type": "object",
      "properties": {
        "default_report_order": {
          "type": "array",
          "items": { "type": "string" }
        },
        "summary_card_ids": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

### 5.3 Key Object Requirements

`source` must include:

- `source_id`
- `source_scope`
- `document_type`
- `title`
- `issuer`
- `filing_date`
- `period_end`
- `is_filed`
- `is_audited`
- `observed_at`
- `effective_from`
- `stale_after`
- `locator_root`

`question_answer` must include:

- `question_id`
- `prompt`
- `status`: `answered | partial | unknown | not_applicable`
- `answer_short`
- `answer_detail`
- `confidence`
- `primary_card_ids`
- `open_question_ids`

`revenue_stream` must include:

- `stream_id`
- `stream_name`
- `segment_refs`
- `offer`
- `payer`
- `user`
- `supplier`
- `pricing`
- `recognition`
- `gross_net`
- `linked_proxy_ids`
- `card_ids`

`unit_econ_proxy` must include:

- `proxy_id`
- `metric_name`
- `definition`
- `formula`
- `quality`: `company_disclosed | directly_computed | indirect_proxy | unknown`
- `series`
- `card_ids`

`cross_check` should support:

- `operating_leverage`
- `cash_conversion`
- `working_capital`
- `capex_intensity`
- `gross_margin`
- `operating_margin`
- `sbc_dilution`
- `revenue_growth_quality`

`evidence_card` must include:

- `card_id`
- `claim_text`
- `claim_normalized`
- `importance`
- `assertion_class`
- `source_scope`
- `audited_scope`: `audited | unaudited_filed | furnished | live_page | third_party | inferred | unknown`
- `support_level`: `direct | computed | corroborative | contradictory | unknown`
- `question_ids`
- `basis_card_ids`
- `evidence[]`
- `confidence`

## 6. Report.md Render Template

`report.md` 的职责只是把 `pack.json` 渲染成可读文档，因此必须按问题而不是按来源组织。Form 20-F Item 5 和 MD&A 的精神都是帮助投资者理解影响财务状况和经营结果的因素，而不是机械复述材料。

```markdown
# {{ issuer_name }} 商业模式与单位经济学工作底稿

## 研究范围
- 覆盖期间：{{ fiscal_period }}
- 会计准则：{{ accounting_framework }}
- 主模型族：{{ model_family }}
- 纳入来源：{{ source_count }} 个
- 结论边界：本文件不包含 Buy/Sell/Hold、目标价或“伟大公司”判断

## 问题总览
| 问题 | 状态 | 短答 | 置信度 | 主要证据卡 |
|---|---|---|---|---|
| BMQ-01 | {{ status }} | {{ answer_short }} | {{ confidence }} | {{ card_ids }} |

## 商业模式地图

### 收入流
| 收入流 | 产品/服务 | payer | user | supplier | 定价机制 | 规模/占比 | 证据卡 |
|---|---|---|---|---|---|---|---|

### 收入确认与总额净额
| 收入流 | 确认时点 | 关键履约义务 | gross/net | 依据 | 证据卡 |
|---|---|---|---|---|---|

### 分部与业务对齐
- 分部结构：{{ segment_alignment_summary }}
- 不一致点：{{ segment_mismatch }}

## 单位经济学

### 已披露指标
| 指标 | 定义 | 披露来源 | 最近值/趋势 | 证据卡 |
|---|---|---|---|---|

### 代理指标
| 代理指标 | 公式 | 质量等级 | 解释限制 | 证据卡 |
|---|---|---|---|---|

## 成本结构与利润驱动

### 成本结构
| 成本桶 | 位于毛利线上下 | 固定/变动 | 关联收入流 | 证据卡 |
|---|---|---|---|---|

### 利润驱动
| 驱动因素 | 方向 | 机制 | 是否被财务支持 | 证据卡 |
|---|---|---|---|---|

### 增长驱动
| 驱动因素 | 量/价/混合/地理/新品/M&A/FX/会计 | 可持续性 | 证据卡 |
|---|---|---|---|

## 财务核验

### 经营杠杆
{{ operating_leverage_summary }}

### 现金转换与营运资本
{{ cash_conversion_summary }}

### 资本开支与资产强度
{{ capex_intensity_summary }}

### SBC 与摊薄
{{ sbc_dilution_summary }}

### 增长质量
{{ revenue_growth_quality_summary }}

## 补贴依赖与脆弱点
| 项目 | 机制 | 严重度 | 监控指标 | 证据卡 |
|---|---|---|---|---|

## 关键未知项
| 问题 | 原因 | 若补齐最需要的来源 | 影响下游 |
|---|---|---|---|

## 向下游代理交接

### Competitive Position
{{ handoff_competitive }}

### Growth Runway
{{ handoff_growth }}

### Risk / Fragility / Red Flag
{{ handoff_risk }}

### Management / Governance / Capital Allocation
{{ handoff_management }}

### Valuation Assumption
{{ handoff_valuation }}

### Right Business
{{ handoff_right_business }}

## 证据卡索引
| Card ID | Claim | 标签 | 主要来源 | 定位 |
|---|---|---|---|---|
```

## 7. Financial Cross-Checks

财务核验不是附加功能，而是本 workpaper 的核心价值。任何商业模式叙事都必须回到三表与附注做支持或反证。

| Check | Main Test | Supports Narrative When | Creates Tension When | Notes |
| --- | --- | --- | --- | --- |
| Operating leverage | revenue growth vs expense growth; expense ratio; segment margin | 收入增长快于费用增长，或规模后 margin 扩张 | 收入涨但费用率不降；“平台化”却持续重资产 | SaaS、广告、平台最关键 |
| Cash conversion | CFO/NI, FCF/NI, CFO vs profit | 利润增长伴随现金增长 | 利润靠应计、现金弱、依赖 SBC 加回 | 银行/保险要改用行业现金逻辑 |
| Working capital | DSO/DIO/DPO, contract liabilities, inventory, payables | 优质 float 或周转改善 | 增长吃掉现金、应收恶化、库存堆积 | Marketplace 要看应付与商家结算 |
| Capex intensity | capex/revenue, capex/D&A, leases/content capitalization | 轻资本模型维持增长 | “轻资产”叙事但 capex/资本化持续抬高 | Amazon/云/制造特别重要 |
| Gross / operating margin | GM, OM, segment margin | 价格权、mix 改善、效率提升 | GM/OM 持续受压或靠一次性因素 | 银行/保险用 NIM/combined ratio 等替代 |
| SBC / dilution | SBC/revenue, SBC/op income, diluted shares CAGR | SBC 合理且被回购覆盖 | 非现金利润改善但摊薄加速 | 与 proxy/治理联动 |
| Revenue growth quality | organic vs M&A/FX; price/volume; backlog/RPO; rev-rec changes | 增长由真实需求与留存驱动 | 增长主要靠并购、FX、gross/net 变化、non-GAAP 调整 | 必须链接收入确认与 segment/KPI |

收入增长质量尤其需要会计口径核验。IFRS 15 / Topic 606 要求基于控制权判断 gross/net；SEC 对 non-GAAP 也提醒，如果公司用调整口径改变 GAAP 收入确认或 gross/net 展示，这类指标可能具有误导性。代理必须把“增长来自需求改善”和“增长来自会计展示、口径变化或 non-GAAP 调整”分开。

## 8. Downstream Handoff

| Downstream Agent | Required Handoff | Follow-Up Questions |
| --- | --- | --- |
| Competitive Position Workpaper | 每个收入流的 payer/user/supplier、定价机制、渠道/供给依赖、对手事实 | 网络效应、切换成本、规模经济是否真实体现在留存/费率/成本曲线 |
| Growth Runway Workpaper | 增长驱动拆解、地理与新品扩张、量价混合、KPI 历史 | 哪些增长源可持续，哪些只是短期扩张或会计/补贴驱动 |
| Risk / Fragility / Red Flag Workpaper | 补贴依赖、gross/net 敏感点、关键会计估计、单点依赖、冲突来源 | 哪些脆弱点最可能在未来 2-3 年打断 economics |
| Management / Governance / Capital Allocation Workpaper | SBC/dilution 结果、proxy 相关激励、资本开支与回购/分红约束 | 管理层激励是否鼓励“做大收入”而非“做强 economics” |
| Valuation Assumption Workpaper | 规范化收入流、价量驱动、margin drivers、capex 强度、现金转换质量 | 长期 margin / reinvestment / dilution 假设能否站得住 |
| Right Business Agent | 已证实的商业模式事实、单位经济学代理、财务核验结果、未知项清单 | 这些 facts 是否指向“高质量业务”由 Right Business 判断，本 agent 不判断 |

## 9. Acceptance Criteria

| Criterion | Standard |
| --- | --- |
| 问题完整性 | 固定问题清单全部有状态值，不能出现静默缺失字段 |
| 证据覆盖率 | 所有高重要性 claim、所有收入流定义、所有 gross/net 判断、所有脆弱点，必须有证据卡 |
| 标签卫生 | 每张证据卡都同时有 `assertion_class`, `source_scope`, `audited_scope` |
| 可追溯性 | 任一结论都能追到 source、locator、excerpt 或 structured fact |
| Unknown discipline | 披露弱时输出 `unknown` 或 `partial`，不得捏造 unit economics |
| Cross-check rigor | 所有“管理层解释型”结论都经过至少一项财务核验 |
| 冲突处理 | 冲突来源必须显式进入 `contradictions[]`，不能在 prose 中偷偷和稀泥 |
| 行业适配 | 银行/保险/平台/SaaS/制造等至少启用对应的模型族代理指标库 |
| 下游可消费性 | `handoff` 中对每个下游代理都有 `facts_passed` 与 `questions_to_answer` |
| 无结论泄漏 | 不出现 Buy/Sell/Hold、目标价、IRR、伟大公司断言、终局护城河判断 |
| 可再生性 | 仅凭 `pack.json` 与 source locators 就能重渲染 `report.md` |

### 9.1 Production Acceptance Targets

When this workpaper moves from MVP to production, use stronger system-level tests:

| Target | Production Standard |
| --- | --- |
| Schema validity | 100% of generated `business_model_unit_economics_pack.json` files pass JSON schema validation. |
| Source traceability | Randomly sampled facts and evidence cards can be traced back to source, locator, excerpt, or structured fact. |
| Role separation | Generated reports contain no Buy/Sell/Hold, target price, final moat verdict, or great-business conclusion. |
| Abstention discipline | Missing CAC, LTV, take rate, gross/net, or segment data produces `unknown` / `partial`, not fabricated estimates. |
| Conflict capture | Known contradictory source fixtures produce explicit `contradictions[]` entries. |
| Cross-check sensitivity | Golden test cases with management narrative vs financial reality tension trigger cross-check flags. |
| Downstream stability | Right Business, Growth, Risk, Competitive Position, Management, and Valuation Assumption agents can parse `handoff[]` without reading raw sources. |

## 10. Failure Modes And Guardrails

| Failure Mode | Why Dangerous | Guardrail |
| --- | --- | --- |
| 按来源总结，不按问题总结 | 产物无法复用，下游拿不到可比较字段 | `question_answers[]` 做主表，报告按问题渲染 |
| 过度相信管理层 narrative | 管理层解释经常领先于、甚至背离财务事实 | `management_claim` 必须经过 `cross_checks[]` |
| 把第三方 commentary 当事实 | 二手材料常混合观点、漏掉口径差异 | commentary 只能生成线索，不可做 primary evidence |
| 披露弱时发明 unit economics | 造成高精度错觉，污染下游估值和质量判断 | 代理指标只能标 `indirect_proxy`；不够就 `unknown` |
| 把 filing narrative 当成 audited fact | 同一 filing 里存在审计边界差异 | 强制 `audited_scope` 字段 |
| 用 non-GAAP 覆盖 GAAP gross/net | SEC 明确提示这类做法可能误导 | 保留 GAAP 对照与 reconciliation 位置 |
| 把提取层当源头 | XBRL/API 可能丢上下文 | 所有提取值必须回链原 filing locator |
| 将商业模式 evidence 偷偷转成投资结论 | 混淆 Evidence 层与 Judgment 层职责 | schema 中不允许 `recommendation` / `target_price` 字段 |
| 在当前 live pricing 上回填历史期 | 价格、规则、费率会变 | live page 必须快照化并加 `effective_from` |
| 遇到冲突就写模糊句子 | 下游代理无法知道哪里不确定 | `contradictions[]` 作为一等对象保存 |

## 11. Decision

Adopt this document as the implementation target for `Business Model & Unit Economics Workpaper Agent`.

Target artifacts:

```text
business_model_unit_economics_pack.json
business_model_unit_economics_report.md
```

During migration, the current MVP artifacts can remain:

```text
business_model_evidence.json
business_model_evidence_report.md
```

The implementation should evolve the current Q1-Q9 Business Model Evidence Agent into the BMQ-01 through BMQ-18 structure defined here.
