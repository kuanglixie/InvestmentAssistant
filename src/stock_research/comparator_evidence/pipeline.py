from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "comparator_evidence_pack_v1"

DEFAULT_DOWNSTREAM_CONSUMERS = [
    "business_model_agent",
    "moat_agent",
    "growth_runway_agent",
    "risk_agent",
    "valuation_agent",
]

ZH_LEVEL_LABELS = {
    "high": "高",
    "medium_high": "中高",
    "medium": "中",
    "medium_low": "中低",
    "low": "低",
    "partial": "部分可用",
    "not_clean": "不适合直接作为估值可比",
    "unknown": "未知",
    "unavailable": "不可得",
}

ZH_COMPANY_TYPE_LABELS = {
    "public_company": "上市公司",
    "private_company": "未上市公司",
    "business_unit": "业务单元",
    "unknown": "未知",
}

ZH_CATEGORY_LABELS = {
    "business_model": "商业模式",
    "moat": "壁垒",
    "growth": "增长空间",
    "risk": "风险",
    "valuation": "估值",
}

ZH_SOURCE_TYPE_LABELS = {
    "official_filing": "官方申报文件",
    "earnings_call": "业绩会材料",
    "investor_presentation": "投资者演示材料",
    "official_website": "官方网站 / 产品页",
    "merchant_terms": "商家条款 / 定价页",
    "app_store_page": "应用商店页面 / 可见评论",
    "alternative_data": "替代数据",
    "parent_company_filing": "母公司申报文件",
    "standalone_financial_statements": "独立财务报表",
    "manual_source_plan_required": "需要人工制定来源计划",
}

ZH_BATTLEFIELD_LABELS = {
    "China ecommerce": "中国电商",
    "Cross-border ecommerce": "跨境电商",
    "Merchant advertising": "商家广告",
    "Logistics": "物流",
    "Supply chain": "供应链",
    "Global marketplace": "全球市场平台",
    "App commerce": "移动端电商",
    "Social commerce": "社交电商",
    "unclassified competitive context": "未分类竞争场景",
}

ZH_COMPETITOR_DETAILS = {
    "alibaba": {
        "relationship": "中国电商和商家广告的直接参照，并通过 AliExpress 与 Temu 的跨境业务重叠。",
        "revenue_model": "以市场平台和商家服务为核心，覆盖中国商业、国际商业、物流、云和数字媒体等业务。",
        "differences": [
            "阿里业务组合更分散，包含中国商业、云、本地生活和国际商业。",
            "商家广告体系和商家工具更成熟。",
            "PDD / Temu 更集中在高性价比、低价发现和平台转化。"
        ],
        "advantages": [
            "商家基础大，市场基础设施成熟。",
            "商家广告产品成熟。",
            "通过 AliExpress 积累了跨境市场经验。",
            "围绕中国商家的支付、物流和生态关系更完整。"
        ],
        "weaknesses": [
            "中国电商主业更成熟，增速弹性有限。",
            "业务组合复杂，难以隔离单一战场经济性。",
            "监管和平台治理压力会约束运营选择。"
        ],
    },
    "jd": {
        "relationship": "中国电商直接竞争者，但物流、信任和自营零售模型与 PDD 明显不同。",
        "revenue_model": "以自营零售、第三方市场、物流和供应链服务组成的电商平台。",
        "differences": [
            "JD 更依赖自营采购、库存和物流能力。",
            "JD 更强调履约可靠性和正品信任。",
            "PDD 更偏轻资产平台和商家广告变现。"
        ],
        "advantages": [
            "自建物流和履约质量。",
            "消费者对正品和配送可靠性的信任。",
            "部分品类的供应商关系和深度。"
        ],
        "weaknesses": [
            "资本和运营强度高于轻平台模型。",
            "自营零售结构与 PDD 的商家广告引擎不完全可比。",
            "对复制 Temu 跨境低价发现模型的直接证据较弱。"
        ],
    },
    "amazon": {
        "relationship": "全球市场平台、履约、卖家服务和广告规模的参照物。",
        "revenue_model": "全球自营与第三方市场、履约网络、会员体系、广告平台和云业务的组合。",
        "differences": [
            "AWS、Prime、FBA 和自营零售使 Amazon 的经济性与 PDD / Temu 不同。",
            "Amazon 更强调选择、速度、信任和便利。",
            "Temu 更集中在低价跨境市场扩张。"
        ],
        "advantages": [
            "核心市场的履约密度和配送速度。",
            "卖家工具和广告市场规模。",
            "Prime 生态和消费者信任。",
            "流量、物流和基础设施的规模优势。"
        ],
        "weaknesses": [
            "高成本履约承诺与极低价定位不完全兼容。",
            "AWS 和 Prime 会污染公司层面的利润率和估值可比性。",
            "商家和消费者主张与 Temu 不完全一致。"
        ],
    },
    "shein": {
        "relationship": "Temu 在跨境电商和低价消费场景中的时尚品类参照。",
        "revenue_model": "以时尚为核心的跨境电商平台，强调快速需求感知、供应链响应和移动端转化。",
        "differences": [
            "SHEIN 更聚焦时尚品类。",
            "Temu 品类更宽，更像泛品类低价市场平台。",
            "SHEIN 的供应链节奏比财务模型更适合作为对比证据。"
        ],
        "advantages": [
            "快时尚需求感知和供应商协同。",
            "移动端商品呈现和用户参与度。",
            "低价时尚品类中的品牌认知。"
        ],
        "weaknesses": [
            "品类集中在时尚。",
            "公开财务披露有限。",
            "监管、可持续、劳工和知识产权压力可能影响扩张。"
        ],
    },
    "tiktok-shop": {
        "relationship": "对 Temu 和 PDD 商家注意力、流量获取和社交电商增长的关键威胁。",
        "revenue_model": "嵌入短视频、直播和达人生态中的社交电商市场平台。",
        "differences": [
            "TikTok Shop 从流量、内容和达人发现出发，而不是传统搜索或低价市场浏览。",
            "PDD / Temu 更依赖高性价比商品组织和市场平台转化。",
            "即使交易基础设施不成熟，TikTok Shop 也可能改变获客成本和商家预算分配。"
        ],
        "advantages": [
            "庞大流量池和内容发现引擎。",
            "达人生态和直播购物形态。",
            "有能力把商家广告预算导向社交电商。"
        ],
        "weaknesses": [
            "市场平台、履约和商家运营成熟度低于传统电商平台。",
            "达人驱动的转化可能存在品类不均衡。",
            "部分市场存在监管和平台准入风险。"
        ],
    },
    "aliexpress": {
        "relationship": "与 Temu 最接近的跨境市场平台参照之一。",
        "revenue_model": "阿里旗下跨境市场平台，连接以中国供应为主的商家和全球买家。",
        "differences": [
            "AliExpress 比阿里中国商业更接近 Temu 的跨境市场结构。",
            "Temu 的低价定位和促销强度更激进。",
            "AliExpress 有母公司生态支持，但独立财务透明度较低。"
        ],
        "advantages": [
            "长期跨境市场运营经验。",
            "阿里商家关系和物流生态。",
            "服务全球买家的中国供应链经验。"
        ],
        "weaknesses": [
            "没有独立公开财务报表。",
            "消费者信任、配送波动和产品质量感知会影响复购。",
            "母公司披露难以隔离 AliExpress 的经济性。"
        ],
    },
}


SOURCE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "public_company": [
        {
            "source_type": "official_filing",
            "source_name": "10-K, 20-F, annual report, or exchange filing",
            "reliability": "high",
            "available": True,
            "use_case": "Segment mix, revenue model, risk factors, management discussion, and audited financial context.",
            "limitations": [
                "Segment disclosure may not isolate the exact battlefield.",
                "Reported economics may include businesses outside the target comparison.",
            ],
        },
        {
            "source_type": "earnings_call",
            "source_name": "Earnings call transcripts and prepared remarks",
            "reliability": "medium",
            "available": True,
            "use_case": "Management framing, competitive pressure, growth priorities, and margin commentary.",
            "limitations": [
                "Management commentary is not audited.",
                "Statements may emphasize favorable trends.",
            ],
        },
        {
            "source_type": "investor_presentation",
            "source_name": "Investor presentations and event materials",
            "reliability": "medium",
            "available": True,
            "use_case": "Business model framing, strategic priorities, KPIs, and peer-relevant claims.",
            "limitations": [
                "Presentation metrics may be selective.",
                "Definitions can differ across companies.",
            ],
        },
    ],
    "private_company": [
        {
            "source_type": "official_website",
            "source_name": "Official website and product pages",
            "reliability": "medium",
            "available": True,
            "use_case": "Customer proposition, category focus, geography, merchant onboarding, and product surface.",
            "limitations": [
                "Commercial pages are marketing evidence, not audited facts.",
                "They usually do not disclose profitability or cash flow.",
            ],
        },
        {
            "source_type": "merchant_terms",
            "source_name": "Seller center, merchant terms, pricing pages, and policy pages",
            "reliability": "medium",
            "available": True,
            "use_case": "Merchant economics, platform rules, fulfillment obligations, fees, and operational friction.",
            "limitations": [
                "Terms can vary by country, category, and merchant tier.",
                "Historical changes may be difficult to reconstruct.",
            ],
        },
        {
            "source_type": "app_store_page",
            "source_name": "App store pages and visible review surfaces",
            "reliability": "medium_low",
            "available": True,
            "use_case": "Consumer demand quality, complaint themes, product positioning, and app cadence.",
            "limitations": [
                "Reviews are not representative of the whole user base.",
                "App metadata is an indirect operating indicator.",
            ],
        },
        {
            "source_type": "alternative_data",
            "source_name": "Search, traffic, product-price, promotion, and social-commerce signals",
            "reliability": "medium_low",
            "available": True,
            "use_case": "Directional demand, paid acquisition pressure, discounting, and product overlap.",
            "limitations": [
                "Alternative data needs calibration before it can support strong conclusions.",
                "Signal coverage can be biased by source availability.",
            ],
        },
    ],
    "business_unit": [
        {
            "source_type": "parent_company_filing",
            "source_name": "Parent company filings and annual reports",
            "reliability": "medium",
            "available": True,
            "use_case": "Parent-level strategy, segment disclosure, and risk language relevant to the business unit.",
            "limitations": [
                "The business unit may not have standalone audited financials.",
                "Parent-level disclosure can obscure unit economics.",
            ],
        },
        {
            "source_type": "official_website",
            "source_name": "Official website, product pages, and merchant pages",
            "reliability": "medium",
            "available": True,
            "use_case": "Customer proposition, merchant rules, fulfillment promise, and category coverage.",
            "limitations": [
                "Commercial pages are not financial statements.",
                "Public pages may vary by country.",
            ],
        },
        {
            "source_type": "alternative_data",
            "source_name": "Traffic, app, marketplace, pricing, and social signals",
            "reliability": "medium_low",
            "available": True,
            "use_case": "Directional pressure against the target across shared battlefields.",
            "limitations": [
                "Alternative data needs validation against official events when possible.",
                "Coverage may be partial by geography.",
            ],
        },
    ],
    "unknown": [
        {
            "source_type": "manual_source_plan_required",
            "source_name": "Manual source plan",
            "reliability": "unknown",
            "available": False,
            "use_case": "This competitor needs an explicit source plan before downstream agents rely on it.",
            "limitations": [
                "The MVP has no configured profile for this competitor.",
            ],
        }
    ],
}


