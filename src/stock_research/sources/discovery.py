from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from stock_research.sources.document_policy import (
    FINANCIAL_EXTRACTION_CATEGORIES,
    classify_sec_document_record,
)
from stock_research.sources.pdd_ir import PddIrClient
from stock_research.sources.sec import SecClient
from stock_research.sources.tencent_ir import TencentIrClient


def discover_pdd_sources(
    *,
    cache_root: str | Path = "data/raw",
    download_reports: bool = True,
) -> dict[str, Any]:
    cache_root = Path(cache_root)
    sec = SecClient(cache_dir=cache_root / "sec")
    pdd_ir = PddIrClient(cache_dir=cache_root / "pdd_ir")

    sec_result = sec.discover_company_filings("PDD")
    filings = sec_result["filings"]
    annual_filings = sorted(
        [filing for filing in filings if filing["form"] in {"20-F", "20-F/A"}],
        key=lambda filing: (filing["download_priority"], filing.get("filing_date") or ""),
    )
    six_k_filings = sorted(
        [filing for filing in filings if filing["form"] in {"6-K", "6-K/A"}],
        key=lambda filing: filing.get("filing_date") or "",
        reverse=True,
    )
    deep_research_filings = sorted(
        [
            filing
            for filing in filings
            if sec.is_deep_research_filing(filing)
            and filing["form"] not in {"20-F", "20-F/A", "6-K", "6-K/A"}
        ],
        key=lambda filing: (filing["download_priority"], filing.get("filing_date") or ""),
    )

    downloaded = []
    download_errors = []
    if download_reports:
        for filing in annual_filings:
            try:
                downloaded.append(sec.download_filing(filing))
            except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
                download_errors.append(
                    {
                        "accession_number": filing.get("accession_number"),
                        "form": filing.get("form"),
                        "url": filing.get("archive_url"),
                        "error": str(exc),
                    }
                )
        for filing in six_k_filings:
            try:
                downloaded.extend(sec.download_6k_if_research_relevant(filing))
            except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
                download_errors.append(
                    {
                        "accession_number": filing.get("accession_number"),
                        "form": filing.get("form"),
                        "url": filing.get("archive_url"),
                        "error": str(exc),
                    }
                )
        for filing in deep_research_filings:
            try:
                downloaded.extend(sec.download_deep_research_filing(filing))
            except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
                download_errors.append(
                    {
                        "accession_number": filing.get("accession_number"),
                        "form": filing.get("form"),
                        "url": filing.get("archive_url"),
                        "error": str(exc),
                    }
                )

    ir_metadata = None
    ir_error = None
    ir_latest_financial_release = None
    ir_latest_financial_release_error = None
    try:
        ir_metadata = pdd_ir.fetch_home()
    except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
        ir_error = str(exc)
    try:
        ir_latest_financial_release = pdd_ir.fetch_latest_financial_results_release()
        if ir_latest_financial_release:
            downloaded.append(ir_latest_financial_release)
    except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
        ir_latest_financial_release_error = str(exc)

    category_counts = Counter()
    downloaded_financial_documents = []
    for document in downloaded:
        category = classify_sec_document_record(document)["category"]
        category_counts[category] += 1
        if category in FINANCIAL_EXTRACTION_CATEGORIES:
            downloaded_financial_documents.append(document)

    return {
        "sec_identity": sec_result["identity"],
        "sec_filings": filings,
        "financial_filings": annual_filings + downloaded_financial_documents,
        "annual_filings": annual_filings,
        "six_k_filings_indexed": six_k_filings,
        "deep_research_filings": deep_research_filings,
        "downloaded_financial_documents": downloaded_financial_documents,
        "downloaded_documents": downloaded,
        "downloaded_document_category_counts": dict(sorted(category_counts.items())),
        "download_errors": download_errors,
        "pdd_ir": ir_metadata,
        "pdd_ir_error": ir_error,
        "pdd_ir_latest_financial_release": ir_latest_financial_release,
        "pdd_ir_latest_financial_release_error": ir_latest_financial_release_error,
    }


def discover_tencent_sources(
    *,
    cache_root: str | Path = "data/raw",
    download_reports: bool = True,
) -> dict[str, Any]:
    cache_root = Path(cache_root)
    tencent_ir = TencentIrClient(cache_dir=cache_root / "tencent_ir")

    downloaded = []
    download_errors = []
    ir_metadata = None
    ir_error = None
    try:
        if download_reports:
            result = tencent_ir.download_financial_reports()
            ir_metadata = {
                key: value
                for key, value in result.items()
                if key not in {"downloaded_documents", "download_errors"}
            }
            downloaded = result.get("downloaded_documents", [])
            download_errors = result.get("download_errors", [])
        else:
            ir_metadata = tencent_ir.fetch_financial_reports_index()
    except Exception as exc:  # noqa: BLE001 - recorded in run artifacts for audit.
        ir_error = str(exc)

    annual_reports = [
        document for document in downloaded if document.get("report_kind") == "annual"
    ]
    interim_reports = [
        document for document in downloaded if document.get("report_kind") == "interim"
    ]
    return {
        "tencent_ir": ir_metadata,
        "tencent_ir_error": ir_error,
        "downloaded_documents": downloaded,
        "download_errors": download_errors,
        "annual_reports": annual_reports,
        "interim_reports": interim_reports,
        "financial_reports_indexed": len((ir_metadata or {}).get("financial_reports", [])),
    }
