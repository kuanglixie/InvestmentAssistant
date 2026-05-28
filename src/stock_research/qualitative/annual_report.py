from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from stock_research.metrics.v1 import annual_fact_rows


TAG_PATTERN = re.compile(r"<[^>]+>")
SCRIPT_STYLE_PATTERN = re.compile(
    r"<(script|style)\b.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)
SPACE_PATTERN = re.compile(r"\s+")


BUSINESS_MODEL_TOPICS = {
    "revenue_model": [
        "online marketing services",
        "transaction services",
        "revenues",
        "merchant",
        "consumer",
    ],
    "platform_and_scale": [
        "platform",
        "technology",
        "supply chain",
        "ecosystem",
        "user",
        "merchant",
    ],
    "competitive_risk": [
        "competition",
        "competitive",
        "competitors",
    ],
    "regulatory_and_structure_risk": [
        "regulation",
        "regulatory",
        "variable interest entity",
        "VIE",
        "restricted net assets",
        "dividends",
    ],
}

LEADERSHIP_TOPICS = {
    "leadership_disclosure": [
        "directors",
        "senior management",
        "board",
        "executive officer",
    ],
    "incentives_and_ownership": [
        "share-based compensation",
        "beneficial ownership",
        "ordinary shares",
        "voting power",
    ],
    "capital_allocation_markers": [
        "repurchase",
        "dividend",
        "capital allocation",
        "investment commitments",
    ],
}

BUSINESS_MODEL_SECTION_TERMS = {
    "business_overview": ["business overview", "information on the company", "our business", "business review"],
    "management_discussion": [
        "management discussion and analysis",
        "management discussion",
        "operating and financial review",
    ],
    "segment_notes": ["segment information", "operating segments", "reportable segments"],
    "revenue_notes": ["revenue recognition", "revenues", "disaggregation of revenues"],
    "risk_factors": ["risk factors", "risks related to our business", "principal risks"],
}

BUSINESS_MODEL_PROFILES = {
    "pdd": {
        "business_terms": ["Pinduoduo", "Temu", "platforms", "buyers", "merchants", "value-for-money"],
        "revenue_terms": ["online marketing services", "transaction services", "third-party merchants"],
        "moat_terms": ["team purchase", "social networks", "merchant", "buyer", "ecosystem", "supply chain"],
        "risk_terms": ["competition", "counterfeit", "merchant", "logistics", "regulatory", "trade"],
        "model_claims": [
            {
                "claim": "PDD is a merchant-funded commerce platform built around Pinduoduo and Temu.",
                "terms": ["Pinduoduo", "Temu", "third-party merchants"],
            },
            {
                "claim": "Its consumer proposition is value-for-money merchandise, broad selection, and interactive shopping.",
                "terms": ["value-for-money", "interactive", "competitive prices"],
            },
            {
                "claim": "Its merchant proposition is access to buyer traffic, marketing tools, transaction services, and operating support.",
                "terms": ["merchants", "online marketing services", "transaction services"],
            },
        ],
        "moat_hypotheses": [
            {
                "hypothesis": "Two-sided marketplace network effect between buyers and merchants.",
                "terms": ["buyers", "merchants", "platform", "ecosystem"],
            },
            {
                "hypothesis": "Cost/value advantage from scale, supply-chain support, and merchant operating efficiency.",
                "terms": ["supply chain", "competitive prices", "efficiency", "manufacturing"],
            },
            {
                "hypothesis": "Engagement advantage from social and interactive shopping behavior.",
                "terms": ["team purchase", "social networks", "interactive"],
            },
        ],
        "missing_evidence": [
            "Customer happiness and repeat-purchase quality outside official reports.",
            "Merchant profitability after ads, discounts, logistics, and platform rules.",
            "Pinduoduo versus Temu economics, because official reporting does not fully separate them.",
            "Competitor evidence from Alibaba, JD, Douyin, Shein, and Amazon-like models.",
        ],
    },
    "tencent": {
        "business_terms": ["Value-added Services", "Marketing Services", "FinTech and Business Services", "Weixin", "games"],
        "revenue_terms": ["VAS", "Marketing Services", "FinTech and Business Services", "segment revenues"],
        "moat_terms": ["ecosystem", "users", "platform", "technology", "content", "Mini Programs"],
        "risk_terms": ["competition", "regulation", "regulatory", "content", "games", "FinTech"],
        "model_claims": [
            {
                "claim": "Tencent is a multi-segment internet ecosystem company rather than a single-product business.",
                "terms": ["Value-added Services", "Marketing Services", "FinTech and Business Services"],
            },
            {
                "claim": "Its revenue engine combines games/social networks, advertising, and fintech/business services.",
                "terms": ["games", "Marketing Services", "FinTech and Business Services"],
            },
            {
                "claim": "Its platform value depends on user engagement, content, payments, and business-service infrastructure.",
                "terms": ["users", "content", "platform", "FinTech"],
            },
        ],
        "moat_hypotheses": [
            {
                "hypothesis": "Ecosystem/network advantage from user engagement across social, content, payments, and services.",
                "terms": ["ecosystem", "users", "Weixin", "Mini Programs"],
            },
            {
                "hypothesis": "Content and games scale advantage from IP, distribution, and operating expertise.",
                "terms": ["games", "content", "Value-added Services"],
            },
            {
                "hypothesis": "Advertising and fintech advantages from scale, data, merchant reach, and payment/service integration.",
                "terms": ["Marketing Services", "FinTech", "Business Services", "technology"],
            },
        ],
        "missing_evidence": [
            "Customer/user satisfaction outside official reports.",
            "Competitive comparison against Alibaba, ByteDance, NetEase, Meituan, and other platform businesses.",
            "Durability of game/content pipelines and regulatory pressure.",
            "Segment-level ROIC and reinvestment needs, which are not fully disclosed.",
        ],
    },
    "generic": {
        "business_terms": ["business", "customers", "products", "services", "platform"],
        "revenue_terms": ["revenues", "revenue", "customers"],
        "moat_terms": ["competitive", "scale", "brand", "technology", "platform"],
        "risk_terms": ["competition", "regulation", "customers", "suppliers"],
        "model_claims": [
            {
                "claim": "Official reports describe the company's products, customers, and revenue model.",
                "terms": ["business", "customers", "revenues"],
            }
        ],
        "moat_hypotheses": [
            {
                "hypothesis": "Potential competitive advantage from scale, brand, technology, or customer relationships.",
                "terms": ["competitive", "scale", "brand", "technology"],
            }
        ],
        "missing_evidence": [
            "Customer evidence outside official reports.",
            "Competitor evidence outside official reports.",
            "Unit economics and segment-level durability evidence.",
        ],
    },
}

PDD_DEEP_EVIDENCE_PROBES = [
    {
        "card_id": "pdd_company_scope",
        "theme": "Company scope",
        "finding": (
            "PDD is no longer just a domestic Pinduoduo story in the latest official report; "
            "the company frames itself as a multinational commerce group built around Pinduoduo and Temu."
        ),
        "terms": ["multinational commerce group", "Pinduoduo", "Temu", "portfolio of businesses"],
        "why_it_matters": "This sets the business-model boundary: domestic China commerce plus global cross-border commerce.",
        "limitation": "The filing does not fully separate Pinduoduo and Temu economics.",
    },
    {
        "card_id": "pdd_pinduoduo_flywheel",
        "theme": "Pinduoduo marketplace flywheel",
        "finding": (
            "The strongest official moat narrative is a buyer-merchant flywheel: value-for-money selection and interactive shopping "
            "increase buyer activity, which attracts merchants, while larger sales volume encourages merchants to offer lower prices "
            "and more customized products."
        ),
        "terms": ["team purchase", "social networks", "buyer base", "merchants", "competitive prices", "virtuous cycle"],
        "why_it_matters": "This is the official-report basis for a two-sided network-effect hypothesis.",
        "limitation": "It is management's narrative; external customer and merchant evidence is still needed.",
    },
    {
        "card_id": "pdd_temu_global_platform",
        "theme": "Temu global expansion",
        "finding": (
            "The report frames Temu as an early-stage global online platform that started in 2022 and expanded across North America, "
            "Oceania, Europe, and other regions, with logistics and fulfillment partners supporting merchant reach."
        ),
        "terms": ["September 2022", "North America", "Oceania", "Europe", "logistics vendors", "fulfillment partners"],
        "why_it_matters": "Temu is now central to whether PDD's business model is stable and scalable outside China.",
        "limitation": "The official report gives strategy and scope but not standalone Temu unit economics.",
    },
    {
        "card_id": "pdd_shared_operating_model",
        "theme": "Pinduoduo and Temu operating model",
        "finding": (
            "The latest report says Pinduoduo and Temu have differentiated geographic coverage but the same value propositions "
            "and operational model, and currently both primarily serve merchants in China."
        ),
        "terms": ["same value propositions", "operational model", "geographical coverage", "merchants in China"],
        "why_it_matters": "This links Pinduoduo's domestic model and Temu's international model, but also creates China-merchant concentration risk.",
        "limitation": "The statement does not prove that customer behavior, competition, or regulation will transfer across markets.",
    },
    {
        "card_id": "pdd_merchant_efficiency",
        "theme": "Merchant efficiency and supply-chain claim",
        "finding": (
            "The official report claims the platforms help merchants streamline manufacturing and operations, reduce waste, "
            "and offer more competitive prices."
        ),
        "terms": ["streamline their manufacturing and operations", "competitive prices", "reduced waste", "merchants"],
        "why_it_matters": "This is the official basis for a low-price structural-efficiency moat hypothesis.",
        "limitation": "The report does not prove merchant profitability after ads, returns, logistics, discounts, and platform rules.",
    },
    {
        "card_id": "pdd_agriculture_supply_chain",
        "theme": "Agriculture and demand aggregation",
        "finding": (
            "PDD still presents agriculture as a strategic opportunity: demand aggregation can create order scale for farmer merchants, "
            "reduce dependence on wholesalers, and support farm-to-table efficiency."
        ),
        "terms": ["agriculture", "aggregate demand", "economies of scale", "farmer merchants", "wholesale distributors", "farm to table"],
        "why_it_matters": "This is a concrete example of how PDD claims its platform can change supply-chain economics.",
        "limitation": "The filing does not quantify how much current revenue or profit comes from this agriculture advantage.",
    },
    {
        "card_id": "pdd_revenue_engine",
        "theme": "Revenue engine",
        "finding": (
            "PDD monetizes third-party merchants primarily through transaction services and online marketing services/others."
        ),
        "terms": ["transaction services", "online marketing services", "third-party merchants", "revenues"],
        "why_it_matters": "This means merchant ROI and merchant dependence on the platform are central to moat durability.",
        "limitation": "Official revenue line items show monetization, but not merchant net profitability.",
    },
    {
        "card_id": "pdd_vie_and_adr_structure",
        "theme": "Ownership and structure risk",
        "finding": (
            "PDD ADR holders own equity in the Cayman holding company, while certain China operations are conducted through a VIE structure."
        ),
        "terms": ["Cayman Islands holding company", "VIE", "contractual arrangements", "ADSs", "do not have direct"],
        "why_it_matters": "For value investing, ownership structure and cash accessibility matter alongside operating quality.",
        "limitation": "The VIE risk is structural; strong operating results do not remove it.",
    },
    {
        "card_id": "pdd_competition_and_quality_risk",
        "theme": "Anti-moat risk",
        "finding": (
            "The official filing repeatedly flags competition, quality, logistics, regulatory, and trade-related risks that could weaken "
            "the low-price marketplace story."
        ),
        "terms": ["competition", "counterfeit", "logistics", "regulatory", "trade", "quality"],
        "why_it_matters": "A moat thesis should survive direct attempts to disprove it, especially around trust, quality, and regulation.",
        "limitation": "Risk-factor language is broad and must be connected to real-world evidence before weighting it heavily.",
    },
]

PDD_MANAGEMENT_FRAMING_PROBES = [
    {
        "theme_id": "pdd_scope_and_mission",
        "theme": "Company scope and mission",
        "management_claim": (
            "PDD frames itself as a multinational commerce group whose mission is to bring more businesses "
            "and people into the digital economy."
        ),
        "terms": [
            "multinational commerce group",
            "We aim to bring more businesses and people into the digital economy",
            "digital economy",
            "portfolio of businesses",
        ],
        "why_it_matters": (
            "This sets the official business boundary as broader than one China shopping app: the report asks us "
            "to analyze Pinduoduo, Temu, and the shared commerce infrastructure."
        ),
        "accuracy_limit": (
            "This is management's scope statement. It does not by itself prove overseas durability, unit economics, "
            "or cash accessibility."
        ),
    },
    {
        "theme_id": "pdd_consumer_value_proposition",
        "theme": "Consumer value proposition",
        "management_claim": (
            "The core consumer promise is value-for-money merchandise, broad selection, fun/interactive shopping, "
            "and competitive pricing."
        ),
        "terms": [
            "value-for-money merchandise",
            "fun and interactive shopping experiences",
            "competitive pricing",
            "competitive prices",
            "team purchase",
        ],
        "why_it_matters": (
            "A value-for-money promise is central to the moat question: if customers come mainly for price, the system "
            "must have a real cost/scale advantage or retention may be fragile."
        ),
        "accuracy_limit": (
            "Official reports can state the proposition, but customer happiness, repeat behavior, and price perception "
            "need external evidence."
        ),
    },
    {
        "theme_id": "pdd_buyer_merchant_flywheel",
        "theme": "Buyer-merchant flywheel",
        "management_claim": (
            "PDD describes a two-sided flywheel: more buyers attract merchants; larger sales volume encourages merchants "
            "to offer better prices and customized products; that reinforces buyer activity."
        ),
        "terms": [
            "buyer base helps attract merchants",
            "scale of the platform's sales volume",
            "scale of the platform’s sales volume",
            "virtuous cycle",
            "customized products and services",
        ],
        "why_it_matters": (
            "This is the official-report basis for a marketplace network-effect hypothesis."
        ),
        "accuracy_limit": (
            "The report gives the flywheel narrative, not direct proof of merchant profit, retention, or competitor inability "
            "to copy the model."
        ),
    },
    {
        "theme_id": "pdd_shared_operating_model",
        "theme": "Pinduoduo and Temu shared operating model",
        "management_claim": (
            "The latest report says Pinduoduo and Temu have different geographic coverage but the same value propositions "
            "and operational model, and both currently primarily serve merchants in China."
        ),
        "terms": [
            "same value propositions and operational model",
            "differentiated geographical coverage",
            "primarily serve merchants in China",
            "Pinduoduo and Temu",
        ],
        "why_it_matters": (
            "This links domestic Pinduoduo and global Temu under one operating model, but also points to China-merchant "
            "concentration and cross-border execution risk."
        ),
        "accuracy_limit": (
            "The same operating-model language does not prove that consumer behavior, logistics, regulation, or competition "
            "will transfer cleanly across markets."
        ),
    },
    {
        "theme_id": "pdd_merchant_efficiency",
        "theme": "Merchant efficiency and supply chain",
        "management_claim": (
            "PDD claims it helps merchants streamline manufacturing and operations, reduce waste, and offer more competitive prices."
        ),
        "terms": [
            "streamline their manufacturing and operations",
            "reduced waste",
            "competitive prices",
            "supply chain",
            "merchants",
        ],
        "why_it_matters": (
            "This is the official basis for a structural low-price advantage hypothesis: the platform is claiming to improve "
            "merchant cost and operating efficiency, not merely subsidize demand."
        ),
        "accuracy_limit": (
            "The annual report does not quantify merchant profitability after advertising, returns, logistics, discounts, "
            "and platform rules."
        ),
    },
    {
        "theme_id": "pdd_operating_leverage",
        "theme": "Operating leverage claim",
        "management_claim": (
            "Management states that the business model has significant operating leverage and structural cost savings as scale expands."
        ),
        "terms": [
            "business model has significant operating leverage",
            "structural cost savings",
            "economies of scale",
            "wider selection of merchandise",
        ],
        "why_it_matters": (
            "This connects the business-model story to financial evidence: revenue growth should eventually show up in margins, "
            "cash conversion, and returns on capital."
        ),
        "accuracy_limit": (
            "This is a management claim. It should be tested against extracted cost lines, margins, cash conversion, and competitor data."
        ),
    },
    {
        "theme_id": "pdd_agriculture_inclusion",
        "theme": "Agriculture and digital inclusion",
        "management_claim": (
            "PDD continues to present agriculture as a strategic opportunity where demand aggregation can improve farm-to-table "
            "efficiency and help smaller merchants."
        ),
        "terms": [
            "business opportunities in agriculture",
            "digital inclusion of smallholder farmers",
            "aggregate demand",
            "farm to table",
            "farmer merchants",
        ],
        "why_it_matters": (
            "This is a concrete example of how PDD says the platform changes supply-chain economics rather than just reselling goods."
        ),
        "accuracy_limit": (
            "The report does not quantify how much current revenue, profit, or moat strength comes from agriculture."
        ),
    },
]


OFFICIAL_REPORT_DOSSIER_FIELDS = [
    {
        "field_id": "legal_and_reporting_scope",
        "label": "Legal and reporting scope",
        "source_section": "company definitions / corporate structure / risk factors",
        "status": "directly_stated",
        "terms": [
            "Cayman Islands holding company",
            "ADSs",
            "ordinary shares",
            "VIE",
            "variable interest entity",
            "contractual arrangements",
        ],
        "summary": "The filing directly discusses the company's legal/listing structure and reporting-scope markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD's official report frames the listed entity as a Cayman holding company with ADS/ordinary-share "
                "disclosures and China VIE/contractual-arrangement context."
            ),
            "tencent": (
                "Tencent's official report provides the listed-company and share-capital context used to anchor the research scope."
            ),
        },
    },
    {
        "field_id": "business_description",
        "label": "Business description",
        "source_section": "business overview",
        "status": "directly_stated",
        "terms": [
            "multinational commerce group",
            "portfolio of businesses",
            "our business",
            "our platforms",
            "Pinduoduo",
            "Temu",
        ],
        "company_terms": {
            "tencent": [
                "Value-added Services",
                "Marketing Services",
                "FinTech and Business Services",
            ],
        },
        "summary": "The filing directly describes the business using these markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD describes itself as a commerce group built around the Pinduoduo and Temu platforms, with a digital-economy and value-for-money shopping framing."
            ),
            "tencent": (
                "Tencent describes a multi-service internet ecosystem with value-added services, marketing services, and fintech/business services."
            ),
        },
    },
    {
        "field_id": "segment_structure",
        "label": "Segment structure",
        "source_section": "segment notes",
        "status": "directly_stated",
        "terms": [
            "segment information",
            "operating segments",
            "reportable segments",
            "segment revenues",
        ],
        "company_terms": {
            "tencent": [
                "Value-added Services",
                "Marketing Services",
                "FinTech and Business Services",
            ],
        },
        "summary": "The filing provides segment or service-line structure markers: {matched_terms}.",
    },
    {
        "field_id": "revenue_model",
        "label": "Revenue model",
        "source_section": "business overview / revenue recognition",
        "status": "directly_stated",
        "terms": [
            "transaction services",
            "online marketing services",
            "revenues",
            "revenue recognition",
            "third-party merchants",
        ],
        "company_terms": {
            "tencent": [
                "VAS",
                "Marketing Services",
                "FinTech and Business Services",
            ],
        },
        "summary": "The filing directly states revenue-model markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD states that revenue primarily comes from transaction services and online marketing services/others provided to third-party merchants."
            ),
            "tencent": (
                "Tencent reports revenue through service lines including VAS, Marketing Services, and FinTech and Business Services."
            ),
        },
    },
    {
        "field_id": "customer_groups",
        "label": "Customer / user groups",
        "source_section": "business overview / operating definitions",
        "status": "directly_stated",
        "terms": [
            "buyers",
            "consumers",
            "customers",
            "users",
            "active merchants",
            "merchants",
            "farmer merchants",
        ],
        "company_terms": {
            "tencent": [
                "Weixin",
                "Mini Programs",
            ],
        },
        "summary": "The filing identifies customer, user, or participant groups through these markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD's official report identifies buyers/consumers and merchants as the key platform participants."
            ),
            "tencent": (
                "Tencent's official report points to users, advertisers, merchants, businesses, and ecosystem participants across its services."
            ),
        },
    },
    {
        "field_id": "supplier_or_partner_dependencies",
        "label": "Supplier / partner dependencies",
        "source_section": "business overview / risk factors",
        "status": "directly_stated",
        "terms": [
            "third-party merchants",
            "merchants",
            "logistics vendors",
            "fulfillment partners",
            "suppliers",
            "distribution partners",
            "content providers",
        ],
        "summary": "The filing names operating partners or dependencies through these markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD depends on merchant participation and, for Temu, logistics vendors and fulfillment partners to support market reach and fulfillment."
            ),
        },
    },
    {
        "field_id": "cost_and_capital_drivers",
        "label": "Cost and capital drivers",
        "source_section": "MD&A / notes to financial statements",
        "status": "directly_stated",
        "terms": [
            "cost of revenues",
            "sales and marketing expenses",
            "research and development",
            "fulfillment",
            "logistics",
            "capital expenditures",
            "purchase of property and equipment",
            "costs of revenues",
        ],
        "summary": "The filing discusses cost or capital-consumption drivers through these markers: {matched_terms}.",
    },
    {
        "field_id": "disclosed_kpis",
        "label": "Disclosed operating KPIs",
        "source_section": "operating definitions / MD&A",
        "status": "directly_stated",
        "terms": [
            "active merchants",
            "active buyers",
            "orders shipped",
            "GMV",
            "gross merchandise value",
            "monthly active users",
            "average monthly active users",
            "MAU",
        ],
        "company_terms": {
            "tencent": [
                "Mini Programs",
            ],
        },
        "summary": (
            "The filing defines or references operating KPI markers: {matched_terms}. "
            "This does not mean V1 has extracted a complete KPI time series."
        ),
    },
    {
        "field_id": "management_framing",
        "label": "Management framing",
        "source_section": "business overview / MD&A",
        "status": "directly_stated",
        "terms": [
            "we aim",
            "business model has significant operating leverage",
            "our strategy",
            "value-for-money",
            "competitive prices",
            "operational model",
            "digital economy",
            "virtuous cycle",
            "streamline their manufacturing and operations",
        ],
        "summary": "The filing contains management framing or strategy language through these markers: {matched_terms}.",
        "company_summaries": {
            "pdd": (
                "PDD's latest official report frames the model around a digital-economy mission, value-for-money shopping, "
                "a Pinduoduo/Temu shared operating model, merchant efficiency, scale-driven operating leverage, and a buyer-merchant flywheel."
            ),
        },
    },
    {
        "field_id": "competitive_position_claims",
        "label": "Competitive position claims",
        "source_section": "business overview / risk factors",
        "status": "directly_stated",
        "terms": [
            "competitive prices",
            "competition",
            "competitors",
            "scale",
            "virtuous cycle",
            "buyer base",
            "supply chain",
            "technology",
            "brand",
        ],
        "summary": (
            "The filing contains competitive-position language through these markers: {matched_terms}. "
            "These are treated as management claims or risk disclosures, not proof of moat durability."
        ),
    },
    {
        "field_id": "risk_factor_map",
        "label": "Risk factor map",
        "source_section": "risk factors",
        "status": "directly_stated",
        "terms": [
            "risk factors",
            "competition",
            "counterfeit",
            "quality",
            "logistics",
            "regulatory",
            "trade",
            "data privacy",
            "intellectual property",
        ],
        "summary": "The filing flags risks relevant to the business model through these markers: {matched_terms}.",
    },
    {
        "field_id": "business_evolution",
        "label": "Business evolution",
        "source_section": "report comparison",
        "status": "inferred_from_multiple_disclosures",
        "special": "business_evolution",
        "terms": [],
        "summary": "The reader compares older and latest official reports to identify changes in business-model framing.",
    },
    {
        "field_id": "missing_disclosures",
        "label": "Missing or insufficient official-report evidence",
        "source_section": "not disclosed / not sufficiently quantified",
        "status": "not_disclosed",
        "special": "missing_disclosures",
        "terms": [],
        "summary": "The reader records official-report gaps that need external validation before investment-grade conclusions.",
    },
]


