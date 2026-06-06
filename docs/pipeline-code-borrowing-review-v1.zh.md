# Pipeline Code Borrowing Review v1

本文不是比较生成出来的 artifacts，而是比较代码层面：新的 Question-Led Evidence Workflow 应该从之前 pipeline 里 borrow 哪些成熟代码，哪些地方不应该继续靠读取旧 artifacts 或手写 adapter。

## 结论

当前新 workflow 的方向是对的，但实现方式还偏“artifact adapter”。它在 `src/stock_research/research_workflow/artifacts.py` 里直接读取旧 state 中的 packs，然后手写了很多转换逻辑。这个方式能跑通 MVP，但不是理想的 production design。

更好的方式是：

- 新 workflow 只负责 source map、question pack、evidence plan、QA/gap triage、pillar readiness。
- 旧 pipeline 的成熟模块继续作为 evidence engines 被调用，而不是让新 workflow 重新解析旧 artifacts。
- 为每个旧 engine 建一个 code-level adapter，输出统一的 `EvidenceItem` / `SourceRef` / `GapRequest`，而不是在 `artifacts.py` 里到处手写字段映射。

换句话说：应该 borrow code capabilities，不是 borrow generated artifacts。

## 2026-06-06 实现状态

这次已经把最重要的 P0/P1/P2 路线落成代码：

- P0 `models.py`: 统一 `EvidenceItem` / `SourceRef` / `GapRequest` helper。
- P0 `financial_adapter.py`: financial report pack 进入统一 evidence schema，并保留 `upstream_fact_id`、`formula_id`、`source_document`、`source_table`、`xbrl_tag`、`verification_record_id`、`human_review_flag_id` 等 lineage。
- P0 `bmue_adapter.py`: BMUE evidence cards、question answers、contradictions、unknowns、handoffs 进入统一 evidence/gap schema。
- P0 `gap_router.py`: deep-read gaps、registry adapter gaps、QA unsupported claims、confidence caps、feedback loop requests 合并成 `research_backlog`。
- P1 `official_evidence_adapter.py`: official report evidence pack 的 Q&A、decision narratives、evidence bundles、still-unknown items 进入 deep-read。
- P1 `people_adapter.py`: Right People 的控制权、激励、资本配置、red flags、open questions 进入 evidence registry / backlog。
- P2 `valuation_adapter.py`: valuation metrics 只进入 `price.*` question，不回灌到 Financial Evidence fact layer。
- V1.25 `filing_deep_read_pack.json`: Evidence Plan 和 Theme Workpaper 之间新增中间深读层，包含 section map、evidence cards、claim ledger、numeric fact refs、contradiction matrix、question coverage 和 gap requests。

保留的技术债：

- `artifacts.py` 仍然偏大，report rendering 和部分 legacy adders 还没有完全拆出。
- Evidence Communication 还没有独立 adapter，当前仍由 registry builder 直接接入。
- People / Valuation adapter 已经结构化接入，但它们还不是 deep-read 的 official-only 核心事实层。

## 当前代码结构

### 新 workflow 入口

- `src/stock_research/research_workflow/artifacts.py`
  - `build_research_workflow_artifacts`
  - `build_source_map`
  - `build_decision_question_pack`
  - `build_evidence_plan`
  - `build_evidence_registry`
  - `build_theme_workpaper_pack`
  - `build_qa_gap_triage`
  - `build_pillar_judgment_stub`

### 旧 pipeline 的成熟代码

- `src/stock_research/report_pack.py`
  - `build_financial_report_pack`
  - `_fact_ledger`
  - `_fact_extraction_summary`
  - `_financial_health`

- `src/stock_research/metrics/v1.py`
  - deterministic financial metrics
  - annual / quarterly fact row builders
  - formula outputs and metric families

- `src/stock_research/feedback_loop.py`
  - `build_feedback_loop_pack`
  - `apply_feedback_to_layer1_question_pack`
  - request routing logic: financial extractor / metric recalculation / layer1 requery / evidence communication / external data / human review

- `src/stock_research/qualitative/business_model_evidence.py`
  - `build_business_model_unit_economics_pack`
  - `_bmue_evidence_registry`
  - BMUE question answers, evidence cards, unknowns, contradictions, cross-checks, handoffs

- `src/stock_research/official_evidence/agent.py`
  - official filing evidence extraction
  - filing fact / management claim / inference / unknown separation

