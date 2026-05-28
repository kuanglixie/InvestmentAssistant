from __future__ import annotations


SOURCE_RELIABILITY = {
    "official_app_store": "high",
    "google_trends": "medium",
    "youtube": "medium",
    "reddit": "medium",
    "forum": "low",
    "ecommerce_crawler": "medium",
    "manual_observation": "low",
}


def score_confidence(
    *,
    source: str,
    sample_size: int = 1,
    completeness: float = 1.0,
    missing_data_rate: float = 0.0,
    duplicate_rate: float = 0.0,
) -> str:
    score = {"high": 3, "medium": 2, "low": 1}.get(SOURCE_RELIABILITY.get(source, "low"), 1)
    if sample_size < 5:
        score -= 1
    if completeness < 0.8 or missing_data_rate > 0.2:
        score -= 1
    if duplicate_rate > 0.2:
        score -= 1
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"
