# 财务证据追查 Skill V1

状态：设计 instruction；runtime Skill 集成待完成。

这个 Skill 负责在财务指标出现疑问时，回到官方报告中尽量寻找解释，并把输出严格分成“事实、管理层解释、推测、未知”。

它不是财务指标计算 Agent，也不是估值 Agent。它不计算公式，不改数字，不做买卖建议。

## 1. 什么时候触发

当 `diagnostic_findings` 或 `latest_interim_trend` 出现以下情况时触发：

- 收入增长但经营利润、净利润或自由现金流下降。
- 增量经营利润率、增量自由现金流率或新增资本回报明显异常。
- 现金流好于净利润，但营运资本顺风很大。
- 受限现金、债务、可转债、VIE、资金可转移性或流动性出现疑问。
- 非 GAAP 调整、投资收益、税率、减值或会计估计影响利润读法。
- 最新季度趋势与年度主线不一致。
- 重大事项扫描发现审计师变更、重述、融资、股权激励、管理层变化、并购、减值、监管事项等。

## 2. 允许使用的来源

只允许使用本次 run 已收集或缓存的官方文件：

- 10-K / 20-F / annual report。
- 10-Q / quarterly 6-K / interim report。
- earnings release 附件，但只作为官方披露文本，不作为业绩电话会文字稿。
- 8-K / 6-K / proxy / AGM / F-1 / S-1 中被 document policy 或 material-event scan 标记为相关的文件。
- 官方年报 PDF 或公司 IR 上的同一份官方报告，用于交叉验证。

不要使用：

- 业绩电话会文字稿。
- 卖方报告、媒体报道、论坛、社交媒体。
- 模型记忆。
- 第三方数据库清洗后的数值作为事实来源。

## 3. 工作方法

对每个触发的问题，按下面顺序工作：

1. 读取触发原因：对应的 question_id、warning flags、异常指标和缺失证据。
2. 确定应该回查的文件和章节：MD&A / operating results / revenue note / cash flow note / segment note / tax note / debt note / SBC note / audit report / ICFR。
3. 在官方文件中搜索与问题相关的关键词。
4. 摘出能解释异常的官方文字、表格或附注位置。
5. 判断这些证据能回答到什么程度：answered、partial、unresolved。
6. 输出时必须区分事实、管理层解释、推测和未知。

## 4. 输出标签

每条解释必须使用下面四类标签之一。

| 标签 | 含义 | 可以怎么写 |
| --- | --- | --- |
| 文件事实 | 官方文件直接披露的数字、项目、事项、会计政策、风险、合同或表格内容 | “2025 年经营利润同比下降 14.1%。” |
| 管理层解释 | 官方文件中管理层对变化原因的文字解释 | “公司称利润率受 merchant support / ecosystem investment 影响。” |
| 基于现有数据的推测 | 由已抽取数字和官方解释合成的合理判断，但文件没有直接明说 | “这更像主动投入期，而不是收入失速；但仍需后续季度验证。” |
| 仍未知 | 官方文件没有披露或现有抽取无法回答的问题 | “Temu 单独收入和利润未披露，不能验证海外业务单位经济性。” |

严禁把“基于现有数据的推测”写成“文件事实”。

## 5. 输出结构

建议输出为 `financial_investigation_notes`：

```json
{
  "status": "calculated",
  "notes": [
    {
      "question_id": "growth_quality",
      "trigger": "revenue grew while operating income declined",
      "answer_status": "partial",
      "documents_searched": [
        {
          "document_type": "20-F",
          "document_id": "0001104659-26-050727:pdd-20251231x20f.htm",
          "sections": ["Item 5. Operating and Financial Review", "Revenue note"]
        }
      ],
      "evidence": [
        {
          "label": "文件事实",
          "text": "收入同比增长，但经营利润同比下降。",
          "source": "annual_facts:2025"
        },
        {
          "label": "管理层解释",
          "text": "管理层把部分压力归因于平台生态、商家支持或供应链投入。",
          "source": "20-F Item 5 / MD&A"
        },
        {
          "label": "基于现有数据的推测",
          "text": "增长仍在，但新增收入的边际利润变差，可能处在再投资阶段。",
          "source": "diagnostic rule + official metrics"
        },
        {
          "label": "仍未知",
          "text": "公司没有披露足够的商家分群 / 单商家经济性，不能验证投入回收期。",
          "source": "disclosure boundary"
        }
      ],
      "report_sentence": "收入仍增长，但新增收入没有转化成新增经营利润；官方文件把部分压力指向生态与供应链投入，但投入回报仍未被披露数据证明。"
    }
  ]
}
```

## 6. 写作规则

- 先写事实，再写解释，再写推测，最后写未知。
- 如果官方文件只说了方向，没有量化，不要替它量化。
- 如果文件没有披露公司特有 KPI，不要反推为事实。
- 如果只能解释一部分，就写 `partial`，不要写成 fully answered。
- 每个推测都必须能回到至少一个文件事实或管理层解释。
- 如果没有找到解释，要明确写“官方文件未提供足够解释”，而不是编一个原因。

## 7. 与其他 Agent 的边界

- 财务抽取 Agent：负责抽取数字和事实。
- 财务指标 Agent：负责计算公式。
- 诊断规则 Agent：负责发现问题和提出回查方向。
- 财务证据追查 Skill：负责回到官方文件找解释，并标注事实 / 推测 / 未知。
- 财务报告解读 Skill：负责把调查结果写成最终中文报告。