def latest_annual_report_document(documents: list[dict[str, Any]]) -> dict[str, Any] | None:
    annuals = [
        doc
        for doc in documents
        if str(doc.get("document_type", "")).startswith(("20-F", "10-K", "annual_report_pdf"))
        and doc.get("local_path")
    ]
    if not annuals:
        return None
    return sorted(annuals, key=lambda doc: doc.get("filing_date") or "")[-1]


def annual_report_topic_evidence(
    documents: list[dict[str, Any]],
    *,
    topic_terms: dict[str, list[str]],
) -> dict[str, Any]:
    document = latest_annual_report_document(documents)
    if not document:
        return {
            "status": "missing_annual_report",
            "source_document": None,
            "topics": {},
        }
    text = _document_text(Path(str(document["local_path"])))
    topics = {
        topic: _term_counts(text, terms)
        for topic, terms in topic_terms.items()
    }
    return {
        "status": "evidence_collected",
        "source_document": {
            "document_id": document.get("document_id"),
            "filing_date": document.get("filing_date"),
            "local_path": document.get("local_path"),
            "source_url": document.get("source_url"),
        },
        "topics": topics,
    }


def official_report_business_model_analysis(
    *,
    company: dict[str, Any],
    documents: list[dict[str, Any]],
    extracted_facts: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    raw_extracted_facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    company_id = str(company.get("company_id") or "generic")
    profile = BUSINESS_MODEL_PROFILES.get(company_id, BUSINESS_MODEL_PROFILES["generic"])
    annual_documents = _annual_documents(documents)
    latest = latest_annual_report_document(documents)
    if not latest:
        return {
            "status": "missing_official_annual_report",
            "input_scope": "official_reports_only",
            "subagent_reports": [],
            "right_business_model_checklist": [],
        }

    latest_text = _document_text(Path(str(latest["local_path"])))
    earliest = annual_documents[0] if annual_documents else latest
    earliest_text = _document_text(Path(str(earliest["local_path"]))) if earliest else ""
    section_presence = _section_presence(latest_text)
    financial_signals = _financial_signal_summary(extracted_facts, metrics)

    business_claims = _supported_claims(latest_text, profile["model_claims"])
    moat_hypotheses = _moat_hypotheses(latest_text, profile["moat_hypotheses"], financial_signals)
    risk_items = _risk_items(latest_text, profile["risk_terms"])
    evidence_cards = _deep_evidence_cards(
        company_id=company_id,
        latest=latest,
        latest_text=latest_text,
        raw_extracted_facts=raw_extracted_facts or [],
    )
    evolution = _business_evolution(
        company_id=company_id,
        earliest=earliest,
        earliest_text=earliest_text,
        latest=latest,
        latest_text=latest_text,
    )
    official_report_dossier = _official_report_dossier(
        company_id=company_id,
        latest=latest,
        latest_text=latest_text,
        evolution=evolution,
        missing_evidence=profile["missing_evidence"],
    )
    operating_kpi_analysis = _official_operating_kpi_analysis(
        company_id=company_id,
        documents=documents,
        latest=latest,
        latest_text=latest_text,
    )
    management_framing_analysis = _official_management_framing_analysis(
        company_id=company_id,
        latest=latest,
        latest_text=latest_text,
    )
    business_model_deep_dive = _business_model_deep_dive(
        company_id=company_id,
        latest=latest,
        latest_text=latest_text,
        extracted_facts=extracted_facts,
        metrics=metrics,
        raw_extracted_facts=raw_extracted_facts or [],
        operating_kpi_analysis=operating_kpi_analysis,
        financial_signals=financial_signals,
        moat_hypotheses=moat_hypotheses,
        risk_items=risk_items,
    )

    source_documents = [
        {
            "document_id": doc.get("document_id"),
            "filing_date": doc.get("filing_date"),
            "local_path": doc.get("local_path"),
            "document_type": doc.get("document_type"),
        }
        for doc in annual_documents[-5:]
    ]
    latest_source = {
        "document_id": latest.get("document_id"),
        "filing_date": latest.get("filing_date"),
        "local_path": latest.get("local_path"),
        "document_type": latest.get("document_type"),
    }
    subagent_reports = [
        {
            "name": "Official Report Reader",
            "status": "completed",
            "summary": "Used official company filings/reports only for V1 business model evidence.",
            "findings": [
                f"Latest annual report source: {latest.get('document_id')}",
                "Sections detected: " + (", ".join(_present_sections(section_presence)) or "none"),
                (
                    "Structured dossier fields: "
                    f"{official_report_dossier.get('field_count', 0)} | "
                    + ", ".join(
                        f"{status}: {count}"
                        for status, count in sorted(official_report_dossier.get("status_counts", {}).items())
                    )
                ),
                (
                    "Operating KPI records extracted: "
                    f"{operating_kpi_analysis.get('record_count', 0)} numeric; "
                    f"{len(operating_kpi_analysis.get('defined_only_markers', []))} defined-only markers"
                ),
                (
                    "Management framing themes extracted: "
                    f"{management_framing_analysis.get('theme_count', 0)} source-linked themes"
                ),
                f"Deep evidence cards extracted: {len(evidence_cards)}",
                "External customer, competitor, forum, and media sources are intentionally excluded in V1.",
            ],
            "source_documents": source_documents,
        },
        {
            "name": "Management Framing Analyst",
            "status": "completed" if management_framing_analysis.get("theme_count") else "limited",
            "summary": "Expanded strategy language into source-linked management claims and explicit accuracy limits.",
            "findings": management_framing_analysis.get("themes", []),
        },
        {
            "name": "Business Model Mapper",
            "status": "completed",
            "summary": "Mapped what the company does, who receives value, and who appears to pay.",
            "findings": business_claims,
        },
        {
            "name": "Revenue Engine Analyst",
            "status": "completed",
            "summary": "Mapped who pays, what they pay for, and which official metrics support the revenue engine.",
            "findings": (
                (business_model_deep_dive.get("revenue_engine") or {}).get("findings")
                or _revenue_engine_findings(latest_text, profile, financial_signals)
            ),
        },
        {
            "name": "Unit Economics Proxy Analyst",
            "status": (business_model_deep_dive.get("unit_economics") or {}).get("status", "limited"),
            "summary": "Converted official KPIs and financial metrics into unit-economics proxy signals.",
            "findings": (business_model_deep_dive.get("unit_economics") or {}).get("proxy_signals", []),
        },
        {
            "name": "Moat Hypothesis Analyst",
            "status": "completed",
            "summary": "Converted official-report evidence into testable moat hypotheses.",
            "findings": business_model_deep_dive.get("moat_hypotheses") or moat_hypotheses,
        },
        {
            "name": "Financial Evidence Analyst",
            "status": "completed" if financial_signals.get("latest_year") else "limited",
            "summary": "Checked whether extracted metrics support business quality claims.",
            "findings": financial_signals.get("findings", []),
        },
        {
            "name": "Business Evolution Analyst",
            "status": "completed",
            "summary": "Compared older and latest official reports for model stability or expansion.",
            "findings": evolution,
        },
        {
            "name": "Anti-Moat Analyst",
            "status": "completed",
            "summary": "Collected official-report evidence that could weaken the moat story.",
            "findings": business_model_deep_dive.get("anti_moat_tests") or risk_items,
        },
        {
            "name": "Evidence Auditor",
            "status": "completed",
            "summary": "Audited source quality and conclusion limits.",
            "findings": [
                "Source quality is high for company self-description and reported financials.",
                "Official reports can support moat hypotheses but cannot prove real-world durability by themselves.",
                "No final moat conclusion should be treated as investment-grade until external validation is added.",
            ],
        },
    ]

    checklist = _right_business_model_checklist(
        business_claims=business_claims,
        moat_hypotheses=moat_hypotheses,
        financial_signals=financial_signals,
    )
    return {
        "status": "official_report_v1_completed",
        "input_scope": "official_reports_only",
        "principle": "right business model",
        "latest_source": latest_source,
        "section_presence": section_presence,
        "official_report_dossier": official_report_dossier,
        "operating_kpi_analysis": operating_kpi_analysis,
        "management_framing_analysis": management_framing_analysis,
        "business_model_deep_dive": business_model_deep_dive,
        "subagent_reports": subagent_reports,
        "evidence_cards": evidence_cards,
        "moat_hypotheses": moat_hypotheses,
        "financial_signals": financial_signals,
        "missing_evidence": profile["missing_evidence"],
        "right_business_model_checklist": checklist,
        "conclusion_limit": (
            "V1 can describe and test management's business-model/moat story using official reports, "
            "but it cannot prove customer happiness, merchant economics, or competitive durability."
        ),
    }


def _official_report_dossier(
    *,
    company_id: str,
    latest: dict[str, Any],
    latest_text: str,
    evolution: list[dict[str, Any]],
    missing_evidence: list[str],
) -> dict[str, Any]:
    source_document = _official_source_document(latest)
    fields = []
    for definition in OFFICIAL_REPORT_DOSSIER_FIELDS:
        special = definition.get("special")
        if special == "business_evolution":
            fields.append(
                _business_evolution_dossier_field(
                    definition=definition,
                    source_document=source_document,
                    evolution=evolution,
                )
            )
            continue
        if special == "missing_disclosures":
            fields.append(
                {
                    "field_id": definition["field_id"],
                    "label": definition["label"],
                    "status": "not_disclosed",
                    "summary": (
                        "Official reports do not yet provide enough evidence for: "
                        + "; ".join(missing_evidence)
                    )
                    if missing_evidence
                    else "No explicit official-report gaps were configured for this company.",
                    "source_section": definition["source_section"],
                    "source_document": source_document,
                    "matched_terms": [],
                    "evidence": [],
                    "accuracy_note": (
                        "This is a gap register, not a company claim. It stays not_disclosed until source-linked evidence is added."
                    ),
                }
            )
            continue

        terms = _dossier_terms(definition, company_id)
        matched_terms = _matched_terms(latest_text, terms)
        evidence = _snippets(latest_text, terms, limit=2)
        if evidence:
            status = str(definition.get("status") or "directly_stated")
            summary = _dossier_field_summary(definition, company_id, matched_terms)
            accuracy_note = (
                "Source-grounded field: the summary is allowed because at least one latest official-report snippet matched."
            )
        else:
            status = "not_disclosed"
            summary = (
                "Not disclosed or not found by the V1 deterministic official-report reader in the latest annual report."
            )
            accuracy_note = (
                "No source snippet was found for the configured terms, so the field is not used as evidence."
            )
        fields.append(
            {
                "field_id": definition["field_id"],
                "label": definition["label"],
                "status": status,
                "summary": summary,
                "source_section": definition["source_section"],
                "source_document": source_document,
                "matched_terms": matched_terms,
                "evidence": evidence,
                "accuracy_note": accuracy_note,
            }
        )

    status_counts = _count_values(field.get("status", "unknown") for field in fields)
    return {
        "version": 1,
        "scope": "latest official annual report plus limited official-report history comparison",
        "accuracy_policy": (
            "Each non-not_disclosed field must have at least one official-report snippet, source document, and source section. "
            "Management claims are recorded as claims or hypotheses, not moat proof."
        ),
        "source_document": source_document,
        "field_count": len(fields),
        "status_counts": status_counts,
        "fields": fields,
    }


def _official_management_framing_analysis(
    *,
    company_id: str,
    latest: dict[str, Any],
    latest_text: str,
) -> dict[str, Any]:
    source_document = _official_source_document(latest)
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company",
            "scope": "latest official annual report",
            "source_document": source_document,
            "summary": "Company-specific management-framing probes are not configured yet.",
            "theme_count": 0,
            "themes": [],
            "audit_note": "No source-linked management framing claims were produced for this company.",
        }

    themes = []
    for probe in PDD_MANAGEMENT_FRAMING_PROBES:
        terms = list(probe.get("terms") or [])
        matched_terms = _matched_terms(latest_text, terms)
        evidence = _snippets(latest_text, terms, limit=4)
        status = "supported_by_official_report" if evidence else "not_found_in_latest_report"
        themes.append(
            {
                "theme_id": probe["theme_id"],
                "theme": probe["theme"],
                "claim": probe["management_claim"],
                "management_claim": probe["management_claim"],
                "status": status,
                "matched_terms": matched_terms,
                "evidence": evidence,
                "why_it_matters": probe["why_it_matters"],
                "accuracy_limit": probe["accuracy_limit"],
                "source_document": source_document,
            }
        )

    supported_themes = [theme for theme in themes if theme.get("status") == "supported_by_official_report"]
    summary = _pdd_management_framing_summary(supported_themes)
    return {
        "status": "completed" if supported_themes else "limited",
        "scope": "latest official PDD annual report; strategy language is treated as management claim, not independent proof",
        "source_document": source_document,
        "summary": summary,
        "theme_count": len(supported_themes),
        "themes": supported_themes,
        "not_found_themes": [theme for theme in themes if theme.get("status") != "supported_by_official_report"],
        "audit_note": (
            "The reader avoids generic forward-looking-statement boilerplate. It only summarizes strategy themes when "
            "the latest official annual report provides a matching source snippet."
        ),
    }