- `src/stock_research/evidence_communication/agent.py`
  - unified evidence/communication pack
  - management claim and proactive discovery extraction

- `src/stock_research/qualitative/right_people.py`
  - governance/control/incentive evidence cards
  - right-people report evidence logic

## 现在新 workflow 的问题

### 1. `artifacts.py` 太胖

`artifacts.py` 现在同时做：

- question template definition
- source map construction
- evidence registry construction
- financial fact priority sorting
- financial support card generation
- business model pack conversion
- right people conversion
- valuation evidence conversion
- workpaper answer writing
- QA/gap triage
- markdown rendering

这会让新 workflow 很快变成第二个 monolith。它应该是 orchestrator，不应该变成所有 agent 的 mini-copy。

### 2. Financial evidence 现在是在手写 summary cards

现在 `_add_financial_fact_evidence` 和 `_add_current_financial_support_evidence` 会直接从 `financial_report_pack` 读取：

- `fact_ledger`
- `annual_facts`
- `quarterly_facts`
- `financial_metrics`
- `human_review_flags`
- `verification_results`

然后新 workflow 自己生成 `ev_fin_support_*`。这能用，但有两个问题：

- 它复制了部分 financial report pack 的理解逻辑。
- 它没有稳定暴露 `upstream_fact_id`、`formula_id`、`verification_record_id`、`source_document`、`source_table` 这些底层引用。

应该 borrow `report_pack.py` / `metrics/v1.py` 的结构，做一个明确的 financial evidence adapter。

### 3. BMUE 已经有成熟 evidence registry，但新 workflow 没有直接复用

`business_model_evidence.py` 里已经有 `_bmue_evidence_registry`，能生成：

- `source_inventory`
- `evidence_cards`
- `card_ids_by_question`

新 workflow 现在只是读 `business_model_unit_economics_pack.question_answers`，然后生成 `ev_bmue_*`。这会丢掉 BMUE evidence cards 的细节。更好的方式是直接 borrow BMUE evidence-card model，把它转换成统一 EvidenceItem。

### 4. Feedback loop 的 routing code 应该进入新 QA/gap triage

`feedback_loop.py` 已经有成熟的 request routing：

- `financial_extractor`
- `metric_recalculation`
- `layer1_requery`
- `evidence_communication`
- `external_data`
- `human_review`

新 `qa_gap_triage` 目前只产生较轻的 gap decisions。它应该 borrow feedback router 的 routing logic，而不是自己重新设计一套 gap next action。

### 5. Pillar readiness label 需要借用更严格的 gate 语义

现在 `pillar_judgment_stub` 里的 `ready` 容易被误解为 “pass”。但从旧 right people / financial reports 的逻辑看，应该分开：

- `ready_for_judgment`
- `passes`
- `fails`
- `blocked_by_missing_evidence`
- `needs_human_review`

这里不应该只靠新 workflow 简单看 evidence 是否存在。

## 应该 borrow 的代码能力

### P0: Financial Evidence Adapter

新增建议模块：

`src/stock_research/research_workflow/financial_adapter.py`

应该复用：

- `financial_report_pack["fact_ledger"]`
- `financial_report_pack["financial_metrics"]`
- `financial_report_pack["diagnostic_findings"]`
- `financial_report_pack["verification_results"]`
- `financial_report_pack["human_review_flags"]`
- `financial_report_pack["missing_facts"]`

输出统一结构：

```python
{
    "evidence_items": [...],
    "source_refs": [...],
    "gap_requests": [...],
    "quality_flags": [...],
}
```

每个 financial evidence item 必须保留：

- `upstream_artifact`: `financial_report_pack`
- `upstream_fact_id`
- `formula_id`
- `source_document`
- `source_table`
- `xbrl_tag`
- `context_ref`
- `verification_record_ids`
- `human_review_flag_ids`

新 workflow 只调用 adapter，不再自己理解财务 pack 细节。

### P0: BMUE Evidence Adapter

新增建议模块：

`src/stock_research/research_workflow/bmue_adapter.py`

应该复用：

- `build_business_model_unit_economics_pack`
- `_bmue_evidence_registry` 目前是 private function，最好重命名/包装成 public adapter function
- BMUE evidence cards
- BMUE unknowns / contradictions / handoffs

输出：

- business-model evidence items
- business-model unknowns
- contradiction checks
- handoff questions

这样新 workflow 不需要从 `question_answers` 里重新猜 evidence kind。

### P0: Gap Router Adapter