KNOWN_COMPETITOR_PROFILES: dict[str, dict[str, Any]] = {
    "alibaba": {
        "competitor_id": "alibaba",
        "name": "Alibaba",
        "aliases": ["Alibaba Group", "BABA", "Taobao", "Tmall"],
        "company_type": "public_company",
        "parent_company": "Alibaba Group Holding Limited",
        "relationship_to_target": "direct China ecommerce peer and cross-border marketplace peer through AliExpress",
        "battlefields": [
            "China ecommerce",
            "Merchant advertising",
            "Cross-border ecommerce",
            "Logistics",
        ],
        "business_model": (
            "Marketplace and merchant services platform with China commerce, international commerce, "
            "logistics, cloud, and digital-media adjacencies."
        ),
        "business_model_differences": [
            "Alibaba is more diversified across China commerce, cloud, local services, and international commerce than PDD.",
            "Alibaba has a more mature merchant advertising system and a broader ecosystem around merchants.",
            "PDD and Temu are more concentrated on value-for-money commerce and consumer bargain discovery.",
        ],
        "advantages": [
            "Large merchant base and mature marketplace infrastructure.",
            "Established merchant advertising products.",
            "International marketplace experience through AliExpress and related assets.",
            "Payments, logistics, and ecosystem relationships around Chinese merchants.",
        ],
        "weaknesses": [
            "Mature China ecommerce growth profile.",
            "Complex portfolio makes battlefield-level economics harder to isolate.",
            "Regulatory and platform-governance scrutiny can constrain operating choices.",
        ],
        "overlap_level": "high",
        "threat_level": "medium",
        "business_model_similarity": "high",
        "moat_replication_risk": "medium",
        "growth_constraint_risk": "medium",
        "valuation_peer_quality": "partial",
        "valuation_peer_reason": (
            "Useful for China ecommerce and merchant-services monetization, but not a clean peer for Temu "
            "because Alibaba has a broader portfolio and different segment mix."
        ),
        "evidence_focus": [
            "merchant monetization",
            "marketplace network effects",
            "cross-border marketplace overlap",
        ],
    },
    "jd": {
        "competitor_id": "jd",
        "name": "JD",
        "aliases": ["JD.com", "Jingdong"],
        "company_type": "public_company",
        "parent_company": "JD.com, Inc.",
        "relationship_to_target": "China ecommerce peer with a different logistics and trust model",
        "battlefields": [
            "China ecommerce",
            "Logistics",
            "Supply chain",
        ],
        "business_model": (
            "First-party retail and marketplace platform with self-operated logistics and supply-chain services."
        ),
        "business_model_differences": [
            "JD relies more on first-party retail, procurement, and logistics than PDD.",
            "JD competes more on fulfillment reliability and product authenticity.",
            "PDD's model is more marketplace and merchant-advertising oriented.",
        ],
        "advantages": [
            "Self-operated logistics and fulfillment quality.",
            "Consumer trust around authentic goods and delivery reliability.",
            "Supplier relationships and category depth in selected verticals.",
        ],
        "weaknesses": [
            "Capital and operating intensity are higher than a lighter marketplace model.",
            "The first-party retail model is less similar to PDD's merchant-advertising engine.",
            "Lower direct evidence for replicating Temu's cross-border bargain-discovery model.",
        ],
        "overlap_level": "high",
        "threat_level": "medium",
        "business_model_similarity": "medium",
        "moat_replication_risk": "low",
        "growth_constraint_risk": "medium",
        "valuation_peer_quality": "partial",
        "valuation_peer_reason": (
            "Useful for China ecommerce trust, logistics, and supply-chain comparison, but the first-party "
            "retail mix makes margins and asset intensity less comparable."
        ),
        "evidence_focus": [
            "logistics trust model",
            "supply-chain capability",
            "China ecommerce competition",
        ],
    },
    "amazon": {
        "competitor_id": "amazon",
        "name": "Amazon",
        "aliases": ["Amazon.com", "AMZN"],
        "company_type": "public_company",
        "parent_company": "Amazon.com, Inc.",
        "relationship_to_target": "global marketplace and fulfillment benchmark",
        "battlefields": [
            "Cross-border ecommerce",
            "Global marketplace",
            "Logistics",
            "Merchant advertising",
        ],
        "business_model": (
            "Global first-party and third-party marketplace, fulfillment network, subscription ecosystem, "
            "advertising platform, and cloud business."
        ),
        "business_model_differences": [
            "Amazon is structurally different because AWS, Prime, FBA, and first-party retail change the economics.",
            "Amazon's customer promise emphasizes selection, speed, trust, and convenience more than bargain discovery.",
            "Temu is more concentrated on low-price cross-border marketplace expansion.",
        ],
        "advantages": [
            "Fulfillment density and delivery-speed expectations in core markets.",
            "Massive seller tooling and advertising marketplace.",
            "Prime ecosystem and customer trust.",
            "Scale advantages across traffic, logistics, and cloud-supported infrastructure.",
        ],
        "weaknesses": [
            "High-cost fulfillment promise may be harder to reconcile with ultra-low-price positioning.",
            "AWS and Prime make company-level valuation and margin comparisons noisy.",
            "Different merchant and customer proposition reduces direct comparability to Temu.",
        ],
        "overlap_level": "medium",
        "threat_level": "medium",
        "business_model_similarity": "medium",
        "moat_replication_risk": "medium",
        "growth_constraint_risk": "medium",
        "valuation_peer_quality": "not_clean",
        "valuation_peer_reason": (
            "Useful as a marketplace, logistics, and advertising benchmark, but not a clean valuation peer "
            "for PDD or Temu because AWS, Prime, and fulfillment economics dominate comparability."
        ),
        "evidence_focus": [
            "fulfillment benchmark",
            "third-party marketplace monetization",
            "advertising scale",
        ],
    },
    "shein": {
        "competitor_id": "shein",
        "name": "SHEIN",
        "aliases": ["Shein"],
        "company_type": "private_company",
        "parent_company": "SHEIN Group",
        "relationship_to_target": "fashion-focused cross-border ecommerce peer to Temu",
        "battlefields": [
            "Cross-border ecommerce",
            "Supply chain",
            "App commerce",
        ],
        "business_model": (
            "Fashion-led cross-border commerce platform with demand-responsive supply chain and marketplace expansion."
        ),
        "business_model_differences": [
            "SHEIN is more fashion-led and category-focused than Temu.",
            "Temu is broader in general merchandise and more explicitly marketplace-like.",
            "SHEIN's supply-chain cadence is a stronger direct benchmark than its financial model.",
        ],
        "advantages": [
            "Fast fashion demand sensing and supplier coordination.",
            "Strong app-native merchandising and consumer engagement.",
            "Brand awareness in low-price fashion categories.",
        ],
        "weaknesses": [
            "Category concentration in fashion.",
            "Limited public financial disclosure.",
            "Regulatory, sustainability, labor, and IP scrutiny can pressure expansion.",
        ],
        "overlap_level": "medium",
        "threat_level": "medium",
        "business_model_similarity": "low",
        "moat_replication_risk": "medium",
        "growth_constraint_risk": "medium",
        "valuation_peer_quality": "not_clean",
        "valuation_peer_reason": (
            "Useful for cross-border supply-chain and app-commerce evidence, but not a direct valuation peer "
            "because audited public financials and broad marketplace comparability are limited."
        ),
        "evidence_focus": [
            "cross-border low-price competition",
            "fashion supply-chain speed",
            "app commerce",
        ],
    },
    "tiktok-shop": {
        "competitor_id": "tiktok-shop",
        "name": "TikTok Shop",
        "aliases": ["TikTokShop", "TikTok commerce", "Douyin ecommerce"],
        "company_type": "business_unit",
        "parent_company": "ByteDance",
        "relationship_to_target": "social-commerce threat to Temu and PDD merchant attention",
        "battlefields": [
            "Cross-border ecommerce",
            "Social commerce",
            "Merchant advertising",
            "App commerce",
        ],
        "business_model": (
            "Social-commerce marketplace embedded in a short-video and creator-discovery platform."
        ),
        "business_model_differences": [
            "TikTok Shop starts from traffic, creators, and discovery rather than search or bargain marketplace browsing.",
            "PDD and Temu rely more on value-for-money merchandising and marketplace conversion.",
            "TikTok Shop can change discovery and customer acquisition costs even when its transaction infrastructure is less mature.",
        ],
        "advantages": [
            "Large traffic pool and discovery engine.",
            "Creator ecosystem and live-shopping formats.",
            "High potential to redirect merchant ad budgets toward social commerce.",
        ],
        "weaknesses": [
            "Marketplace, fulfillment, and merchant operations are less mature than established ecommerce platforms.",
            "Creator-led conversion may be category uneven.",
            "Regulatory and platform-access risk is material in some markets.",
        ],
        "overlap_level": "high",
        "threat_level": "high",
        "business_model_similarity": "low",
        "moat_replication_risk": "high",
        "growth_constraint_risk": "high",
        "valuation_peer_quality": "not_clean",
        "valuation_peer_reason": (
            "Not a valuation peer, but critical competitive evidence for traffic acquisition, social commerce, "
            "merchant budgets, and discovery risk."
        ),
        "evidence_focus": [
            "social commerce",
            "traffic acquisition pressure",
            "merchant advertising substitution",
        ],
    },
    "aliexpress": {
        "competitor_id": "aliexpress",
        "name": "AliExpress",
        "aliases": ["Ali Express"],
        "company_type": "business_unit",
        "parent_company": "Alibaba Group Holding Limited",
        "relationship_to_target": "cross-border marketplace peer to Temu",
        "battlefields": [
            "Cross-border ecommerce",
            "Global marketplace",
            "Supply chain",
            "Logistics",
        ],
        "business_model": (
            "Alibaba-owned cross-border marketplace connecting merchants, largely China-linked supply, and global buyers."
        ),
        "business_model_differences": [
            "AliExpress is closer to Temu in cross-border marketplace structure than Alibaba's China commerce segments.",
            "Temu appears more aggressive in low-price positioning and promotion intensity.",
            "AliExpress has parent-level ecosystem support but less standalone financial visibility.",
        ],
        "advantages": [
            "Long-running cross-border marketplace operations.",
            "Alibaba merchant relationships and logistics ecosystem.",
            "Experience serving global buyers from China-linked supply.",
        ],
        "weaknesses": [
            "No standalone public financial statements.",
            "Consumer trust, delivery variability, and product-quality perception can limit repeat purchase.",
            "Parent-company disclosure may not isolate AliExpress economics.",
        ],
        "overlap_level": "high",
        "threat_level": "medium_high",
        "business_model_similarity": "high",
        "moat_replication_risk": "medium_high",
        "growth_constraint_risk": "medium_high",
        "valuation_peer_quality": "not_clean",
        "valuation_peer_reason": (
            "Useful as direct Temu competitive evidence, but not a standalone valuation peer because it is a "
            "business unit without isolated public financial statements."
        ),
        "evidence_focus": [
            "direct Temu marketplace overlap",
            "China-linked merchant supply",
            "cross-border logistics promise",
        ],
    },
}