def _pdd_management_framing_summary(themes: list[dict[str, Any]]) -> str:
    if not themes:
        return "No source-linked PDD management-framing themes were extracted."
    theme_ids = {str(theme.get("theme_id")) for theme in themes}
    parts = []
    if "pdd_scope_and_mission" in theme_ids:
        parts.append("PDD frames itself as a multinational commerce group built around a digital-economy mission.")
    if "pdd_consumer_value_proposition" in theme_ids:
        parts.append("The customer promise is value-for-money selection, competitive pricing, and interactive shopping.")
    if "pdd_buyer_merchant_flywheel" in theme_ids:
        parts.append("The core moat narrative is a buyer-merchant flywheel reinforced by scale.")
    if "pdd_shared_operating_model" in theme_ids:
        parts.append("The latest filing links Pinduoduo and Temu through a shared value proposition and operating model.")
    if "pdd_merchant_efficiency" in theme_ids:
        parts.append("Management claims merchant efficiency and supply-chain improvements are part of the model.")
    if "pdd_operating_leverage" in theme_ids:
        parts.append("Management also claims operating leverage and structural cost savings from scale.")
    if "pdd_agriculture_inclusion" in theme_ids:
        parts.append("Agriculture remains a stated example of demand aggregation and digital inclusion.")
    return " ".join(parts)


def _official_operating_kpi_analysis(
    *,
    company_id: str,
    documents: list[dict[str, Any]],
    latest: dict[str, Any],
    latest_text: str,
) -> dict[str, Any]:
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company",
            "scope": "official_reports_and_filings",
            "record_count": 0,
            "records": [],
            "latest_by_metric": {},
            "defined_only_markers": [],
        }

    records = _pdd_operating_kpi_records(documents)
    defined_only_markers = _pdd_defined_only_kpi_markers(latest=latest, latest_text=latest_text)
    latest_by_metric = _latest_kpi_by_metric(records)
    metric_coverage = _pdd_operating_metric_coverage_notes(
        latest=latest,
        latest_text=latest_text,
        records=records,
        latest_by_metric=latest_by_metric,
    )
    return {
        "status": "completed",
        "scope": "PDD official SEC 20-F and 6-K earnings exhibits",
        "record_count": len(records),
        "metric_counts": _count_values(record.get("metric", "unknown") for record in records),
        "records": records,
        "latest_by_metric": latest_by_metric,
        "metric_coverage": metric_coverage,
        "defined_only_markers": defined_only_markers,
        "audit_note": (
            "Active merchants are extracted when official reports quantify them in MD&A. "
            "Literal orders shipped remains definition-only unless a filing provides an actual shipped-order count. "
            "Numeric extraction uses disclosed GMV, active buyers, MAU, annual spending per active buyer, "
            "active merchants, average transaction services revenue per active merchant, and total orders placed "
            "where official filings provide values."
        ),
    }