新增建议模块：

`src/stock_research/research_workflow/gap_router.py`

应该复用：

- `build_feedback_loop_pack`
- `_route_request` 的分类逻辑
- metric/fact catalog matching

目标：把 `qa_gap_triage` 从简单检查升级成真正的 research backlog。

输出字段建议：

- `gap_id`
- `question_id`
- `blocking_pillar`
- `route`
- `owner_agent`
- `required_source_types`
- `required_metrics`
- `depends_on_artifact`
- `priority`
- `status`

### P1: Official Evidence Adapter

新增建议模块：

`src/stock_research/research_workflow/official_evidence_adapter.py`

应该复用：

- official report evidence pack 的 question answers
- decision relevant narratives
- source catalog
- fact / management claim / inference / unknown separation

这个 adapter 负责把 filed-text evidence 接进统一 registry。

### P1: Right People Adapter

新增建议模块：

`src/stock_research/research_workflow/people_adapter.py`

应该复用：

- `leadership_findings`
- `right_people_report` 的 evidence source logic
- governance/control/incentive/capital allocation red flags

重点不是生成 prose report，而是生成结构化：

- control evidence
- incentive evidence
- capital allocation evidence
- candor evidence
- unresolved governance gaps

## 不应该 borrow 的东西

### 不应该 borrow `final_report.md`

`final_report.md` 是 readable memo，不应该作为新 workflow 的 source。它可以给人读，但系统内部不应该从它抽 evidence。

### 不应该 borrow markdown report prose

例如：

- `financial_results_report.md`
- `business_model_report.md`
- `right_people_report.md`

这些可以作为 human-facing view，但不应作为下游 agent 的事实输入。

### 不应该复制旧模块里的私有逻辑到 `artifacts.py`

如果新 workflow 需要某个旧模块的能力，应该把旧代码重构成 public adapter，而不是把 private helper 逻辑复制一份。

## 建议的重构顺序

### Step 1: 抽出统一 evidence schema

新增：

`src/stock_research/research_workflow/models.py`

定义：

- `EvidenceItem`
- `SourceRef`
- `GapRequest`
- `PillarReadiness`

先不一定用 dataclass 强约束，但字段要稳定。

### Step 2: Financial adapter 先落地

这是最高价值，因为 financial_report_pack 是最成熟底稿。

改造目标：

- 把 `_add_financial_fact_evidence`
- `_add_current_financial_support_evidence`
- `_financial_metric_support_cards`

从 `artifacts.py` 移到 `financial_adapter.py`。

同时加 upstream refs。

### Step 3: BMUE adapter

把 `_bmue_evidence_registry` 包装成 public function，例如：

```python
def build_bmue_workflow_evidence(unit_pack: dict[str, Any]) -> dict[str, Any]:
    ...
```

新 workflow 调用它，而不是手写 `_add_business_model_items`。

### Step 4: Feedback loop / QA gap 合并

把 `feedback_loop.py` 的 routing logic 接进 `build_qa_gap_triage`。

目标是让 triage 不只是说 `collect_more_sources`，而是明确：

- 哪个 agent 做
- 需要什么 source
- 需要什么 metric
- 是自动补抽还是 human review

### Step 5: 拆小 `artifacts.py`

最终 `artifacts.py` 应该只保留：

- `build_research_workflow_artifacts`
- `build_source_map`
- `build_decision_question_pack`
- `build_evidence_plan`
- `build_theme_workpaper_pack`
- `build_qa_gap_triage`
- `build_pillar_judgment_stub`
- report rendering 或把 rendering 再拆出去

Evidence ingestion 应该来自 adapters。

## 当前最重要的 code smell

`src/stock_research/research_workflow/artifacts.py` 现在超过两千行，而且混合了 orchestration、adapters、rules、rendering。短期可以接受，但如果继续往里面加 logic，它会变成一个很难维护的大文件。

下一步不要继续往 `artifacts.py` 里加具体 agent 逻辑。应该先拆 adapter。

## 最小可执行改造

最小的一步是：

1. 新建 `src/stock_research/research_workflow/financial_adapter.py`
2. 移动/包装 financial evidence 生成逻辑
3. 给 financial evidence item 增加 upstream refs
4. 修改 `artifacts.py` 调用 adapter
5. 跑 `tests.test_scaffold`

这一步完成后，新 workflow 就真正开始 borrow 旧 financial pipeline 的 code capability，而不是只读旧 artifact。