SOURCE_REF_CATALOG: list[dict[str, Any]] = [
    {
        "source_id": "pdd_2024_20f",
        "entity_id": "pdd",
        "entity_name": "PDD Holdings",
        "scope": "target_company",
        "source_type": "official_filing",
        "source_name": "PDD Holdings 2024 Form 20-F",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1737806/000141057825000951/pdd-20241231x20f.htm",
        "reliability": "high",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["China ecommerce", "Cross-border ecommerce", "Merchant advertising"],
        "claim_candidates": [
            "Target-company baseline for marketplace monetization, Temu positioning, risk factors, and disclosed operating model.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "risk_agent", "valuation_agent"],
    },
    {
        "source_id": "alibaba_2025_20f",
        "entity_id": "alibaba",
        "entity_name": "Alibaba",
        "scope": "competitor",
        "source_type": "official_filing",
        "source_name": "Alibaba Group fiscal 2025 Form 20-F",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1577552/000095017025090161/baba-20250331.htm",
        "reliability": "high",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["China ecommerce", "Cross-border ecommerce", "Merchant advertising", "Logistics"],
        "claim_candidates": [
            "Use for China commerce, international commerce, merchant services, and platform risk comparison.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "growth_runway_agent", "valuation_agent"],
    },
    {
        "source_id": "jd_2024_20f",
        "entity_id": "jd",
        "entity_name": "JD",
        "scope": "competitor",
        "source_type": "official_filing",
        "source_name": "JD.com 2024 Form 20-F",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1549802/000119312525083473/d871796d20f.htm",
        "reliability": "high",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["China ecommerce", "Logistics", "Supply chain"],
        "claim_candidates": [
            "Use for self-operated retail, logistics, supply-chain services, and asset-intensity comparison.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "risk_agent", "valuation_agent"],
    },
    {
        "source_id": "amazon_2024_annual_report",
        "entity_id": "amazon",
        "entity_name": "Amazon",
        "scope": "competitor",
        "source_type": "official_filing",
        "source_name": "Amazon 2024 annual report / Form 10-K",
        "source_url": "https://s2.q4cdn.com/299287126/files/doc_financials/2025/ar/Amazon-2024-Annual-Report.pdf",
        "reliability": "high",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Global marketplace", "Logistics", "Merchant advertising", "Cross-border ecommerce"],
        "claim_candidates": [
            "Use as a fulfillment, seller services, advertising, and multi-business comparability benchmark.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "valuation_agent"],
    },
    {
        "source_id": "shein_marketplace_get_started",
        "entity_id": "shein",
        "entity_name": "SHEIN",
        "scope": "competitor",
        "source_type": "merchant_terms",
        "source_name": "SHEIN Marketplace seller requirements",
        "source_url": "https://seller-us.shein.com/get-started-shein-marketplace",
        "reliability": "medium",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Cross-border ecommerce", "Supply chain", "App commerce"],
        "claim_candidates": [
            "Use for marketplace onboarding, seller requirements, and category expansion signals.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "growth_runway_agent"],
    },
    {
        "source_id": "shein_marketplace_agreement",
        "entity_id": "shein",
        "entity_name": "SHEIN",
        "scope": "competitor",
        "source_type": "merchant_terms",
        "source_name": "SHEIN Marketplace services agreement",
        "source_url": "https://seller-us.shein.com/agreement",
        "reliability": "medium",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Cross-border ecommerce", "Supply chain"],
        "claim_candidates": [
            "Use for seller obligations, marketplace rules, and platform control points.",
        ],
        "downstream_consumers": ["business_model_agent", "risk_agent"],
    },
    {
        "source_id": "tiktok_shop_seller_terms_us",
        "entity_id": "tiktok-shop",
        "entity_name": "TikTok Shop",
        "scope": "competitor",
        "source_type": "merchant_terms",
        "source_name": "TikTok Shop US seller terms",
        "source_url": "https://seller-us.tiktok.com/university/essay?default_language=en&identity=1&knowledge_id=1331308753078058",
        "reliability": "medium",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Social commerce", "Merchant advertising", "App commerce"],
        "claim_candidates": [
            "Use for seller obligations, platform control, account suspension risk, and commerce product scope.",
        ],
        "downstream_consumers": ["moat_agent", "growth_runway_agent", "risk_agent"],
    },
    {
        "source_id": "tiktok_shop_intro_newsroom",
        "entity_id": "tiktok-shop",
        "entity_name": "TikTok Shop",
        "scope": "competitor",
        "source_type": "official_website",
        "source_name": "TikTok newsroom introduction to TikTok Shop",
        "source_url": "https://newsroom.tiktok.com/en-us/introducing-tiktok-shop",
        "reliability": "medium",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Social commerce", "App commerce", "Cross-border ecommerce"],
        "claim_candidates": [
            "Use for TikTok Shop product surface, shop tab, discovery flow, and creator-led commerce framing.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "growth_runway_agent"],
    },
    {
        "source_id": "aliexpress_alibaba_20f",
        "entity_id": "aliexpress",
        "entity_name": "AliExpress",
        "scope": "competitor",
        "source_type": "parent_company_filing",
        "source_name": "Alibaba Group Form 20-F references to international commerce and AliExpress",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1577552/000095017025090161/baba-20250331.htm",
        "reliability": "medium",
        "evidence_status": "source_ref_only_pending_excerpt",
        "battlefields": ["Cross-border ecommerce", "Global marketplace", "Supply chain", "Logistics"],
        "claim_candidates": [
            "Use for parent-level disclosure about international commerce; do not infer standalone AliExpress margins.",
        ],
        "downstream_consumers": ["business_model_agent", "moat_agent", "valuation_agent"],
    },
]

BATTLEFIELD_PLAYBOOK: dict[str, dict[str, Any]] = {
    "China ecommerce": {
        "question": "Who pressures PDD's domestic China marketplace model?",
        "pressure_mechanisms": ["merchant monetization", "user retention", "fulfillment trust", "platform governance"],
        "primary_downstream_consumers": ["business_model_agent", "moat_agent", "risk_agent"],
    },
    "Cross-border ecommerce": {
        "question": "Who pressures Temu's cross-border low-price proposition?",
        "pressure_mechanisms": ["price band overlap", "China-linked supply", "delivery promise", "category expansion"],
        "primary_downstream_consumers": ["business_model_agent", "moat_agent", "growth_runway_agent"],
    },
    "Merchant advertising": {
        "question": "Who competes for merchant advertising budgets and platform take-rate?",
        "pressure_mechanisms": ["ad load", "seller tools", "creator campaigns", "marketplace traffic allocation"],
        "primary_downstream_consumers": ["business_model_agent", "valuation_agent", "risk_agent"],
    },
    "Logistics": {
        "question": "Who sets customer expectations for delivery speed, returns, and fulfillment reliability?",
        "pressure_mechanisms": ["delivery speed", "returns workflow", "warehouse density", "third-party fulfillment partners"],
        "primary_downstream_consumers": ["moat_agent", "risk_agent", "valuation_agent"],
    },
    "Supply chain": {
        "question": "Who can match or pressure low-cost supply and supplier coordination?",
        "pressure_mechanisms": ["supplier relationships", "demand sensing", "inventory risk", "category sourcing"],
        "primary_downstream_consumers": ["moat_agent", "growth_runway_agent", "risk_agent"],
    },
    "Global marketplace": {
        "question": "Who defines the benchmark for global marketplace scale and seller services?",
        "pressure_mechanisms": ["seller tooling", "buyer protection", "global catalog", "cross-border trust"],
        "primary_downstream_consumers": ["business_model_agent", "valuation_agent"],
    },
    "App commerce": {
        "question": "Who competes for app-native discovery and repeat shopping behavior?",
        "pressure_mechanisms": ["app engagement", "push/promotion cadence", "content-led conversion", "review quality"],
        "primary_downstream_consumers": ["growth_runway_agent", "moat_agent", "risk_agent"],
    },
    "Social commerce": {
        "question": "Who can change shopping discovery through content and creators?",
        "pressure_mechanisms": ["creator ecosystem", "live shopping", "affiliate incentives", "feed discovery"],
        "primary_downstream_consumers": ["moat_agent", "growth_runway_agent", "risk_agent"],
    },
}

SCORECARD_BY_COMPETITOR: dict[str, dict[str, str]] = {
    "alibaba": {
        "user_overlap": "high",
        "merchant_overlap": "high",
        "price_band_overlap": "medium",
        "category_overlap": "high",
        "geography_overlap": "high",
        "acquisition_channel_overlap": "medium",
        "monetization_model_overlap": "high",
        "replication_difficulty": "medium",
    },
    "jd": {
        "user_overlap": "high",
        "merchant_overlap": "medium",
        "price_band_overlap": "medium",
        "category_overlap": "high",
        "geography_overlap": "high",
        "acquisition_channel_overlap": "low",
        "monetization_model_overlap": "medium",
        "replication_difficulty": "high",
    },
    "amazon": {
        "user_overlap": "medium",
        "merchant_overlap": "medium",
        "price_band_overlap": "low",
        "category_overlap": "high",
        "geography_overlap": "medium",
        "acquisition_channel_overlap": "medium",
        "monetization_model_overlap": "medium",
        "replication_difficulty": "high",
    },
    "shein": {
        "user_overlap": "medium",
        "merchant_overlap": "medium",
        "price_band_overlap": "medium_high",
        "category_overlap": "medium",
        "geography_overlap": "medium_high",
        "acquisition_channel_overlap": "medium",
        "monetization_model_overlap": "low",
        "replication_difficulty": "medium",
    },
    "tiktok-shop": {
        "user_overlap": "high",
        "merchant_overlap": "medium_high",
        "price_band_overlap": "medium",
        "category_overlap": "medium_high",
        "geography_overlap": "medium_high",
        "acquisition_channel_overlap": "high",
        "monetization_model_overlap": "medium_high",
        "replication_difficulty": "medium",
    },
    "aliexpress": {
        "user_overlap": "high",
        "merchant_overlap": "high",
        "price_band_overlap": "high",
        "category_overlap": "high",
        "geography_overlap": "high",
        "acquisition_channel_overlap": "medium",
        "monetization_model_overlap": "high",
        "replication_difficulty": "medium",
    },
}

COUNTEREVIDENCE_BY_COMPETITOR: dict[str, list[dict[str, Any]]] = {
    "alibaba": [
        {
            "point": "Alibaba's broader portfolio can make it look stronger or weaker than the specific China ecommerce battlefield.",
            "why_it_matters": "Avoid over-weighting cloud, local services, or unrelated segments when judging PDD's marketplace moat.",
            "resolution_needed": "Segment-specific extraction from 20-F and investor materials.",
        }
    ],
    "jd": [
        {
            "point": "JD's first-party and logistics-heavy model may not attack PDD's merchant-advertising model directly.",
            "why_it_matters": "JD is a trust and fulfillment benchmark, not always a take-rate or ad-load benchmark.",
            "resolution_needed": "Separate marketplace pressure from fulfillment-quality pressure.",
        }
    ],
    "amazon": [
        {
            "point": "Amazon's AWS, Prime, and mature fulfillment network can distort valuation and margin comparisons.",
            "why_it_matters": "Amazon should be treated as an operating benchmark rather than a clean valuation peer.",
            "resolution_needed": "Use battlefield-level operating analogies instead of company-level multiples.",
        }
    ],
    "shein": [
        {
            "point": "SHEIN is category-concentrated in fashion and may not replicate Temu's broad general-merchandise marketplace.",
            "why_it_matters": "The threat may be strong in fashion but weaker in categories where Temu has broader supplier coverage.",
            "resolution_needed": "Compare category overlap, app ranking, and product-price baskets.",
        }
    ],
    "tiktok-shop": [
        {
            "point": "TikTok Shop may be powerful for discovery but weaker in marketplace operations, returns, and fulfillment consistency.",
            "why_it_matters": "High traffic does not automatically equal durable ecommerce moat replication.",
            "resolution_needed": "Track merchant terms, fulfillment policies, app reviews, and seller complaint themes.",
        }
    ],
    "aliexpress": [
        {
            "point": "AliExpress is close to Temu structurally but lacks standalone financial disclosure.",
            "why_it_matters": "It is strong competitive evidence but weak direct valuation evidence.",
            "resolution_needed": "Use Alibaba parent filings plus product/pricing/traffic signals, not inferred standalone margins.",
        }
    ],
}


def load_comparator_request(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Comparator request not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".json":
        return json.loads(input_path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "YAML input requires PyYAML. Use JSON input or install the optional YAML parser."
            ) from exc
        loaded = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        return loaded or {}
    raise ValueError(f"Unsupported comparator request format: {suffix}")


def run_comparator_evidence_pipeline(
    *,
    input_path: str | Path,
    output_dir: str | Path = "data/comparator_evidence",
    run_id: str | None = None,
) -> dict[str, Any]:
    request = load_comparator_request(input_path)
    pack = build_comparator_evidence_pack(request)
    return write_comparator_outputs(pack, output_dir=output_dir, run_id=run_id)


def write_comparator_outputs(
    pack: dict[str, Any],
    *,
    output_dir: str | Path = "data/comparator_evidence",
    run_id: str | None = None,
) -> dict[str, Any]:
    main_company = pack.get("main_company") or {}
    run_label = run_id or make_comparator_run_id(main_company)
    run_dir = Path(output_dir) / run_label
    run_dir.mkdir(parents=True, exist_ok=True)

    json_path = run_dir / "comparator_evidence_pack.json"
    markdown_path = run_dir / "comparator_evidence_report.md"
    markdown_zh_path = run_dir / "comparator_evidence_report.zh.md"
    json_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_comparator_markdown(pack).strip() + "\n", encoding="utf-8")
    markdown_zh_path.write_text(render_comparator_markdown_zh(pack).strip() + "\n", encoding="utf-8")

    return {
        "run_id": run_label,
        "run_dir": str(run_dir),
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "markdown_zh_path": str(markdown_zh_path),
        "schema_version": pack.get("schema_version"),
        "competitor_count": len(pack.get("competitor_packs", [])),
        "battlefield_count": len(pack.get("battlefields", [])),
        "implication_count": sum(len(items) for items in (pack.get("implications") or {}).values()),
    }


def make_comparator_run_id(main_company: dict[str, Any]) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    label = str(main_company.get("ticker") or main_company.get("name") or "company")
    return f"{timestamp}-{_slugify(label)}-comparator-evidence"


def build_comparator_evidence_pack(request: dict[str, Any]) -> dict[str, Any]:
    main_company = _normalize_main_company(request.get("main_company") or {})
    competitor_names = [str(item) for item in request.get("competitors", []) if str(item).strip()]
    if not competitor_names:
        raise ValueError("Comparator request requires at least one competitor.")

    profile_records = [_profile_for_competitor(name) for name in competitor_names]
    battlefields = _battlefields_from_request_or_profiles(request.get("battlefields"), profile_records)

    competitor_map = [
        _build_competitor_map_item(profile=profile, battlefields=battlefields)
        for profile in profile_records
    ]
    competitor_packs = [
        _build_competitor_pack(main_company=main_company, profile=profile, map_item=map_item)
        for profile, map_item in zip(profile_records, competitor_map)
    ]
    source_refs = _build_source_refs(main_company=main_company, competitor_packs=competitor_packs)
    _attach_deep_evidence_to_competitor_packs(competitor_packs, source_refs)
    battlefield_analysis = _build_battlefield_analysis(
        battlefields=battlefields,
        competitor_packs=competitor_packs,
        source_refs=source_refs,
    )
    comparison_matrix = _build_comparison_matrix(competitor_packs)
    implications = _generate_implications(
        main_company=main_company,
        competitor_packs=competitor_packs,
        comparison_matrix=comparison_matrix,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "pipeline": {
            "name": "Comparator Evidence Pipeline",
            "stage": "mvp",
            "purpose": (
                "Generate comparative evidence about the main company. This pipeline does not judge "
                "whether competitors are attractive investments."
            ),
        },
        "main_company": main_company,
        "battlefields": battlefields,
        "battlefield_analysis": battlefield_analysis,
        "source_refs": source_refs,
        "competitor_map": competitor_map,
        "competitor_packs": competitor_packs,
        "comparison_matrix": comparison_matrix,
        "implications": implications,
        "downstream_routing": _build_downstream_routing(
            competitor_packs=competitor_packs,
            implications=implications,
            battlefield_analysis=battlefield_analysis,
        ),
        "downstream_consumers": DEFAULT_DOWNSTREAM_CONSUMERS,
        "mvp_exclusions": [
            "No DCF or full valuation model.",
            "No investment recommendation for the target or competitors.",
            "No automatic competitor discovery.",
            "No bull or bear debate.",
            "No promotion of private-company estimates into audited facts.",
        ],
    }


def render_comparator_markdown(pack: dict[str, Any]) -> str:
    main_company = pack.get("main_company") or {}
    main_label = _main_company_label(main_company)
    lines = [
        f"# Comparator Evidence Report: {main_label}",
        "",
        "This report treats competitors as evidence about the target company. It does not assess whether the competitors are attractive investments.",
        "",
        "## Scope",
        "",
        f"- Schema version: {pack.get('schema_version')}",
        f"- Generated at: {pack.get('generated_at')}",
        f"- Battlefields: {_join(pack.get('battlefields', []))}",
        "",
        "## Competitor Map",
        "",
        "| Competitor | Type | Battlefields | Relationship To Target |",
        "| --- | --- | --- | --- |",
    ]
    for item in pack.get("competitor_map", []):
        lines.append(
            "| {name} | {company_type} | {battlefields} | {relationship} |".format(
                name=_md(item.get("name")),
                company_type=_md(item.get("company_type")),
                battlefields=_md(_join(item.get("battlefields", []))),
                relationship=_md(item.get("relationship_to_target")),
            )
        )

    lines.extend(
        [
            "",
            "## Comparison Matrix",
            "",
            "| Competitor | Overlap | Threat | Model Similarity | Moat Replication Risk | Evidence Reliability | Valuation Peer Quality |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("comparison_matrix", []):
        lines.append(
            "| {competitor} | {overlap} | {threat} | {similarity} | {moat} | {reliability} | {peer} |".format(
                competitor=_md(row.get("competitor")),
                overlap=_md(row.get("overlap")),
                threat=_md(row.get("threat")),
                similarity=_md(row.get("business_model_similarity")),
                moat=_md(row.get("moat_replication_risk")),
                reliability=_md(row.get("evidence_reliability")),
                peer=_md(row.get("valuation_peer_quality")),
            )
        )

    lines.extend(["", "## Battlefield Deep Dive", ""])
    for battlefield in pack.get("battlefield_analysis", []):
        lines.extend(
            [
                f"### {battlefield.get('battlefield')}",
                "",
                f"- Question: {battlefield.get('question')}",
                f"- Pressure mechanisms: {_join(battlefield.get('pressure_mechanisms', []))}",
                f"- Source refs: {_join(battlefield.get('source_refs', []))}",
                f"- Evidence status: {battlefield.get('evidence_status')}",
                "",
                "| Competitor | Overlap | Threat | Scorecard Focus |",
                "| --- | --- | --- | --- |",
            ]
        )
        for competitor in battlefield.get("competitors", []):
            lines.append(
                "| {name} | {overlap} | {threat} | {focus} |".format(
                    name=_md(competitor.get("competitor_name")),
                    overlap=_md(competitor.get("overlap")),
                    threat=_md(competitor.get("threat_to_target")),
                    focus=_md(_scorecard_focus_text(competitor.get("scorecard_focus", {}))),
                )
            )
        lines.append("")

    lines.extend(["## Source-Grounded Evidence Index", ""])
    lines.extend(
        [
            "| Source ID | Entity | Type | Reliability | Status | Battlefields | URL |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for source in pack.get("source_refs", []):
        lines.append(
            "| {source_id} | {entity} | {source_type} | {reliability} | {status} | {battlefields} | {url} |".format(
                source_id=_md(source.get("source_id")),
                entity=_md(source.get("entity_name")),
                source_type=_md(source.get("source_type")),
                reliability=_md(source.get("reliability")),
                status=_md(source.get("evidence_status")),
                battlefields=_md(_join(source.get("battlefields", []))),
                url=_md(source.get("source_url")),
            )
        )
    lines.append("")

    lines.extend(["", "## Implications", ""])
    implications = pack.get("implications") or {}
    for category in ["business_model", "moat", "growth", "risk", "valuation"]:
        lines.extend([f"### {category.replace('_', ' ').title()}", ""])
        category_items = implications.get(category, [])
        if not category_items:
            lines.append("- No implication generated at MVP confidence threshold.")
        for item in category_items:
            refs = _join(item.get("evidence_refs", []))
            lines.append(f"- {item.get('statement')} Confidence: {item.get('confidence')}. Evidence refs: {refs}.")
        lines.append("")

    lines.extend(["## Competitor Evidence Packs", ""])
    for pack_item in pack.get("competitor_packs", []):
        lines.extend(
            [
                f"### {pack_item.get('competitor_name')}",
                "",
                f"- Business overlap: {pack_item.get('business_overlap', {}).get('level')}",
                f"- Threat to target: {pack_item.get('threat_to_target')}",
                f"- Evidence reliability: {pack_item.get('evidence_reliability', {}).get('overall')}",
                f"- Primary battlefields: {_join(pack_item.get('business_overlap', {}).get('battlefields', []))}",
                "",
                "Fixed questions:",
            ]
        )
        for answer in pack_item.get("fixed_question_answers", []):
            lines.append(f"- {answer.get('question_id')}: {answer.get('answer')}")
        scorecard = pack_item.get("scorecard") or {}
        if scorecard:
            lines.extend(["", "Scorecard:"])
            for dimension, value in (scorecard.get("dimensions") or {}).items():
                lines.append(f"- {dimension}: {value}")
        uncertainties = pack_item.get("counterevidence_and_uncertainties") or []
        if uncertainties:
            lines.extend(["", "Counterevidence / uncertainties:"])
            for item in uncertainties:
                lines.append(f"- {item.get('point')} Why it matters: {item.get('why_it_matters')}")
        gaps = pack_item.get("evidence_gaps") or []
        if gaps:
            lines.extend(["", "Evidence gaps:"])
            for gap in gaps:
                lines.append(f"- {gap}")
        lines.extend(["", "Source labels:"])
        for source in pack_item.get("source_inventory", []):
            lines.append(
                "- {source_type}: {source_name}. Reliability: {reliability}. Available: {available}.".format(
                    source_type=source.get("source_type"),
                    source_name=source.get("source_name"),
                    reliability=source.get("reliability"),
                    available=str(source.get("available")).lower(),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## MVP Guardrails",
            "",
        ]
    )
    for exclusion in pack.get("mvp_exclusions", []):
        lines.append(f"- {exclusion}")

    lines.extend(["", "## Downstream Routing", ""])
    routing = pack.get("downstream_routing") or {}
    for consumer in DEFAULT_DOWNSTREAM_CONSUMERS:
        item = routing.get(consumer) or {}
        lines.append(f"- {consumer}: {item.get('notes')} Battlefields: {_join(item.get('battlefields', []))}.")

    return "\n".join(lines)


def render_comparator_markdown_zh(pack: dict[str, Any]) -> str:
    main_company = pack.get("main_company") or {}
    main_label = _main_company_label(main_company)
    lines = [
        f"# 竞争对手证据报告：{main_label}",
        "",
        "本报告把竞争对手当作理解目标公司的比较证据，而不是判断竞争对手本身是否值得投资。",
        "",
        "## 范围",
        "",
        f"- Schema version: {pack.get('schema_version')}",
        f"- 生成时间: {pack.get('generated_at')}",
        f"- 竞争战场: {_zh_join_battlefields(pack.get('battlefields', []))}",
        "",
        "## 竞品地图",
        "",
        "| 竞争对手 | 类型 | 竞争战场 | 对目标公司的意义 |",
        "| --- | --- | --- | --- |",
    ]
    for item in pack.get("competitor_map", []):
        competitor_id = str(item.get("competitor_id") or "")
        details = ZH_COMPETITOR_DETAILS.get(competitor_id, {})
        lines.append(
            "| {name} | {company_type} | {battlefields} | {relationship} |".format(
                name=_md(item.get("name")),
                company_type=_md(_zh_enum(item.get("company_type"), ZH_COMPANY_TYPE_LABELS)),
                battlefields=_md(_zh_join_battlefields(item.get("battlefields", []))),
                relationship=_md(details.get("relationship") or item.get("relationship_to_target")),
            )
        )

    lines.extend(
        [
            "",
            "## 对比矩阵",
            "",
            "| 竞争对手 | 业务重叠 | 威胁程度 | 模式相似度 | 壁垒复制风险 | 证据可靠性 | 估值可比性 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("comparison_matrix", []):
        lines.append(
            "| {competitor} | {overlap} | {threat} | {similarity} | {moat} | {reliability} | {peer} |".format(
                competitor=_md(row.get("competitor")),
                overlap=_md(_zh_level(row.get("overlap"))),
                threat=_md(_zh_level(row.get("threat"))),
                similarity=_md(_zh_level(row.get("business_model_similarity"))),
                moat=_md(_zh_level(row.get("moat_replication_risk"))),
                reliability=_md(_zh_level(row.get("evidence_reliability"))),
                peer=_md(_zh_level(row.get("valuation_peer_quality"))),
            )
        )

    lines.extend(["", "## 战场级深挖", ""])
    for battlefield in pack.get("battlefield_analysis", []):
        lines.extend(
            [
                f"### {_zh_battlefield(battlefield.get('battlefield'))}",
                "",
                f"- 核心问题: {_zh_battlefield_question(battlefield)}",
                f"- 压力机制: {_zh_join_pressure_mechanisms(battlefield.get('pressure_mechanisms', []))}",
                f"- 来源引用: {_join(battlefield.get('source_refs', []))}",
                f"- 证据状态: {_zh_evidence_status(battlefield.get('evidence_status'))}",
                "",
                "| 竞争对手 | 业务重叠 | 威胁程度 | 评分关注点 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for competitor in battlefield.get("competitors", []):
            lines.append(
                "| {name} | {overlap} | {threat} | {focus} |".format(
                    name=_md(competitor.get("competitor_name")),
                    overlap=_md(_zh_level(competitor.get("overlap"))),
                    threat=_md(_zh_level(competitor.get("threat_to_target"))),
                    focus=_md(_zh_scorecard_focus_text(competitor.get("scorecard_focus", {}))),
                )
            )
        if battlefield.get("open_questions"):
            lines.append("")
            lines.append("待验证问题:")
            for question in battlefield.get("open_questions", []):
                lines.append(f"- {_zh_open_question(question)}")
        lines.append("")

    lines.extend(["## 真实来源索引", ""])
    lines.extend(
        [
            "| Source ID | 对象 | 类型 | 可靠性 | 状态 | 竞争战场 | URL |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for source in pack.get("source_refs", []):
        lines.append(
            "| {source_id} | {entity} | {source_type} | {reliability} | {status} | {battlefields} | {url} |".format(
                source_id=_md(source.get("source_id")),
                entity=_md(source.get("entity_name")),
                source_type=_md(_zh_enum(source.get("source_type"), ZH_SOURCE_TYPE_LABELS)),
                reliability=_md(_zh_level(source.get("reliability"))),
                status=_md(_zh_evidence_status(source.get("evidence_status"))),
                battlefields=_md(_zh_join_battlefields(source.get("battlefields", []))),
                url=_md(source.get("source_url")),
            )
        )

    lines.extend(["", f"## 对 {main_label} 的含义", ""])
    implications = pack.get("implications") or {}
    for category in ["business_model", "moat", "growth", "risk", "valuation"]:
        lines.extend([f"### {ZH_CATEGORY_LABELS[category]}", ""])
        category_items = implications.get(category, [])
        if not category_items:
            lines.append("- MVP 置信度门槛下暂未生成明确含义。")
        for item in category_items:
            refs = _join(item.get("evidence_refs", []))
            statement = _zh_implication_statement(item, main_label)
            confidence = _zh_level(item.get("confidence"))
            lines.append(f"- {statement} 置信度：{confidence}。证据引用：{refs}。")
        lines.append("")

    lines.extend(["## 竞品证据包", ""])
    for pack_item in pack.get("competitor_packs", []):
        competitor_id = str(pack_item.get("competitor_id") or "")
        details = ZH_COMPETITOR_DETAILS.get(competitor_id, {})
        overlap = pack_item.get("business_overlap", {})
        lines.extend(
            [
                f"### {pack_item.get('competitor_name')}",
                "",
                f"- 业务重叠: {_zh_level(overlap.get('level'))}",
                f"- 对目标公司的威胁: {_zh_level(pack_item.get('threat_to_target'))}",
                f"- 证据可靠性: {_zh_level((pack_item.get('evidence_reliability') or {}).get('overall'))}",
                f"- 主要竞争战场: {_zh_join_battlefields(overlap.get('battlefields', []))}",
                "",
                "固定问题:",
            ]
        )
        lines.extend(_zh_fixed_question_answers(pack_item, main_label, details))
        scorecard = pack_item.get("scorecard") or {}
        if scorecard:
            lines.extend(["", "可复核评分:"])
            for dimension, value in (scorecard.get("dimensions") or {}).items():
                lines.append(f"- {_zh_scorecard_dimension(dimension)}: {_zh_level(value)}")
        uncertainties = pack_item.get("counterevidence_and_uncertainties") or []
        if uncertainties:
            lines.extend(["", "反证与不确定性:"])
            for item in uncertainties:
                lines.append(
                    f"- {_zh_uncertainty_item(item)}"
                )
        gaps = pack_item.get("evidence_gaps") or []
        if gaps:
            lines.extend(["", "证据缺口:"])
            for gap in gaps:
                lines.append(f"- {_zh_evidence_gap(gap)}")
        lines.extend(["", "来源标签:"])
        for source in pack_item.get("source_inventory", []):
            lines.append(
                "- {source_type}: {source_name}。可靠性：{reliability}。是否可用：{available}。".format(
                    source_type=_zh_enum(source.get("source_type"), ZH_SOURCE_TYPE_LABELS),
                    source_name=_zh_source_name(source),
                    reliability=_zh_level(source.get("reliability")),
                    available="是" if source.get("available") else "否",
                )
            )
        lines.append("")

    lines.extend(["## MVP 边界", ""])
    lines.extend(
        [
            "- 不做 DCF 或完整估值模型。",
            "- 不对目标公司或竞争对手给出买卖建议。",
            "- 不做自动竞品发现。",
            "- 不做牛熊辩论。",
            "- 不把未上市公司或业务单元的估算数据升级成已审计事实。",
        ]
    )

    lines.extend(["", "## 下游 Agent 使用路由", ""])
    routing = pack.get("downstream_routing") or {}
    for consumer in DEFAULT_DOWNSTREAM_CONSUMERS:
        item = routing.get(consumer) or {}
        lines.append(
            f"- {consumer}: {_zh_routing_note(item.get('notes'))} 相关战场：{_zh_join_battlefields(item.get('battlefields', []))}。"
        )

    return "\n".join(lines)


def _build_source_refs(
    *,
    main_company: dict[str, Any],
    competitor_packs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entity_ids = {pack["competitor_id"] for pack in competitor_packs}
    main_ticker = str(main_company.get("ticker") or "").casefold()
    if main_ticker == "pdd" or str(main_company.get("name") or "").casefold().startswith("pdd"):
        entity_ids.add("pdd")
    refs = []
    for source in SOURCE_REF_CATALOG:
        if source["entity_id"] not in entity_ids:
            continue
        record = dict(source)
        record["limitations"] = _source_ref_limitations(record)
        record["excerpt_policy"] = (
            "No verbatim excerpt is stored in this MVP unless a fetch/extraction step has populated it."
        )
        refs.append(record)
    return refs


def _attach_deep_evidence_to_competitor_packs(
    competitor_packs: list[dict[str, Any]],
    source_refs: list[dict[str, Any]],
) -> None:
    for pack in competitor_packs:
        competitor_id = str(pack.get("competitor_id") or "")
        refs = [source for source in source_refs if source.get("entity_id") == competitor_id]
        pack["source_refs"] = [source["source_id"] for source in refs]
        pack["source_ref_details"] = refs
        pack["scorecard"] = _scorecard_for_competitor(competitor_id)
        pack["counterevidence_and_uncertainties"] = COUNTEREVIDENCE_BY_COMPETITOR.get(
            competitor_id,
            [
                {
                    "point": "No configured counterevidence yet.",
                    "why_it_matters": "Downstream agents should not over-weight an unconfigured competitor.",
                    "resolution_needed": "Add source-grounded competitor profile.",
                }
            ],
        )
        pack["evidence_gaps"] = _evidence_gaps_for_pack(pack)


def _build_battlefield_analysis(
    *,
    battlefields: list[str],
    competitor_packs: list[dict[str, Any]],
    source_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for battlefield in battlefields:
        competitor_rows = [
            {
                "competitor_id": pack["competitor_id"],
                "competitor_name": pack["competitor_name"],
                "threat_to_target": pack["threat_to_target"],
                "overlap": pack["business_overlap"]["level"],
                "scorecard_focus": _scorecard_focus_for_battlefield(
                    battlefield,
                    pack.get("scorecard", {}),
                ),
            }
            for pack in competitor_packs
            if battlefield in pack.get("business_overlap", {}).get("battlefields", [])
        ]
        source_ids = [
            source["source_id"]
            for source in source_refs
            if battlefield in source.get("battlefields", [])
        ]
        playbook = BATTLEFIELD_PLAYBOOK.get(battlefield, {})
        rows.append(
            {
                "battlefield": battlefield,
                "question": playbook.get("question") or f"What does {battlefield} imply for the target?",
                "pressure_mechanisms": playbook.get("pressure_mechanisms", []),
                "competitors": competitor_rows,
                "source_refs": source_ids,
                "primary_downstream_consumers": playbook.get(
                    "primary_downstream_consumers",
                    ["business_model_agent", "risk_agent"],
                ),
                "evidence_status": "source_ref_only_pending_excerpt",
                "open_questions": _battlefield_open_questions(battlefield, competitor_rows),
            }
        )
    return rows


def _build_downstream_routing(
    *,
    competitor_packs: list[dict[str, Any]],
    implications: dict[str, list[dict[str, Any]]],
    battlefield_analysis: list[dict[str, Any]],
) -> dict[str, Any]:
    routing: dict[str, Any] = {}
    for consumer in DEFAULT_DOWNSTREAM_CONSUMERS:
        routing[consumer] = {
            "implication_ids": [
                item["implication_id"]
                for category_items in implications.values()
                for item in category_items
                if consumer in item.get("downstream_consumers", [])
            ],
            "battlefields": [
                item["battlefield"]
                for item in battlefield_analysis
                if consumer in item.get("primary_downstream_consumers", [])
            ],
            "competitor_pack_fields": _fields_for_downstream_consumer(consumer),
            "notes": _routing_note_for_consumer(consumer),
        }
    routing["shared_warning"] = (
        "Use competitor evidence as comparative context for the target company. Do not convert it into "
        "standalone investment recommendations for competitors."
    )
    routing["pack_count"] = len(competitor_packs)
    return routing


def _source_ref_limitations(source: dict[str, Any]) -> list[str]:
    source_type = source.get("source_type")
    if source.get("scope") == "target_company":
        return ["Target-company source; use for baseline, not competitor proof."]
    if source_type in {"official_filing", "parent_company_filing"}:
        return [
            "May not isolate the exact battlefield.",
            "Requires extraction before treating a claim as source-grounded.",
        ]
    if source_type in {"merchant_terms", "official_website"}:
        return [
            "Useful for business-model evidence, but not audited financial evidence.",
            "Terms and product surfaces can change over time.",
        ]
    return ["Use as directional evidence only until calibrated."]


def _scorecard_for_competitor(competitor_id: str) -> dict[str, Any]:
    dimensions = SCORECARD_BY_COMPETITOR.get(competitor_id, {})
    return {
        "status": "rule_based_v1_pending_source_calibration",
        "dimensions": dimensions,
        "dimension_count": len(dimensions),
        "interpretation": _scorecard_interpretation(dimensions),
    }


def _scorecard_interpretation(dimensions: dict[str, str]) -> str:
    high_dimensions = [
        name
        for name, value in dimensions.items()
        if value in {"high", "medium_high"}
    ]
    if not high_dimensions:
        return "Low configured overlap; requires manual review before use."
    return f"Highest pressure dimensions: {_join(high_dimensions)}."


def _scorecard_focus_for_battlefield(
    battlefield: str,
    scorecard: dict[str, Any],
) -> dict[str, str]:
    dimensions = scorecard.get("dimensions") or {}
    focus_map = {
        "China ecommerce": ["user_overlap", "merchant_overlap", "category_overlap", "geography_overlap"],
        "Cross-border ecommerce": ["price_band_overlap", "category_overlap", "geography_overlap"],
        "Merchant advertising": ["merchant_overlap", "acquisition_channel_overlap", "monetization_model_overlap"],
        "Logistics": ["replication_difficulty", "geography_overlap"],
        "Supply chain": ["merchant_overlap", "category_overlap", "replication_difficulty"],
        "Global marketplace": ["merchant_overlap", "category_overlap", "geography_overlap"],
        "App commerce": ["user_overlap", "acquisition_channel_overlap", "price_band_overlap"],
        "Social commerce": ["user_overlap", "acquisition_channel_overlap", "merchant_overlap"],
    }
    return {
        dimension: dimensions.get(dimension, "unknown")
        for dimension in focus_map.get(battlefield, [])
    }


def _battlefield_open_questions(
    battlefield: str,
    competitor_rows: list[dict[str, Any]],
) -> list[str]:
    if not competitor_rows:
        return [f"No configured competitor currently maps to {battlefield}."]
    questions = [
        f"Which source excerpts directly prove pressure in {battlefield}?",
        f"Are the high-threat competitors in {battlefield} gaining share or only creating noise?",
    ]
    if battlefield in {"Cross-border ecommerce", "Social commerce", "App commerce"}:
        questions.append("Do app reviews, merchant terms, and product surfaces show repeatable demand or one-time promotion spikes?")
    if battlefield in {"Merchant advertising", "Valuation"}:
        questions.append("Can the evidence separate ad monetization from broad marketplace GMV growth?")
    return questions


def _evidence_gaps_for_pack(pack: dict[str, Any]) -> list[str]:
    gaps = []
    if pack.get("company_type") in {"private_company", "business_unit"}:
        gaps.append("Standalone audited revenue, margin, and cash-flow data are unavailable.")
    if not pack.get("source_refs"):
        gaps.append("No source refs are configured yet.")
    if pack.get("valuation_peer_quality") != "partial":
        gaps.append("Do not use this competitor as a direct valuation multiple peer without manual review.")
    return gaps


def _fields_for_downstream_consumer(consumer: str) -> list[str]:
    fields = {
        "business_model_agent": [
            "revenue_model",
            "business_model_differences",
            "scorecard.dimensions.monetization_model_overlap",
            "source_refs",
        ],
        "moat_agent": [
            "advantages",
            "weaknesses",
            "moat_replication_risk",
            "counterevidence_and_uncertainties",
        ],
        "growth_runway_agent": [
            "business_overlap.battlefields",
            "growth_constraint_risk",
            "battlefield_analysis",
            "scorecard.dimensions.geography_overlap",
        ],
        "risk_agent": [
            "threat_to_target",
            "evidence_gaps",
            "counterevidence_and_uncertainties",
            "source_ref_details.limitations",
        ],
        "valuation_agent": [
            "valuation_peer_quality",
            "valuation_peer_reason",
            "scorecard",
            "source_refs",
        ],
    }
    return fields.get(consumer, [])


def _routing_note_for_consumer(consumer: str) -> str:
    notes = {
        "business_model_agent": "Use competitors to sharpen the target's monetization and operating-model differences.",
        "moat_agent": "Use replication risk and counterevidence before concluding durability.",
        "growth_runway_agent": "Treat each battlefield as a separate growth constraint.",
        "risk_agent": "Promote evidence gaps and private-company opacity into explicit risk flags.",
        "valuation_agent": "Use peer quality controls before applying any multiple or margin analogy.",
    }
    return notes.get(consumer, "Use only as comparative evidence.")


def _scorecard_focus_text(focus: dict[str, str]) -> str:
    if not focus:
        return "none"
    return "; ".join(f"{key}: {value}" for key, value in focus.items())


def _zh_battlefield(value: Any) -> str:
    return ZH_BATTLEFIELD_LABELS.get(str(value or ""), str(value or "未知战场"))


def _zh_battlefield_question(battlefield: dict[str, Any]) -> str:
    value = battlefield.get("battlefield")
    questions = {
        "China ecommerce": "谁在压制 PDD 的中国本土市场平台模型？",
        "Cross-border ecommerce": "谁在压制 Temu 的跨境低价主张？",
        "Merchant advertising": "谁在争夺商家广告预算和平台抽佣空间？",
        "Logistics": "谁在设定配送速度、退货和履约可靠性的消费者预期？",
        "Supply chain": "谁能匹配或压制低成本供应和供应商协同？",
        "Global marketplace": "谁定义了全球市场平台规模和卖家服务的标杆？",
        "App commerce": "谁在争夺移动端发现和复购行为？",
        "Social commerce": "谁能通过内容和达人改变购物发现路径？",
    }
    return questions.get(str(value), str(battlefield.get("question") or "这个战场对目标公司意味着什么？"))


def _zh_join_pressure_mechanisms(values: Any) -> str:
    translations = {
        "merchant monetization": "商家变现",
        "user retention": "用户留存",
        "fulfillment trust": "履约信任",
        "platform governance": "平台治理",
        "price band overlap": "价格带重叠",
        "China-linked supply": "中国供应链",
        "delivery promise": "配送承诺",
        "category expansion": "品类扩张",
        "seller tooling": "卖家工具",
        "ad load": "广告负载",
        "seller tools": "卖家工具",
        "creator campaigns": "达人营销",
        "marketplace traffic allocation": "平台流量分配",
        "delivery speed": "配送速度",
        "returns workflow": "退货流程",
        "warehouse density": "仓储密度",
        "third-party fulfillment partners": "第三方履约伙伴",
        "supplier relationships": "供应商关系",
        "demand sensing": "需求感知",
        "inventory risk": "库存风险",
        "category sourcing": "品类采购",
        "buyer protection": "买家保护",
        "global catalog": "全球商品目录",
        "cross-border trust": "跨境信任",
        "app engagement": "App 参与度",
        "push/promotion cadence": "推送和促销节奏",
        "content-led conversion": "内容驱动转化",
        "review quality": "评论质量",
        "creator ecosystem": "达人生态",
        "live shopping": "直播购物",
        "affiliate incentives": "分销激励",
        "feed discovery": "信息流发现",
    }
    if not values:
        return "无"
    return "、".join(translations.get(str(item), str(item)) for item in values)


def _zh_evidence_status(value: Any) -> str:
    statuses = {
        "source_ref_only_pending_excerpt": "已有来源链接，待抓取摘录",
        "excerpt_seeded": "已有来源摘录",
    }
    return statuses.get(str(value or ""), str(value or "未知"))


def _zh_scorecard_focus_text(focus: dict[str, str]) -> str:
    if not focus:
        return "无"
    return "；".join(
        f"{_zh_scorecard_dimension(key)}: {_zh_level(value)}"
        for key, value in focus.items()
    )


def _zh_scorecard_dimension(value: str) -> str:
    labels = {
        "user_overlap": "用户重叠",
        "merchant_overlap": "商家重叠",
        "price_band_overlap": "价格带重叠",
        "category_overlap": "品类重叠",
        "geography_overlap": "地域重叠",
        "acquisition_channel_overlap": "获客渠道重叠",
        "monetization_model_overlap": "变现模型重叠",
        "replication_difficulty": "复制难度",
    }
    return labels.get(value, value)


def _zh_open_question(question: str) -> str:
    exact = {
        "Do app reviews, merchant terms, and product surfaces show repeatable demand or one-time promotion spikes?": "App 评论、商家条款和商品页面显示的是可重复需求，还是一次性促销峰值？",
        "Can the evidence separate ad monetization from broad marketplace GMV growth?": "证据能否把广告变现与平台 GMV 增长分开？",
    }
    if question in exact:
        return exact[question]
    direct_prefix = "Which source excerpts directly prove pressure in "
    if question.startswith(direct_prefix):
        battlefield = question.removeprefix(direct_prefix).rstrip("?")
        return f"哪些来源摘录能直接证明这个战场的竞争压力：{_zh_battlefield(battlefield)}"
    share_prefix = "Are the high-threat competitors in "
    share_suffix = " gaining share or only creating noise?"
    if question.startswith(share_prefix) and question.endswith(share_suffix):
        battlefield = question.removeprefix(share_prefix).removesuffix(share_suffix)
        return f"{_zh_battlefield(battlefield)}中的高威胁竞争者是否真的在获得份额，还是只制造噪音？"
    return question


def _zh_uncertainty_item(item: dict[str, Any]) -> str:
    translations = {
        "Alibaba's broader portfolio can make it look stronger or weaker than the specific China ecommerce battlefield.": "阿里业务组合更宽，可能让它看起来比单一中国电商战场更强或更弱。",
        "Avoid over-weighting cloud, local services, or unrelated segments when judging PDD's marketplace moat.": "评估 PDD 市场平台壁垒时，不能过度纳入云、本地生活或无关业务。",
        "Segment-specific extraction from 20-F and investor materials.": "需要从 20-F 和投资者材料中抽取分战场证据。",
        "JD's first-party and logistics-heavy model may not attack PDD's merchant-advertising model directly.": "JD 的自营和重物流模型不一定直接攻击 PDD 的商家广告模型。",
        "JD is a trust and fulfillment benchmark, not always a take-rate or ad-load benchmark.": "JD 更像信任和履约标杆，不一定是抽佣率或广告负载标杆。",
        "Separate marketplace pressure from fulfillment-quality pressure.": "需要区分市场平台压力和履约质量压力。",
        "Amazon's AWS, Prime, and mature fulfillment network can distort valuation and margin comparisons.": "Amazon 的 AWS、Prime 和成熟履约网络会扭曲估值和利润率比较。",
        "Amazon should be treated as an operating benchmark rather than a clean valuation peer.": "Amazon 应作为运营标杆，而不是干净的估值可比公司。",
        "Use battlefield-level operating analogies instead of company-level multiples.": "使用战场级运营类比，而不是公司级倍数。",
        "SHEIN is category-concentrated in fashion and may not replicate Temu's broad general-merchandise marketplace.": "SHEIN 偏时尚品类，未必能复制 Temu 的泛品类市场平台。",
        "The threat may be strong in fashion but weaker in categories where Temu has broader supplier coverage.": "威胁在时尚品类可能很强，但在 Temu 供应覆盖更宽的品类可能较弱。",
        "Compare category overlap, app ranking, and product-price baskets.": "需要比较品类重叠、App 排名和商品价格篮子。",
        "TikTok Shop may be powerful for discovery but weaker in marketplace operations, returns, and fulfillment consistency.": "TikTok Shop 在发现流量上可能很强，但市场运营、退货和履约一致性可能较弱。",
        "High traffic does not automatically equal durable ecommerce moat replication.": "高流量不自动等于能复制持久电商壁垒。",
        "Track merchant terms, fulfillment policies, app reviews, and seller complaint themes.": "需要跟踪商家条款、履约政策、App 评论和卖家投诉主题。",
        "AliExpress is close to Temu structurally but lacks standalone financial disclosure.": "AliExpress 结构上接近 Temu，但缺少独立财务披露。",
        "It is strong competitive evidence but weak direct valuation evidence.": "它是强竞争证据，但不是强直接估值证据。",
        "Use Alibaba parent filings plus product/pricing/traffic signals, not inferred standalone margins.": "应使用阿里母公司披露和产品/价格/流量信号，而不是推断独立利润率。",
    }
    point = translations.get(str(item.get("point")), str(item.get("point") or ""))
    why = translations.get(str(item.get("why_it_matters")), str(item.get("why_it_matters") or ""))
    resolution = translations.get(str(item.get("resolution_needed")), str(item.get("resolution_needed") or ""))
    return f"{point} 重要性：{why} 需要补证：{resolution}"


def _zh_evidence_gap(gap: str) -> str:
    translations = {
        "Standalone audited revenue, margin, and cash-flow data are unavailable.": "缺少独立经审计收入、利润率和现金流数据。",
        "No source refs are configured yet.": "尚未配置来源引用。",
        "Do not use this competitor as a direct valuation multiple peer without manual review.": "未经人工复核，不要把该竞争者作为直接估值倍数可比公司。",
    }
    return translations.get(gap, gap)


def _zh_routing_note(note: Any) -> str:
    translations = {
        "Use competitors to sharpen the target's monetization and operating-model differences.": "用竞品来压实目标公司的变现和运营模型差异。",
        "Use replication risk and counterevidence before concluding durability.": "在判断壁垒持久性前，先使用复制风险和反证。",
        "Treat each battlefield as a separate growth constraint.": "把每个竞争战场当成独立增长约束。",
        "Promote evidence gaps and private-company opacity into explicit risk flags.": "把证据缺口和未上市公司不透明性提升为显性风险。",
        "Use peer quality controls before applying any multiple or margin analogy.": "应用倍数或利润率类比前，先做可比质量控制。",
    }
    return translations.get(str(note or ""), str(note or "仅作为比较证据使用。"))


def _normalize_main_company(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or raw.get("legal_name") or raw.get("ticker") or "").strip()
    ticker = str(raw.get("ticker") or "").strip()
    market = str(raw.get("market") or "").strip()
    if not name:
        raise ValueError("Comparator request requires main_company.name or main_company.ticker.")
    return {
        "name": name,
        "ticker": ticker,
        "market": market,
    }


def _profile_for_competitor(name: str) -> dict[str, Any]:
    normalized = _slugify(name)
    for profile in KNOWN_COMPETITOR_PROFILES.values():
        names = [profile["name"], *profile.get("aliases", [])]
        if normalized in {_slugify(item) for item in names}:
            return dict(profile)
    return _unknown_profile(name)


def _unknown_profile(name: str) -> dict[str, Any]:
    return {
        "competitor_id": _slugify(name),
        "name": name,
        "aliases": [],
        "company_type": "unknown",
        "parent_company": None,
        "relationship_to_target": "unconfigured competitor requiring manual source plan",
        "battlefields": ["unclassified competitive context"],
        "business_model": "Not configured in the MVP profile library.",
        "business_model_differences": [
            "Manual evidence is required before this competitor can be used by downstream agents."
        ],
        "advantages": ["Unknown until sources are classified."],
        "weaknesses": ["Unknown until sources are classified."],
        "overlap_level": "unknown",
        "threat_level": "unknown",
        "business_model_similarity": "unknown",
        "moat_replication_risk": "unknown",
        "growth_constraint_risk": "unknown",
        "valuation_peer_quality": "unknown",
        "valuation_peer_reason": "No configured evidence profile.",
        "evidence_focus": ["manual source plan"],
    }


def _battlefields_from_request_or_profiles(
    requested: Any,
    profiles: list[dict[str, Any]],
) -> list[str]:
    inferred: list[str] = []
    for profile in profiles:
        inferred.extend(str(item) for item in profile.get("battlefields", []))
    if requested:
        values = [str(item).strip() for item in requested if str(item).strip()]
        values.extend(inferred)
        return _dedupe_preserve_order(values)
    return _dedupe_preserve_order(inferred)


def _build_competitor_map_item(
    *,
    profile: dict[str, Any],
    battlefields: list[str],
) -> dict[str, Any]:
    selected_battlefields = _select_relevant_battlefields(
        profile_battlefields=[str(item) for item in profile.get("battlefields", [])],
        requested_battlefields=battlefields,
    )
    return {
        "competitor_id": profile["competitor_id"],
        "name": profile["name"],
        "company_type": profile["company_type"],
        "parent_company": profile.get("parent_company"),
        "battlefields": selected_battlefields,
        "relationship_to_target": profile["relationship_to_target"],
        "overlap_level": profile["overlap_level"],
        "evidence_focus": profile.get("evidence_focus", []),
    }


def _select_relevant_battlefields(
    *,
    profile_battlefields: list[str],
    requested_battlefields: list[str],
) -> list[str]:
    if not requested_battlefields:
        return profile_battlefields
    selected = [
        battlefield
        for battlefield in requested_battlefields
        if _battlefield_matches_any(battlefield, profile_battlefields)
    ]
    return selected or profile_battlefields


def _battlefield_matches_any(candidate: str, profile_battlefields: list[str]) -> bool:
    candidate_tokens = _keyword_tokens(candidate)
    for battlefield in profile_battlefields:
        profile_tokens = _keyword_tokens(battlefield)
        if candidate_tokens & profile_tokens:
            return True
    return False


def _keyword_tokens(value: str) -> set[str]:
    stopwords = {"and", "the", "commerce", "ecommerce", "marketplace"}
    return {
        token
        for token in _slugify(value).replace("-", " ").split()
        if token and token not in stopwords
    }


def _build_competitor_pack(
    *,
    main_company: dict[str, Any],
    profile: dict[str, Any],
    map_item: dict[str, Any],
) -> dict[str, Any]:
    sources = _source_inventory_for_profile(profile)
    evidence_reliability = _source_reliability_summary(profile, sources)
    main_label = _main_company_label(main_company)
    competitor_name = profile["name"]
    battlefields = map_item["battlefields"]

    fixed_question_answers = [
        {
            "question_id": "Q1_business_overlap",
            "question": "What business overlap exists?",
            "answer": (
                f"{competitor_name} has {profile['overlap_level']} overlap with {main_label} across "
                f"{_join(battlefields)}."
            ),
            "evidence_basis": profile.get("evidence_focus", []),
        },
        {
            "question_id": "Q2_revenue_model",
            "question": "How does the competitor make money?",
            "answer": profile["business_model"],
            "evidence_basis": ["source_classification", "configured_profile"],
        },
        {
            "question_id": "Q3_business_model_difference",
            "question": "How is the business model different?",
            "answer": " ".join(profile.get("business_model_differences", [])),
            "evidence_basis": profile.get("evidence_focus", []),
        },
        {
            "question_id": "Q4_competitor_advantages",
            "question": "What advantages does the competitor have?",
            "answer": _sentence_list(profile.get("advantages", [])),
            "evidence_basis": profile.get("evidence_focus", []),
        },
        {
            "question_id": "Q5_competitor_weaknesses",
            "question": "What weaknesses does the competitor have?",
            "answer": _sentence_list(profile.get("weaknesses", [])),
            "evidence_basis": ["source_classification", "configured_profile"],
        },
        {
            "question_id": "Q6_moat_replication",
            "question": "Could it replicate the target company's moat?",
            "answer": (
                f"Replication risk is {profile['moat_replication_risk']}. This should be used as moat evidence "
                f"for {main_label}, not as a standalone judgment on {competitor_name}."
            ),
            "evidence_basis": profile.get("evidence_focus", []),
        },
        {
            "question_id": "Q7_growth_constraint",
            "question": "Could it limit the target company's growth?",
            "answer": (
                f"Growth constraint risk is {profile['growth_constraint_risk']} because the competitor overlaps "
                f"with {main_label} in {_join(battlefields)}."
            ),
            "evidence_basis": profile.get("evidence_focus", []),
        },
        {
            "question_id": "Q8_evidence_reliability",
            "question": "How reliable is the available evidence?",
            "answer": evidence_reliability["reason"],
            "evidence_basis": ["source_inventory"],
        },
    ]

    return {
        "competitor_id": profile["competitor_id"],
        "competitor_name": competitor_name,
        "company_type": profile["company_type"],
        "parent_company": profile.get("parent_company"),
        "business_overlap": {
            "level": profile["overlap_level"],
            "battlefields": battlefields,
            "relationship_to_target": profile["relationship_to_target"],
        },
        "revenue_model": profile["business_model"],
        "business_model_differences": profile.get("business_model_differences", []),
        "advantages": profile.get("advantages", []),
        "weaknesses": profile.get("weaknesses", []),
        "threat_to_target": profile["threat_level"],
        "business_model_similarity": profile["business_model_similarity"],
        "moat_replication_risk": profile["moat_replication_risk"],
        "growth_constraint_risk": profile["growth_constraint_risk"],
        "valuation_peer_quality": profile["valuation_peer_quality"],
        "valuation_peer_reason": profile["valuation_peer_reason"],
        "source_inventory": sources,
        "evidence_reliability": evidence_reliability,
        "fixed_question_answers": fixed_question_answers,
        "downstream_uses": _downstream_uses_for_pack(profile),
    }


def _source_inventory_for_profile(profile: dict[str, Any]) -> list[dict[str, Any]]:
    profile_type = str(profile.get("company_type") or "unknown")
    template_key = profile_type if profile_type in SOURCE_TEMPLATES else "unknown"
    inventory = []
    for source in SOURCE_TEMPLATES[template_key]:
        record = dict(source)
        record["competitor_id"] = profile["competitor_id"]
        record["competitor_name"] = profile["name"]
        inventory.append(record)
    if template_key in {"private_company", "business_unit"}:
        inventory.append(
            {
                "competitor_id": profile["competitor_id"],
                "competitor_name": profile["name"],
                "source_type": "standalone_financial_statements",
                "source_name": "Detailed standalone financial statements",
                "reliability": "unavailable",
                "available": False,
                "use_case": "Would be needed for direct margin, cash flow, and valuation comparison.",
                "limitations": [
                    "Unavailable in MVP source set.",
                    "Do not infer detailed margins or cash flow from third-party estimates.",
                ],
            }
        )
    return inventory


def _source_reliability_summary(
    profile: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    reliability_counts: dict[str, int] = {}
    for source in sources:
        reliability = str(source.get("reliability") or "unknown")
        reliability_counts[reliability] = reliability_counts.get(reliability, 0) + 1

    company_type = profile.get("company_type")
    if company_type == "public_company":
        overall = "high"
        reason = "Public-company filings provide high-reliability source coverage, with management commentary labeled separately as medium reliability."
    elif company_type in {"private_company", "business_unit"}:
        overall = "medium"
        reason = "Official product, merchant, and parent-company sources can support business-model comparison, but standalone financial evidence is unavailable."
    else:
        overall = "unknown"
        reason = "The competitor has no configured source plan in this MVP."

    unavailable = [
        source["source_name"]
        for source in sources
        if source.get("available") is False
    ]
    return {
        "overall": overall,
        "reliability_counts": reliability_counts,
        "unavailable_evidence": unavailable,
        "reason": reason,
    }


def _downstream_uses_for_pack(profile: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "consumer": "business_model_agent",
            "use": "Compare monetization model, customer promise, and operating model against the target.",
        },
        {
            "consumer": "moat_agent",
            "use": "Assess whether the competitor can replicate target advantages or attack weak points.",
        },
        {
            "consumer": "growth_runway_agent",
            "use": "Use overlap and threat level to frame expansion constraints by battlefield.",
        },
        {
            "consumer": "risk_agent",
            "use": "Treat high-overlap competitors as evidence for competitive pressure and execution risk.",
        },
        {
            "consumer": "valuation_agent",
            "use": f"Use peer quality as {profile.get('valuation_peer_quality')} and avoid direct multiples when peer quality is not clean.",
        },
    ]


def _build_comparison_matrix(competitor_packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for pack in competitor_packs:
        rows.append(
            {
                "competitor_id": pack["competitor_id"],
                "competitor": pack["competitor_name"],
                "overlap": pack["business_overlap"]["level"],
                "threat": pack["threat_to_target"],
                "business_model_similarity": pack["business_model_similarity"],
                "moat_replication_risk": pack["moat_replication_risk"],
                "growth_constraint_risk": pack["growth_constraint_risk"],
                "evidence_reliability": pack["evidence_reliability"]["overall"],
                "valuation_peer_quality": pack["valuation_peer_quality"],
                "primary_battlefields": pack["business_overlap"]["battlefields"],
                "key_reason": pack["valuation_peer_reason"],
            }
        )
    return rows


def _generate_implications(
    *,
    main_company: dict[str, Any],
    competitor_packs: list[dict[str, Any]],
    comparison_matrix: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    main_label = _main_company_label(main_company)
    main_possessive = _possessive(main_label)
    by_id = {pack["competitor_id"]: pack for pack in competitor_packs}
    implications = {
        "business_model": [],
        "moat": [],
        "growth": [],
        "risk": [],
        "valuation": [],
    }

    if "alibaba" in by_id:
        implications["business_model"].append(
            _implication(
                "business_model",
                (
                    f"{main_possessive} merchant monetization should be compared against Alibaba before Amazon: "
                    "Alibaba is the more relevant evidence source for China marketplace advertising load, merchant tools, and platform take-rate pressure."
                ),
                ["alibaba"],
                "medium_high",
                ["business_model_agent", "valuation_agent"],
            )
        )
    if "jd" in by_id:
        implications["business_model"].append(
            _implication(
                "business_model",
                (
                    f"JD implies that {main_possessive} lighter marketplace model should not be judged with a first-party retail cost structure; "
                    "JD is useful for trust and logistics comparison, not for direct margin analogy."
                ),
                ["jd"],
                "medium",
                ["business_model_agent", "valuation_agent"],
            )
        )
    if "amazon" in by_id:
        implications["business_model"].append(
            _implication(
                "business_model",
                (
                    f"Amazon is a benchmark for fulfillment, seller services, and advertising scale, but it should not redefine {main_possessive} core model because AWS, Prime, and FBA create different economics."
                ),
                ["amazon"],
                "medium",
                ["business_model_agent", "valuation_agent"],
            )
        )

    cross_border_refs = [ref for ref in ["shein", "aliexpress"] if ref in by_id]
    if cross_border_refs:
        implications["moat"].append(
            _implication(
                "moat",
                (
                    f"{main_possessive} low-price cross-border proposition is only partially protected: SHEIN and AliExpress show that China-linked supply, app commerce, and bargain merchandising are replicable in selected categories."
                ),
                cross_border_refs,
                "medium",
                ["moat_agent", "risk_agent"],
            )
        )

    if "tiktok-shop" in by_id:
        implications["moat"].append(
            _implication(
                "moat",
                (
                    f"TikTok Shop is the clearest replication threat to {main_possessive} discovery and merchant-attention moat because it can start from traffic and creators rather than from conventional ecommerce search."
                ),
                ["tiktok-shop"],
                "medium_high",
                ["moat_agent", "growth_runway_agent"],
            )
        )
        implications["growth"].append(
            _implication(
                "growth",
                (
                    f"TikTok Shop may constrain {main_possessive} future growth by redirecting merchant budgets and consumer discovery time into social commerce, especially in categories where creator-led conversion works."
                ),
                ["tiktok-shop"],
                "medium_high",
                ["growth_runway_agent", "risk_agent"],
            )
        )
        implications["risk"].append(
            _implication(
                "risk",
                (
                    f"Competitive pressure for {main_label} is rising in social commerce and paid traffic acquisition; this risk should be separated from normal marketplace price competition."
                ),
                ["tiktok-shop"],
                "medium_high",
                ["risk_agent", "moat_agent"],
            )
        )

    high_overlap = [
        row["competitor_id"]
        for row in comparison_matrix
        if row.get("overlap") in {"high", "medium_high"}
    ]
    if high_overlap:
        implications["growth"].append(
            _implication(
                "growth",
                (
                    f"{main_possessive} runway should be segmented by battlefield rather than treated as one ecommerce market; high-overlap competitors pressure different parts of China ecommerce, cross-border ecommerce, social commerce, and logistics."
                ),
                high_overlap,
                "medium",
                ["growth_runway_agent", "risk_agent"],
            )
        )

    private_or_unit_refs = [
        pack["competitor_id"]
        for pack in competitor_packs
        if pack.get("company_type") in {"private_company", "business_unit"}
    ]
    if private_or_unit_refs:
        implications["risk"].append(
            _implication(
                "risk",
                (
                    f"Evidence gaps are themselves a risk input for {main_label}: private competitors and business units can affect pricing, acquisition costs, and merchant behavior before audited financial evidence is available."
                ),
                private_or_unit_refs,
                "medium",
                ["risk_agent"],
            )
        )

    partial_peers = [
        row["competitor_id"]
        for row in comparison_matrix
        if row.get("valuation_peer_quality") == "partial"
    ]
    not_clean_peers = [
        row["competitor_id"]
        for row in comparison_matrix
        if row.get("valuation_peer_quality") in {"not_clean", "unknown"}
    ]
    if partial_peers or not_clean_peers:
        implications["valuation"].append(
            _implication(
                "valuation",
                (
                    f"{main_possessive} valuation peer set should be filtered by battlefield: Alibaba and JD can be partial operating peers, while Amazon, SHEIN, TikTok Shop, and AliExpress are better used as business-model or threat evidence than direct multiple peers."
                ),
                [*partial_peers, *not_clean_peers],
                "medium_high",
                ["valuation_agent"],
            )
        )

    return implications


def _implication(
    category: str,
    statement: str,
    evidence_refs: list[str],
    confidence: str,
    downstream_consumers: list[str],
) -> dict[str, Any]:
    return {
        "implication_id": f"{category}_{_slugify(statement)[:48]}",
        "category": category,
        "statement": statement,
        "evidence_refs": evidence_refs,
        "confidence": confidence,
        "downstream_consumers": downstream_consumers,
    }


def _main_company_label(main_company: dict[str, Any]) -> str:
    return str(main_company.get("name") or main_company.get("ticker") or "the target company")


def _zh_fixed_question_answers(
    pack_item: dict[str, Any],
    main_label: str,
    details: dict[str, Any],
) -> list[str]:
    competitor_name = str(pack_item.get("competitor_name") or "该竞争对手")
    overlap = pack_item.get("business_overlap") or {}
    battlefields = _zh_join_battlefields(overlap.get("battlefields", []))
    differences = details.get("differences") or pack_item.get("business_model_differences") or []
    advantages = details.get("advantages") or pack_item.get("advantages") or []
    weaknesses = details.get("weaknesses") or pack_item.get("weaknesses") or []
    reliability = pack_item.get("evidence_reliability") or {}
    unavailable = reliability.get("unavailable_evidence") or []
    unavailable_text = f" 不可得证据：{_zh_join_unavailable_evidence(unavailable)}。" if unavailable else ""
    return [
        (
            f"- Q1 业务重叠: {competitor_name} 与 {main_label} 的重叠度为"
            f"{_zh_level(overlap.get('level'))}，主要发生在 {battlefields}。"
        ),
        f"- Q2 如何赚钱: {details.get('revenue_model') or pack_item.get('revenue_model')}",
        f"- Q3 商业模式差异: {_zh_sentence_list(differences)}",
        f"- Q4 竞争优势: {_zh_sentence_list(advantages)}",
        f"- Q5 竞争弱点: {_zh_sentence_list(weaknesses)}",
        (
            f"- Q6 能否复制目标公司的壁垒: 复制风险为"
            f"{_zh_level(pack_item.get('moat_replication_risk'))}。这应作为 {main_label} 的壁垒压力证据，"
            f"不是对 {competitor_name} 的独立投资判断。"
        ),
        (
            f"- Q7 能否限制目标公司的增长: 增长约束风险为"
            f"{_zh_level(pack_item.get('growth_constraint_risk'))}，因为双方在 {battlefields} 有竞争交集。"
        ),
        f"- Q8 证据可靠性: {_zh_reliability_reason(pack_item)}{unavailable_text}",
    ]


def _zh_implication_statement(item: dict[str, Any], main_label: str) -> str:
    category = item.get("category")
    refs = set(item.get("evidence_refs") or [])
    if category == "business_model" and refs == {"alibaba"}:
        return (
            f"{main_label} 的商家变现应优先与 Alibaba 比较，而不是先与 Amazon 比较；"
            "Alibaba 对中国市场平台广告负载、商家工具和平台抽佣压力更有参考价值。"
        )
    if category == "business_model" and refs == {"jd"}:
        return (
            f"JD 说明 {main_label} 的轻平台模型不应套用自营零售成本结构；"
            "JD 更适合作为信任和物流能力参照，而不是直接利润率参照。"
        )
    if category == "business_model" and refs == {"amazon"}:
        return (
            f"Amazon 可作为履约、卖家服务和广告规模的标杆，但 AWS、Prime 和 FBA 让其经济性不同，"
            f"不应反向定义 {main_label} 的核心商业模式。"
        )
    if category == "moat" and {"shein", "aliexpress"} & refs:
        return (
            f"{main_label} 的低价跨境主张并非完全不可复制；SHEIN 和 AliExpress 说明中国供应、"
            "移动端商品组织和低价心智在部分品类可被复制。"
        )
    if category == "moat" and "tiktok-shop" in refs:
        return (
            f"TikTok Shop 是 {main_label} 发现式购物和商家注意力壁垒的最清晰复制威胁，"
            "因为它可以从内容流量和达人生态切入，而不是依赖传统电商搜索。"
        )
    if category == "growth" and refs == {"tiktok-shop"}:
        return (
            f"TikTok Shop 可能通过重新分配商家预算和消费者发现时间来限制 {main_label} 的未来增长，"
            "尤其是在达人转化有效的品类。"
        )
    if category == "growth":
        return (
            f"{main_label} 的增长空间应按竞争战场拆分，而不是抽象成一个电商总市场；"
            "不同高重叠竞争者分别压制中国电商、跨境电商、社交电商和物流等环节。"
        )
    if category == "risk" and refs == {"tiktok-shop"}:
        return (
            f"{main_label} 面临的竞争压力正在向社交电商和付费流量获取上升；"
            "这类风险应与普通市场平台价格竞争分开处理。"
        )
    if category == "risk":
        return (
            f"证据缺口本身也是 {main_label} 的风险输入：未上市公司和业务单元可能先影响价格、"
            "获客成本和商家行为，之后才出现可审计的财务证据。"
        )
    if category == "valuation":
        return (
            f"{main_label} 的估值可比公司应按战场筛选：Alibaba 和 JD 只能作为部分经营参照，"
            "Amazon、SHEIN、TikTok Shop 和 AliExpress 更适合用作商业模式或威胁证据，而不是直接倍数可比。"
        )
    return str(item.get("statement") or "")


def _zh_reliability_reason(pack_item: dict[str, Any]) -> str:
    company_type = pack_item.get("company_type")
    if company_type == "public_company":
        return "上市公司申报文件能提供高可靠性的基础证据，但管理层表述仍需单独标记为中等可靠性。"
    if company_type in {"private_company", "business_unit"}:
        return "官方产品页、商家条款、母公司材料和替代数据可以支持商业模式比较，但独立财务证据不可得。"
    return "该竞争对手尚未配置完整来源计划，暂不适合被下游 agent 强引用。"


def _zh_source_name(source: dict[str, Any]) -> str:
    source_type = source.get("source_type")
    names = {
        "official_filing": "10-K、20-F、年报或交易所申报文件",
        "earnings_call": "业绩会文字稿和管理层发言",
        "investor_presentation": "投资者演示材料和活动材料",
        "official_website": "官方网站、产品页和商家页面",
        "merchant_terms": "卖家中心、商家条款、定价页和政策页",
        "app_store_page": "应用商店页面和可见评论",
        "alternative_data": "搜索、流量、商品价格、促销和社交信号",
        "parent_company_filing": "母公司申报文件和年报",
        "standalone_financial_statements": "详细独立财务报表",
        "manual_source_plan_required": "人工来源计划",
    }
    return names.get(str(source_type), str(source.get("source_name") or "未命名来源"))


def _zh_join_battlefields(values: Any) -> str:
    if not values:
        return "无"
    if isinstance(values, str):
        return ZH_BATTLEFIELD_LABELS.get(values, values)
    return "、".join(ZH_BATTLEFIELD_LABELS.get(str(item), str(item)) for item in values)


def _zh_join_unavailable_evidence(values: Any) -> str:
    if not values:
        return "无"
    translations = {
        "Detailed standalone financial statements": "详细独立财务报表",
    }
    if isinstance(values, str):
        return translations.get(values, values)
    return "、".join(translations.get(str(item), str(item)) for item in values)


def _zh_enum(value: Any, mapping: dict[str, str]) -> str:
    return mapping.get(str(value or ""), str(value or "未知"))


def _zh_level(value: Any) -> str:
    return _zh_enum(value, ZH_LEVEL_LABELS)


def _zh_sentence_list(values: Any) -> str:
    if not values:
        return "暂无。"
    if isinstance(values, str):
        return values
    cleaned = [str(item).strip().rstrip("。").rstrip(".") for item in values if str(item).strip()]
    if not cleaned:
        return "暂无。"
    return "；".join(cleaned) + "。"


def _possessive(label: str) -> str:
    return f"{label}'" if label.endswith("s") else f"{label}'s"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value)).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "unknown"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _join(values: Any) -> str:
    if not values:
        return "none"
    if isinstance(values, str):
        return values
    return ", ".join(str(item) for item in values)


def _sentence_list(values: Any) -> str:
    if not values:
        return "none"
    if isinstance(values, str):
        return values
    cleaned = [str(item).strip().rstrip(".") for item in values if str(item).strip()]
    if not cleaned:
        return "none"
    return "; ".join(cleaned) + "."


def _md(value: Any) -> str:
    text = str(value or "")
    return text.replace("|", "\\|").replace("\n", " ")