def _pdd_operating_kpi_records(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for document in documents:
        if not document.get("local_path"):
            continue
        if document.get("research_category") in {"DROP_SEC_INDEX_OR_HEADERS", "LOW_KEEP_WRAPPER_METADATA"}:
            continue
        document_type = str(document.get("document_type") or "")
        if not document_type.startswith(("20-F", "6-K")):
            continue
        text = _document_text(Path(str(document["local_path"])))
        if not text:
            continue
        extracted.extend(_pdd_ttm_kpi_records(text=text, document=document))
        extracted.extend(_pdd_quarterly_mau_records(text=text, document=document))
        extracted.extend(_pdd_total_order_records(text=text, document=document))
        extracted.extend(_pdd_active_merchant_records(text=text, document=document))
        extracted.extend(_pdd_avg_transaction_revenue_per_active_merchant_records(text=text, document=document))
    return _dedupe_kpi_records(extracted)


def _pdd_ttm_kpi_records(*, text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    configs = [
        {
            "metric": "gmv",
            "label": "GMV",
            "unit": "CNY",
            "scale": 1_000_000_000,
            "period_type": "trailing_twelve_months",
            "pattern": (
                r"GMV(?:\s*\d+)?\s+in\s+the\s+twelve-month\s+period\s+ended\s+"
                r"(?P<date>[A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s+was\s+RMB\s*"
                r"(?P<value>[\d,]+(?:\.\d+)?)\s+billion"
            ),
        },
        {
            "metric": "active_buyers",
            "label": "Active buyers",
            "unit": "users",
            "scale": 1_000_000,
            "period_type": "trailing_twelve_months",
            "pattern": (
                r"Active\s+buyers(?:\s*\d+)?\s+in\s+the\s+twelve-month\s+period\s+ended\s+"
                r"(?P<date>[A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s+(?:was|were)\s+"
                r"(?P<value>[\d,]+(?:\.\d+)?)\s+million"
            ),
        },
        {
            "metric": "annual_spending_per_active_buyer",
            "label": "Annual spending per active buyer",
            "unit": "CNY_per_active_buyer",
            "scale": 1,
            "period_type": "trailing_twelve_months",
            "pattern": (
                r"Annual\s+spending\s+per\s+active\s+buyer(?:\s*\d+)?\s+in\s+the\s+twelve-month\s+period\s+ended\s+"
                r"(?P<date>[A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s+was\s+RMB\s*"
                r"(?P<value>[\d,]+(?:\.\d+)?)"
            ),
        },
    ]
    records = []
    for config in configs:
        for match in re.finditer(config["pattern"], text, flags=re.IGNORECASE):
            period_end = _parse_month_day_year(match.group("date"))
            value = _scaled_number(match.group("value"), config["scale"])
            if not period_end or value is None:
                continue
            records.append(
                _operating_kpi_record(
                    metric=config["metric"],
                    label=config["label"],
                    value=value,
                    unit=config["unit"],
                    period_type=config["period_type"],
                    period_end=period_end,
                    document=document,
                    evidence=_evidence_from_match(text, match),
                    extraction_method="official_pdd_kpi_regex",
                )
            )
    return records


def _pdd_quarterly_mau_records(*, text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    quarter_end = _pdd_quarter_end(text)
    if not quarter_end:
        return []
    records = []
    pattern = (
        r"Average\s+monthly\s+active\s+users(?:\s*\(MAU\))?(?:\s*\d+)?\s+"
        r"in\s+the\s+quarter\s+(?:was|were)\s+(?P<value>[\d,]+(?:\.\d+)?)\s+million"
    )
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        value = _scaled_number(match.group("value"), 1_000_000)
        if value is None:
            continue
        records.append(
            _operating_kpi_record(
                metric="average_monthly_active_users",
                label="Average monthly active users",
                value=value,
                unit="users",
                period_type="quarter",
                period_end=quarter_end,
                document=document,
                evidence=_evidence_from_match(text, match),
                extraction_method="official_pdd_kpi_regex",
            )
        )
    return records


def _pdd_total_order_records(*, text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    pattern = (
        r"In\s+(?P<years>(?:\d{4},\s*)*(?:\d{4})\s+and\s+\d{4}),\s+"
        r"the\s+number\s+of\s+total\s+orders\s+placed\s+on\s+our\s+Pinduoduo\s+mobile\s+platform\s+"
        r"(?:reached|was)\s+(?P<values>.*?)\s*,\s+respectively"
    )
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        years = re.findall(r"\d{4}", match.group("years"))
        values = re.findall(r"([\d,]+(?:\.\d+)?)\s+billion", match.group("values"), flags=re.IGNORECASE)
        if len(years) != len(values):
            continue
        for year, raw_value in zip(years, values, strict=True):
            value = _scaled_number(raw_value, 1_000_000_000)
            if value is None:
                continue
            records.append(
                _operating_kpi_record(
                    metric="total_orders_placed",
                    label="Total orders placed",
                    value=value,
                    unit="orders",
                    period_type="annual",
                    period_end=f"{year}-12-31",
                    document=document,
                    evidence=_evidence_from_match(text, match),
                    extraction_method="official_pdd_total_orders_regex",
                )
            )
    return records


def _pdd_active_merchant_records(*, text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    comparative_pattern = (
        r"The\s+number\s+of\s+our\s+active\s+merchants\s+increased\s+from\s+"
        r"(?P<from_value>[\d,]+(?:\.\d+)?)\s+million\s+in\s+(?P<from_year>\d{4})\s+"
        r"to\s+(?P<to_value>[\d,]+(?:\.\d+)?)\s+million\s+in\s+(?P<to_year>\d{4})"
    )
    for match in re.finditer(comparative_pattern, text, flags=re.IGNORECASE):
        for prefix in ("from", "to"):
            value = _scaled_number(match.group(f"{prefix}_value"), 1_000_000)
            if value is None:
                continue
            records.append(
                _operating_kpi_record(
                    metric="active_merchants",
                    label="Active merchants",
                    value=value,
                    unit="merchants",
                    period_type="annual",
                    period_end=f"{match.group(f'{prefix}_year')}-12-31",
                    document=document,
                    evidence=_evidence_from_match(text, match),
                    extraction_method="official_pdd_active_merchants_regex",
                )
            )

    point_in_time_pattern = (
        r"In\s+(?P<year>\d{4}),\s+we\s+had\s+"
        r"(?P<value>[\d,]+(?:\.\d+)?)\s+million\s+active\s+merchants"
    )
    for match in re.finditer(point_in_time_pattern, text, flags=re.IGNORECASE):
        value = _scaled_number(match.group("value"), 1_000_000)
        if value is None:
            continue
        records.append(
            _operating_kpi_record(
                metric="active_merchants",
                label="Active merchants",
                value=value,
                unit="merchants",
                period_type="annual",
                period_end=f"{match.group('year')}-12-31",
                document=document,
                evidence=_evidence_from_match(text, match),
                extraction_method="official_pdd_active_merchants_regex",
            )
        )
    return records


def _pdd_avg_transaction_revenue_per_active_merchant_records(
    *,
    text: str,
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    records = []
    pattern = (
        r"Average\s+transaction\s+services\s+revenues\s+per\s+active\s+merchant\s+"
        r"increased\s+from\s+RMB\s*(?P<from_value>[\d,]+(?:\.\d+)?)\s+in\s+"
        r"(?P<from_year>\d{4})\s+to\s+RMB\s*(?P<to_value>[\d,]+(?:\.\d+)?)"
        r"(?:\s+\(US\$[\d,]+(?:\.\d+)?\))?\s+in\s+(?P<to_year>\d{4})"
    )
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        for prefix in ("from", "to"):
            value = _scaled_number(match.group(f"{prefix}_value"), 1)
            if value is None:
                continue
            records.append(
                _operating_kpi_record(
                    metric="average_transaction_services_revenue_per_active_merchant",
                    label="Average transaction services revenue per active merchant",
                    value=value,
                    unit="CNY_per_active_merchant",
                    period_type="annual",
                    period_end=f"{match.group(f'{prefix}_year')}-12-31",
                    document=document,
                    evidence=_evidence_from_match(text, match),
                    extraction_method="official_pdd_avg_transaction_revenue_per_active_merchant_regex",
                )
            )
    return records


def _pdd_defined_only_kpi_markers(*, latest: dict[str, Any], latest_text: str) -> list[dict[str, Any]]:
    markers = []
    for metric, label, terms, note in [
        (
            "orders_shipped",
            "Orders shipped",
            ["orders shipped"],
            "Appears inside the active-merchant definition; V1 found active merchants and total orders placed where quantified, but not a literal orders-shipped count.",
        ),
    ]:
        evidence = _snippets(latest_text, terms, limit=2)
        if not evidence:
            continue
        markers.append(
            {
                "metric": metric,
                "label": label,
                "status": "defined_not_quantified",
                "source_document": _official_source_document(latest),
                "matched_terms": _matched_terms(latest_text, terms),
                "evidence": evidence,
                "note": note,
            }
        )
    return markers


def _pdd_operating_metric_coverage_notes(
    *,
    latest: dict[str, Any],
    latest_text: str,
    records: list[dict[str, Any]],
    latest_by_metric: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    source_document = _official_source_document(latest)

    def coverage_item(
        *,
        metric_id: str,
        label: str,
        status: str,
        note: str,
        why_it_matters: str,
        terms: list[str],
        latest_metric: str | None = None,
    ) -> dict[str, Any]:
        metric_records = [
            record for record in records if latest_metric and record.get("metric") == latest_metric
        ]
        latest_record = latest_by_metric.get(latest_metric or "")
        return {
            "metric_id": metric_id,
            "label": label,
            "status": status,
            "note": note,
            "why_it_matters": why_it_matters,
            "record_count": len(metric_records),
            "latest_record": latest_record,
            "source_document": source_document,
            "matched_terms": _matched_terms(latest_text, terms),
            "evidence": _snippets(latest_text, terms, limit=2),
        }

    return [
        coverage_item(
            metric_id="gmv",
            label="GMV",
            status="historical_series_extracted",
            latest_metric="gmv",
            note=(
                "PDD disclosed GMV as a historical Pinduoduo platform KPI through the older earnings-report period; "
                "V1 currently finds the latest GMV record at 2021-12-31."
            ),
            why_it_matters="GMV helps test marketplace scale, but stale GMV should not be treated as current platform volume.",
            terms=["GMV", "gross merchandise value"],
        ),
        coverage_item(
            metric_id="active_merchants",
            label="Active merchants",
            status="current_series_extracted",
            latest_metric="active_merchants",
            note="Latest official annual report quantifies active merchants through 2025.",
            why_it_matters="Merchant count supports the supply-side scale hypothesis and merchant-dependence questions.",
            terms=["active merchants", "orders shipped"],
        ),
        coverage_item(
            metric_id="active_buyers_and_mau",
            label="Active buyers / MAU",
            status="historical_series_extracted",
            latest_metric="active_buyers",
            note=(
                "Active buyers and average monthly active users are extracted where older official filings disclose them; "
                "V1 currently finds the latest active-buyer record at 2022-03-31."
            ),
            why_it_matters="User scale and engagement are central to the buyer side of the flywheel, but the series is stale.",
            terms=["active buyers", "monthly active users", "MAU"],
        ),
        coverage_item(
            metric_id="total_orders",
            label="Total orders placed",
            status="historical_series_extracted",
            latest_metric="total_orders_placed",
            note="Official annual reports disclose total orders placed on the Pinduoduo mobile platform through 2021.",
            why_it_matters="Order count helps distinguish buyer scale from actual transaction frequency.",
            terms=["total orders", "orders placed"],
        ),
        coverage_item(
            metric_id="merchant_monetization",
            label="Average transaction services revenue per active merchant",
            status="current_series_extracted",
            latest_metric="average_transaction_services_revenue_per_active_merchant",
            note="Latest official annual report quantifies average transaction-services revenue per active merchant through 2025.",
            why_it_matters="This is a useful merchant monetization/take-intensity proxy, though not merchant profitability.",
            terms=["average transaction services revenues per active merchant", "transaction services revenues"],
        ),
        coverage_item(
            metric_id="return_rate",
            label="Return / refund rate",
            status="not_disclosed",
            note=(
                "V1 found return/refund language in metric definitions, but no official return-rate or refund-rate KPI."
            ),
            why_it_matters=(
                "Return/refund rate would be important for customer satisfaction, logistics quality, and true GMV/order quality."
            ),
            terms=["returns the merchandise", "refunds the purchase price", "returned", "return rate", "refund rate"],
        ),
        coverage_item(
            metric_id="sku_count",
            label="SKU / listed-product count",
            status="not_found_by_v1",
            note="V1 did not find a quantified SKU count or listed-product count in the official PDD annual report text.",
            why_it_matters="SKU breadth would help test selection advantage, but PDD does not appear to disclose a count here.",
            terms=["SKU", "SKUs", "stock keeping", "number of products", "product categories"],
        ),
        coverage_item(
            metric_id="temu_geography",
            label="Temu country / region footprint",
            status="mentioned_not_counted",
            note=(
                "The latest official report says Temu serves consumers in various countries and regions and names examples, "
                "but V1 did not find a total country count."
            ),
            why_it_matters="Geographic footprint matters for Temu scale, logistics complexity, and regulatory exposure.",
            terms=["serving consumers in various countries and regions", "countries and regions worldwide"],
        ),
        coverage_item(
            metric_id="logistics_partner_count",
            label="Logistics / fulfillment partner count",
            status="mentioned_not_counted",
            note="The latest official report mentions logistics vendors and fulfillment partners, but not a count.",
            why_it_matters="Partner count and concentration would help test fulfillment resilience and bargaining power.",
            terms=["logistics vendors", "fulfillment partners"],
        ),
    ]


def _operating_kpi_record(
    *,
    metric: str,
    label: str,
    value: float,
    unit: str,
    period_type: str,
    period_end: str,
    document: dict[str, Any],
    evidence: str,
    extraction_method: str,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "label": label,
        "value": value,
        "unit": unit,
        "period_type": period_type,
        "period_end": period_end,
        "filing_date": document.get("filing_date"),
        "source_document": _official_source_document(document),
        "source_url": document.get("source_url"),
        "evidence": evidence,
        "extraction_method": extraction_method,
    }


def _dedupe_kpi_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        key = (
            str(record.get("metric")),
            str(record.get("period_type")),
            str(record.get("period_end")),
        )
        current = best.get(key)
        if current is None or _kpi_source_rank(record) < _kpi_source_rank(current):
            best[key] = record
    return sorted(
        best.values(),
        key=lambda record: (
            str(record.get("metric")),
            str(record.get("period_end")),
            str(record.get("source_document", {}).get("document_id")),
        ),
    )


def _kpi_source_rank(record: dict[str, Any]) -> tuple[int, str]:
    source_document = record.get("source_document") or {}
    document_type = str(source_document.get("document_type") or "")
    source_id = str(source_document.get("document_id") or "")
    if document_type.startswith("6-K"):
        return (0, source_id)
    if document_type.startswith("20-F"):
        return (1, source_id)
    return (2, source_id)


def _latest_kpi_by_metric(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        metric = str(record.get("metric"))
        current = latest.get(metric)
        if current is None or str(record.get("period_end")) > str(current.get("period_end")):
            latest[metric] = record
    return latest


def _parse_month_day_year(value: str) -> str | None:
    try:
        return datetime.strptime(value.replace("\xa0", " "), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _pdd_quarter_end(text: str) -> str | None:
    match = re.search(r"quarter\s+ended\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", text, flags=re.IGNORECASE)
    if not match:
        return None
    return _parse_month_day_year(match.group(1))


def _scaled_number(raw_value: str, scale: int | float) -> float | None:
    try:
        return float(raw_value.replace(",", "")) * float(scale)
    except ValueError:
        return None


def _evidence_from_match(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 120)
    end = min(len(text), match.end() + 160)
    snippet = SPACE_PATTERN.sub(" ", text[start:end]).strip()
    if start > 0:
        snippet = "... " + snippet
    if end < len(text):
        snippet += " ..."
    return snippet


def _business_evolution_dossier_field(
    *,
    definition: dict[str, Any],
    source_document: dict[str, Any],
    evolution: list[dict[str, Any]],
) -> dict[str, Any]:
    if not evolution:
        return {
            "field_id": definition["field_id"],
            "label": definition["label"],
            "status": "not_disclosed",
            "summary": "No official-report history comparison was available.",
            "source_section": definition["source_section"],
            "source_document": source_document,
            "matched_terms": [],
            "evidence": [],
            "accuracy_note": "No report-comparison evidence was produced.",
        }
    primary = evolution[0]
    evidence = list(primary.get("evidence") or [])
    status = "inferred_from_multiple_disclosures" if evidence else "not_disclosed"
    return {
        "field_id": definition["field_id"],
        "label": definition["label"],
        "status": status,
        "summary": primary.get("claim") or definition["summary"],
        "source_section": definition["source_section"],
        "source_document": source_document,
        "source_comparison": primary.get("source_comparison"),
        "matched_terms": primary.get("matched_terms") or [],
        "evidence": evidence,
        "accuracy_note": (
            "This field is an inference from official-report comparison, so it should be reviewed separately from directly stated fields."
            if evidence
            else "No source snippet was found for the report-comparison inference."
        ),
    }


def _dossier_field_summary(
    definition: dict[str, Any],
    company_id: str,
    matched_terms: list[str],
) -> str:
    company_summaries = definition.get("company_summaries") or {}
    if company_id in company_summaries:
        return str(company_summaries[company_id])
    matched = ", ".join(matched_terms) or "configured terms"
    return str(definition.get("summary", "")).format(matched_terms=matched)


def _dossier_terms(definition: dict[str, Any], company_id: str) -> list[str]:
    terms = list(definition.get("terms") or [])
    company_terms = (definition.get("company_terms") or {}).get(company_id, [])
    return terms + list(company_terms)


def _official_source_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": document.get("document_id"),
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "local_path": document.get("local_path"),
        "document_type": document.get("document_type"),
        "source_url": document.get("source_url"),
    }


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _annual_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annuals = [
        doc
        for doc in documents
        if str(doc.get("document_type", "")).startswith(("20-F", "10-K", "annual_report_pdf"))
        and doc.get("local_path")
    ]
    return sorted(
        annuals,
        key=lambda doc: (
            int(doc.get("fiscal_year") or 0),
            doc.get("filing_date") or "",
        ),
    )


def _section_presence(text: str) -> dict[str, Any]:
    text_lower = text.lower()
    sections = {}
    for section, terms in BUSINESS_MODEL_SECTION_TERMS.items():
        matched = [term for term in terms if term.lower() in text_lower]
        sections[section] = {
            "found": bool(matched),
            "matched_terms": matched,
        }
    return sections


def _present_sections(section_presence: dict[str, Any]) -> list[str]:
    return [
        section
        for section, details in section_presence.items()
        if details.get("found")
    ]


def _supported_claims(text: str, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for claim in claims:
        terms = claim.get("terms", [])
        matched_terms = _matched_terms(text, terms)
        status = "supported_by_official_report" if matched_terms else "unproven_in_current_report"
        output.append(
            {
                "claim": claim["claim"],
                "status": status,
                "matched_terms": matched_terms,
                "evidence": _snippets(text, terms, limit=2),
            }
        )
    return output


def _revenue_engine_findings(
    text: str,
    profile: dict[str, Any],
    financial_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    matched_terms = _matched_terms(text, profile["revenue_terms"])
    findings: list[dict[str, Any]] = [
        {
            "claim": "Official reports identify revenue streams and monetization language.",
            "status": "supported_by_official_report" if matched_terms else "unproven_in_current_report",
            "matched_terms": matched_terms,
            "evidence": _snippets(text, profile["revenue_terms"], limit=3),
        }
    ]
    latest = financial_signals.get("latest_year")
    if latest:
        findings.append(
            {
                "claim": f"Latest extracted financials provide a profit/cash-flow check for {latest}.",
                "status": "supported_by_extracted_financials",
                "matched_terms": [],
                "evidence": financial_signals.get("findings", [])[:4],
            }
        )
    return findings


def _moat_hypotheses(
    text: str,
    hypotheses: list[dict[str, Any]],
    financial_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    output = []
    quality_support = bool(financial_signals.get("quality_support"))
    for hypothesis in hypotheses:
        matched_terms = _matched_terms(text, hypothesis.get("terms", []))
        if matched_terms and quality_support:
            status = "partially_supported"
        elif matched_terms:
            status = "official_narrative_supported"
        else:
            status = "unproven"
        output.append(
            {
                "hypothesis": hypothesis["hypothesis"],
                "status": status,
                "matched_terms": matched_terms,
                "evidence": _snippets(text, hypothesis.get("terms", []), limit=2),
                "missing_validation": "Needs competitor and customer/merchant evidence outside official reports.",
            }
        )
    return output


def _risk_items(text: str, risk_terms: list[str]) -> list[dict[str, Any]]:
    matched_terms = _matched_terms(text, risk_terms)
    snippets = _snippets(text, risk_terms, limit=5)
    if not snippets:
        return [
            {
                "claim": "Anti-moat risks need more targeted extraction.",
                "status": "limited_evidence",
                "matched_terms": matched_terms,
                "evidence": [],
            }
        ]
    return [
        {
            "claim": "Official reports identify risks that could weaken or disprove the moat story.",
            "status": "risk_flagged_by_official_report",
            "matched_terms": matched_terms,
            "evidence": snippets,
        }
    ]


def _business_model_deep_dive(
    *,
    company_id: str,
    latest: dict[str, Any],
    latest_text: str,
    extracted_facts: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    raw_extracted_facts: list[dict[str, Any]],
    operating_kpi_analysis: dict[str, Any],
    financial_signals: dict[str, Any],
    moat_hypotheses: list[dict[str, Any]],
    risk_items: list[dict[str, Any]],
) -> dict[str, Any]:
    if company_id != "pdd":
        return {
            "status": "generic_pending_company_specific_deep_dive",
            "scope": "Company-specific deep-dive templates are currently implemented for PDD first.",
            "revenue_engine": {},
            "unit_economics": {},
            "answer_cards": [],
            "moat_hypotheses": moat_hypotheses,
            "anti_moat_tests": risk_items,
        }

    annual_rows = annual_fact_rows(extracted_facts)
    financial_bridge = _pdd_financial_bridge(annual_rows, metrics=metrics, financial_signals=financial_signals)
    revenue_mix = _pdd_latest_revenue_mix(
        raw_extracted_facts,
        latest_document_id=str(latest.get("document_id") or ""),
    )
    revenue_mix_history = _pdd_revenue_mix_history(raw_extracted_facts)
    active_merchants = _latest_operating_record(operating_kpi_analysis, "active_merchants")
    transaction_revenue_per_merchant = _latest_operating_record(
        operating_kpi_analysis,
        "average_transaction_services_revenue_per_active_merchant",
    )
    active_buyers = _latest_operating_record(operating_kpi_analysis, "active_buyers")
    gmv = _latest_operating_record(operating_kpi_analysis, "gmv")
    orders = _latest_operating_record(operating_kpi_analysis, "total_orders_placed")
    annual_spend = _latest_operating_record(operating_kpi_analysis, "annual_spending_per_active_buyer")
    scale_snapshot = _pdd_scale_snapshot(
        active_merchants=active_merchants,
        transaction_revenue_per_merchant=transaction_revenue_per_merchant,
        active_buyers=active_buyers,
        gmv=gmv,
        orders=orders,
        annual_spend=annual_spend,
    )

    revenue_engine = {
        "status": "source_grounded",
        "summary": (
            "PDD's official revenue engine is merchant funded: third-party merchants pay for online marketing "
            "services/others and transaction services. The latest filing makes transaction-service monetization "
            "and active-merchant scale especially important to the current model."
        ),
        "payer": "Third-party merchants, primarily merchants in China according to the latest official report.",
        "customer_value_proposition": "Consumers are promised value-for-money selection, competitive pricing, and interactive shopping.",
        "merchant_value_proposition": (
            "Merchants receive buyer reach, marketing/transaction services, and claimed operating-efficiency support."
        ),
        "revenue_mix": revenue_mix,
        "revenue_mix_history": revenue_mix_history[-6:],
        "financial_bridge": financial_bridge,
        "findings": [
            {
                "claim": "Revenue comes mainly from merchant services rather than direct retail inventory sales.",
                "status": "supported_by_official_report",
                "evidence": _snippets(
                    latest_text,
                    ["transaction services", "online marketing services", "third-party merchants"],
                    limit=3,
                ),
                "why_it_matters": "Merchant ROI and dependence on the platform are therefore central to durability.",
                "limitation": "Official reports do not show merchant net profit after ads, logistics, returns, or platform rules.",
            },
            {
                "claim": "The current official KPI set emphasizes merchant count and transaction-service monetization.",
                "status": "supported_by_official_kpis",
                "evidence": [
                    _operating_record_line("Active merchants", active_merchants),
                    _operating_record_line(
                        "Average transaction-services revenue per active merchant",
                        transaction_revenue_per_merchant,
                    ),
                ],
                "why_it_matters": "This is a stronger current clue than stale GMV/user KPIs for how PDD monetizes today.",
                "limitation": "It is a monetization proxy, not a merchant-profitability measure.",
            },
            {
                "claim": "Historical Pinduoduo scale KPIs are useful but stale.",
                "status": "historical_context_only",
                "evidence": [
                    _operating_record_line("GMV", gmv),
                    _operating_record_line("Active buyers", active_buyers),
                    _operating_record_line("Total orders placed", orders),
                    _operating_record_line("Annual spending per active buyer", annual_spend),
                ],
                "why_it_matters": "They show prior marketplace scale, but cannot prove the current Temu/PDD combined flywheel.",
                "limitation": "Most buyer/GMV/order KPIs stop around 2021 or Q1 2022 in the extracted official series.",
            },
        ],
    }

    answer_cards = _pdd_business_model_answer_cards(
        latest_text=latest_text,
        financial_bridge=financial_bridge,
        revenue_mix_history=revenue_mix_history,
        scale_snapshot=scale_snapshot,
        active_merchants=active_merchants,
        transaction_revenue_per_merchant=transaction_revenue_per_merchant,
        active_buyers=active_buyers,
        gmv=gmv,
        orders=orders,
        annual_spend=annual_spend,
    )

    unit_economics = {
        "status": "proxy_only_official_reporting",
        "summary": (
            "PDD does not disclose full unit economics by Pinduoduo versus Temu. V1 therefore uses official "
            "merchant KPIs, margins, cash conversion, ROIC, and cash flow as proxy evidence."
        ),
        "proxy_signals": [
            _unit_proxy_signal(
                name="Merchant monetization per active merchant",
                status="current_official_kpi",
                value=_operating_record_line(
                    "Average transaction-services revenue per active merchant",
                    transaction_revenue_per_merchant,
                ),
                interpretation=(
                    "Rising revenue per merchant can support the merchant-service monetization story, "
                    "but it may also indicate higher platform take intensity."
                ),
                limitation="Does not show whether merchants are more profitable or merely paying more.",
            ),
            _unit_proxy_signal(
                name="Active merchant scale",
                status="current_official_kpi",
                value=_operating_record_line("Active merchants", active_merchants),
                interpretation="More active merchants supports supply-side breadth and potential network effects.",
                limitation="Merchant count alone does not prove merchant satisfaction or retention quality.",
            ),
            _unit_proxy_signal(
                name="Gross margin",
                status="financial_proxy",
                value=_format_financial_finding("Latest gross margin", financial_signals.get("gross_margin"), percent=True),
                interpretation="High gross margin is consistent with a platform/service model rather than heavy inventory ownership.",
                limitation="Gross margin does not isolate Pinduoduo versus Temu or fulfillment obligations.",
            ),
            _unit_proxy_signal(
                name="Cash conversion",
                status="financial_proxy",
                value=_format_financial_finding("Latest cash conversion", financial_signals.get("cash_conversion")),
                interpretation="Cash conversion helps test whether accounting earnings turn into owner-relevant cash.",
                limitation="Needs working-capital and cross-border logistics detail before being treated as durable.",
            ),
            _unit_proxy_signal(
                name="ROIC",
                status="financial_proxy",
                value=_format_financial_finding("Latest unlevered ROIC", financial_signals.get("roic"), percent=True),
                interpretation="High ROIC can support a moat hypothesis if it persists under competition.",
                limitation="ROIC is company-level; segment/Temu economics are not separated.",
            ),
        ],
        "missing_unit_economics": [
            "Pinduoduo versus Temu revenue, margin, cash-flow, and reinvestment split.",
            "Merchant profitability after ads, discounts, logistics, returns, penalties, and platform rules.",
            "Customer cohort retention, repeat-purchase frequency, and current GMV/order disclosure.",
            "Fulfillment/logistics cost per order and return/refund cost burden.",
        ],
    }

    deep_moat_hypotheses = [
        {
            "hypothesis_id": "pdd_buyer_merchant_network_effect",
            "hypothesis": "Buyer-merchant marketplace network effect",
            "official_support": "Official report describes buyers, merchants, scale, and a virtuous cycle.",
            "financial_or_kpi_support": _operating_record_line("Active merchants", active_merchants),
            "evidence": _snippets(latest_text, ["buyer base helps attract merchants", "virtuous cycle", "active merchants"], limit=3),
            "missing_tests": [
                "Merchant retention/profit evidence",
                "Customer repeat-purchase evidence",
                "Competitor ability to copy low-price traffic acquisition",
            ],
            "current_read": "hypothesis_supported_by_official_report_not_proven",
        },
        {
            "hypothesis_id": "pdd_low_price_supply_chain_advantage",
            "hypothesis": "Low-price supply-chain or merchant-efficiency advantage",
            "official_support": "Official report claims merchant manufacturing/operations streamlining, reduced waste, and competitive prices.",
            "financial_or_kpi_support": _format_financial_finding("Latest gross margin", financial_signals.get("gross_margin"), percent=True),
            "evidence": _snippets(
                latest_text,
                ["streamline their manufacturing and operations", "reduced waste", "competitive prices"],
                limit=3,
            ),
            "missing_tests": [
                "External merchant economics",
                "Customer quality and return/refund evidence",
                "Competitor cost comparison",
            ],
            "current_read": "management_claim_with_financial_support_needing_external_validation",
        },
        {
            "hypothesis_id": "pdd_merchant_service_monetization",
            "hypothesis": "Merchant value proposition and monetization are improving",
            "official_support": "Latest report identifies active merchants and average transaction-services revenue per active merchant as key drivers.",
            "financial_or_kpi_support": _operating_record_line(
                "Average transaction-services revenue per active merchant",
                transaction_revenue_per_merchant,
            ),
            "evidence": _snippets(latest_text, ["average transaction services revenues per active merchant", "active merchants"], limit=3),
            "missing_tests": [
                "Whether merchants accept higher monetization because ROI is good",
                "Whether merchant complaints reveal adversarial platform rules",
            ],
            "current_read": "current_kpi_supports_monetization_but_not_merchant_happiness",
        },
        {
            "hypothesis_id": "pdd_temu_scalability",
            "hypothesis": "Temu can extend PDD's operating model outside China",
            "official_support": "Latest filing links Pinduoduo and Temu through the same value propositions and operating model.",
            "financial_or_kpi_support": "Not separately disclosed.",
            "evidence": _snippets(latest_text, ["Pinduoduo and Temu", "same value propositions and operational model"], limit=3),
            "missing_tests": [
                "Standalone Temu unit economics",
                "Regulatory/trade sensitivity",
                "Customer trust and logistics quality outside China",
            ],
            "current_read": "important_hypothesis_but_currently_low_proof",
        },
    ]

    anti_moat_tests = [
        _anti_moat_test(
            risk_id="competition_copyability",
            risk="Competitors may copy low-price marketplace mechanics or use stronger logistics/merchant relationships.",
            official_evidence=_snippets(latest_text, ["competition", "competitors", "competitive"], limit=2),
            external_test="Compare Alibaba, JD, Douyin/TikTok commerce, Shein, and Amazon official materials and merchant economics.",
        ),
        _anti_moat_test(
            risk_id="customer_trust_quality",
            risk="Low prices may be offset by quality, refund, customer-service, or trust problems.",
            official_evidence=_snippets(latest_text, ["counterfeit", "quality", "consumer protection", "refund"], limit=2),
            external_test="Use app/review sources and customer forums only as source-labeled pattern evidence.",
        ),
        _anti_moat_test(
            risk_id="merchant_relationship",
            risk="Merchant monetization can become extractive if ads, returns, fines, or logistics obligations hurt seller ROI.",
            official_evidence=_snippets(latest_text, ["merchant", "transaction services", "returns"], limit=2),
            external_test="Collect merchant/seller feedback and official seller rules before treating merchant scale as a moat.",
        ),
        _anti_moat_test(
            risk_id="regulatory_trade",
            risk="Cross-border de minimis, consumer-protection, data/privacy, product-safety, and trade rules can cap Temu economics.",
            official_evidence=_snippets(latest_text, ["regulatory", "trade", "data privacy", "logistics"], limit=2),
            external_test="Start with regulator/government sources, not social commentary.",
        ),
        _anti_moat_test(
            risk_id="ownership_cash_access",
            risk="ADR/VIE/Cayman structure and China operating constraints may affect ownership quality and cash accessibility.",
            official_evidence=_snippets(latest_text, ["Cayman Islands holding company", "VIE", "contractual arrangements"], limit=2),
            external_test="Keep structural ownership risk separate from operating moat strength.",
        ),
    ]

    return {
        "status": "pdd_deep_dive_v1_completed",
        "scope": "official reports plus extracted official financial/KPI facts; no external source is treated as proof yet",
        "source_document": _official_source_document(latest),
        "revenue_engine": revenue_engine,
        "answer_cards": answer_cards,
        "unit_economics": unit_economics,
        "moat_hypotheses": deep_moat_hypotheses,
        "anti_moat_tests": anti_moat_tests,
        "evidence_standard": [
            "Official reports can support company claims and financial facts.",
            "External sources are required before concluding customer happiness, merchant satisfaction, or moat durability.",
            "Forum/review evidence can only create leads until triangulated.",
        ],
    }


def _pdd_business_model_answer_cards(
    *,
    latest_text: str,
    financial_bridge: dict[str, Any],
    revenue_mix_history: list[dict[str, Any]],
    scale_snapshot: list[str],
    active_merchants: dict[str, Any] | None,
    transaction_revenue_per_merchant: dict[str, Any] | None,
    active_buyers: dict[str, Any] | None,
    gmv: dict[str, Any] | None,
    orders: dict[str, Any] | None,
    annual_spend: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    latest_mix = revenue_mix_history[-1] if revenue_mix_history else {}
    transaction_share = latest_mix.get("transaction_share")
    online_share = latest_mix.get("online_marketing_share")
    latest_snapshot = financial_bridge.get("latest_snapshot") or []
    yoy_pressure = financial_bridge.get("yoy_pressure") or []

    return [
        _answer_card(
            question_id="economic_engine",
            question="What is the real economic engine?",
            current_answer=(
                "PDD is best read as a merchant-funded demand aggregation and commerce-services platform, "
                "not a conventional inventory retailer. Consumers are pulled by value-for-money selection and "
                "interactive shopping; merchants then pay for demand generation and transaction-related services. "
                "The model works only if PDD can keep consumer traffic cheap enough and merchant ROI high enough "
                "that merchants continue funding the platform."
            ),
            evidence_grade="medium-high for mechanics; medium for durability",
            quantitative_support=[
                _format_revenue_mix_line(latest_mix),
                _operating_record_line("Active merchants", active_merchants),
                _operating_record_line(
                    "Average transaction-services revenue per active merchant",
                    transaction_revenue_per_merchant,
                ),
            ],
            official_support=[
                "Revenue is split between online marketing services/others and transaction services.",
                "The latest report says Pinduoduo and Temu share value propositions and operating model.",
            ],
            source_evidence=_snippets(
                latest_text,
                ["online marketing services", "transaction services", "same value propositions and operational model"],
                limit=2,
            ),
            what_could_be_wrong=[
                "Merchant payments may reflect rising take intensity rather than better merchant economics.",
                "Temu may have a different cost structure even if management describes the operating model as shared.",
            ],
            next_tests=[
                "Build merchant ROI evidence from seller forums, rules, ad costs, refund burden, and logistics obligations.",
                "Compare PDD/Temu monetization with Alibaba, JD, Douyin/TikTok commerce, Shein, and Amazon-like models.",
            ],
        ),
        _answer_card(
            question_id="revenue_quality",
            question="Is revenue quality improving or just getting larger?",
            current_answer=(
                "Official data show a major mix shift. Transaction services grew from a small part of revenue "
                "into nearly half of 2025 revenue, while online marketing remains the other half. That makes the "
                "business less purely advertising-like and more tied to transaction/service intensity. This can be "
                "good if it reflects more merchant value-added services, but risky if it reflects pressure on merchants."
            ),
            evidence_grade="medium",
            quantitative_support=[
                _format_revenue_mix_line(latest_mix),
                _format_share_line("Transaction services share", transaction_share),
                _format_share_line("Online marketing services/others share", online_share),
                _revenue_mix_trend_line(revenue_mix_history),
            ],
            official_support=[
                "The latest filing attributes transaction-service growth to more active merchants and higher transaction-services revenue per active merchant.",
            ],
            source_evidence=_snippets(
                latest_text,
                ["transaction services revenues per active merchant", "increase in the number of active merchants"],
                limit=2,
            ),
            what_could_be_wrong=[
                "Revenue mix may be affected by Temu expansion, but PDD does not disclose Pinduoduo versus Temu economics separately.",
                "Higher transaction-service revenue per merchant does not prove merchant profit or retention.",
            ],
            next_tests=[
                "Create a multi-year revenue-mix chart and tie inflection points to Temu launch and disclosure changes.",
                "Collect merchant evidence on ad spend, fees, fulfillment, returns, and realized seller margin.",
            ],
        ),
        _answer_card(
            question_id="unit_economics",
            question="Do official numbers support attractive unit economics?",
            current_answer=(
                "At company level, yes, but with an important warning. PDD still has high gross margin, strong free "
                "cash flow, positive cash conversion, and high ROIC. However, 2025 weakened versus 2024: revenue grew, "
                "but operating income, net income, FCF, gross margin, operating margin, and ROIC all moved the wrong way. "
                "That means the agent should not simply say 'great economics'; it should ask whether Temu, logistics, "
                "competition, subsidies, or merchant/customer issues are consuming incremental economics."
            ),
            evidence_grade="medium-high for company-level economics; low for segment/unit economics",
            quantitative_support=latest_snapshot + yoy_pressure,
            official_support=[
                "Official filings provide company-level revenue, gross profit, operating income, net income, OCF, capex, cash, and liabilities.",
            ],
            source_evidence=[],
            what_could_be_wrong=[
                "Company-level profitability can hide weak Temu economics or different economics across markets.",
                "Cash conversion can be flattered by working-capital timing and merchant/customer settlement flows.",
            ],
            next_tests=[
                "Separate Pinduoduo and Temu as much as possible using disclosures, earnings-call language, and external operating evidence.",
                "Track cost of revenue, fulfillment/logistics language, sales and marketing, and working-capital movements each year.",
            ],
        ),
        _answer_card(
            question_id="customer_value",
            question="Why do customers use it, and is that durable?",
            current_answer=(
                "The official customer proposition is low price/value-for-money plus broad selection and interactive discovery. "
                "The older Pinduoduo KPIs show huge historical scale, but most buyer/GMV/order KPIs stop around 2021 or early 2022. "
                "So official reports support that the model reached scale; they do not prove current customer love, repeat quality, "
                "or Temu trust outside China."
            ),
            evidence_grade="medium for historical scale; low for current customer happiness",
            quantitative_support=[
                _operating_record_line("GMV", gmv),
                _operating_record_line("Active buyers", active_buyers),
                _operating_record_line("Total orders placed", orders),
                _operating_record_line("Annual spending per active buyer", annual_spend),
            ],
            official_support=[
                "Pinduoduo is described as value-for-money and interactive.",
                "Temu is described as expanding globally, but current customer KPIs are not separated.",
            ],
            source_evidence=_snippets(
                latest_text,
                ["value-for-money merchandise", "fun and interactive shopping", "Temu expanded"],
                limit=2,
            ),
            what_could_be_wrong=[
                "Customers may be loyal to price only, not to the platform.",
                "Quality, shipping, refunds, or trust problems can destroy repeat behavior even when prices are low.",
            ],
            next_tests=[
                "Use customer-happiness agent evidence by dimension: value, product quality, shipping, refunds, trust, loyalty.",
                "Compare customer value proposition against AliExpress, Shein, Amazon, JD, Taobao/Tmall, and Douyin commerce.",
            ],
        ),
        _answer_card(
            question_id="moat_source",
            question="Where could a real moat exist?",
            current_answer=(
                "The most plausible moat is not 'cheap products' by itself. It is the combination of demand scale, "
                "merchant density, data/traffic allocation, supply-chain operating support, and possibly cross-border merchant "
                "infrastructure. The official reports and financials are consistent with that story, but they do not prove "
                "that competitors cannot copy it or that merchants/customers are better off over time."
            ),
            evidence_grade="medium as hypothesis; not proven",
            quantitative_support=scale_snapshot + [
                _first(latest_snapshot, "Latest gross margin"),
                _first(latest_snapshot, "Latest unlevered ROIC"),
            ],
            official_support=[
                "Official filings describe buyer-merchant flywheel, merchant efficiency, scale, and competitive pricing.",
            ],
            source_evidence=_snippets(
                latest_text,
                ["buyer base helps attract merchants", "streamline their manufacturing and operations", "virtuous cycle"],
                limit=3,
            ),
            what_could_be_wrong=[
                "If merchant ROI is poor, merchant scale may be fragile rather than a moat.",
                "If logistics, regulation, or product trust problems rise with scale, growth may weaken the moat rather than deepen it.",
            ],
            next_tests=[
                "Run an external merchant-economics collector before upgrading this from hypothesis to supported moat.",
                "Run competitor official-material comparison to test copyability and relative cost/traffic advantage.",
            ],
        ),
        _answer_card(
            question_id="anti_moat",
            question="What evidence would make the model less attractive?",
            current_answer=(
                "The strongest anti-moat concern is that low price may be bought through hidden costs: quality problems, "
                "refund friction, regulatory/trade exposure, logistics burden, merchant margin pressure, or expensive growth. "
                "The 2025 margin and ROIC decline makes this a real diligence question, not just a generic risk-factor note."
            ),
            evidence_grade="medium",
            quantitative_support=yoy_pressure,
            official_support=[
                "Official risk factors flag competition, counterfeit/quality, logistics, regulation, trade, consumer protection, and data/privacy risks.",
            ],
            source_evidence=_snippets(
                latest_text,
                ["competition", "counterfeit", "quality", "regulatory", "trade"],
                limit=3,
            ),
            what_could_be_wrong=[
                "Some 2025 pressure may be deliberate long-term investment rather than deterioration.",
                "Forum/review evidence can overrepresent unhappy users, so it needs source-quality labels and triangulation.",
            ],
            next_tests=[
                "Triangulate public voice with app reviews, regulator complaints/actions, merchant feedback, and competitor evidence.",
                "Track whether 2025 margin pressure reverses, stabilizes, or worsens in later filings.",
            ],
        ),
    ]


def _answer_card(
    *,
    question_id: str,
    question: str,
    current_answer: str,
    evidence_grade: str,
    quantitative_support: list[str | None],
    official_support: list[str],
    source_evidence: list[str],
    what_could_be_wrong: list[str],
    next_tests: list[str],
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question": question,
        "current_answer": current_answer,
        "evidence_grade": evidence_grade,
        "quantitative_support": [item for item in quantitative_support if item],
        "official_support": official_support,
        "source_evidence": source_evidence,
        "what_could_be_wrong": what_could_be_wrong,
        "next_tests": next_tests,
    }


def _pdd_financial_bridge(
    annual_rows: list[dict[str, Any]],
    *,
    metrics: list[dict[str, Any]],
    financial_signals: dict[str, Any],
) -> dict[str, Any]:
    rows = [row for row in annual_rows if row.get("year")]
    if not rows:
        return {
            "status": "missing_financial_rows",
            "latest_snapshot": [],
            "yoy_pressure": [],
        }
    rows = sorted(rows, key=lambda row: row.get("year") or 0)
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else {}
    latest_year = latest.get("year")
    previous_year = previous.get("year")
    revenue = latest.get("revenue")
    gross_profit = latest.get("gross_profit")
    operating_income = latest.get("operating_income")
    net_income = latest.get("net_income")
    operating_cash_flow = latest.get("operating_cash_flow")
    free_cash_flow = latest.get("free_cash_flow")
    gross_margin = _ratio(gross_profit, revenue)
    operating_margin = _ratio(operating_income, revenue)
    cash_conversion = _ratio(operating_cash_flow, net_income)
    latest_roic = financial_signals.get("roic")
    previous_roic = _metric_value_for_year(metrics, "unlevered_roic_v1", previous_year)

    latest_snapshot = [
        _annual_metric_line("Latest revenue", revenue, latest_year, unit="RMB"),
        _annual_metric_line("Latest gross margin", gross_margin, latest_year, percent=True),
        _annual_metric_line("Latest operating margin", operating_margin, latest_year, percent=True),
        _annual_metric_line("Latest net income", net_income, latest_year, unit="RMB"),
        _annual_metric_line("Latest free cash flow", free_cash_flow, latest_year, unit="RMB"),
        _annual_metric_line("Latest cash conversion", cash_conversion, latest_year),
        _format_financial_finding("Latest unlevered ROIC", latest_roic, percent=True),
        _format_financial_finding("Latest owner earnings yield", financial_signals.get("owner_earnings_yield"), percent=True),
    ]

    previous_gross_margin = _ratio(previous.get("gross_profit"), previous.get("revenue"))
    previous_operating_margin = _ratio(previous.get("operating_income"), previous.get("revenue"))
    yoy_pressure = [
        _pct_change_line("Revenue YoY", previous.get("revenue"), revenue, previous_year, latest_year),
        _pct_change_line("Operating income YoY", previous.get("operating_income"), operating_income, previous_year, latest_year),
        _pct_change_line("Net income YoY", previous.get("net_income"), net_income, previous_year, latest_year),
        _pct_change_line("Free cash flow YoY", previous.get("free_cash_flow"), free_cash_flow, previous_year, latest_year),
        _margin_change_line("Gross margin", previous_gross_margin, gross_margin, previous_year, latest_year),
        _margin_change_line("Operating margin", previous_operating_margin, operating_margin, previous_year, latest_year),
        _margin_change_line("Unlevered ROIC", previous_roic, latest_roic, previous_year, latest_year),
    ]

    return {
        "status": "calculated_from_selected_official_facts",
        "latest_year": latest_year,
        "previous_year": previous_year,
        "latest_snapshot": [item for item in latest_snapshot if item],
        "yoy_pressure": [item for item in yoy_pressure if item],
        "interpretation": (
            "Company-level economics remain strong, but the latest year shows margin and profit pressure despite revenue growth."
        ),
    }


def _pdd_scale_snapshot(
    *,
    active_merchants: dict[str, Any] | None,
    transaction_revenue_per_merchant: dict[str, Any] | None,
    active_buyers: dict[str, Any] | None,
    gmv: dict[str, Any] | None,
    orders: dict[str, Any] | None,
    annual_spend: dict[str, Any] | None,
) -> list[str]:
    return [
        _operating_record_line("Active merchants", active_merchants),
        _operating_record_line(
            "Average transaction-services revenue per active merchant",
            transaction_revenue_per_merchant,
        ),
        _operating_record_line("GMV", gmv),
        _operating_record_line("Active buyers", active_buyers),
        _operating_record_line("Total orders placed", orders),
        _operating_record_line("Annual spending per active buyer", annual_spend),
    ]


def _pdd_revenue_mix_history(raw_extracted_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, dict[str, float]] = {}
    for fact in raw_extracted_facts:
        if fact.get("metric") != "revenue" or fact.get("unit") != "CNY":
            continue
        if fact.get("period_type") != "annual":
            continue
        if not fact.get("end_date"):
            continue
        value = fact.get("value")
        if value is None:
            continue
        year = int(str(fact["end_date"])[:4])
        context = str(fact.get("context_ref") or "")
        record = by_year.setdefault(year, {})
        if "OnlineMarketingServicesAndOthersMember" in context:
            record["online_marketing_services_and_others"] = float(value)
        elif "TransactionServicesMember" in context:
            record["transaction_services"] = float(value)
        elif "ProductOrServiceAxis" not in context and "MarketplaceServicesMember" not in context and "MerchandiseSalesMember" not in context:
            record["total_revenue"] = float(value)

    output = []
    for year, record in sorted(by_year.items()):
        total = record.get("total_revenue")
        online = record.get("online_marketing_services_and_others")
        transaction = record.get("transaction_services")
        output.append(
            {
                "year": year,
                "total_revenue": total,
                "online_marketing_services_and_others": online,
                "transaction_services": transaction,
                "online_marketing_share": _ratio(online, total),
                "transaction_share": _ratio(transaction, total),
            }
        )
    return output


def _format_revenue_mix_line(record: dict[str, Any]) -> str | None:
    if not record:
        return None
    year = record.get("year")
    total = _format_billion(record.get("total_revenue"))
    online = _format_billion(record.get("online_marketing_services_and_others"))
    transaction = _format_billion(record.get("transaction_services"))
    online_share = _format_pct(record.get("online_marketing_share"))
    transaction_share = _format_pct(record.get("transaction_share"))
    if not total:
        return None
    return (
        f"Revenue mix {year}: total {total}; online marketing/others {online} ({online_share}); "
        f"transaction services {transaction} ({transaction_share})"
    )


def _revenue_mix_trend_line(history: list[dict[str, Any]]) -> str | None:
    valid = [
        item
        for item in history
        if item.get("transaction_share") is not None and item.get("year") is not None
    ]
    if len(valid) < 2:
        return None
    first = valid[0]
    latest = valid[-1]
    return (
        "Transaction-services share moved from "
        f"{_format_pct(first.get('transaction_share'))} in {first.get('year')} "
        f"to {_format_pct(latest.get('transaction_share'))} in {latest.get('year')}."
    )


def _format_share_line(label: str, value: Any) -> str | None:
    formatted = _format_pct(value)
    if not formatted:
        return None
    return f"{label}: {formatted}"


def _metric_value_for_year(metrics: list[dict[str, Any]], formula_id: str, year: Any) -> float | None:
    if year is None:
        return None
    for metric in metrics:
        if metric.get("formula_id") != formula_id:
            continue
        for result in metric.get("annual_results", []):
            if result.get("year") == year and result.get("status") == "calculated":
                value = result.get("value")
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
    return None


def _annual_metric_line(
    label: str,
    value: Any,
    year: Any,
    *,
    unit: str | None = None,
    percent: bool = False,
) -> str | None:
    if value is None:
        return None
    if percent:
        formatted = _format_pct(value)
    elif unit == "RMB":
        formatted = _format_billion(value)
    else:
        try:
            formatted = f"{float(value):.2f}"
        except (TypeError, ValueError):
            return None
    if not formatted:
        return None
    return f"{label} {year}: {formatted}"


def _pct_change_line(
    label: str,
    previous: Any,
    latest: Any,
    previous_year: Any,
    latest_year: Any,
) -> str | None:
    if previous in (None, 0) or latest is None:
        return None
    try:
        change = (float(latest) - float(previous)) / abs(float(previous))
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return f"{label} {previous_year}->{latest_year}: {_format_pct(change)}"


def _margin_change_line(
    label: str,
    previous: Any,
    latest: Any,
    previous_year: Any,
    latest_year: Any,
) -> str | None:
    previous_text = _format_pct(previous)
    latest_text = _format_pct(latest)
    if not previous_text or not latest_text:
        return None
    return f"{label} {previous_year}->{latest_year}: {previous_text} to {latest_text}"


def _format_billion(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"RMB {float(value) / 1_000_000_000:.1f}B"
    except (TypeError, ValueError):
        return None


def _format_pct(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _first(items: list[str], prefix: str) -> str | None:
    for item in items:
        if item.startswith(prefix):
            return item
    return None


def _latest_operating_record(
    operating_kpi_analysis: dict[str, Any],
    metric: str,
) -> dict[str, Any] | None:
    latest = operating_kpi_analysis.get("latest_by_metric") or {}
    return latest.get(metric)


def _operating_record_line(label: str, record: dict[str, Any] | None) -> str:
    if not record:
        return f"{label}: not disclosed/extracted"
    return f"{label}: {_format_operating_record_value(record)} as of {record.get('period_end')}"


def _format_operating_record_value(record: dict[str, Any]) -> str:
    value = record.get("value")
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    unit = record.get("unit")
    if unit == "CNY":
        return f"RMB {numeric / 1_000_000_000:.1f}B"
    if unit in {"users", "merchants", "orders"}:
        if numeric >= 1_000_000_000:
            return f"{numeric / 1_000_000_000:.1f}B"
        return f"{numeric / 1_000_000:.1f}M"
    if unit in {"CNY_per_active_buyer", "CNY_per_active_merchant"}:
        return f"RMB {numeric:,.1f}"
    return f"{numeric:,.0f}"


def _unit_proxy_signal(
    *,
    name: str,
    status: str,
    value: str | None,
    interpretation: str,
    limitation: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "value": value or "not available",
        "interpretation": interpretation,
        "limitation": limitation,
    }


def _anti_moat_test(
    *,
    risk_id: str,
    risk: str,
    official_evidence: list[str],
    external_test: str,
) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "risk": risk,
        "status": "official_risk_or_limitation_identified" if official_evidence else "external_test_required",
        "official_evidence": official_evidence,
        "external_test_needed": external_test,
    }


def _business_evolution(
    *,
    company_id: str,
    earliest: dict[str, Any],
    earliest_text: str,
    latest: dict[str, Any],
    latest_text: str,
) -> list[dict[str, Any]]:
    if company_id == "pdd":
        temu_added = "Temu" in latest_text and "Temu" not in earliest_text
        return [
            {
                "claim": "PDD's official story evolved from Pinduoduo-centered domestic commerce toward Pinduoduo plus Temu global commerce.",
                "status": "supported_by_report_comparison" if temu_added else "needs_more_history_review",
                "matched_terms": _matched_terms(latest_text, ["Pinduoduo", "Temu", "platforms"]),
                "evidence": _snippets(latest_text, ["Pinduoduo", "Temu"], limit=2),
                "source_comparison": f"{earliest.get('document_id')} -> {latest.get('document_id')}",
            }
        ]
    if company_id == "tencent":
        return [
            {
                "claim": "Tencent's latest official reports present a multi-segment ecosystem model built around VAS, Marketing Services, and FinTech and Business Services.",
                "status": "supported_by_official_report",
                "matched_terms": _matched_terms(
                    latest_text,
                    ["Value-added Services", "Marketing Services", "FinTech and Business Services"],
                ),
                "evidence": _snippets(
                    latest_text,
                    ["Value-added Services", "Marketing Services", "FinTech and Business Services"],
                    limit=2,
                ),
                "source_comparison": f"{earliest.get('document_id')} -> {latest.get('document_id')}",
            }
        ]
    return [
        {
            "claim": "Business evolution needs company-specific review.",
            "status": "limited_evidence",
            "matched_terms": [],
            "evidence": [],
            "source_comparison": f"{earliest.get('document_id')} -> {latest.get('document_id')}",
        }
    ]


def _financial_signal_summary(
    extracted_facts: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = annual_fact_rows(extracted_facts)
    if not rows:
        return {
            "latest_year": None,
            "quality_support": False,
            "findings": ["No extracted annual financial rows are available yet."],
        }
    latest = rows[-1]
    revenue = latest.get("revenue")
    gross_profit = latest.get("gross_profit")
    operating_income = latest.get("operating_income")
    free_cash_flow = latest.get("free_cash_flow")
    gross_margin = gross_profit / revenue if revenue else None
    operating_margin = operating_income / revenue if revenue else None
    metric_latest = {
        metric.get("formula_id"): _latest_calculated(metric)
        for metric in metrics
    }
    roic = (metric_latest.get("unlevered_roic_v1") or {}).get("value")
    cash_conversion = (metric_latest.get("cash_conversion_ratio_v1") or {}).get("value")
    owner_earnings_yield = (metric_latest.get("true_yield_v1") or {}).get("value")
    findings = [
        _format_financial_finding("Latest revenue", revenue, suffix="RMB"),
        _format_financial_finding("Latest gross margin", gross_margin, percent=True),
        _format_financial_finding("Latest operating margin", operating_margin, percent=True),
        _format_financial_finding("Latest free cash flow", free_cash_flow, suffix="RMB"),
        _format_financial_finding("Latest cash conversion", cash_conversion),
        _format_financial_finding("Latest unlevered ROIC", roic, percent=True),
        _format_financial_finding("Latest owner earnings yield", owner_earnings_yield, percent=True),
    ]
    findings = [finding for finding in findings if finding]
    quality_support = any(
        value is not None and value > 0
        for value in [gross_margin, operating_margin, free_cash_flow, roic, cash_conversion]
    )
    return {
        "latest_year": latest.get("year"),
        "quality_support": quality_support,
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "cash_conversion": cash_conversion,
        "roic": roic,
        "owner_earnings_yield": owner_earnings_yield,
        "findings": findings,
    }


def _latest_calculated(metric: dict[str, Any]) -> dict[str, Any] | None:
    results = [
        result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
    ]
    if not results:
        return None
    return sorted(results, key=lambda result: result.get("year", 0))[-1]


def _format_financial_finding(
    label: str,
    value: Any,
    *,
    suffix: str | None = None,
    percent: bool = False,
) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if percent:
        return f"{label}: {number * 100:.1f}%"
    if suffix == "RMB":
        return f"{label}: RMB {number / 1_000_000_000:.1f}B"
    return f"{label}: {number:.2f}"


def _deep_evidence_cards(
    *,
    company_id: str,
    latest: dict[str, Any],
    latest_text: str,
    raw_extracted_facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if company_id != "pdd":
        return []

    cards = []
    for probe in PDD_DEEP_EVIDENCE_PROBES:
        snippets = _snippets(latest_text, probe["terms"], limit=3)
        matched_terms = _matched_terms(latest_text, probe["terms"])
        cards.append(
            {
                "card_id": probe["card_id"],
                "theme": probe["theme"],
                "finding": probe["finding"],
                "status": "supported_by_official_report" if matched_terms else "not_found_in_latest_report",
                "matched_terms": matched_terms,
                "evidence": snippets,
                "why_it_matters": probe["why_it_matters"],
                "limitation": probe["limitation"],
                "source_document": {
                    "document_id": latest.get("document_id"),
                    "filing_date": latest.get("filing_date"),
                    "local_path": latest.get("local_path"),
                },
            }
        )

    revenue_mix = _pdd_latest_revenue_mix(
        raw_extracted_facts,
        latest_document_id=str(latest.get("document_id") or ""),
    )
    if revenue_mix:
        cards.append(
            {
                "card_id": "pdd_revenue_mix_from_xbrl",
                "theme": "Revenue mix",
                "finding": (
                    "The latest official XBRL facts split PDD revenue between online marketing services/others "
                    "and transaction services."
                ),
                "status": "supported_by_official_xbrl",
                "matched_terms": ["OnlineMarketingServicesAndOthersMember", "TransactionServicesMember"],
                "evidence": revenue_mix,
                "why_it_matters": (
                    "Revenue mix helps test whether monetization is mainly advertising/merchant demand generation "
                    "or transaction-service monetization."
                ),
                "limitation": "This still does not show merchant profit after platform costs.",
                "source_document": {
                    "document_id": latest.get("document_id"),
                    "filing_date": latest.get("filing_date"),
                    "local_path": latest.get("local_path"),
                },
            }
        )
    return cards


def _pdd_latest_revenue_mix(
    raw_extracted_facts: list[dict[str, Any]],
    *,
    latest_document_id: str,
) -> list[str]:
    latest_year = None
    for fact in raw_extracted_facts:
        if fact.get("metric") != "revenue" or fact.get("unit") != "CNY":
            continue
        if fact.get("period_type") != "annual":
            continue
        if latest_document_id and fact.get("document_id") != latest_document_id:
            continue
        if not fact.get("end_date"):
            continue
        year = int(str(fact["end_date"])[:4])
        latest_year = year if latest_year is None else max(latest_year, year)
    if latest_year is None:
        return []

    components: dict[str, float] = {}
    total = None
    for fact in raw_extracted_facts:
        if fact.get("metric") != "revenue" or fact.get("unit") != "CNY":
            continue
        if fact.get("period_type") != "annual":
            continue
        if latest_document_id and fact.get("document_id") != latest_document_id:
            continue
        if str(fact.get("end_date", ""))[:4] != str(latest_year):
            continue
        context = str(fact.get("context_ref") or "")
        value = fact.get("value")
        if value is None:
            continue
        if "OnlineMarketingServicesAndOthersMember" in context:
            components["online marketing services and others"] = float(value)
        elif "TransactionServicesMember" in context:
            components["transaction services"] = float(value)
        elif "ProductOrServiceAxis" not in context:
            total = float(value)

    lines = []
    if total:
        lines.append(f"Total revenue {latest_year}: RMB {total / 1_000_000_000:.1f}B")
    for name, value in sorted(components.items()):
        share = f" ({value / total * 100:.1f}% of total)" if total else ""
        lines.append(f"{name}: RMB {value / 1_000_000_000:.1f}B{share}")
    return lines


def _right_business_model_checklist(
    *,
    business_claims: list[dict[str, Any]],
    moat_hypotheses: list[dict[str, Any]],
    financial_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    supported_claims = sum(
        1 for claim in business_claims if claim.get("status") == "supported_by_official_report"
    )
    supported_hypotheses = sum(
        1 for hypothesis in moat_hypotheses if hypothesis.get("status") in {"partially_supported", "official_narrative_supported"}
    )
    return [
        {
            "item": "Understandable business model",
            "status": "supported" if supported_claims else "unproven",
            "note": "Based on official-report business description only.",
        },
        {
            "item": "Durable customer value proposition",
            "status": "partially_supported" if supported_hypotheses else "unproven",
            "note": "Needs external customer evidence before final judgment.",
        },
        {
            "item": "Financial evidence of business quality",
            "status": "partially_supported" if financial_signals.get("quality_support") else "unproven",
            "note": "Based on extracted margins, cash flow, ROIC, and cash conversion where available.",
        },
        {
            "item": "Hard-to-copy moat",
            "status": "hypothesis_only" if supported_hypotheses else "unproven",
            "note": "Official reports can support a hypothesis but cannot prove competitive durability.",
        },
    ]


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _term_index(text, term) != -1]


def _snippets(text: str, terms: list[str], *, limit: int) -> list[str]:
    normalized = SPACE_PATTERN.sub(" ", text).strip()
    if not normalized:
        return []
    output = []
    for term in terms:
        index = _term_index(normalized, term)
        if index == -1:
            continue
        start = max(0, index - 110)
        end = min(len(normalized), index + len(term) + 150)
        snippet = normalized[start:end].strip()
        if start > 0:
            snippet = "... " + snippet
        if end < len(normalized):
            snippet += " ..."
        if snippet not in output:
            output.append(snippet)
        if len(output) >= limit:
            break
    return output


def _document_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        sidecar = path.with_suffix(".txt")
        if sidecar.exists():
            return SPACE_PATTERN.sub(" ", sidecar.read_text(encoding="utf-8", errors="ignore")).strip()
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError:
            return ""
        reader = PdfReader(str(path))
        return SPACE_PATTERN.sub(" ", "\n".join(page.extract_text() or "" for page in reader.pages)).strip()
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = SCRIPT_STYLE_PATTERN.sub(" ", raw)
    raw = TAG_PATTERN.sub(" ", raw)
    text = html.unescape(raw)
    return SPACE_PATTERN.sub(" ", text).strip()


def _term_counts(text: str, terms: list[str]) -> dict[str, Any]:
    counts = {
        term: len(list(_term_pattern(term).finditer(text)))
        for term in terms
    }
    matched_terms = [term for term, count in counts.items() if count > 0]
    return {
        "matched_terms": matched_terms,
        "term_counts": counts,
        "total_hits": sum(counts.values()),
    }


def _term_index(text: str, term: str) -> int:
    match = _term_pattern(term).search(text)
    return match.start() if match else -1


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", flags=re.IGNORECASE)
