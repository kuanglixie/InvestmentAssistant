"""Merchant and regulatory alternative-data monitor."""

from .models import MerchantRegulatoryEvent, MerchantRegulatorySummary
from .normalizer import (
    build_summary,
    classify_topics,
    normalize_cpsc_recalls,
    normalize_text_record,
)

__all__ = [
    "MerchantRegulatoryEvent",
    "MerchantRegulatorySummary",
    "build_summary",
    "classify_topics",
    "normalize_cpsc_recalls",
    "normalize_text_record",
]
