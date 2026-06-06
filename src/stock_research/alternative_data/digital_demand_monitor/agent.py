"""Alternative data analyst agent.

This layer turns raw metrics/signals into research-facing answers. It is
intentionally deterministic so the same alternative-data pack produces the same
brief every time.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import to_jsonable


QuestionCard = dict[str, Any]


def load_signal_pack(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_alternative_data_brief(packs: list[dict[str, Any]], primary_brand_id: str | None = None) -> dict[str, Any]:
    if not packs:
        raise ValueError("At least one demand_signal_pack is required.")

    primary_brand_id = primary_brand_id or packs[0].get("primary_brand_id") or "temu"
    merged = _merge_packs(packs)
    metrics = merged["metrics"]
    signals = merged["signals"]
    primary_metrics = [metric for metric in metrics if metric.get("brand_id") == primary_brand_id]

    questions = [
        _demand_question(primary_metrics, signals, primary_brand_id),
        _paid_acquisition_question(metrics, primary_brand_id),
        _experience_question(primary_metrics, signals, primary_brand_id),
        _product_surface_question(primary_metrics, primary_brand_id),
        _competitive_question(metrics, signals, primary_brand_id),
    ]
    coverage = _coverage(metrics, primary_brand_id)
    watchlist = _market_watchlist(primary_metrics, signals)

    return {
        "agent_name": "alternative_data_analyst",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ticker": merged["ticker"],
        "company_name": merged["company_name"],
        "primary_brand_id": primary_brand_id,
        "source_pack_count": len(packs),
        "coverage": coverage,
        "bottom_line": _bottom_line(questions, watchlist, coverage),
        "questions": questions,
        "market_watchlist": watchlist,
        "how_to_use": [
            "Use this brief as an early-warning layer before reading filings or earnings-call transcripts.",
            "Treat one-off levels as cross-sectional evidence; require repeated runs before calling a trend.",
            "Escalate markets where app/review/ad/product signals point in the same direction.",
        ],
    }


def write_agent_outputs(output_dir: str | Path, brief: dict[str, Any]) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "alternative_data_brief.json").write_text(
        json.dumps(to_jsonable(brief), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (path / "alternative_data_brief.md").write_text(render_agent_markdown(brief), encoding="utf-8")


def render_agent_markdown(brief: dict[str, Any]) -> str:
    lines = [
        f"# {brief['ticker']} Alternative Data Analyst",
        "",
        f"- Generated at: `{brief['generated_at']}`",
        f"- Primary brand: `{brief['primary_brand_id']}`",
        f"- Source packs: `{brief['source_pack_count']}`",
        "",
        "## Bottom Line",
        "",
        brief["bottom_line"],
        "",
        "## Questions Answered",
        "",
    ]
    for question in brief["questions"]:
        lines.extend(
            [
                f"### {question['question']}",
                "",
                f"- Answer: **{question['answer']}**",
                f"- Confidence: **{question['confidence']}**",
                f"- Summary: {question['summary']}",
            ]
        )
        if question["evidence"]:
            lines.append("- Evidence:")
            for item in question["evidence"]:
                lines.append(f"  - {item}")
        if question["limitations"]:
            lines.append("- Limitations:")
            for item in question["limitations"]:
                lines.append(f"  - {item}")
        if question["follow_up"]:
            lines.append("- Follow-up:")
            for item in question["follow_up"]:
                lines.append(f"  - {item}")
        lines.append("")

    lines.extend(["## Source Coverage", ""])
    coverage = brief["coverage"]
    lines.append(f"- Metrics: `{coverage['metric_count']}`")
    lines.append(f"- Markets: `{', '.join(coverage['markets'])}`")
    lines.append("- Source types:")
    for source, count in sorted(coverage["source_type_counts"].items()):
        lines.append(f"  - `{source}`: {count}")
    lines.append("- Primary-brand source coverage:")
    for source, markets in sorted(coverage["primary_brand_markets_by_source"].items()):
        lines.append(f"  - `{source}`: {', '.join(markets)}")

    lines.extend(["", "## Market Watchlist", ""])
    if brief["market_watchlist"]:
        for item in brief["market_watchlist"]:
            lines.append(f"- `{item['market']}` {item['severity']}: {item['reason']}")
    else:
        lines.append("- No market crossed the V1 watchlist thresholds.")

    lines.extend(["", "## How To Use", ""])
    for item in brief["how_to_use"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _merge_packs(packs: list[dict[str, Any]]) -> dict[str, Any]:
    first = packs[0]
    markets: list[str] = []
    metrics: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    for pack in packs:
        for market in pack.get("markets", []):
            if market not in markets:
                markets.append(market)
        metrics.extend(pack.get("metrics", []))
        signals.extend(pack.get("signals", []))
    return {
        "ticker": first.get("ticker", "unknown"),
        "company_name": first.get("company_name", first.get("ticker", "unknown")),
        "primary_brand_id": first.get("primary_brand_id"),
        "markets": markets,
        "metrics": metrics,
        "signals": signals,
    }


def _coverage(metrics: list[dict[str, Any]], primary_brand_id: str) -> dict[str, Any]:
    source_counts = Counter(metric.get("source_type", "unknown") for metric in metrics)
    markets = sorted({metric.get("market", "unknown") for metric in metrics})
    primary_by_source: dict[str, set[str]] = defaultdict(set)
    for metric in metrics:
        if metric.get("brand_id") == primary_brand_id:
            primary_by_source[metric.get("source_type", "unknown")].add(metric.get("market", "unknown"))
    return {
        "metric_count": len(metrics),
        "markets": markets,
        "source_type_counts": dict(source_counts),
        "primary_brand_markets_by_source": {
            source: sorted(markets)
            for source, markets in primary_by_source.items()
        },
    }


def _bottom_line(questions: list[QuestionCard], watchlist: list[dict[str, str]], coverage: dict[str, Any]) -> str:
    answers = {card["question"]: card["answer"] for card in questions}
    risk_count = sum(1 for item in watchlist if item.get("severity") == "high")
    source_types = ", ".join(sorted(coverage["source_type_counts"]))
    demand = answers.get("Is demand momentum improving?", "unknown").lower()
    paid = answers.get("Is growth being bought through paid acquisition?", "unknown").lower()
    experience = answers.get("Is user experience risk rising?", "unknown").lower()
    return (
        f"The current alternative-data layer covers {source_types}. "
        f"Demand reads as {demand}; paid-acquisition intensity reads as {paid}; "
        f"user-experience risk reads as {experience}. "
        f"{risk_count} markets are high-priority review-risk watch items."
    )


def _demand_question(metrics: list[dict[str, Any]], signals: list[dict[str, Any]], primary_brand_id: str) -> QuestionCard:
    demand_signals = [signal for signal in signals if signal.get("brand_id") == primary_brand_id and signal.get("signal") in {"demand_accelerating", "demand_softening"}]
    improving_app = [m for m in metrics if m.get("source_type") == "app" and m.get("metric_name", "").endswith("_app_rank") and m.get("direction") == "improving"]
    worsening_app = [m for m in metrics if m.get("source_type") == "app" and m.get("metric_name", "").endswith("_app_rank") and m.get("direction") == "worsening"]
    review_counts = [m for m in metrics if m.get("source_type") == "app" and m.get("metric_name", "").endswith("_review_count")]
    search = [m for m in metrics if m.get("source_type") == "search" and m.get("metric_name") == "search_interest_avg"]
    web = [m for m in metrics if m.get("source_type") == "web"]

    if any(signal.get("signal") == "demand_accelerating" for signal in demand_signals):
        answer = "Improving in some markets"
    elif any(signal.get("signal") == "demand_softening" for signal in demand_signals):
        answer = "Softening in some markets"
    elif improving_app and not worsening_app:
        answer = "Stable to positive, but trend confidence is limited"
    else:
        answer = "Mixed or not enough trend evidence"

    evidence = []
    if improving_app:
        evidence.append(f"{len(improving_app)} app-rank metrics are improving.")
    if worsening_app:
        evidence.append(f"{len(worsening_app)} app-rank metrics are worsening.")
    if review_counts:
        max_review_count = max((m.get("current_value") or 0 for m in review_counts), default=0)
        evidence.append(f"Highest observed app review count is {max_review_count:,.0f}.")
    if search:
        evidence.append(f"Search interest metrics are available for {len({m['market'] for m in search})} markets.")
    if web:
        evidence.append(f"Web/domain-rank proxy metrics are available for {len({m['market'] for m in web})} markets.")

    return _card(
        "Is demand momentum improving?",
        answer,
        "App rank/review counts are the main live demand proxy; search and web are confirmation layers when present.",
        _confidence([improving_app, worsening_app, review_counts, search, web]),
        evidence,
        _missing(["search", "web"], metrics),
        ["Run repeated weekly snapshots so rank/review_count levels become real trends."],
    )


def _paid_acquisition_question(metrics: list[dict[str, Any]], primary_brand_id: str) -> QuestionCard:
    ad_metrics = [m for m in metrics if m.get("source_type") == "ad" and m.get("metric_name", "").endswith("ad_count_lower_bound")]
    primary_ads = [m for m in ad_metrics if m.get("brand_id") == primary_brand_id and m.get("current_value") is not None]
    competitor_ads = [m for m in ad_metrics if m.get("brand_id") != primary_brand_id and m.get("current_value") is not None]

    strong_markets: list[str] = []
    for metric in primary_ads:
        market = metric.get("market")
        peers = [m for m in competitor_ads if m.get("market") == market]
        peer_max = max((m.get("current_value") or 0 for m in peers), default=0)
        if (metric.get("current_value") or 0) >= max(peer_max * 2, 50_000):
            strong_markets.append(str(market))

    if len(strong_markets) >= 3:
        answer = "Yes, paid acquisition is very prominent"
    elif strong_markets:
        answer = "Prominent in selected markets"
    elif primary_ads:
        answer = "Present but not clearly dominant"
    else:
        answer = "Not available"

    top_primary = sorted(primary_ads, key=lambda m: m.get("current_value") or 0, reverse=True)[:5]
    evidence = [
        f"{m['market']}: {m.get('current_value'):,.0f} {m.get('metric_name')}"
        for m in top_primary
    ]
    if strong_markets:
        evidence.append(f"Temu ad count is materially above peers in: {', '.join(sorted(set(strong_markets)))}.")

    return _card(
        "Is growth being bought through paid acquisition?",
        answer,
        "Ad transparency data helps separate organic demand from acquisition-heavy growth.",
        "high" if len(primary_ads) >= 5 else ("medium" if primary_ads else "low"),
        evidence,
        _missing(["ad"], metrics),
        ["Build a time series; current ad libraries are point-in-time snapshots, not spend estimates."],
    )


def _experience_question(metrics: list[dict[str, Any]], signals: list[dict[str, Any]], primary_brand_id: str) -> QuestionCard:
    negative = [
        m for m in metrics
        if m.get("brand_id") == primary_brand_id and m.get("metric_name") == "negative_review_share" and m.get("current_value") is not None
    ]
    high_markets = [m for m in negative if (m.get("current_value") or 0) >= 0.45]
    medium_markets = [m for m in negative if 0.35 <= (m.get("current_value") or 0) < 0.45]
    risk_signals = [s for s in signals if s.get("brand_id") == primary_brand_id and s.get("signal") == "experience_risk_rising"]

    if high_markets:
        answer = "Yes, elevated in several markets"
    elif medium_markets or risk_signals:
        answer = "Some elevation"
    elif negative:
        answer = "Contained in available review data"
    else:
        answer = "Not available"

    top_topics = _top_review_topics(metrics, primary_brand_id)
    evidence = [
        f"{m['market']}: negative review share {m.get('current_value'):.2f}"
        for m in sorted(high_markets + medium_markets, key=lambda x: x.get("current_value") or 0, reverse=True)[:8]
    ]
    if top_topics:
        evidence.append("Top negative topics: " + ", ".join(top_topics))

    return _card(
        "Is user experience risk rising?",
        answer,
        "Review text and app ratings are best for detecting trust, delivery, app-bug, return/refund, and promo-friction risks.",
        "high" if len(negative) >= 8 else ("medium" if negative else "low"),
        evidence,
        _missing(["review"], metrics),
        ["Improve non-English topic classification before over-reading country-level topic mix."],
    )


def _product_surface_question(metrics: list[dict[str, Any]], primary_brand_id: str) -> QuestionCard:
    surface = [
        m for m in metrics
        if m.get("brand_id") == primary_brand_id and m.get("metric_name", "").startswith("product_surface_")
    ]
    by_name = {m["metric_name"]: m for m in surface}
    card_count = _value(by_name, "product_surface_card_count")
    priced_count = _value(by_name, "product_surface_priced_card_count")
    median_price = _value(by_name, "product_surface_median_price")
    discount = _value(by_name, "product_surface_median_discount_pct")
    coupon_rate = _value(by_name, "product_surface_coupon_card_rate")

    if surface:
        answer = "Yes, for visible landing-page product mix"
    else:
        answer = "Not available"

    evidence = []
    if card_count is not None:
        evidence.append(f"Visible product cards: {card_count:.0f}.")
    if priced_count is not None:
        evidence.append(f"Priced product cards: {priced_count:.0f}.")
    if median_price is not None:
        evidence.append(f"Median visible price: {median_price:.2f}.")
    if discount is not None:
        evidence.append(f"Median visible discount: {discount:.2f}%.")
    if coupon_rate is not None:
        evidence.append(f"Coupon-card rate: {coupon_rate:.2f}.")

    limitations = _missing(["product"], metrics)
    if priced_count is not None and card_count is not None and card_count > 0 and priced_count / card_count < 0.5:
        limitations.append("Only a minority of visible product cards carried parseable prices in this run.")

    return _card(
        "What is Temu pushing on its product surface?",
        answer,
        "Product-surface data answers what the ad/landing page is actually merchandising: price band, discount level, and promo cues.",
        "medium" if surface else "low",
        evidence,
        limitations,
        ["Track multiple landing URLs per market before treating this as the whole Temu assortment."],
    )


def _competitive_question(metrics: list[dict[str, Any]], signals: list[dict[str, Any]], primary_brand_id: str) -> QuestionCard:
    competitive_signals = [
        signal for signal in signals
        if signal.get("brand_id") == primary_brand_id and signal.get("signal", "").startswith("competitive_position_")
    ]
    ad_metrics = [m for m in metrics if m.get("source_type") == "ad" and m.get("metric_name", "").endswith("ad_count_lower_bound")]
    search_metrics = [m for m in metrics if m.get("metric_name") == "relative_search_share_vs_competitors"]

    if any(s.get("signal") == "competitive_position_improving" for s in competitive_signals):
        answer = "Improving where search-share data is available"
    elif any(s.get("signal") == "competitive_position_weakening" for s in competitive_signals):
        answer = "Weakening where search-share data is available"
    elif ad_metrics:
        answer = "Temu is highly visible in paid channels, but organic share is unclear"
    else:
        answer = "Not enough competitor data"

    evidence = []
    if search_metrics:
        evidence.append(f"Relative-search metrics available for {len(search_metrics)} markets.")
    if ad_metrics:
        brands = sorted({m.get("brand_id") for m in ad_metrics if m.get("brand_id") != primary_brand_id})
        evidence.append("Paid-ad competitor set includes: " + ", ".join(brand for brand in brands if brand))

    return _card(
        "How does Temu look versus competitors?",
        answer,
        "Competitor baselines stop us from confusing category-wide movement with Temu-specific movement.",
        "medium" if (search_metrics or ad_metrics) else "low",
        evidence,
        _missing(["search", "ad"], metrics),
        ["Keep SHEIN and AliExpress as the core cross-border baseline; treat Amazon/Walmart as broad retail baselines."],
    )


def _market_watchlist(metrics: list[dict[str, Any]], signals: list[dict[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for signal in signals:
        if signal.get("signal") == "experience_risk_rising" and signal.get("severity") in {"high", "medium"}:
            output.append(
                {
                    "market": signal.get("market", "unknown"),
                    "severity": signal.get("severity", "medium"),
                    "reason": signal.get("summary", "Experience risk signal"),
                }
            )
    for metric in metrics:
        if metric.get("metric_name") == "negative_review_share" and (metric.get("current_value") or 0) >= 0.5:
            market = metric.get("market", "unknown")
            if not any(item["market"] == market for item in output):
                output.append(
                    {
                        "market": market,
                        "severity": "high",
                        "reason": f"Negative review share is {metric.get('current_value'):.2f}.",
                    }
                )
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(output, key=lambda item: (severity_rank.get(item["severity"], 9), item["market"]))[:12]


def _top_review_topics(metrics: list[dict[str, Any]], primary_brand_id: str) -> list[str]:
    topics: Counter[str] = Counter()
    for metric in metrics:
        name = metric.get("metric_name", "")
        if metric.get("brand_id") == primary_brand_id and name.startswith("negative_review_topic_share:"):
            topic = name.removeprefix("negative_review_topic_share:")
            topics[topic] += metric.get("current_value") or 0
    return [topic for topic, _value in topics.most_common(5)]


def _card(
    question: str,
    answer: str,
    summary: str,
    confidence: str,
    evidence: list[str],
    limitations: list[str],
    follow_up: list[str],
) -> QuestionCard:
    return {
        "question": question,
        "answer": answer,
        "summary": summary,
        "confidence": confidence,
        "evidence": evidence,
        "limitations": limitations,
        "follow_up": follow_up,
    }


def _confidence(groups: list[list[Any]]) -> str:
    active = sum(1 for group in groups if group)
    if active >= 4:
        return "high"
    if active >= 2:
        return "medium"
    return "low"


def _missing(expected_sources: list[str], metrics: list[dict[str, Any]]) -> list[str]:
    available = {metric.get("source_type") for metric in metrics}
    return [f"No {source} metrics available in the supplied pack." for source in expected_sources if source not in available]


def _value(by_name: dict[str, dict[str, Any]], name: str) -> float | None:
    metric = by_name.get(name)
    value = metric.get("current_value") if metric else None
    return float(value) if value is not None else None
